"""Session model for tutoring sessions."""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class SessionStatusEnum(PyEnum):
    """Enumeration for session statuses."""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    AI_REVIEWED = "AI_REVIEWED"


class Session(Base):
    """Session model representing a tutoring session."""

    __tablename__ = "sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    tutor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(
        Enum(SessionStatusEnum, native_enum=True, name="session_status_enum"),
        nullable=False,
        default=SessionStatusEnum.SCHEDULED,
    )
    notes = Column(Text, nullable=True)
    homework = Column(Text, nullable=True)
    ai_plan = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tutor = relationship("User", foreign_keys=[tutor_id], back_populates="tutor_sessions")
    student = relationship("User", foreign_keys=[student_id], back_populates="student_sessions")

    @property
    def student_name(self):
        return self.student.name if self.student else None

    @property
    def tutor_name(self):
        return self.tutor.name if self.tutor else None

    # Composite index for overlap checking: (tutor_id, start_time)
    __table_args__ = (
        Index("ix_sessions_tutor_start", "tutor_id", "start_time"),
    )

    def __repr__(self):
        return (
            f"<Session(id={self.id}, tutor_id={self.tutor_id}, "
            f"student_id={self.student_id}, status={self.status})>"
        )
