import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
import models

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Provide an in-memory SQLite session in place of the real database"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestAuthentication:
    """Test authentication endpoints"""

    def test_register_user(self):
        """Test user registration"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "testpass123"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert "id" in data

    def test_register_duplicate_user(self):
        """Test registration with duplicate username"""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "email": "user1@example.com",
                "username": "duplicate",
                "password": "pass123"
            }
        )

        # Duplicate registration
        response = client.post(
            "/api/auth/register",
            json={
                "email": "user2@example.com",
                "username": "duplicate",
                "password": "pass456"
            }
        )
        assert response.status_code == 400

    def test_login_success(self):
        """Test successful login"""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "username": "loginuser",
                "password": "loginpass"
            }
        )

        # Login
        response = client.post(
            "/api/auth/login",
            data={
                "username": "loginuser",
                "password": "loginpass"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        """Test login with wrong password"""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user123",
                "password": "correctpass"
            }
        )

        # Login with wrong password
        response = client.post(
            "/api/auth/login",
            data={
                "username": "user123",
                "password": "wrongpass"
            }
        )
        assert response.status_code == 401

    def test_get_current_user(self):
        """Test getting current user info"""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "email": "current@example.com",
                "username": "currentuser",
                "password": "pass123"
            }
        )

        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "currentuser",
                "password": "pass123"
            }
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "currentuser"
        assert data["email"] == "current@example.com"

    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
