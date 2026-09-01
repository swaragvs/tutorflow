"""Authentication API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.deps import CurrentUser, get_current_user, get_token_from_header
from app.models import User, RoleEnum

router = APIRouter(prefix="/auth", tags=["auth"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class RegisterTutorRequest(BaseModel):
    """Request body for tutor registration."""
    
    email: EmailStr = Field(..., description="Email address for the tutor account")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")


class LoginRequest(BaseModel):
    """Request body for login."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response containing JWT access token."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserResponse(BaseModel):
    """Response containing user information."""
    
    id: str = Field(..., description="User ID (UUID)")
    email: str = Field(..., description="User email address")
    role: str = Field(..., description="User role (TUTOR or STUDENT)")
    
    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/register-tutor", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_tutor(request: RegisterTutorRequest, db: Session = Depends(get_db)):
    """
    Register a new tutor account.
    
    Args:
        request: Registration details (email, password)
        db: Database session
        
    Returns:
        Created user details
        
    Raises:
        HTTPException 400: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new tutor user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        role=RoleEnum.TUTOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.
    
    Args:
        request: Login credentials (email, password)
        db: Database session
        
    Returns:
        Access token with 24-hour expiry
        
    Raises:
        HTTPException 401: If email not found or password incorrect
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get current authenticated user's information.
    
    Args:
        current_user: Current user from JWT token (injected by dependency)
        
    Returns:
        Current user's id, email, and role
    """
    return UserResponse(
        id=str(current_user.user_id),
        email=current_user.email,
        role=current_user.role.value,
    )
