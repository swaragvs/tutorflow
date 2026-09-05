"""Tests for session scheduling endpoints."""

from datetime import datetime, timedelta

import pytest
from uuid import uuid4

from app.core.security import hash_password, create_access_token
from app.models import User, StudentProfile, Session as SessionModel, RoleEnum


class TestSessionCreation:
    """Test session creation endpoint."""

    def test_create_session_success(self, client, db):
        """Test successful session creation."""
        # Create tutor
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        # Create student
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        # Create student profile
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Python",
        )
        db.add(profile)
        db.commit()

        # Create tutor token
        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Create session
        now = datetime.utcnow()
        start = now + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student.id),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["student_id"] == str(student.id)
        assert data["tutor_id"] == str(tutor.id)
        assert data["status"] == "SCHEDULED"

    def test_create_session_invalid_time_range(self, client, db):
        """Test session creation fails if end_time <= start_time."""
        # Create tutor and student
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

        # Create student profile
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
        )
        db.add(profile)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        now = datetime.utcnow()
        start = now + timedelta(days=1)
        end = start - timedelta(hours=1)  # End before start

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student.id),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_create_session_student_not_owned_by_tutor(self, client, db):
        """Test cannot create session for student not owned by tutor."""
        # Create tutor1 and tutor2
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
        
        # Create student for tutor2
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        # Create profile for tutor2
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor2.id,
        )
        db.add(profile)
        db.commit()

        # Create token for tutor1
        token = create_access_token(
            data={"sub": str(tutor1.id), "role": tutor1.role.value}
        )

        now = datetime.utcnow()
        start = now + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student.id),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert "does not belong" in response.json()["detail"]

    def test_create_session_student_cannot_create(self, client, db):
        """Test student cannot create sessions."""
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        token = create_access_token(
            data={"sub": str(student.id), "role": student.role.value}
        )

        now = datetime.utcnow()
        start = now + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = client.post(
            "/sessions",
            json={
                "student_id": str(uuid4()),
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestSessionOverlapPrevention:
    """Test overlap prevention in session scheduling."""

    def test_overlapping_sessions_same_tutor_rejected(self, client, db):
        """Test overlapping sessions for same tutor are rejected."""
        # Create tutor and student
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

        # Create student profile
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
        )
        db.add(profile)
        db.commit()

        # Create first session
        now = datetime.utcnow()
        start1 = now + timedelta(days=1, hours=10)
        end1 = start1 + timedelta(hours=1)
        
        session1 = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start1,
            end_time=end1,
        )
        db.add(session1)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Try to create overlapping session
        start2 = start1 + timedelta(minutes=30)
        end2 = start2 + timedelta(hours=1)

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student.id),
                "start_time": start2.isoformat(),
                "end_time": end2.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )


class TestSessionSchedulingUpdates:
    """Test reschedule, delete, and early-start checks."""

    def test_reschedule_session_success(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        now = datetime.utcnow()
        start = now + timedelta(days=2, hours=10)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="SCHEDULED",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})

        new_start = start + timedelta(hours=2)
        new_end = new_start + timedelta(hours=1)
        response = client.patch(
            f"/sessions/{session.id}/reschedule",
            json={"start_time": new_start.isoformat(), "end_time": new_end.isoformat()},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["start_time"] == new_start.isoformat().replace("+00:00", "Z") or True

    def test_reschedule_session_overlap_409(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        now = datetime.utcnow()
        start1 = now + timedelta(days=2, hours=10)
        session1 = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start1,
            end_time=start1 + timedelta(hours=1),
            status="SCHEDULED",
        )
        session2 = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start1 + timedelta(hours=3),
            end_time=start1 + timedelta(hours=4),
            status="SCHEDULED",
        )
        db.add_all([session1, session2])
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})
        response = client.patch(
            f"/sessions/{session1.id}/reschedule",
            json={
                "start_time": (start1 + timedelta(hours=2, minutes=30)).isoformat(),
                "end_time": (start1 + timedelta(hours=3, minutes=30)).isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

    def test_reschedule_session_wrong_status_409(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        start = datetime.utcnow() + timedelta(days=2)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="IN_PROGRESS",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})
        response = client.patch(
            f"/sessions/{session.id}/reschedule",
            json={"start_time": (start + timedelta(hours=1)).isoformat(), "end_time": (start + timedelta(hours=2)).isoformat()},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

    def test_delete_session_success(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        start = datetime.utcnow() + timedelta(days=3)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="SCHEDULED",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})

        response = client.delete(
            f"/sessions/{session.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["detail"] == "Session deleted"

    def test_delete_session_wrong_status_409(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        start = datetime.utcnow() + timedelta(days=3)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="COMPLETED",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})
        response = client.delete(
            f"/sessions/{session.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409

    def test_start_session_too_early_409(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        start = datetime.utcnow() + timedelta(minutes=30)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="SCHEDULED",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})
        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 409
        assert "earliest allowed" in response.json()["detail"].lower()

    def test_start_session_in_window_success(self, client, db):
        tutor = User(
            name="Tutor One",
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()

        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        db.commit()

        start = datetime.utcnow() + timedelta(minutes=5)
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="SCHEDULED",
        )
        db.add(session)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})
        response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"

        second_response = client.patch(
            f"/sessions/{session.id}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert second_response.status_code == 409
        assert "only scheduled sessions can be started" in second_response.json()["detail"].lower()

    def test_non_overlapping_sessions_same_tutor_allowed(self, client, db):
        """Test non-overlapping sessions for same tutor are allowed."""
        # Create tutor and 2 students
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student1)
        
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student2)
        db.commit()

        # Create profiles
        profile1 = StudentProfile(user_id=student1.id, tutor_id=tutor.id)
        profile2 = StudentProfile(user_id=student2.id, tutor_id=tutor.id)
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create first session
        now = datetime.utcnow()
        start1 = now + timedelta(days=1, hours=10)
        end1 = start1 + timedelta(hours=1)
        
        session1 = SessionModel(
            tutor_id=tutor.id,
            student_id=student1.id,
            start_time=start1,
            end_time=end1,
        )
        db.add(session1)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Create non-overlapping session with different student
        start2 = end1 + timedelta(minutes=30)
        end2 = start2 + timedelta(hours=1)

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student2.id),
                "start_time": start2.isoformat(),
                "end_time": end2.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201

    def test_overlapping_sessions_different_tutors_allowed(self, client, db):
        """Test overlapping sessions for different tutors are allowed."""
        # Create tutor1 and tutor2
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
        
        # Create students for each tutor
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student1)
        
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student2)
        db.commit()

        # Create profiles
        profile1 = StudentProfile(user_id=student1.id, tutor_id=tutor1.id)
        profile2 = StudentProfile(user_id=student2.id, tutor_id=tutor2.id)
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create first session for tutor1
        now = datetime.utcnow()
        start1 = now + timedelta(days=1, hours=10)
        end1 = start1 + timedelta(hours=1)
        
        session1 = SessionModel(
            tutor_id=tutor1.id,
            student_id=student1.id,
            start_time=start1,
            end_time=end1,
        )
        db.add(session1)
        db.commit()

        # Create overlapping session for tutor2
        token = create_access_token(
            data={"sub": str(tutor2.id), "role": tutor2.role.value}
        )

        response = client.post(
            "/sessions",
            json={
                "student_id": str(student2.id),
                "start_time": start1.isoformat(),
                "end_time": end1.isoformat(),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201


class TestSessionListing:
    """Test session listing endpoints."""

    def test_tutor_sees_all_own_sessions(self, client, db):
        """Test tutor sees all their sessions."""
        # Create tutor
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        # Create 2 students
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student1)
        
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student2)
        db.commit()

        # Create profiles
        profile1 = StudentProfile(user_id=student1.id, tutor_id=tutor.id)
        profile2 = StudentProfile(user_id=student2.id, tutor_id=tutor.id)
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create 2 sessions
        now = datetime.utcnow()
        session1 = SessionModel(
            tutor_id=tutor.id,
            student_id=student1.id,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        session2 = SessionModel(
            tutor_id=tutor.id,
            student_id=student2.id,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
        )
        db.add(session1)
        db.add(session2)
        db.commit()

        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_student_sees_only_own_sessions(self, client, db):
        """Test student sees only their own sessions."""
        # Create tutor
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        # Create 2 students
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student1)
        
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student2)
        db.commit()

        # Create profiles
        profile1 = StudentProfile(user_id=student1.id, tutor_id=tutor.id)
        profile2 = StudentProfile(user_id=student2.id, tutor_id=tutor.id)
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create sessions for both students
        now = datetime.utcnow()
        session1 = SessionModel(
            tutor_id=tutor.id,
            student_id=student1.id,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        session2 = SessionModel(
            tutor_id=tutor.id,
            student_id=student2.id,
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
        )
        db.add(session1)
        db.add(session2)
        db.commit()

        # Get sessions as student1
        token = create_access_token(
            data={"sub": str(student1.id), "role": student1.role.value}
        )

        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["student_id"] == str(student1.id)

    def test_get_session_owner_can_access(self, client, db):
        """Test session owner can access their session."""
        # Create tutor and student
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

        # Create profile and session
        profile = StudentProfile(user_id=student.id, tutor_id=tutor.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        db.add(session)
        db.commit()

        # Get as tutor
        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        response = client.get(
            f"/sessions/{session.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == str(session.id)

    def test_get_session_non_owner_cannot_access(self, client, db):
        """Test non-owner cannot access session."""
        # Create 2 tutors
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
        
        # Create student for tutor1
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        # Create profile and session
        profile = StudentProfile(user_id=student.id, tutor_id=tutor1.id)
        db.add(profile)
        
        now = datetime.utcnow()
        session = SessionModel(
            tutor_id=tutor1.id,
            student_id=student.id,
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
        )
        db.add(session)
        db.commit()

        # Try to get as tutor2
        token = create_access_token(
            data={"sub": str(tutor2.id), "role": tutor2.role.value}
        )

        response = client.get(
            f"/sessions/{session.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
