"""Tests for student management endpoints."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, create_access_token
from app.models import User, StudentProfile, RoleEnum
from app.db.session import get_db


class TestStudentCreation:
    """Test student creation endpoint."""

    def test_create_student_success(self, client, db):
        """Test successful student creation by tutor."""
        # Create a tutor
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        db.commit()

        # Create tutor token
        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Create student
        response = client.post(
            "/students",
            json={
                "email": "student@example.com",
                "initial_password": "StudentPass123",
                "learning_goals": "Learn Python",
                "skill_level": "Beginner",
                "preferences": "Evening sessions",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["learning_goals"] == "Learn Python"
        assert data["skill_level"] == "Beginner"
        assert data["preferences"] == "Evening sessions"
        assert data["tutor_id"] == str(tutor.id)
        
        # Verify user was created
        student_user = db.query(User).filter(User.email == "student@example.com").first()
        assert student_user is not None
        assert student_user.role == RoleEnum.STUDENT

    def test_create_student_email_already_exists(self, client, db):
        """Test student creation fails if email already registered."""
        # Create tutor and existing user with same email
        tutor = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        
        existing_user = User(
            email="existing@example.com",
            password_hash=hash_password("ExistingPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(existing_user)
        db.commit()

        # Create tutor token
        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )

        # Try to create student with existing email
        response = client.post(
            "/students",
            json={
                "email": "existing@example.com",
                "initial_password": "NewPass123",
                "learning_goals": "Learn Python",
                "skill_level": "Beginner",
                "preferences": "Evening sessions",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_create_student_student_cannot_create(self, client, db):
        """Test student cannot create other students."""
        # Create student user
        student = User(
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()

        # Create student token
        token = create_access_token(
            data={"sub": str(student.id), "role": student.role.value}
        )

        # Try to create a student
        response = client.post(
            "/students",
            json={
                "email": "newstudent@example.com",
                "initial_password": "NewPass123",
                "learning_goals": "Learn Python",
                "skill_level": "Beginner",
                "preferences": "Evening sessions",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "Only tutors" in response.json()["detail"]


class TestStudentListing:
    """Test student listing endpoints."""

    def test_list_students_tutor_sees_own_students(self, client, db):
        """Test tutor can see only their students."""
        # Create tutor 1
        tutor1 = User(
            email="tutor1@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor1)
        
        # Create tutor 2
        tutor2 = User(
            email="tutor2@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        db.add(tutor2)
        db.commit()

        # Create student for tutor1
        student1 = User(
            email="student1@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student1)
        
        # Create student for tutor2
        student2 = User(
            email="student2@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add(student2)
        db.commit()

        # Create profiles
        profile1 = StudentProfile(
            user_id=student1.id,
            tutor_id=tutor1.id,
            learning_goals="Python",
            skill_level="Beginner",
        )
        profile2 = StudentProfile(
            user_id=student2.id,
            tutor_id=tutor2.id,
            learning_goals="Math",
            skill_level="Intermediate",
        )
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create tutor1 token
        token = create_access_token(
            data={"sub": str(tutor1.id), "role": tutor1.role.value}
        )

        # List students for tutor1
        response = client.get(
            "/students",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == str(student1.id)
        assert data[0]["learning_goals"] == "Python"

    def test_list_students_student_cannot_list(self, client, db):
        """Test student cannot list students."""
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

        response = client.get(
            "/students",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


class TestStudentRetrieval:
    """Test individual student retrieval."""

    def test_get_student_tutor_can_view_own_student(self, client, db):
        """Test tutor can view their student's profile."""
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

        # Create profile
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Python",
            skill_level="Beginner",
            preferences="Weekends",
        )
        db.add(profile)
        db.commit()

        # Create tutor token
        token = create_access_token(
            data={"sub": str(tutor.id), "role": tutor.role.value}
        )


class TestStudentProfileUpdates:
    """Test profile editing on owned students."""

    def test_patch_student_profile_success(self, client, db):
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

        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Old goal",
            skill_level="Beginner",
            preferences="Old pref",
        )
        db.add(profile)
        db.commit()

        token = create_access_token({"sub": str(tutor.id), "role": tutor.role.value})

        response = client.patch(
            f"/students/{profile.id}",
            json={
                "name": "Updated Student",
                "learning_goals": "New goal",
                "skill_level": "Intermediate",
                "preferences": "New pref",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Student"
        assert data["learning_goals"] == "New goal"
        assert data["skill_level"] == "Intermediate"
        assert data["preferences"] == "New pref"

    def test_patch_student_profile_wrong_tutor_404(self, client, db):
        tutor_a = User(
            name="Tutor A",
            email="tutora@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        tutor_b = User(
            name="Tutor B",
            email="tutorb@example.com",
            password_hash=hash_password("TutorPass123"),
            role=RoleEnum.TUTOR,
        )
        student = User(
            name="Student One",
            email="student@example.com",
            password_hash=hash_password("StudentPass123"),
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor_a, tutor_b, student])
        db.commit()

        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor_a.id,
            learning_goals="Goal",
        )
        db.add(profile)
        db.commit()

        token = create_access_token({"sub": str(tutor_b.id), "role": tutor_b.role.value})

        response = client.patch(
            f"/students/{profile.id}",
            json={"name": "Should fail"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

        # Verify the legitimate owner can still fetch the student after the blocked update
        owner_token = create_access_token({"sub": str(tutor_a.id), "role": tutor_a.role.value})
        response = client.get(
            f"/students/{profile.id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(student.id)
        assert data["learning_goals"] == "Goal"
        assert data["email"] == "student@example.com"

    def test_get_student_tutor_cannot_view_other_tutor_student(self, client, db):
        """Test tutor cannot view another tutor's student."""
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
            learning_goals="Python",
            skill_level="Beginner",
        )
        db.add(profile)
        db.commit()

        # Create tutor1 token
        token = create_access_token(
            data={"sub": str(tutor1.id), "role": tutor1.role.value}
        )

        # Try to get tutor2's student
        response = client.get(
            f"/students/{profile.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    def test_get_student_student_cannot_view_other_student(self, client, db):
        """Test student cannot view other students."""
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
        profile1 = StudentProfile(
            user_id=student1.id,
            tutor_id=tutor.id,
            learning_goals="Python",
            skill_level="Beginner",
        )
        profile2 = StudentProfile(
            user_id=student2.id,
            tutor_id=tutor.id,
            learning_goals="Math",
            skill_level="Beginner",
        )
        db.add(profile1)
        db.add(profile2)
        db.commit()

        # Create student1 token
        token = create_access_token(
            data={"sub": str(student1.id), "role": student1.role.value}
        )

        # Try to get student2's profile
        response = client.get(
            f"/students/{profile2.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
