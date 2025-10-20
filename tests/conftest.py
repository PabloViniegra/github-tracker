"""
Pytest configuration and shared fixtures.

This module provides test fixtures and configuration for the entire test suite,
including mock database connections, test clients, and common test data.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import AsyncClient
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import Settings, get_settings
from app.core.database import db
from app.core.security import create_access_token, create_refresh_token
from app.main import app
from app.models.user import UserInDB
from app.models.webhook import WebhookNotification


# =============================================================================
# Test Settings
# =============================================================================

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Provide test settings configuration.

    Returns:
        Settings object with test configuration
    """
    return Settings(
        app_name="GitHub Activity Tracker Test",
        app_version="1.0.0-test",
        debug=True,
        log_level="DEBUG",
        mongodb_url="mongodb://localhost:27017",
        mongodb_db_name="github_tracker_test",
        github_client_id="test_client_id",
        github_client_secret="test_client_secret",
        github_redirect_uri="http://localhost:8000/api/v1/auth/github/callback",
        github_webhook_secret="test_webhook_secret_with_sufficient_length",
        webhook_url="http://localhost:8000/api/v1/webhooks/github",
        jwt_secret_key="test_jwt_secret_key_with_sufficient_length_for_validation",
        jwt_algorithm="HS256",
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
        rate_limit_enabled=False,  # Disable rate limiting in tests
        rate_limit_default="1000/minute",
        rate_limit_auth="100/minute",
        rate_limit_activity="500/minute",
        api_v1_prefix="/api/v1",
        frontend_url="http://localhost:3000"
    )


@pytest.fixture(scope="function")
def settings(test_settings: Settings) -> Settings:
    """Get application settings for tests."""
    return test_settings


# =============================================================================
# Database Fixtures
# =============================================================================

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
async def mock_db() -> AsyncMock:
    """
    Provide a mock MongoDB database.

    Returns:
        Mocked AsyncIOMotorDatabase
    """
    db_mock = AsyncMock(spec=AsyncIOMotorDatabase)
    db_mock.users = AsyncMock()
    db_mock.webhook_notifications = AsyncMock()
    return db_mock


@pytest.fixture
def mock_db_collection() -> AsyncMock:
    """
    Provide a mock MongoDB collection.

    Returns:
        Mocked collection
    """
    collection = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find = Mock()
    collection.insert_one = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.update_one = AsyncMock()
    collection.update_many = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.count_documents = AsyncMock()
    collection.create_index = AsyncMock()
    return collection


# =============================================================================
# HTTP Client Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Get test client for API requests."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP client for testing.

    Yields:
        AsyncClient instance
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """
    Provide a mock httpx AsyncClient.

    Returns:
        Mocked AsyncClient
    """
    client_mock = AsyncMock()
    client_mock.get = AsyncMock()
    client_mock.post = AsyncMock()
    client_mock.put = AsyncMock()
    client_mock.delete = AsyncMock()
    client_mock.is_closed = False
    client_mock.aclose = AsyncMock()
    return client_mock


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_github_user() -> Dict:
    """Sample GitHub user data."""
    return {
        "id": 123456,
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/123456",
        "email": "test@example.com",
        "html_url": "https://github.com/testuser",
        "bio": "Test bio",
        "public_repos": 10,
        "followers": 50,
        "following": 30
    }


@pytest.fixture
def sample_user_in_db(sample_github_user: Dict) -> UserInDB:
    """
    Provide a sample user as stored in database.

    Args:
        sample_github_user: Sample GitHub user fixture

    Returns:
        UserInDB instance
    """
    return UserInDB(
        _id=ObjectId("507f1f77bcf86cd799439011"),
        github_id=sample_github_user["id"],
        username=sample_github_user["login"],
        name=sample_github_user["name"],
        email=sample_github_user["email"],
        avatar_url=sample_github_user["avatar_url"],
        profile_url=sample_github_user["html_url"],
        github_access_token="gho_test_token_1234567890",
        github_token_expires_at=None,
        webhook_configured=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_access_token(sample_user_in_db: UserInDB) -> str:
    """
    Generate a sample JWT access token.

    Args:
        sample_user_in_db: Sample user fixture

    Returns:
        JWT access token string
    """
    token, _ = create_access_token(str(sample_user_in_db.id))
    return token


@pytest.fixture
def sample_refresh_token(sample_user_in_db: UserInDB) -> str:
    """
    Generate a sample JWT refresh token.

    Args:
        sample_user_in_db: Sample user fixture

    Returns:
        JWT refresh token string
    """
    token, _ = create_refresh_token(str(sample_user_in_db.id))
    return token


@pytest.fixture
def auth_headers(sample_access_token: str) -> Dict[str, str]:
    """
    Provide authorization headers with JWT token.

    Args:
        sample_access_token: Sample access token fixture

    Returns:
        Dict with Authorization header
    """
    return {"Authorization": f"Bearer {sample_access_token}"}


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
        "forks_count": 2
    }


@pytest.fixture
def sample_github_repos(sample_github_repo: Dict) -> list:
    """
    Provide sample GitHub repositories data.

    Returns:
        List of repository dicts
    """
    return [
        sample_github_repo,
        {
            "id": 789013,
            "name": "another-repo",
            "full_name": "testuser/another-repo",
            "private": True,
            "html_url": "https://github.com/testuser/another-repo",
            "description": "Another test repository",
            "fork": False,
            "created_at": "2024-01-10T00:00:00Z",
            "updated_at": "2024-01-20T00:00:00Z",
            "pushed_at": "2024-01-20T00:00:00Z",
            "stargazers_count": 5,
            "watchers_count": 3,
            "language": "JavaScript",
            "forks_count": 1
        }
    ]


@pytest.fixture
def sample_github_events() -> list:
    """
    Provide sample GitHub events data.

    Returns:
        List of event dicts
    """
    return [
        {
            "id": "12345",
            "type": "PushEvent",
            "actor": {
                "id": 123456,
                "login": "testuser",
                "avatar_url": "https://avatars.githubusercontent.com/u/123456"
            },
            "repo": {
                "id": 789012,
                "name": "testuser/test-repo"
            },
            "payload": {
                "push_id": 9876543,
                "size": 1,
                "distinct_size": 1,
                "ref": "refs/heads/main",
                "commits": [
                    {
                        "sha": "abc123",
                        "message": "Test commit",
                        "author": {
                            "name": "Test User",
                            "email": "test@example.com"
                        }
                    }
                ]
            },
            "public": True,
            "created_at": "2024-01-15T12:00:00Z"
        },
        {
            "id": "12346",
            "type": "PullRequestEvent",
            "actor": {
                "id": 123456,
                "login": "testuser",
                "avatar_url": "https://avatars.githubusercontent.com/u/123456"
            },
            "repo": {
                "id": 789012,
                "name": "testuser/test-repo"
            },
            "payload": {
                "action": "opened",
                "number": 1,
                "pull_request": {
                    "id": 1,
                    "title": "Test PR",
                    "state": "open"
                }
            },
            "public": True,
            "created_at": "2024-01-16T12:00:00Z"
        }
    ]


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload."""
    return {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1,
            "number": 42,
            "title": "Test PR",
            "state": "open",
            "user": {
                "login": "testuser",
                "id": 123456,
            },
            "html_url": "https://github.com/testuser/test-repo/pull/42",
        },
        "repository": {
            "id": 789012,
            "name": "test-repo",
            "full_name": "testuser/test-repo",
            "owner": {
                "login": "testuser",
                "id": 123456
            }
        },
        "sender": {
            "login": "testuser",
            "id": 123456
        }
    }


@pytest.fixture
def sample_webhook_notification(
    sample_user_in_db: UserInDB,
    sample_webhook_payload: Dict
) -> WebhookNotification:
    """
    Provide a sample webhook notification.

    Args:
        sample_user_in_db: Sample user fixture
        sample_webhook_payload: Sample webhook payload fixture

    Returns:
        WebhookNotification instance
    """
    return WebhookNotification(
        _id=ObjectId("507f1f77bcf86cd799439012"),
        user_id=sample_user_in_db.id,
        repository="testuser/test-repo",
        event_type="pull_request",
        action="opened",
        payload=sample_webhook_payload,
        processed=False,
        created_at=datetime.now(timezone.utc)
    )


# =============================================================================
# OAuth Fixtures
# =============================================================================

@pytest.fixture
def oauth_state() -> str:
    """OAuth state token."""
    return "test_oauth_state_token_1234567890"


@pytest.fixture
def oauth_code() -> str:
    """OAuth authorization code."""
    return "test_oauth_authorization_code"


@pytest.fixture
def mock_github_token():
    """Mock GitHub access token."""
    return "gho_test_token_1234567890abcdef"


@pytest.fixture
def mock_jwt_token(sample_access_token: str):
    """Mock JWT access token."""
    return sample_access_token


@pytest.fixture
def github_token_response(mock_github_token: str) -> Dict:
    """GitHub token exchange response."""
    return {
        "access_token": mock_github_token,
        "token_type": "bearer",
        "scope": "repo,read:user,user:email,admin:repo_hook"
    }


# =============================================================================
# Webhook Signature Fixtures
# =============================================================================

@pytest.fixture
def webhook_signature(test_settings: Settings, sample_webhook_payload: Dict) -> str:
    """
    Generate a valid GitHub webhook signature.

    Args:
        test_settings: Test settings fixture
        sample_webhook_payload: Sample webhook payload

    Returns:
        HMAC signature string
    """
    import hashlib
    import hmac
    import json

    payload_bytes = json.dumps(sample_webhook_payload).encode()
    mac = hmac.new(
        test_settings.github_webhook_secret.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    )
    return f"sha256={mac.hexdigest()}"


# =============================================================================
# Mock Service Fixtures
# =============================================================================

@pytest.fixture
def mock_github_service(
    sample_github_user: Dict,
    sample_github_repos: list,
    sample_github_events: list,
    github_token_response: Dict
) -> Mock:
    """
    Provide a mock GitHub service.

    Returns:
        Mocked GitHubService
    """
    service = Mock()
    service.get_authorization_url = Mock(
        return_value="https://github.com/login/oauth/authorize?client_id=test&redirect_uri=http://localhost:8000/callback&scope=repo&state=test_state"
    )
    service.exchange_code_for_token = AsyncMock(return_value=github_token_response)
    service.get_user_info = AsyncMock(return_value=sample_github_user)
    service.verify_token_validity = AsyncMock(return_value=True)
    service.get_user_repos = AsyncMock(return_value=sample_github_repos)
    service.get_user_activity = AsyncMock(return_value=sample_github_events)
    service.create_webhook = AsyncMock(return_value={
        "id": 123456789,
        "name": "web",
        "active": True,
        "events": ["push", "pull_request"],
        "config": {
            "url": "http://localhost:8000/api/v1/webhooks/github",
            "content_type": "json"
        }
    })
    service.list_webhooks = AsyncMock(return_value=[])
    service.delete_webhook = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_user_service(sample_user_in_db: UserInDB) -> Mock:
    """
    Provide a mock User service.

    Args:
        sample_user_in_db: Sample user fixture

    Returns:
        Mocked UserService
    """
    service = Mock()
    service.create_or_update_user = AsyncMock(return_value=sample_user_in_db)
    service.get_user_by_id = AsyncMock(return_value=sample_user_in_db)
    service.get_user_by_github_id = AsyncMock(return_value=sample_user_in_db)
    service.get_user_by_username = AsyncMock(return_value=sample_user_in_db)
    service.update_webhook_status = AsyncMock(return_value=True)
    service.verify_user_tokens = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_webhook_service(sample_webhook_notification: WebhookNotification) -> Mock:
    """
    Provide a mock Webhook service.

    Args:
        sample_webhook_notification: Sample webhook notification fixture

    Returns:
        Mocked WebhookService
    """
    service = Mock()
    service.create_notification = AsyncMock(return_value=sample_webhook_notification)
    service.get_user_notifications = AsyncMock(return_value=[sample_webhook_notification])
    service.get_notification_by_id = AsyncMock(return_value=sample_webhook_notification)
    service.mark_as_processed = AsyncMock(return_value=True)
    service.mark_all_as_processed = AsyncMock(return_value=1)
    service.count_user_notifications = AsyncMock(return_value=1)
    service.delete_notification = AsyncMock(return_value=True)
    return service


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.

    Yields:
        Event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
