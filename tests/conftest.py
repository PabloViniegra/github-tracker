"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app
from app.core.config import get_settings
from app.core.database import db


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
async def test_db():
    """Create a test database using mongomock."""
    client = AsyncMongoMockClient()
    test_database = client["test_github_tracker"]

    # Save original db client
    original_client = db.client

    # Replace with test client
    db.client = client

    yield test_database

    # Restore original client
    db.client = original_client


@pytest.fixture
def client():
    """Get test client for API requests."""
    return TestClient(app)


@pytest.fixture
def sample_github_user():
    """Sample GitHub user data."""
    return {
        "id": 123456,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/123456",
        "email": "test@example.com",
        "html_url": "https://github.com/testuser",
    }


@pytest.fixture
def sample_github_repo():
    """Sample GitHub repository data."""
    return {
        "id": 789012,
        "name": "test-repo",
        "full_name": "testuser/test-repo",
        "private": False,
        "html_url": "https://github.com/testuser/test-repo",
        "description": "A test repository",
        "fork": False,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T00:00:00Z",
        "pushed_at": "2024-01-15T12:00:00Z",
        "stargazers_count": 10,
        "watchers_count": 5,
        "language": "Python",
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload."""
    return {
        "action": "opened",
        "pull_request": {
            "id": 1,
            "number": 42,
            "title": "Test PR",
            "user": {
                "login": "testuser",
                "id": 123456,
            },
            "html_url": "https://github.com/testuser/test-repo/pull/42",
        },
        "repository": {
            "full_name": "testuser/test-repo",
        },
    }


@pytest.fixture
def mock_github_token():
    """Mock GitHub access token."""
    return "ghp_test_token_1234567890abcdef"


@pytest.fixture
def mock_jwt_token():
    """Mock JWT access token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NWE3ZjViMjNjNDU2NzAwMDFhYmNkZWYiLCJleHAiOjE3MDUzMjAwMDAsInR5cGUiOiJhY2Nlc3MifQ"
