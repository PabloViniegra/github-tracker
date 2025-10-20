"""
Unit tests for Pydantic models.

Tests model validation, serialization, and field constraints.
"""

import pytest
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import ValidationError

from app.models.user import UserInDB, UserResponse
from app.models.webhook import WebhookNotification, WebhookNotificationResponse
from app.models.token import TokenPayload, TokenResponse
from app.models.auth import OAuthState
from app.models.activity import RepositoriesResponse, EventsResponse
from app.models.base import PyObjectId


@pytest.mark.unit
class TestPyObjectId:
    """Test PyObjectId custom type."""

    def test_pyobjectid_in_model(self):
        """Test that PyObjectId works in model."""
        # Test creation with ObjectId
        notification = WebhookNotification(
            _id=ObjectId("507f1f77bcf86cd799439012"),
            user_id=ObjectId("507f1f77bcf86cd799439011"),
            repository="testuser/repo",
            event_type="push",
            payload={},
            processed=False,
            created_at=datetime.now(timezone.utc)
        )

        assert isinstance(notification.id, ObjectId)
        assert isinstance(notification.user_id, ObjectId)


@pytest.mark.unit
class TestUserModels:
    """Test user-related models."""

    def test_user_in_db_creation(self):
        """Test UserInDB model creation with valid data."""
        user_data = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "github_id": 123456,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "profile_url": "https://github.com/testuser",
            "github_access_token": "token123",
            "github_token_expires_at": None,
            "webhook_configured": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        user = UserInDB(**user_data)

        assert user.id == user_data["_id"]
        assert user.github_id == 123456
        assert user.username == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.webhook_configured is False

    def test_user_in_db_optional_fields(self):
        """Test UserInDB with optional fields as None."""
        user_data = {
            "_id": ObjectId(),
            "github_id": 123456,
            "username": "testuser",
            "name": None,
            "email": None,
            "avatar_url": None,
            "profile_url": "https://github.com/testuser",
            "github_access_token": "token123",
            "github_token_expires_at": None,
            "webhook_configured": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        user = UserInDB(**user_data)

        assert user.name is None
        assert user.email is None
        assert user.avatar_url is None

    def test_user_response_from_user_in_db(self):
        """Test UserResponse creation from UserInDB."""
        user_in_db = UserInDB(
            _id=ObjectId("507f1f77bcf86cd799439011"),
            github_id=123456,
            username="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/123456",
            profile_url="https://github.com/testuser",
            github_access_token="token123",
            github_token_expires_at=None,
            webhook_configured=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        response = UserResponse(
            id=str(user_in_db.id),
            github_id=user_in_db.github_id,
            username=user_in_db.username,
            name=user_in_db.name,
            email=user_in_db.email,
            avatar_url=user_in_db.avatar_url,
            profile_url=user_in_db.profile_url,
            webhook_configured=user_in_db.webhook_configured,
            created_at=user_in_db.created_at,
            updated_at=user_in_db.updated_at
        )

        assert response.id == str(user_in_db.id)
        assert response.github_id == user_in_db.github_id
        assert response.username == user_in_db.username
        assert response.webhook_configured is True


@pytest.mark.unit
class TestWebhookModels:
    """Test webhook-related models."""

    def test_webhook_notification_creation(self):
        """Test WebhookNotification model creation."""
        notification_data = {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "repository": "testuser/test-repo",
            "event_type": "pull_request",
            "action": "opened",
            "payload": {"number": 42, "title": "Test PR"},
            "processed": False,
            "created_at": datetime.now(timezone.utc)
        }

        notification = WebhookNotification(**notification_data)

        assert notification.id == notification_data["_id"]
        assert notification.user_id == notification_data["user_id"]
        assert notification.repository == "testuser/test-repo"
        assert notification.event_type == "pull_request"
        assert notification.action == "opened"
        assert notification.processed is False

    def test_webhook_notification_without_action(self):
        """Test WebhookNotification with optional action field."""
        notification = WebhookNotification(
            _id=ObjectId(),
            user_id=ObjectId(),
            repository="testuser/repo",
            event_type="push",
            action=None,
            payload={},
            processed=False,
            created_at=datetime.now(timezone.utc)
        )

        assert notification.action is None

    def test_webhook_notification_response(self):
        """Test WebhookNotificationResponse creation."""
        now = datetime.now(timezone.utc)

        response = WebhookNotificationResponse(
            id="507f1f77bcf86cd799439012",
            repository="testuser/repo",
            event_type="push",
            action=None,
            processed=True,
            created_at=now
        )

        assert response.id == "507f1f77bcf86cd799439012"
        assert response.repository == "testuser/repo"
        assert response.event_type == "push"
        assert response.processed is True


@pytest.mark.unit
class TestTokenModels:
    """Test token-related models."""

    def test_token_payload_creation(self):
        """Test TokenPayload model creation."""
        exp = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub="507f1f77bcf86cd799439011",
            exp=exp,
            type="access"
        )

        assert payload.sub == "507f1f77bcf86cd799439011"
        assert payload.exp == exp
        assert payload.type == "access"

    def test_token_response_creation(self):
        """Test TokenResponse model creation."""
        response = TokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            token_type="bearer",
            expires_in=900
        )

        assert response.access_token == "access_token_123"
        assert response.refresh_token == "refresh_token_456"
        assert response.token_type == "bearer"
        assert response.expires_in == 900


@pytest.mark.unit
class TestAuthModels:
    """Test authentication-related models."""

    def test_oauth_state_creation(self):
        """Test OAuthState model creation."""
        now = datetime.now(timezone.utc)
        oauth_state = OAuthState(created_at=now)

        assert oauth_state.created_at == now

    def test_oauth_state_json_encoding(self):
        """Test OAuthState JSON encoding."""
        now = datetime.now(timezone.utc)
        oauth_state = OAuthState(created_at=now)

        # Test that it can be serialized to JSON
        state_dict = oauth_state.model_dump()
        assert "created_at" in state_dict
        assert state_dict["created_at"] == now


@pytest.mark.unit
class TestActivityModels:
    """Test activity-related models."""

    def test_repositories_response_creation(self):
        """Test RepositoriesResponse model creation."""
        repos_data = [
            {
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
        ]

        repos_response = RepositoriesResponse(repositories=repos_data)

        assert len(repos_response.repositories) == 1
        assert repos_response.repositories[0]["name"] == "test-repo"
        assert repos_response.repositories[0]["language"] == "Python"

    def test_events_response_creation(self):
        """Test EventsResponse model creation."""
        events_data = [
            {
                "id": "12345",
                "type": "PushEvent",
                "actor": {
                    "id": 123,
                    "login": "testuser",
                    "avatar_url": "https://avatars.githubusercontent.com/u/123"
                },
                "repo": {
                    "id": 789012,
                    "name": "testuser/test-repo",
                    "url": "https://api.github.com/repos/testuser/test-repo"
                },
                "payload": {
                    "push_id": 987654,
                    "size": 1,
                    "commits": []
                },
                "public": True,
                "created_at": "2024-01-15T12:00:00Z"
            }
        ]

        events_response = EventsResponse(events=events_data)

        assert len(events_response.events) == 1
        assert events_response.events[0]["type"] == "PushEvent"
        assert events_response.events[0]["repo"]["name"] == "testuser/test-repo"


@pytest.mark.unit
class TestModelSerialization:
    """Test model JSON serialization."""

    def test_user_model_dict(self):
        """Test UserResponse serialization to dict."""
        user = UserResponse(
            id="507f1f77bcf86cd799439011",
            github_id=123456,
            username="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://avatars.githubusercontent.com/u/123456",
            profile_url="https://github.com/testuser",
            webhook_configured=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        user_dict = user.model_dump()

        assert user_dict["id"] == "507f1f77bcf86cd799439011"
        assert user_dict["github_id"] == 123456
        assert user_dict["username"] == "testuser"

    def test_webhook_notification_model_dict(self):
        """Test WebhookNotificationResponse serialization to dict."""
        now = datetime.now(timezone.utc)
        notification = WebhookNotificationResponse(
            id="507f1f77bcf86cd799439012",
            repository="testuser/repo",
            event_type="push",
            action=None,
            processed=False,
            created_at=now
        )

        notif_dict = notification.model_dump()

        assert notif_dict["id"] == "507f1f77bcf86cd799439012"
        assert notif_dict["repository"] == "testuser/repo"
        assert notif_dict["event_type"] == "push"


@pytest.mark.unit
class TestModelValidation:
    """Test model field validation."""

    def test_user_in_db_requires_github_id(self):
        """Test that UserInDB requires github_id."""
        with pytest.raises(ValidationError):
            UserInDB(
                _id=ObjectId(),
                username="testuser",
                profile_url="https://github.com/testuser",
                github_access_token="token",
                webhook_configured=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

    def test_webhook_notification_requires_user_id(self):
        """Test that WebhookNotification requires user_id."""
        with pytest.raises(ValidationError):
            WebhookNotification(
                _id=ObjectId(),
                repository="testuser/repo",
                event_type="push",
                payload={},
                processed=False,
                created_at=datetime.now(timezone.utc)
            )

    def test_token_payload_requires_all_fields(self):
        """Test that TokenPayload requires all fields."""
        with pytest.raises(ValidationError):
            TokenPayload(sub="user_id", type="access")

        with pytest.raises(ValidationError):
            TokenPayload(sub="user_id", exp=datetime.now(timezone.utc))
