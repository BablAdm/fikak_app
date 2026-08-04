import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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


def get_auth_token():
    """Helper function to register and login a user"""
    client.post(
        "/api/auth/register",
        json={
            "email": "postuser@example.com",
            "username": "postuser",
            "password": "postpass"
        }
    )

    response = client.post(
        "/api/auth/login",
        data={
            "username": "postuser",
            "password": "postpass"
        }
    )
    return response.json()["access_token"]


class TestPosts:
    """Test post endpoints"""

    def test_create_post(self):
        """Test creating a post"""
        token = get_auth_token()

        response = client.post(
            "/api/posts",
            json={
                "title": "Test Post",
                "content": "This is a test post",
                "published": True
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Post"
        assert data["content"] == "This is a test post"
        assert data["published"] is True

    def test_get_posts(self):
        """Test getting all posts"""
        token = get_auth_token()

        # Create a post
        client.post(
            "/api/posts",
            json={
                "title": "Post 1",
                "content": "Content 1",
                "published": True
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Get posts
        response = client.get(
            "/api/posts",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_post_by_id(self):
        """Test getting a specific post"""
        token = get_auth_token()

        # Create a post
        create_response = client.post(
            "/api/posts",
            json={
                "title": "Specific Post",
                "content": "Specific Content",
                "published": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        post_id = create_response.json()["id"]

        # Get post by ID
        response = client.get(
            f"/api/posts/{post_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Specific Post"

    def test_update_post(self):
        """Test updating a post"""
        token = get_auth_token()

        # Create a post
        create_response = client.post(
            "/api/posts",
            json={
                "title": "Original Title",
                "content": "Original Content",
                "published": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        post_id = create_response.json()["id"]

        # Update post
        response = client.put(
            f"/api/posts/{post_id}",
            json={
                "title": "Updated Title",
                "published": True
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["published"] is True

    def test_delete_post(self):
        """Test deleting a post"""
        token = get_auth_token()

        # Create a post
        create_response = client.post(
            "/api/posts",
            json={
                "title": "Post to Delete",
                "content": "Will be deleted",
                "published": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        post_id = create_response.json()["id"]

        # Delete post
        response = client.delete(
            f"/api/posts/{post_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(
            f"/api/posts/{post_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404
