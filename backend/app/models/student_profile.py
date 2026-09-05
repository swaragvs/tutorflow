"""StudentProfile model linking students to tutors and storing preferences."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class StudentProfile(Base):
    """StudentProfile model for student metadata and tutor relationship."""

    __tablename__ = "student_profiles"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    tutor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    learning_goals = Column(Text, nullable=True)
    skill_level = Column(Text, nullable=True)
    preferences = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="student_profiles")
    tutor = relationship("User", foreign_keys=[tutor_id], back_populates="tutor_students")

    @property
    def name(self):
        return self.user.name if self.user else None

    def __repr__(self):
        return (
            f"<StudentProfile(id={self.id}, user_id={self.user_id}, "
            f"tutor_id={self.tutor_id})>"
        )
