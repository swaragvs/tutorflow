"""User model for tutors and students."""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class RoleEnum(PyEnum):
    """Enumeration for user roles."""
    TUTOR = "TUTOR"
    STUDENT = "STUDENT"


class User(Base):
    """User model representing tutors and students."""

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(
        Enum(RoleEnum, native_enum=True, name="role_enum"),
        nullable=False,
    )
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
