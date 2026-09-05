"""Students API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.deps import get_current_user, CurrentUser
from app.models import User, StudentProfile, RoleEnum
from app.schemas.student import StudentCreateRequest, StudentUpdateRequest, StudentResponse, StudentDetailResponse

router = APIRouter(prefix="/students", tags=["students"])


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(
    request: StudentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new student (tutor-only).
    
    A tutor creates a student account and links it to themselves.
    The request body contains the student's initial credentials and preferences.
    
    Args:
        request: StudentCreateRequest with email, password, preferences
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        Created StudentProfile
        
    Raises:
        HTTPException 403: If current user is not a TUTOR
        HTTPException 400: If email already registered
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can create students",
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create student user account
    student_user = User(
        name=request.name or "Student",
        email=request.email,
        password_hash=hash_password(request.initial_password),
        role=RoleEnum.STUDENT,
    )
    db.add(student_user)
    db.flush()  # Flush to get the user ID before creating profile
    
    # Create student profile linked to this tutor
    student_profile = StudentProfile(
        user_id=student_user.id,
        tutor_id=current_user.user_id,
        learning_goals=request.learning_goals,
        skill_level=request.skill_level,
        preferences=request.preferences,
    )
    db.add(student_profile)
    db.commit()
    db.refresh(student_profile)
    
    return student_profile


@router.get("", response_model=list[StudentResponse])
async def list_students(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all students belonging to the current tutor (tutor-only).
    
    Args:
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        List of StudentProfile belonging to the current tutor
        
    Raises:
        HTTPException 403: If current user is not a TUTOR
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can view students",
        )
    
    # Get all students for this tutor
    students = (
        db.query(StudentProfile)
        .filter(StudentProfile.tutor_id == current_user.user_id)
        .all()
    )
    
    return students


@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific student's profile (tutor-only).
    
    Only the student's tutor can view their profile.
    
    Args:
        student_id: ID of the student to retrieve
        current_user: Current authenticated user (must be TUTOR)
        db: Database session
        
    Returns:
        StudentProfile with email
        
    Raises:
        HTTPException 403: If current user is not a TUTOR
        HTTPException 404: If student doesn't exist or doesn't belong to this tutor
    """
    # Check if current user is a tutor
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can view student details",
        )
    
    # Get student profile
    student_profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.id == student_id,
            StudentProfile.tutor_id == current_user.user_id,
        )
        .first()
    )
    
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    
    # Load email from the related user
    student_user = db.query(User).filter(User.id == student_profile.user_id).first()
    
    response = StudentDetailResponse(
        id=student_profile.id,
        user_id=student_profile.user_id,
        tutor_id=student_profile.tutor_id,
        name=student_user.name if student_user else None,
        learning_goals=student_profile.learning_goals,
        skill_level=student_profile.skill_level,
        preferences=student_profile.preferences,
        created_at=student_profile.created_at,
        email=student_user.email if student_user else None,
    )
    
    return response


@router.patch("/{student_id}", response_model=StudentDetailResponse)
async def update_student(
    student_id: UUID,
    request: StudentUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a student's own profile fields (tutor-only)."""
    if current_user.role != RoleEnum.TUTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only tutors can update student details",
        )

    student_profile = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.id == student_id,
            StudentProfile.tutor_id == current_user.user_id,
        )
        .first()
    )
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    student_user = db.query(User).filter(User.id == student_profile.user_id).first()
    if student_user and request.name is not None:
        student_user.name = request.name.strip() or student_user.name

    if request.learning_goals is not None:
        student_profile.learning_goals = request.learning_goals
    if request.skill_level is not None:
        student_profile.skill_level = request.skill_level
    if request.preferences is not None:
        student_profile.preferences = request.preferences

    db.commit()
    db.refresh(student_profile)
    if student_user:
        db.refresh(student_user)

    return StudentDetailResponse(
        id=student_profile.id,
        user_id=student_profile.user_id,
        tutor_id=student_profile.tutor_id,
        name=student_user.name if student_user else None,
        learning_goals=student_profile.learning_goals,
        skill_level=student_profile.skill_level,
        preferences=student_profile.preferences,
        created_at=student_profile.created_at,
        email=student_user.email if student_user else None,
    )
