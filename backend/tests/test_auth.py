"""Tests for authentication endpoints and authorization."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, RoleEnum


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing works."""
        password = "my_secure_password_123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 20

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "MyPassword123"
        hashed = hash_password(password)
        assert verify_password("mypassword123", hashed) is False


class TestJWTTokenGeneration:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test creating a JWT token."""
        user_id = str(uuid4())
        role = "TUTOR"
        token = create_access_token(data={"sub": user_id, "role": role})
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert "exp" in payload

    def test_token_has_expiry(self):
        """Test that token includes expiry claim."""
        token = create_access_token(data={"sub": str(uuid4()), "role": "TUTOR"})
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        assert "exp" in payload
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        # Token should expire in approximately JWT_EXPIRE_MINUTES
        time_diff = (exp_time - now).total_seconds() / 60
        assert 1400 < time_diff < 1460  # Around 24 hours (1440 minutes)

    def test_token_with_custom_expiry(self):
        """Test creating token with custom expiry."""
        token = create_access_token(
            data={"sub": str(uuid4()), "role": "TUTOR"},
            expires_delta=timedelta(hours=1),
        )
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = (exp_time - now).total_seconds() / 60
        assert 55 < time_diff < 65  # Around 60 minutes

    def test_token_invalid_signature(self):
        """Test that token with wrong signature fails validation."""
        user_id = str(uuid4())
        token = create_access_token(data={"sub": user_id, "role": "TUTOR"})
        
        # Try to decode with wrong secret
        with pytest.raises(Exception):  # JWTError
            jwt.decode(token, "wrong_secret", algorithms=["HS256"])


class TestAuthEndpointsWithClient:
    """Test auth endpoints with FastAPI TestClient."""

    def test_register_tutor_success(self, client, db):
        """Test successful tutor registration."""
        response = client.post(
            "/auth/register-tutor",
            json={
                "email": "newttutor@example.com",
                "password": "SecurePassword123",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newttutor@example.com"
        assert data["role"] == "TUTOR"
        assert "id" in data

    def test_register_tutor_email_exists(self, client, db):
        """Test registration fails if email already exists."""
        # Create a user first
        user = User(
            email="existing@example.com",
            password_hash=hash_password("Password123"),
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        # Try to register with same email
        response = client.post(
            "/auth/register-tutor",
            json={
                "email": "existing@example.com",
                "password": "AnotherPassword123",
            },
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_tutor_weak_password(self, client):
        """Test registration fails with weak password."""
        response = client.post(
            "/auth/register-tutor",
            json={
                "email": "newuser@example.com",
                "password": "weak",  # Less than 8 characters
            },
        )
        
        assert response.status_code == 422  # Validation error

    def test_register_tutor_invalid_email(self, client):
        """Test registration fails with invalid email."""
        response = client.post(
            "/auth/register-tutor",
            json={
                "email": "not-an-email",
                "password": "ValidPassword123",
            },
        )
        
        assert response.status_code == 422  # Validation error

    def test_login_success_tutor(self, client, db):
        """Test successful tutor login."""
        # Create a tutor user
        user = User(
            email="tutor@example.com",
            password_hash=hash_password("TutorPassword123"),
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "tutor@example.com",
                "password": "TutorPassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is valid
        token = data["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["role"] == "TUTOR"

    def test_login_success_student(self, client, db):
        """Test successful student login."""
        # Create a student user
        user = User(
            email="student@example.com",
            password_hash=hash_password("StudentPassword123"),
            role=RoleEnum.STUDENT,
        )
        db.add(user)
        db.commit()
        
        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "student@example.com",
                "password": "StudentPassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
        # Verify token contains STUDENT role
        token = data["access_token"]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["role"] == "STUDENT"

    def test_login_user_not_found(self, client):
        """Test login fails when user doesn't exist."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_wrong_password(self, client, db):
        """Test login fails with wrong password."""
        # Create user
        user = User(
            email="testuser@example.com",
            password_hash=hash_password("CorrectPassword123"),
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        # Try login with wrong password
        response = client.post(
            "/auth/login",
            json={
                "email": "testuser@example.com",
                "password": "WrongPassword123",
            },
        )
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_get_me_success(self, client, db):
        """Test GET /auth/me returns current user info."""
        # Create user
        user = User(
            email="authtest@example.com",
            password_hash=hash_password("AuthTestPassword123"),
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        # Create token
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        
        # Get user info
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["email"] == "authtest@example.com"
        assert data["role"] == "TUTOR"

    def test_get_me_no_token(self, client):
        """Test GET /auth/me fails without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]

    def test_get_me_invalid_token(self, client):
        """Test GET /auth/me fails with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_get_me_malformed_header(self, client):
        """Test GET /auth/me fails with malformed Authorization header."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "InvalidFormat"},
        )
        
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]

    def test_get_me_wrong_bearer_scheme(self, client):
        """Test GET /auth/me fails with wrong authorization scheme."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        
        assert response.status_code == 401


class TestAuthRoleBased:
    """Test role-based access control."""

    def test_tutor_token_structure(self, db):
        """Test that tutor tokens contain correct role."""
        user = User(
            email="tutor_role@example.com",
            password_hash=hash_password("Password123"),
            role=RoleEnum.TUTOR,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["role"] == "TUTOR"

    def test_student_token_structure(self, db):
        """Test that student tokens contain correct role."""
        user = User(
            email="student_role@example.com",
            password_hash=hash_password("Password123"),
            role=RoleEnum.STUDENT,
        )
        db.add(user)
        db.commit()
        
        token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value}
        )
        
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["role"] == "STUDENT"
