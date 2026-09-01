"""Tests for session state machine (Phase 4)."""

from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

import pytest

from app.core.security import hash_password, create_access_token
from app.models import User, StudentProfile, Session as SessionModel, RoleEnum, SessionStatusEnum


class TestSessionStateTransitions:
    """Test legal session state transitions."""

    def test_transition_scheduled_to_in_progress(self, client, db):
        """Test SCHEDULED → IN_PROGRESS transition."""
        # Setup: Create tutor, student, and SCHEDULED session
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

        # Start session
        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_PROGRESS"

    def test_transition_in_progress_to_completed(self, client, db):
        """Test IN_PROGRESS → COMPLETED transition with notes and homework."""
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
            status=SessionStatusEnum.IN_PROGRESS,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Complete session
        response = client.patch(
            f"/sessions/{session.id}/complete",
            json={
                "notes": "Student understood the main concept",
                "homework": "Complete chapter 5 exercises",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["notes"] == "Student understood the main concept"
        assert data["homework"] == "Complete chapter 5 exercises"

    def test_transition_completed_to_ai_reviewed(self, client, db):
        """Test COMPLETED → AI_REVIEWED transition (Phase 5 with mocked Gemini)."""
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
            notes="Session notes",
            homework="Homework",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Mock Gemini client
        with patch("app.services.ai.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "summary": "Great session",
                "strengths": [],
                "areas_to_improve": [],
                "recommended_next_topic": "Next topic",
            })
            mock_client.models.generate_content.return_value = mock_response

            # Trigger AI review
            response = client.patch(
                f"/sessions/{session.id}/trigger-ai-review",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "AI_REVIEWED"


class TestIllegalTransitions:
    """Test that illegal transitions are rejected with 409."""

    def test_scheduled_to_completed_rejected(self, client, db):
        """Test illegal transition SCHEDULED → COMPLETED is rejected."""
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

        # Try to complete directly from SCHEDULED
        response = client.patch(
            f"/sessions/{session.id}/complete",
            json={
                "notes": "Notes",
                "homework": "Homework",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "Cannot transition" in response.json()["detail"]

    def test_scheduled_to_ai_reviewed_rejected(self, client, db):
        """Test illegal transition SCHEDULED → AI_REVIEWED is rejected."""
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

        # Try to trigger AI review from SCHEDULED
        response = client.patch(
            f"/sessions/{session.id}/trigger-ai-review",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        # Should reject because status must be COMPLETED
        assert "COMPLETED" in response.json()["detail"]

    def test_completed_to_scheduled_rejected(self, client, db):
        """Test illegal transition COMPLETED → SCHEDULED is rejected."""
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

        # Try to start a completed session
        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "Cannot transition" in response.json()["detail"]

    def test_ai_reviewed_to_anything_rejected(self, client, db):
        """Test illegal transitions from AI_REVIEWED are rejected."""
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
            status=SessionStatusEnum.AI_REVIEWED,
            notes="Notes",
            homework="Homework",
            ai_summary="Summary",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Try to start an AI_REVIEWED session
        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409


class TestSessionNotesUpdate:
    """Test session notes update endpoint."""

    def test_update_notes_while_in_progress(self, client, db):
        """Test updating notes while session is IN_PROGRESS."""
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
            status=SessionStatusEnum.IN_PROGRESS,
            notes="Initial notes",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Update notes
        response = client.patch(
            f"/sessions/{session.id}/notes",
            json={"notes": "Updated notes with new information"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes with new information"

    def test_update_notes_while_scheduled_rejected(self, client, db):
        """Test updating notes while SCHEDULED is rejected."""
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

        response = client.patch(
            f"/sessions/{session.id}/notes",
            json={"notes": "Some notes"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "IN_PROGRESS" in response.json()["detail"]

    def test_update_notes_while_completed_rejected(self, client, db):
        """Test updating notes on COMPLETED session is rejected."""
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
            notes="Original notes",
            homework="Homework",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/notes",
            json={"notes": "Updated notes"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "locked" in response.json()["detail"].lower()

    def test_update_notes_while_ai_reviewed_rejected(self, client, db):
        """Test updating notes on AI_REVIEWED session is rejected."""
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
            status=SessionStatusEnum.AI_REVIEWED,
            notes="Notes",
            homework="Homework",
            ai_summary="Summary",
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/notes",
            json={"notes": "Updated notes"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "locked" in response.json()["detail"].lower()


class TestSessionAuthorizationPhase4:
    """Test authorization for state transition endpoints."""

    def test_student_cannot_start_session(self, client, db):
        """Test student cannot start session (403)."""
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
            data={"sub": str(student.id), "role": student.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_tutor_cannot_modify_other_tutor_session(self, client, db):
        """Test tutor cannot modify another tutor's session (404)."""
        tutor1 = User(
            email="tutor1@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor1)
        
        tutor2 = User(
            email="tutor2@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor2)
        
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor1.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor1.id,
            student_id=student.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            status=SessionStatusEnum.SCHEDULED,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor2.id), "role": tutor2.role.value}
        )

        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestCompleteSessionValidation:
    """Test complete session endpoint validation."""

    def test_complete_session_requires_notes(self, client, db):
        """Test completing session requires non-empty notes."""
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
            status=SessionStatusEnum.IN_PROGRESS,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Try with empty notes
        response = client.patch(
            f"/sessions/{session.id}/complete",
            json={
                "notes": "",
                "homework": "Homework",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error

    def test_complete_session_requires_homework(self, client, db):
        """Test completing session requires non-empty homework."""
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
            status=SessionStatusEnum.IN_PROGRESS,
        )
        db.add(session)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Try with empty homework
        response = client.patch(
            f"/sessions/{session.id}/complete",
            json={
                "notes": "Notes",
                "homework": "",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error
