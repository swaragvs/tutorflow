"""User model for tutors and students."""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

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
    name = Column(String(255), nullable=False, default="Unknown", server_default="Unknown")
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(
        Enum(RoleEnum, native_enum=True, name="role_enum"),
        nullable=False,
    )
    created_at = Column(DateTime, default=func.now(), nullable=False)

    student_profiles = relationship("StudentProfile", foreign_keys="[StudentProfile.user_id]", back_populates="user")
    tutor_students = relationship("StudentProfile", foreign_keys="[StudentProfile.tutor_id]", back_populates="tutor")
    tutor_sessions = relationship("Session", foreign_keys="[Session.tutor_id]", back_populates="tutor")
    student_sessions = relationship("Session", foreign_keys="[Session.student_id]", back_populates="student")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email}, role={self.role})>"
