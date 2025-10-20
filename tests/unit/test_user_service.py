"""
Unit tests for UserService.

Tests all CRUD operations, token management, and error handling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from pymongo.errors import PyMongoError

from app.services.user import UserService
from app.models import UserInDB


def create_mock_collection():
    """Helper to create a properly mocked collection."""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    mock_collection.update_one = AsyncMock()
    return mock_collection


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceCreation:
    """Test UserService initialization and user creation/update."""

    async def test_create_or_update_user_creates_new_user(self):
        """Test creating a new user when user doesn't exist."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        github_user = {
            "id": 123456,
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "email": "test@example.com",
            "html_url": "https://github.com/testuser"
        }
        github_token = "gho_test_token_123"

        result = await service.create_or_update_user(github_user, github_token)

        assert result is not None
        assert isinstance(result, UserInDB)
        assert result.github_id == 123456
        assert result.username == "testuser"
        assert result.github_access_token == github_token
        assert result.webhook_configured is False
        mock_collection.insert_one.assert_called_once()

    async def test_create_or_update_user_updates_existing_user(self):
        """Test updating an existing user."""
        existing_user = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "github_id": 123456,
            "username": "testuser",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "webhook_configured": True
        }

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=existing_user)
        mock_collection.update_one = AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        github_user = {
            "id": 123456,
            "login": "testuser",
            "name": "Updated Name",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "email": "newemail@example.com",
            "html_url": "https://github.com/testuser"
        }
        github_token = "gho_new_token_456"

        result = await service.create_or_update_user(github_user, github_token)

        assert result is not None
        assert result.name == "Updated Name"
        assert result.email == "newemail@example.com"
        assert result.github_access_token == github_token
        assert result.webhook_configured is True
        mock_collection.update_one.assert_called_once()

    async def test_create_or_update_user_missing_required_fields(self):
        """Test that ValueError is raised when required fields are missing."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        # Missing 'id' field
        github_user_no_id = {
            "login": "testuser"
        }

        with pytest.raises(ValueError, match="must contain 'id' and 'login' fields"):
            await service.create_or_update_user(github_user_no_id, "token")

        # Missing 'login' field
        github_user_no_login = {
            "id": 123456
        }

        with pytest.raises(ValueError, match="must contain 'id' and 'login' fields"):
            await service.create_or_update_user(github_user_no_login, "token")

    async def test_create_or_update_user_with_token_expiration(self):
        """Test creating user with token expiration date."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        github_user = {
            "id": 123456,
            "login": "testuser",
            "html_url": "https://github.com/testuser"
        }
        github_token = "gho_test_token_123"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        result = await service.create_or_update_user(github_user, github_token, expires_at)

        assert result is not None
        assert result.github_token_expires_at == expires_at

    async def test_create_or_update_user_database_error(self):
        """Test handling of database errors during user creation."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        github_user = {
            "id": 123456,
            "login": "testuser",
            "html_url": "https://github.com/testuser"
        }

        result = await service.create_or_update_user(github_user, "token")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceRetrieval:
    """Test UserService retrieval methods."""

    async def test_get_user_by_id_success(self):
        """Test successful user retrieval by ID."""
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

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_id("507f1f77bcf86cd799439011")

        assert result is not None
        assert isinstance(result, UserInDB)
        assert result.username == "testuser"
        assert str(result.id) == "507f1f77bcf86cd799439011"

    async def test_get_user_by_id_not_found(self):
        """Test user retrieval when user doesn't exist."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_id("507f1f77bcf86cd799439011")

        assert result is None

    async def test_get_user_by_id_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.get_user_by_id("invalid_id")

    async def test_get_user_by_id_database_error(self):
        """Test handling of database errors during retrieval."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_id("507f1f77bcf86cd799439011")

        assert result is None

    async def test_get_user_by_github_id_success(self):
        """Test successful user retrieval by GitHub ID."""
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

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_github_id(123456)

        assert result is not None
        assert result.github_id == 123456
        assert result.username == "testuser"

    async def test_get_user_by_github_id_not_found(self):
        """Test GitHub ID retrieval when user doesn't exist."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_github_id(999999)

        assert result is None

    async def test_get_user_by_username_success(self):
        """Test successful user retrieval by username."""
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

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_username("testuser")

        assert result is not None
        assert result.username == "testuser"

    async def test_get_user_by_username_empty_string(self):
        """Test that empty username returns None."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_username("")

        assert result is None

    async def test_get_user_by_username_not_found(self):
        """Test username retrieval when user doesn't exist."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.get_user_by_username("nonexistent")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceWebhookStatus:
    """Test UserService webhook status management."""

    async def test_update_webhook_status_success(self):
        """Test successful webhook status update."""
        mock_result = MagicMock()
        mock_result.modified_count = 1

        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.update_webhook_status("507f1f77bcf86cd799439011", True)

        assert result is True
        mock_collection.update_one.assert_called_once()

    async def test_update_webhook_status_user_not_found(self):
        """Test webhook status update when user doesn't exist."""
        mock_result = MagicMock()
        mock_result.modified_count = 0

        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.update_webhook_status("507f1f77bcf86cd799439011", True)

        assert result is False

    async def test_update_webhook_status_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.update_webhook_status("invalid_id", True)

    async def test_update_webhook_status_database_error(self):
        """Test handling of database errors during status update."""
        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.update_webhook_status("507f1f77bcf86cd799439011", True)

        assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserServiceTokenVerification:
    """Test UserService token verification."""

    @patch('app.services.user.GitHubService.verify_token_validity')
    async def test_verify_user_tokens_valid(self, mock_verify):
        """Test token verification for valid tokens."""
        user_data = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "github_id": 123456,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "profile_url": "https://github.com/testuser",
            "github_access_token": "valid_token",
            "github_token_expires_at": None,
            "webhook_configured": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        mock_verify.return_value = True

        result = await service.verify_user_tokens("507f1f77bcf86cd799439011")

        assert result is True

    @patch('app.services.user.GitHubService.verify_token_validity')
    async def test_verify_user_tokens_expired(self, mock_verify):
        """Test token verification for expired tokens."""
        user_data = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "github_id": 123456,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "profile_url": "https://github.com/testuser",
            "github_access_token": "expired_token",
            "github_token_expires_at": datetime.now(timezone.utc) - timedelta(days=1),
            "webhook_configured": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.verify_user_tokens("507f1f77bcf86cd799439011")

        assert result is False
        mock_verify.assert_not_called()

    async def test_verify_user_tokens_user_not_found(self):
        """Test token verification when user doesn't exist."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        result = await service.verify_user_tokens("507f1f77bcf86cd799439011")

        assert result is False

    async def test_verify_user_tokens_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.verify_user_tokens("invalid_id")

    @patch('app.services.user.GitHubService.verify_token_validity')
    async def test_verify_user_tokens_github_returns_invalid(self, mock_verify):
        """Test token verification when GitHub returns invalid."""
        user_data = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "github_id": 123456,
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123456",
            "profile_url": "https://github.com/testuser",
            "github_access_token": "invalid_token",
            "github_token_expires_at": None,
            "webhook_configured": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=user_data)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = UserService(mock_db)

        mock_verify.return_value = False

        result = await service.verify_user_tokens("507f1f77bcf86cd799439011")

        assert result is False
