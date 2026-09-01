"""Pydantic schemas for session management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SessionCreateRequest(BaseModel):
    """Request schema for creating a session."""
    student_id: UUID = Field(..., description="Student ID")
    start_time: datetime = Field(..., description="Session start time")
    end_time: datetime = Field(..., description="Session end time")

    @field_validator("end_time")
    @classmethod
    def end_time_after_start_time(cls, v, info):
        """Ensure end_time is after start_time."""
        start_time = info.data.get("start_time")
        if start_time and v <= start_time:
            raise ValueError("end_time must be after start_time")
        return v


class SessionResponse(BaseModel):
    """Response schema for session."""
    id: UUID
    tutor_id: UUID
    student_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    notes: Optional[str]
    homework: Optional[str]
    ai_plan: Optional[str]
    ai_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionConflictResponse(BaseModel):
    """Response when session creation conflicts with existing session."""
    detail: str
    conflicting_session: Optional[dict] = None
