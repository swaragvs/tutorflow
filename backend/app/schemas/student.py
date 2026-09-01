"""Pydantic schemas for student management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class StudentCreateRequest(BaseModel):
    """Request schema for creating a student."""
    email: EmailStr = Field(..., description="Student email address")
    initial_password: str = Field(..., min_length=8, description="Initial password (min 8 chars)")
    learning_goals: Optional[str] = Field(None, description="Student's learning goals")
    skill_level: Optional[str] = Field(None, description="Current skill level")
    preferences: Optional[str] = Field(None, description="Student preferences")


class StudentResponse(BaseModel):
    """Response schema for student profile."""
    id: UUID
    user_id: UUID
    tutor_id: UUID
    learning_goals: Optional[str]
    skill_level: Optional[str]
    preferences: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StudentDetailResponse(StudentResponse):
    """Extended student response including email."""
    email: Optional[str] = None
