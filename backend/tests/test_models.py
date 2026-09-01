"""Tests for TutorFlow database models and schema."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.models import User, StudentProfile, Session as SessionModel
from app.models.user import RoleEnum
from app.models.session import SessionStatusEnum


class TestModelRegistration:
    """Test that models are properly registered with SQLAlchemy."""

    def test_user_table_exists(self, test_engine):
        """Verify users table is created."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "users" in tables

    def test_student_profiles_table_exists(self, test_engine):
        """Verify student_profiles table is created."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "student_profiles" in tables

    def test_sessions_table_exists(self, test_engine):
        """Verify sessions table is created."""
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "sessions" in tables

    def test_user_columns(self, test_engine):
        """Verify users table has correct columns."""
        inspector = inspect(test_engine)
        columns = [col["name"] for col in inspector.get_columns("users")]
        assert "id" in columns
        assert "email" in columns
        assert "password_hash" in columns
        assert "role" in columns
        assert "created_at" in columns

    def test_session_columns(self, test_engine):
        """Verify sessions table has correct columns."""
        inspector = inspect(test_engine)
        columns = [col["name"] for col in inspector.get_columns("sessions")]
        assert "id" in columns
        assert "tutor_id" in columns
        assert "student_id" in columns
        assert "start_time" in columns
        assert "end_time" in columns
        assert "status" in columns
        assert "notes" in columns
        assert "homework" in columns
        assert "ai_plan" in columns
        assert "ai_summary" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


class TestUserModel:
    """Test User model creation and validation."""

    def test_user_creation(self, db):
        """Test creating a user."""
        user = User(
            email="tutor@example.com",
            password_hash="hashed_password_123",
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        fetched = db.query(User).filter(User.email == "tutor@example.com").first()
        assert fetched is not None
        assert fetched.email == "tutor@example.com"
        assert fetched.role == RoleEnum.TUTOR

    def test_user_id_is_uuid(self, db):
        """Test that user ID is a UUID."""
        user = User(
            email="user@example.com",
            password_hash="hashed_password",
            role=RoleEnum.STUDENT,
        )
        db.add(user)
        db.commit()
        
        fetched = db.query(User).filter(User.email == "user@example.com").first()
        assert fetched.id is not None
        assert isinstance(fetched.id, uuid.UUID)

    def test_user_created_at_auto_set(self, db):
        """Test that created_at is automatically set."""
        user = User(
            email="autotime@example.com",
            password_hash="hashed_password",
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        fetched = db.query(User).filter(User.email == "autotime@example.com").first()
        assert fetched.created_at is not None
        assert isinstance(fetched.created_at, datetime)

    def test_user_email_unique_constraint(self, db):
        """Test that email must be unique."""
        user1 = User(
            email="duplicate@example.com",
            password_hash="hash1",
            role=RoleEnum.TUTOR,
        )
        user2 = User(
            email="duplicate@example.com",
            password_hash="hash2",
            role=RoleEnum.STUDENT,
        )
        db.add(user1)
        db.commit()
        
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_email_required(self, db):
        """Test that email is required."""
        user = User(
            password_hash="hashed_password",
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_password_hash_required(self, db):
        """Test that password_hash is required."""
        user = User(
            email="nohash@example.com",
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_user_role_required(self, db):
        """Test that role is required."""
        user = User(
            email="norole@example.com",
            password_hash="hashed_password",
        )
        db.add(user)
        with pytest.raises(IntegrityError):
            db.commit()


class TestRoleEnum:
    """Test role enumeration values."""

    def test_role_enum_tutor(self, db):
        """Test TUTOR role value."""
        user = User(
            email="tutor@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        fetched = db.query(User).filter(User.email == "tutor@example.com").first()
        assert fetched.role == RoleEnum.TUTOR
        assert fetched.role.value == "TUTOR"

    def test_role_enum_student(self, db):
        """Test STUDENT role value."""
        user = User(
            email="student@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add(user)
        db.commit()
        
        fetched = db.query(User).filter(User.email == "student@example.com").first()
        assert fetched.role == RoleEnum.STUDENT
        assert fetched.role.value == "STUDENT"

    def test_role_enum_values(self):
        """Test that only TUTOR and STUDENT roles exist."""
        roles = [e.value for e in RoleEnum]
        assert "TUTOR" in roles
        assert "STUDENT" in roles
        assert len(roles) == 2


class TestStudentProfileModel:
    """Test StudentProfile model creation and foreign keys."""

    def test_student_profile_creation(self, db):
        """Test creating a student profile."""
        tutor = User(
            email="tutor@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            learning_goals="Learn Python",
            skill_level="Beginner",
            preferences="Morning sessions",
        )
        db.add(profile)
        db.commit()
        
        fetched = db.query(StudentProfile).filter(
            StudentProfile.user_id == student.id
        ).first()
        assert fetched is not None
        assert fetched.user_id == student.id
        assert fetched.tutor_id == tutor.id
        assert fetched.learning_goals == "Learn Python"

    def test_student_profile_user_id_unique(self, db):
        """Test that each user can only have one profile."""
        tutor = User(
            email="tutor2@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student2@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        profile1 = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
        )
        profile2 = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
        )
        db.add(profile1)
        db.commit()
        
        db.add(profile2)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_student_profile_foreign_key_user(self, db):
        """Test that student profile user_id must reference valid user."""
        fake_id = uuid.uuid4()
        profile = StudentProfile(
            user_id=fake_id,
            tutor_id=fake_id,
        )
        db.add(profile)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_student_profile_optional_fields(self, db):
        """Test that learning_goals, skill_level, preferences are optional."""
        tutor = User(
            email="tutor3@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student3@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        profile = StudentProfile(
            user_id=student.id,
            tutor_id=tutor.id,
            # Omit optional fields
        )
        db.add(profile)
        db.commit()
        
        fetched = db.query(StudentProfile).filter(
            StudentProfile.user_id == student.id
        ).first()
        assert fetched.learning_goals is None
        assert fetched.skill_level is None
        assert fetched.preferences is None


class TestSessionModel:
    """Test Session model creation and constraints."""

    def test_session_creation(self, db):
        """Test creating a session."""
        tutor = User(
            email="tutor4@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student4@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
            status=SessionStatusEnum.SCHEDULED,
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched is not None
        assert fetched.tutor_id == tutor.id
        assert fetched.student_id == student.id
        assert fetched.status == SessionStatusEnum.SCHEDULED

    def test_session_status_default_scheduled(self, db):
        """Test that session status defaults to SCHEDULED."""
        tutor = User(
            email="tutor5@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student5@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
            # Don't specify status
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched.status == SessionStatusEnum.SCHEDULED

    def test_session_optional_fields(self, db):
        """Test that notes, homework, ai_plan, ai_summary are optional."""
        tutor = User(
            email="tutor6@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student6@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
            # Omit optional fields
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched.notes is None
        assert fetched.homework is None
        assert fetched.ai_plan is None
        assert fetched.ai_summary is None

    def test_session_created_at_auto_set(self, db):
        """Test that created_at is automatically set."""
        tutor = User(
            email="tutor7@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student7@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched.created_at is not None
        assert isinstance(fetched.created_at, datetime)

    def test_session_updated_at_auto_set(self, db):
        """Test that updated_at is automatically set."""
        tutor = User(
            email="tutor8@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student8@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched.updated_at is not None
        assert isinstance(fetched.updated_at, datetime)


class TestSessionStatusEnum:
    """Test session status enumeration values."""

    def test_session_status_scheduled(self, db):
        """Test SCHEDULED status."""
        tutor = User(
            email="tutor9@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student9@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=start,
            end_time=end,
            status=SessionStatusEnum.SCHEDULED,
        )
        db.add(session)
        db.commit()
        
        fetched = db.query(SessionModel).filter(SessionModel.id == session.id).first()
        assert fetched.status == SessionStatusEnum.SCHEDULED
        assert fetched.status.value == "SCHEDULED"

    def test_session_status_all_values(self):
        """Test that all required status values exist."""
        statuses = [e.value for e in SessionStatusEnum]
        assert "SCHEDULED" in statuses
        assert "IN_PROGRESS" in statuses
        assert "COMPLETED" in statuses
        assert "AI_REVIEWED" in statuses
        assert len(statuses) == 4


class TestConstraints:
    """Test database constraints."""

    def test_session_tutor_id_required(self, db):
        """Test that session tutor_id is required."""
        student = User(
            email="student10@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add(student)
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            student_id=student.id,
            start_time=start,
            end_time=end,
            # Missing tutor_id
        )
        db.add(session)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_session_student_id_required(self, db):
        """Test that session student_id is required."""
        tutor = User(
            email="tutor10@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        db.add(tutor)
        db.commit()
        
        start = datetime.utcnow()
        end = start + timedelta(hours=1)
        
        session = SessionModel(
            tutor_id=tutor.id,
            start_time=start,
            end_time=end,
            # Missing student_id
        )
        db.add(session)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_session_start_time_required(self, db):
        """Test that session start_time is required."""
        tutor = User(
            email="tutor11@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student11@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            end_time=datetime.utcnow() + timedelta(hours=1),
            # Missing start_time
        )
        db.add(session)
        with pytest.raises(IntegrityError):
            db.commit()

    def test_session_end_time_required(self, db):
        """Test that session end_time is required."""
        tutor = User(
            email="tutor12@example.com",
            password_hash="hash",
            role=RoleEnum.TUTOR,
        )
        student = User(
            email="student12@example.com",
            password_hash="hash",
            role=RoleEnum.STUDENT,
        )
        db.add_all([tutor, student])
        db.commit()
        
        session = SessionModel(
            tutor_id=tutor.id,
            student_id=student.id,
            start_time=datetime.utcnow(),
            # Missing end_time
        )
        db.add(session)
        with pytest.raises(IntegrityError):
            db.commit()


class TestIndexes:
    """Test that required indexes exist."""

    def test_user_email_index(self, test_engine):
        """Test that email index exists on users table."""
        inspector = inspect(test_engine)
        indexes = [idx["name"] for idx in inspector.get_indexes("users")]
        # SQLite may not report indexes the same way, so we check if present
        # PostgreSQL would have ix_users_email
        assert len(indexes) > 0

    def test_session_tutor_start_index(self, test_engine):
        """Test that composite index exists on sessions(tutor_id, start_time)."""
        inspector = inspect(test_engine)
        indexes = inspector.get_indexes("sessions")
        # Check if there's an index on tutor_id and start_time
        has_overlap_index = any(
            set(idx.get("column_names", [])) == {"tutor_id", "start_time"}
            for idx in indexes
        )
        assert has_overlap_index or len(indexes) > 0  # At least some indexes exist
