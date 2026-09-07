"""Tests for Phase 5: AI Integration with Gemini."""

from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

import pytest

from app.core.security import hash_password, create_access_token
from app.models import User, StudentProfile, Session as SessionModel, RoleEnum, SessionStatusEnum
from app.services.ai import (
    generate_session_plan,
    generate_session_summary,
    AIServiceError,
    AIServiceRateLimitError,
    AIServiceTimeoutError,
)


class TestGenerateSessionPlan:
    """Test AI plan generation service."""

    @patch("app.services.ai.genai.Client")
    def test_generate_plan_no_prior_session(self, mock_client_class):
        """Test plan generation with no prior session."""
        # Mock Gemini response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "warm_up": "Start with a quick review",
            "main_focus": "Working with loops",
            "practice_activities": ["Basic loop examples", "Loop exercises"],
            "check_for_understanding": "Ask student to explain a loop",
        })
        mock_client.models.generate_content.return_value = mock_response
        
        # Create student profile
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
            learning_goals="Learn Python programming",
            skill_level="Beginner",
            preferences="Morning sessions",
        )
        
        # Generate plan with no prior session
        result = generate_session_plan(student_profile, previous_session=None, duration_minutes=60)
        
        # Verify result
        assert result["warm_up"] == "Start with a quick review"
        assert result["main_focus"] == "Working with loops"
        assert "Loop" in str(result["practice_activities"])
        
        # Verify Gemini was called with correct prompt
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "There is no prior session record for this student" in prompt
        assert "Beginner" in prompt  # skill_level
        assert "Learn Python programming" in prompt  # learning_goals

    @patch("app.services.ai.genai.Client")
    def test_generate_plan_with_prior_session(self, mock_client_class):
        """Test plan generation references prior session notes."""
        # Mock Gemini response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "warm_up": "Review previous homework",
            "main_focus": "Building on loop concepts with nested loops",
            "practice_activities": ["Nested loop patterns", "Real-world examples"],
            "check_for_understanding": "Debug a nested loop",
        })
        mock_client.models.generate_content.return_value = mock_response
        
        # Create student profile and prior session
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
            learning_goals="Learn Python programming",
            skill_level="Beginner",
            preferences="Morning sessions",
        )
        
        prior_session = SessionModel(
            id="prior-session-id",
            tutor_id="tutor-id",
            student_id="student-id",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() - timedelta(days=1, hours=-1),
            status=SessionStatusEnum.COMPLETED,
            notes="Student understood basic loops",
            homework="Practice 10 simple loop exercises",
            ai_summary="Student grasped loop fundamentals",
        )
        
        # Generate plan with prior session
        result = generate_session_plan(student_profile, prior_session, duration_minutes=60)
        
        # Verify result
        assert result["main_focus"] == "Building on loop concepts with nested loops"
        
        # Verify Gemini was called with prior session context
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "Student understood basic loops" in prompt
        assert "Practice 10 simple loop exercises" in prompt

    @patch("app.services.ai.genai.Client")
    def test_generate_summary_grounded_in_notes(self, mock_client_class):
        """Test summary generation is grounded in actual notes."""
        # Mock Gemini response
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "summary": "Great session on functions. You learned how to define and call functions.",
            "strengths": ["Quick learner", "Asks good questions"],
            "areas_to_improve": ["Variable naming could be clearer"],
            "recommended_next_topic": "Function parameters and return values",
        })
        mock_client.models.generate_content.return_value = mock_response
        
        # Create student profile and session
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
            learning_goals="Master Python functions",
            skill_level="Intermediate",
        )
        
        session = SessionModel(
            id="session-id",
            tutor_id="tutor-id",
            student_id="student-id",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=1),
            status=SessionStatusEnum.COMPLETED,
            notes="Covered function definition, calling functions with arguments, and return values. Student demonstrated understanding with examples.",
            homework="Write 3 functions: factorial, palindrome checker, fibonacci",
        )
        previous_session = SessionModel(
            id="previous-session-id",
            tutor_id="tutor-id",
            student_id="student-id",
            start_time=datetime.utcnow() - timedelta(days=1, hours=1),
            end_time=datetime.utcnow() - timedelta(days=1),
            status=SessionStatusEnum.AI_REVIEWED,
            notes="Previously practiced list comprehensions",
            homework="Rewrite a loop using a list comprehension",
            ai_summary='{"summary":"The student is ready for function composition."}',
        )
        
        # Generate summary
        result = generate_session_summary(student_profile, session, previous_session)
        
        # Verify result is grounded in actual notes
        assert "functions" in result["summary"].lower()
        assert "Quick learner" in result["strengths"]
        
        # Verify Gemini was called with actual notes
        call_args = mock_client.models.generate_content.call_args
        prompt = call_args[1]["contents"]
        assert "function definition" in prompt
        assert "return values" in prompt
        assert "Previously practiced list comprehensions" in prompt
        assert "Rewrite a loop using a list comprehension" in prompt

    @patch("app.services.ai.genai.Client")
    def test_generate_plan_handles_json_wrapped_response(self, mock_client_class):
        """Test handling of JSON wrapped in code blocks."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Response with markdown code blocks
        mock_response = MagicMock()
        mock_response.text = """```json
{
    "warm_up": "Quick review",
    "main_focus": "Main topic",
    "practice_activities": ["Activity 1"],
    "check_for_understanding": "Question"
}
```"""
        mock_client.models.generate_content.return_value = mock_response
        
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
        )
        
        result = generate_session_plan(student_profile, None)
        assert result["warm_up"] == "Quick review"

    @patch("app.services.ai.genai.Client")
    def test_generate_plan_rate_limit_error(self, mock_client_class):
        """Test rate limit error handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("429 Too Many Requests")
        
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
        )
        
        with pytest.raises(AIServiceRateLimitError):
            generate_session_plan(student_profile, None)

    @patch("app.services.ai.genai.Client")
    def test_generate_plan_timeout_with_retry(self, mock_client_class):
        """Test timeout error with retry."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # First call times out, second succeeds
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "warm_up": "Quick review",
            "main_focus": "Main topic",
            "practice_activities": ["Activity 1"],
            "check_for_understanding": "Question",
        })
        mock_client.models.generate_content.side_effect = [
            Exception("timeout"),
            mock_response,
        ]
        
        student_profile = StudentProfile(
            id="test-id",
            user_id="student-id",
            tutor_id="tutor-id",
        )
        
        # Should succeed on retry
        result = generate_session_plan(student_profile, None)
        assert result["warm_up"] == "Quick review"


class TestAIPlanEndpoint:
    """Test POST /sessions/{id}/ai-plan endpoint."""

    @patch("app.services.ai.genai.Client")
    def test_generate_ai_plan_success(self, mock_client_class, client, db):
        """Test successful AI plan generation via endpoint."""
        # Mock Gemini
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "warm_up": "Review",
            "main_focus": "Focus",
            "practice_activities": ["Activity"],
            "check_for_understanding": "Check",
        })
        mock_client.models.generate_content.return_value = mock_response
        
        # Setup: Create tutor, student, profile, and SCHEDULED session
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Learn Python",
            skill_level="Beginner",
        )
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.SCHEDULED,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Generate AI plan
        response = client.post(
            f"/sessions/{session.id}/ai-plan",
            json={"duration_minutes": 60},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SCHEDULED"
        assert data["ai_plan"] is not None
        
        # Verify ai_plan is valid JSON
        plan_data = json.loads(data["ai_plan"])
        assert plan_data["warm_up"] == "Review"

    def test_ai_plan_not_scheduled(self, client, db):
        """Test cannot generate plan if session not SCHEDULED."""
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.IN_PROGRESS,  # Not SCHEDULED
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.post(
            f"/sessions/{session.id}/ai-plan",
            json={"duration_minutes": 60},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "SCHEDULED" in response.json()["detail"]

    @patch("app.services.ai.genai.Client")
    def test_ai_plan_service_error_returns_502(self, mock_client_class, client, db):
        """Test AI service error returns 502."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = AIServiceError("Service error")
        
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.SCHEDULED,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.post(
            f"/sessions/{session.id}/ai-plan",
            json={"duration_minutes": 60},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 502
        assert "AI service" in response.json()["detail"]


class TestAIReviewEndpoint:
    """Test PATCH /sessions/{id}/trigger-ai-review endpoint."""

    @patch("app.services.ai.genai.Client")
    def test_trigger_ai_review_success(self, mock_client_class, client, db):
        """Test successful AI review generation."""
        # Mock Gemini
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "summary": "Great session on functions.",
            "strengths": ["Good understanding"],
            "areas_to_improve": ["Practice more"],
            "recommended_next_topic": "Classes",
        })
        mock_client.models.generate_content.return_value = mock_response
        
        # Setup: Create tutor, student, profile, and COMPLETED session
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Learn Python",
        )
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.COMPLETED,
            notes="Student learned functions",
            homework="Write 5 functions",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Trigger AI review
        response = client.patch(
            f"/sessions/{session.id}/trigger-ai-review",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "AI_REVIEWED"
        assert data["ai_summary"] is not None
        
        # Verify ai_summary is valid JSON
        summary_data = json.loads(data["ai_summary"])
        assert summary_data["summary"] == "Great session on functions."

    def test_trigger_ai_review_not_completed(self, client, db):
        """Test cannot trigger review if session not COMPLETED."""
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.SCHEDULED,  # Not COMPLETED
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/trigger-ai-review",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "COMPLETED" in response.json()["detail"]

    @patch("app.services.ai.genai.Client")
    def test_trigger_ai_review_rate_limit_returns_502(self, mock_client_class, client, db):
        """Test AI rate limit returns 502."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = AIServiceRateLimitError("Rate limited")
        
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.COMPLETED,
            notes="Notes",
            homework="Homework",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/trigger-ai-review",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 502
        assert "temporarily unavailable" in response.json()["detail"]
