"""Sessions API endpoints with overlap prevention."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models import Session as SessionModel, StudentProfile, RoleEnum
from app.schemas.session import SessionCreateRequest, SessionResponse

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
