"""FastAPI dependency functions for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, RoleEnum


class CurrentUser:
    """Represents the currently authenticated user."""
    
    def __init__(self, user_id: UUID, name: str, email: str, role: RoleEnum):
        self.user_id = user_id
        self.id = user_id  # Alias for convenience
        self.name = name
        self.email = email
        self.role = role


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """
    Dependency that decodes JWT and returns the current authenticated user.
    
    Extracts the token from the Authorization header (Bearer <token>),
    decodes it, and loads the user from the database.
    
    Args:
        authorization: Authorization header value (Bearer <token>)
        db: Database session
        
    Returns:
        CurrentUser object with user_id, email, role
        
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        HTTPException 404: If user not found in database
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    role = payload.get("role")
    
    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Load user from database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return CurrentUser(user_id=user.id, name=user.name, email=user.email, role=user.role)


def require_role(required_role: RoleEnum):
    """
    Factory function that creates a dependency for role-based access control.
    
    Usage:
        @router.get("/tutor-only")
        async def tutor_endpoint(current_user: CurrentUser = Depends(require_role(RoleEnum.TUTOR))):
            ...
    
    Args:
        required_role: The role required to access this endpoint
        
    Returns:
        A dependency function that checks the current user's role
        
    Raises:
        HTTPException 403: If user's role does not match the required role
    """
    async def check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_role.value} role",
            )
        return current_user
    
    return check_role


def get_token_from_header(authorization: Optional[str] = None) -> Optional[str]:
    """
    Extract JWT token from Authorization header (Bearer scheme).
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Token string or None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]
