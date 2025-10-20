"""
Unit tests for WebhookService.

Tests all CRUD operations, pagination, filtering, and error handling.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
from pymongo.errors import PyMongoError

from app.services.webhook import WebhookService
from app.models import WebhookNotification


def create_mock_collection():
    """Helper to create a properly mocked webhook collection."""
    mock_collection = AsyncMock()
    mock_collection.find_one = AsyncMock()
    mock_collection.find = MagicMock()
    mock_collection.insert_one = AsyncMock()
    mock_collection.update_one = AsyncMock()
    mock_collection.update_many = AsyncMock()
    mock_collection.delete_one = AsyncMock()
    mock_collection.count_documents = AsyncMock()
    return mock_collection


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookServiceCreation:
    """Test WebhookService notification creation."""

    async def test_create_notification_success(self):
        """Test successful notification creation."""
        mock_collection = create_mock_collection()

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439012")
        mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")
        repository = "testuser/test-repo"
        event_type = "pull_request"
        action = "opened"
        payload = {
            "action": "opened",
            "number": 42,
            "pull_request": {
                "id": 1,
                "title": "Test PR"
            }
        }

        result = await service.create_notification(user_id, repository, event_type, action, payload)

        assert result is not None
        assert isinstance(result, WebhookNotification)
        assert result.user_id == user_id
        assert result.repository == repository
        assert result.event_type == event_type
        assert result.action == action
        assert result.payload == payload
        assert result.processed is False
        mock_collection.insert_one.assert_called_once()

    async def test_create_notification_without_action(self):
        """Test notification creation without action field."""
        mock_collection = create_mock_collection()

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439012")
        mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")
        payload = {"event": "data"}

        result = await service.create_notification(
            user_id, "testuser/repo", "push", None, payload
        )

        assert result is not None
        assert result.action is None

    async def test_create_notification_invalid_user_id(self):
        """Test that non-ObjectId user_id raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="user_id must be an ObjectId"):
            await service.create_notification(
                "not_an_objectid",
                "testuser/repo",
                "push",
                None,
                {}
            )

    async def test_create_notification_invalid_repository(self):
        """Test that invalid repository raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")

        # Empty repository
        with pytest.raises(ValueError, match="repository must be a non-empty string"):
            await service.create_notification(user_id, "", "push", None, {})

        # Non-string repository
        with pytest.raises(ValueError, match="repository must be a non-empty string"):
            await service.create_notification(user_id, None, "push", None, {})

    async def test_create_notification_invalid_event_type(self):
        """Test that invalid event_type raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")

        # Empty event_type
        with pytest.raises(ValueError, match="event_type must be a non-empty string"):
            await service.create_notification(user_id, "repo", "", None, {})

        # Non-string event_type
        with pytest.raises(ValueError, match="event_type must be a non-empty string"):
            await service.create_notification(user_id, "repo", None, None, {})

    async def test_create_notification_invalid_payload(self):
        """Test that non-dict payload raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")

        with pytest.raises(ValueError, match="payload must be a dictionary"):
            await service.create_notification(
                user_id, "repo", "push", None, "not a dict"
            )

    async def test_create_notification_database_error(self):
        """Test handling of database errors during creation."""
        mock_collection = create_mock_collection()
        mock_collection.insert_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        user_id = ObjectId("507f1f77bcf86cd799439011")

        result = await service.create_notification(
            user_id, "repo", "push", None, {}
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookServiceRetrieval:
    """Test WebhookService notification retrieval."""

    async def test_get_user_notifications_success(self):
        """Test successful notification retrieval."""
        notifications = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "user_id": ObjectId("507f1f77bcf86cd799439011"),
                "repository": "testuser/repo1",
                "event_type": "push",
                "action": None,
                "payload": {},
                "processed": False,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439013"),
                "user_id": ObjectId("507f1f77bcf86cd799439011"),
                "repository": "testuser/repo2",
                "event_type": "pull_request",
                "action": "opened",
                "payload": {},
                "processed": False,
                "created_at": datetime.now(timezone.utc)
            }
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=notifications)

        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.get_user_notifications("507f1f77bcf86cd799439011")

        assert len(result) == 2
        assert all(isinstance(n, WebhookNotification) for n in result)
        assert result[0].repository == "testuser/repo1"
        assert result[1].repository == "testuser/repo2"

    async def test_get_user_notifications_with_processed_filter(self):
        """Test notification retrieval with processed filter."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        # Test with processed=False
        await service.get_user_notifications("507f1f77bcf86cd799439011", processed=False)
        mock_collection.find.assert_called_with({
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "processed": False
        })

        # Test with processed=True
        await service.get_user_notifications("507f1f77bcf86cd799439011", processed=True)
        mock_collection.find.assert_called_with({
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "processed": True
        })

    async def test_get_user_notifications_with_pagination(self):
        """Test notification retrieval with pagination."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        await service.get_user_notifications("507f1f77bcf86cd799439011", limit=20, skip=10)

        mock_cursor.skip.assert_called_with(10)
        mock_cursor.limit.assert_called_with(20)

    async def test_get_user_notifications_limit_validation(self):
        """Test limit validation and constraints."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        # Test limit < 1 (should default to 50)
        await service.get_user_notifications("507f1f77bcf86cd799439011", limit=0)
        mock_cursor.limit.assert_called_with(50)

        # Test limit > 100 (should cap at 100)
        await service.get_user_notifications("507f1f77bcf86cd799439011", limit=200)
        mock_cursor.limit.assert_called_with(100)

    async def test_get_user_notifications_skip_validation(self):
        """Test skip validation."""
        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        # Test negative skip (should default to 0)
        await service.get_user_notifications("507f1f77bcf86cd799439011", skip=-5)
        mock_cursor.skip.assert_called_with(0)

    async def test_get_user_notifications_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.get_user_notifications("invalid_id")

    async def test_get_user_notifications_database_error(self):
        """Test handling of database errors during retrieval."""
        mock_collection = create_mock_collection()
        mock_collection.find = MagicMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.get_user_notifications("507f1f77bcf86cd799439011")

        assert result == []

    async def test_get_notification_by_id_success(self):
        """Test successful notification retrieval by ID."""
        notification = {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "repository": "testuser/repo",
            "event_type": "push",
            "action": None,
            "payload": {},
            "processed": False,
            "created_at": datetime.now(timezone.utc)
        }

        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=notification)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.get_notification_by_id("507f1f77bcf86cd799439012")

        assert result is not None
        assert isinstance(result, WebhookNotification)
        assert str(result.id) == "507f1f77bcf86cd799439012"

    async def test_get_notification_by_id_not_found(self):
        """Test notification retrieval when not found."""
        mock_collection = create_mock_collection()
        mock_collection.find_one = AsyncMock(return_value=None)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.get_notification_by_id("507f1f77bcf86cd799439012")

        assert result is None

    async def test_get_notification_by_id_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.get_notification_by_id("invalid_id")


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookServiceProcessing:
    """Test WebhookService notification processing."""

    async def test_mark_as_processed_success(self):
        """Test successful notification marking as processed."""
        mock_result = MagicMock()
        mock_result.modified_count = 1

        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_as_processed("507f1f77bcf86cd799439012")

        assert result is True
        mock_collection.update_one.assert_called_once()

    async def test_mark_as_processed_not_found(self):
        """Test marking notification as processed when not found."""
        mock_result = MagicMock()
        mock_result.modified_count = 0

        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_as_processed("507f1f77bcf86cd799439012")

        assert result is False

    async def test_mark_as_processed_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.mark_as_processed("invalid_id")

    async def test_mark_as_processed_database_error(self):
        """Test handling of database errors during marking."""
        mock_collection = create_mock_collection()
        mock_collection.update_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_as_processed("507f1f77bcf86cd799439012")

        assert result is False

    async def test_mark_all_as_processed_success(self):
        """Test successful marking of all notifications as processed."""
        mock_result = MagicMock()
        mock_result.modified_count = 5

        mock_collection = create_mock_collection()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_all_as_processed("507f1f77bcf86cd799439011")

        assert result == 5
        mock_collection.update_many.assert_called_once()

    async def test_mark_all_as_processed_none_found(self):
        """Test marking all as processed when no unprocessed notifications exist."""
        mock_result = MagicMock()
        mock_result.modified_count = 0

        mock_collection = create_mock_collection()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_all_as_processed("507f1f77bcf86cd799439011")

        assert result == 0

    async def test_mark_all_as_processed_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.mark_all_as_processed("invalid_id")

    async def test_mark_all_as_processed_database_error(self):
        """Test handling of database errors during bulk marking."""
        mock_collection = create_mock_collection()
        mock_collection.update_many = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.mark_all_as_processed("507f1f77bcf86cd799439011")

        assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookServiceCounting:
    """Test WebhookService notification counting."""

    async def test_count_user_notifications_all(self):
        """Test counting all notifications for a user."""
        mock_collection = create_mock_collection()
        mock_collection.count_documents = AsyncMock(return_value=10)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.count_user_notifications("507f1f77bcf86cd799439011")

        assert result == 10
        mock_collection.count_documents.assert_called_with({
            "user_id": ObjectId("507f1f77bcf86cd799439011")
        })

    async def test_count_user_notifications_with_filter(self):
        """Test counting notifications with processed filter."""
        mock_collection = create_mock_collection()
        mock_collection.count_documents = AsyncMock(return_value=5)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        # Count unprocessed
        result = await service.count_user_notifications("507f1f77bcf86cd799439011", processed=False)
        assert result == 5
        mock_collection.count_documents.assert_called_with({
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "processed": False
        })

        # Count processed
        result = await service.count_user_notifications("507f1f77bcf86cd799439011", processed=True)
        mock_collection.count_documents.assert_called_with({
            "user_id": ObjectId("507f1f77bcf86cd799439011"),
            "processed": True
        })

    async def test_count_user_notifications_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.count_user_notifications("invalid_id")

    async def test_count_user_notifications_database_error(self):
        """Test handling of database errors during counting."""
        mock_collection = create_mock_collection()
        mock_collection.count_documents = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.count_user_notifications("507f1f77bcf86cd799439011")

        assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestWebhookServiceDeletion:
    """Test WebhookService notification deletion."""

    async def test_delete_notification_success(self):
        """Test successful notification deletion."""
        mock_result = MagicMock()
        mock_result.deleted_count = 1

        mock_collection = create_mock_collection()
        mock_collection.delete_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.delete_notification("507f1f77bcf86cd799439012")

        assert result is True
        mock_collection.delete_one.assert_called_once()

    async def test_delete_notification_not_found(self):
        """Test deletion when notification doesn't exist."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0

        mock_collection = create_mock_collection()
        mock_collection.delete_one = AsyncMock(return_value=mock_result)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.delete_notification("507f1f77bcf86cd799439012")

        assert result is False

    async def test_delete_notification_invalid_objectid(self):
        """Test that invalid ObjectId raises ValueError."""
        mock_collection = create_mock_collection()
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        with pytest.raises(ValueError, match="Invalid ObjectId"):
            await service.delete_notification("invalid_id")

    async def test_delete_notification_database_error(self):
        """Test handling of database errors during deletion."""
        mock_collection = create_mock_collection()
        mock_collection.delete_one = AsyncMock(side_effect=PyMongoError("Database error"))

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        service = WebhookService(mock_db)

        result = await service.delete_notification("507f1f77bcf86cd799439012")

        assert result is False
