"""Sessions API endpoints with overlap prevention."""

import json
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models import Session as SessionModel, StudentProfile, RoleEnum, SessionStatusEnum, User
from app.schemas.session import (
    SessionCreateRequest,
    SessionResponse,
    SessionStartRequest,
    SessionRescheduleRequest,
    SessionCompleteRequest,
    SessionNotesRequest,
    SessionAIPlanRequest,
)
from app.services.session_state import (
    transition_session,
    assert_session_not_locked,
    InvalidTransitionError,
    SessionLockedError,
)
from app.services.ai import (
    generate_session_plan,
    generate_session_summary,
    AIServiceError,
    AIServiceRateLimitError,
    AIServiceTimeoutError,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def check_session_overlap(
    tutor_id: UUID,
    start_time,
    end_time,
    db: Session,
    exclude_session_id: UUID = None,
):
    """
    Check if a new session overlaps with existing sessions for a tutor.
    
    Overlap condition: new.start_time < existing.end_time AND new.end_time > existing.start_time
    
    Args:
        tutor_id: ID of the tutor
        start_time: Session start time
        end_time: Session end time
        db: Database session
        exclude_session_id: Optional session ID to exclude from check (for updates)
        
    Returns:
        Overlapping SessionModel if found, None otherwise
    """
    query = db.query(SessionModel).filter(
        SessionModel.tutor_id == tutor_id,
        SessionModel.start_time < end_time,
        SessionModel.end_time > start_time,
    )
    
    if exclude_session_id:
        query = query.filter(SessionModel.id != exclude_session_id)
    
    return query.first()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    request: SessionCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new session (tutor-only).
    
    Before inserting, checks that:
    1. The student belongs to the current tutor
    2. No overlapping sessions exist for this tutor
    
    Args:
        request: SessionCreateRequest with student_id, start_time, end_time
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Created Session
        
    Raises:
        HTTPException 403: If current user is not a TUTOR
        HTTPException 404: If student doesn't belong to this tutor
        HTTPException 409: If session overlaps with existing tutor session
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can create sessions",
        )
    
    # Verify student exists and belongs to this tutor
    student_profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id == request.student_id,
            StudentProfile.tutor_id == current_user.user_id,
        )
        .first()
    )
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or does not belong to your roster",
        )
    
    # Check for overlapping sessions
    conflicting_session = check_session_overlap(
        current_user.user_id,
        request.start_time,
        request.end_time,
        db,
    )
    
    if conflicting_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session conflicts with existing booking from {conflicting_session.start_time} to {conflicting_session.end_time}",
        )
    
    # Create session
    session = SessionModel(
        tutor_id=current_user.user_id,
        student_id=request.student_id,
        start_time=request.start_time,
        end_time=request.end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List sessions (tutor sees all their sessions, student sees only their own).
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of Session objects filtered by role and ownership
    """
    if current_user.role == RoleEnum.TUTOR:
        # Tutors see all sessions where they are the tutor
        sessions = (
            db.query(SessionModel)
            .filter(SessionModel.tutor_id == current_user.user_id)
            .all()
        )
    else:
        # Students see only sessions where they are the student
        sessions = (
            db.query(SessionModel)
            .filter(SessionModel.student_id == current_user.user_id)
            .all()
        )
    
    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific session (must be owner).
    
    Args:
        session_id: ID of the session
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Session if current user owns it
        
    Raises:
        HTTPException 404: If session doesn't exist or current user doesn't own it
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Check authorization
    if current_user.role == RoleEnum.TUTOR:
        if session.tutor_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        # Student can only view their own sessions
        if session.student_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    
    return session


@router.patch("/{session_id}/start", response_model=SessionResponse)
async def start_session(
    session_id: UUID,
    request: SessionStartRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a session (transition SCHEDULED → IN_PROGRESS).
    
    Only tutor who owns the session can start it.
    
    Args:
        session_id: ID of the session
        request: StartRequest (no body)
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Updated Session
        
    Raises:
        HTTPException 403: If not tutor
        HTTPException 404: If session not found or not owned
        HTTPException 409: If transition is illegal
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can start sessions",
        )
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.status != SessionStatusEnum.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start session in {session.status.value} state. Only SCHEDULED sessions can be started.",
        )
    
    earliest_allowed = session.start_time - timedelta(minutes=settings.SESSION_START_WINDOW_MINUTES)
    if datetime.utcnow() < earliest_allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Earliest allowed start time is {earliest_allowed.strftime('%Y-%m-%d %H:%M:%S')}. "
                "The session is not yet open for start."
            ),
        )

    # Attempt transition
    try:
        transition_session(session, "start")
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {e.current_status} to IN_PROGRESS via start",
        )
    
    db.commit()
    db.refresh(session)
    
    return session


@router.patch("/{session_id}/reschedule", response_model=SessionResponse)
async def reschedule_session(
    session_id: UUID,
    request: SessionRescheduleRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reschedule a scheduled session for its tutor."""
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can reschedule sessions",
        )

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.status != SessionStatusEnum.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reschedule a session in {session.status.value} state. Only SCHEDULED sessions can be rescheduled.",
        )

    conflicting_session = check_session_overlap(
        current_user.user_id,
        request.start_time,
        request.end_time,
        db,
        exclude_session_id=session.id,
    )
    if conflicting_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session conflicts with existing booking from {conflicting_session.start_time} to {conflicting_session.end_time}",
        )

    session.start_time = request.start_time
    session.end_time = request.end_time
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", response_model=dict)
async def delete_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hard-delete a scheduled session for its tutor."""
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can delete sessions",
        )

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if session.status != SessionStatusEnum.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete a session in {session.status.value} state. Only SCHEDULED sessions can be deleted.",
        )

    db.delete(session)
    db.commit()
    return {"detail": "Session deleted"}


@router.patch("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: UUID,
    request: SessionCompleteRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Complete a session (transition IN_PROGRESS → COMPLETED).
    
    Requires both notes and homework to be non-empty.
    Only tutor who owns the session can complete it.
    
    Args:
        session_id: ID of the session
        request: CompleteRequest with notes and homework
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Updated Session
        
    Raises:
        HTTPException 403: If not tutor
        HTTPException 404: If session not found or not owned
        HTTPException 409: If transition is illegal
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can complete sessions",
        )
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Set notes and homework
    session.notes = request.notes
    session.homework = request.homework
    
    # Attempt transition
    try:
        transition_session(session, "complete")
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {e.current_status} to COMPLETED via complete",
        )
    
    db.commit()
    db.refresh(session)
    
    return session


@router.patch("/{session_id}/notes", response_model=SessionResponse)
async def update_session_notes(
    session_id: UUID,
    request: SessionNotesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update session notes (only allowed while IN_PROGRESS).
    
    Only tutor who owns the session can update notes.
    
    Args:
        session_id: ID of the session
        request: NotesRequest with notes
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Updated Session
        
    Raises:
        HTTPException 403: If not tutor
        HTTPException 404: If session not found or not owned
        HTTPException 409: If session is not IN_PROGRESS
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can update session notes",
        )
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Check if session is locked
    try:
        assert_session_not_locked(session)
    except SessionLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is locked in {e.current_status} state. Cannot update notes.",
        )
    
    # Can only update notes while IN_PROGRESS
    from app.models import SessionStatusEnum
    if session.status != SessionStatusEnum.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update notes while session is {session.status.value}. Notes can only be updated while IN_PROGRESS.",
        )
    
    session.notes = request.notes
    
    db.commit()
    db.refresh(session)
    
    return session


@router.patch("/{session_id}/trigger-ai-review", response_model=SessionResponse)
async def trigger_ai_review(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger AI review of a completed session (COMPLETED → AI_REVIEWED).
    
    Calls the AI service to generate a structured summary from session notes,
    stores the result in ai_summary, and transitions the session to AI_REVIEWED.
    
    Args:
        session_id: ID of the session
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Updated Session with ai_summary populated and status AI_REVIEWED
        
    Raises:
        HTTPException 403: If not tutor
        HTTPException 404: If session not found or not owned
        HTTPException 409: If session is not COMPLETED
        HTTPException 502: If AI service fails
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can trigger AI review",
        )
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Check session status is COMPLETED
    if session.status != SessionStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot trigger AI review for session in {session.status.value} state. Session must be COMPLETED.",
        )
    
    # Get student profile
    student_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == session.student_id)
        .first()
    )
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )
    
    # Call AI service to generate summary
    try:
        summary_result = generate_session_summary(student_profile, session)
        # Store as JSON string
        session.ai_summary = json.dumps(summary_result)
    except (AIServiceRateLimitError, AIServiceTimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service temporarily unavailable: {str(e)}",
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )
    
    # Attempt transition
    try:
        transition_session(session, "trigger_ai_review")
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from {e.current_status} to AI_REVIEWED via trigger_ai_review",
        )
    
    db.commit()
    db.refresh(session)
    
    return session


@router.post("/{session_id}/ai-plan", response_model=SessionResponse)
async def generate_ai_plan(
    session_id: UUID,
    request: SessionAIPlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate an AI plan for a session (tutor-only, SCHEDULED only).
    
    Fetches the student's profile and prior session (if any), sends to Gemini,
    stores the result in ai_plan, and returns the session.
    
    Args:
        session_id: ID of the session
        request: GenerateAIPlanRequest with optional duration_minutes
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Updated Session with ai_plan populated
        
    Raises:
        HTTPException 403: If not tutor
        HTTPException 404: If session not found or not owned
        HTTPException 409: If session is not SCHEDULED
        HTTPException 502: If AI service fails
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can generate AI plans",
        )
    
    # Get session
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session or session.tutor_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    # Check session status is SCHEDULED
    if session.status != SessionStatusEnum.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate AI plan for session in {session.status.value} state. Session must be SCHEDULED.",
        )
    
    # Get student profile
    student_profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == session.student_id)
        .first()
    )
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )
    
    # Get most recent COMPLETED-or-later session for this student
    previous_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.student_id == session.student_id,
            SessionModel.id != session.id,
            SessionModel.status.in_([SessionStatusEnum.COMPLETED, SessionStatusEnum.AI_REVIEWED]),
        )
        .order_by(SessionModel.end_time.desc())
        .first()
    )
    
    # Calculate duration if not provided
    duration_minutes = request.duration_minutes
    if not duration_minutes and session.start_time and session.end_time:
        duration_minutes = int((session.end_time - session.start_time).total_seconds() / 60)
    
    # Call AI service to generate plan
    try:
        plan_result = generate_session_plan(student_profile, previous_session, duration_minutes)
        # Store as JSON string
        session.ai_plan = json.dumps(plan_result)
    except (AIServiceRateLimitError, AIServiceTimeoutError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service temporarily unavailable: {str(e)}",
        )
    except AIServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )
    
    db.commit()
    db.refresh(session)
    
    return session
