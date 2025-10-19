"""
Webhook service for managing webhook notifications.

This module provides the WebhookService class which handles all webhook
notification database operations including creation, retrieval, and processing.
"""

import logging
from typing import Optional, Dict, Any, List

from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.models import WebhookNotification

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service class for webhook notification database operations.

    This service handles CRUD operations for webhook notifications received
    from GitHub, including filtering by processing status and pagination.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        """
        Initialize the WebhookService.

        Args:
            db: AsyncIO Motor database instance
        """
        self.collection = db["webhook_notifications"]
        logger.info("WebhookService initialized")

    async def create_notification(
        self,
        user_id: ObjectId,
        repository: str,
        event_type: str,
        action: Optional[str],
        payload: Dict[str, Any]
    ) -> Optional[WebhookNotification]:
        """
        Create a new webhook notification in the database.

        This method stores incoming webhook events from GitHub for later
        retrieval and processing by users.

        Args:
            user_id: MongoDB ObjectId of the user who owns the repository
            repository: Full repository name (e.g., "owner/repo")
            event_type: Type of GitHub event (e.g., "push", "pull_request", "issues")
            action: Optional action associated with the event (e.g., "opened", "closed")
            payload: Complete webhook payload from GitHub

        Returns:
            WebhookNotification object representing the created notification,
            or None if the operation fails

        Raises:
            ValueError: If required fields are invalid or missing
        """
        try:
            # Validate inputs
            if not isinstance(user_id, ObjectId):
                logger.error(f"Invalid user_id type: {type(user_id)}")
                raise ValueError("user_id must be an ObjectId instance")

            if not repository or not isinstance(repository, str):
                logger.error(f"Invalid repository: {repository}")
                raise ValueError("repository must be a non-empty string")

            if not event_type or not isinstance(event_type, str):
                logger.error(f"Invalid event_type: {event_type}")
                raise ValueError("event_type must be a non-empty string")

            if not isinstance(payload, dict):
                logger.error(f"Invalid payload type: {type(payload)}")
                raise ValueError("payload must be a dictionary")

            notification_data = {
                "user_id": user_id,
                "repository": repository,
                "event_type": event_type,
                "action": action,
                "payload": payload,
                "processed": False,
                "created_at": datetime.now(timezone.utc)
            }

            logger.info(f"Creating notification for user {user_id}, repo: {repository}, event: {event_type}")

            result = await self.collection.insert_one(notification_data)
            notification_data["_id"] = result.inserted_id

            logger.info(f"Successfully created notification {result.inserted_id}")
            return WebhookNotification(**notification_data)

        except ValueError as ve:
            logger.error(f"Validation error in create_notification: {ve}")
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in create_notification: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in create_notification: {e}", exc_info=True)
            return None

    async def get_user_notifications(
        self,
        user_id: str,
        processed: Optional[bool] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[WebhookNotification]:
        """
        Retrieve webhook notifications for a specific user with pagination.

        This method supports filtering by processing status and includes
        pagination parameters for handling large notification lists.

        Args:
            user_id: String representation of the user's MongoDB ObjectId
            processed: Optional filter - True for processed only, False for unprocessed only,
                      None for all notifications
            limit: Maximum number of notifications to return (default: 50, max: 100)
            skip: Number of notifications to skip for pagination (default: 0)

        Returns:
            List of WebhookNotification objects sorted by creation date (newest first)

        Raises:
            ValueError: If user_id is not a valid ObjectId or if limit/skip are invalid
        """
        try:
            # Validate user_id
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            # Validate and constrain limit
            if limit < 1:
                logger.warning(f"Invalid limit: {limit}, using default 50")
                limit = 50
            elif limit > 100:
                logger.warning(f"Limit {limit} exceeds maximum, capping at 100")
                limit = 100

            # Validate skip
            if skip < 0:
                logger.warning(f"Invalid skip: {skip}, using 0")
                skip = 0

            # Build query
            query = {"user_id": ObjectId(user_id)}
            if processed is not None:
                query["processed"] = processed

            logger.debug(f"Fetching notifications for user {user_id} with filter: {query}, skip={skip}, limit={limit}")

            cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
            notifications = await cursor.to_list(length=limit)

            logger.info(f"Retrieved {len(notifications)} notifications for user {user_id}")

            return [WebhookNotification(**notif) for notif in notifications]

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in get_user_notifications: {pe}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_user_notifications: {e}", exc_info=True)
            return []

    async def get_notification_by_id(self, notification_id: str) -> Optional[WebhookNotification]:
        """
        Retrieve a specific notification by its ID.

        Args:
            notification_id: String representation of the notification's MongoDB ObjectId

        Returns:
            WebhookNotification object if found, None otherwise

        Raises:
            ValueError: If notification_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(notification_id):
                logger.warning(f"Invalid ObjectId format: {notification_id}")
                raise ValueError(f"Invalid ObjectId: {notification_id}")

            logger.debug(f"Fetching notification by id: {notification_id}")
            notification = await self.collection.find_one({"_id": ObjectId(notification_id)})

            if notification:
                logger.debug(f"Found notification: {notification_id}")
                return WebhookNotification(**notification)

            logger.debug(f"Notification not found: {notification_id}")
            return None

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in get_notification_by_id: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_notification_by_id: {e}", exc_info=True)
            return None

    async def mark_as_processed(self, notification_id: str) -> bool:
        """
        Mark a specific notification as processed.

        Args:
            notification_id: String representation of the notification's MongoDB ObjectId

        Returns:
            True if update was successful, False otherwise

        Raises:
            ValueError: If notification_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(notification_id):
                logger.warning(f"Invalid ObjectId format: {notification_id}")
                raise ValueError(f"Invalid ObjectId: {notification_id}")

            logger.info(f"Marking notification {notification_id} as processed")

            result = await self.collection.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc)
                }}
            )

            if result.modified_count > 0:
                logger.info(f"Successfully marked notification {notification_id} as processed")
                return True
            else:
                logger.warning(f"No notification found or already processed: {notification_id}")
                return False

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in mark_as_processed: {pe}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in mark_as_processed: {e}", exc_info=True)
            return False

    async def mark_all_as_processed(self, user_id: str) -> int:
        """
        Mark all unprocessed notifications for a user as processed.

        Args:
            user_id: String representation of the user's MongoDB ObjectId

        Returns:
            Number of notifications marked as processed

        Raises:
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            logger.info(f"Marking all unprocessed notifications for user {user_id} as processed")

            result = await self.collection.update_many(
                {"user_id": ObjectId(user_id), "processed": False},
                {"$set": {
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc)
                }}
            )

            count = result.modified_count
            logger.info(f"Marked {count} notifications as processed for user {user_id}")

            return count

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in mark_all_as_processed: {pe}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in mark_all_as_processed: {e}", exc_info=True)
            return 0

    async def count_user_notifications(
        self,
        user_id: str,
        processed: Optional[bool] = None
    ) -> int:
        """
        Count the total number of notifications for a user.

        Useful for pagination to determine total pages.

        Args:
            user_id: String representation of the user's MongoDB ObjectId
            processed: Optional filter - True for processed only, False for unprocessed only,
                      None for all notifications

        Returns:
            Total count of matching notifications

        Raises:
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            query = {"user_id": ObjectId(user_id)}
            if processed is not None:
                query["processed"] = processed

            logger.debug(f"Counting notifications for user {user_id} with filter: {query}")

            count = await self.collection.count_documents(query)

            logger.debug(f"Found {count} notifications for user {user_id}")
            return count

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in count_user_notifications: {pe}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in count_user_notifications: {e}", exc_info=True)
            return 0

    async def delete_notification(self, notification_id: str) -> bool:
        """
        Delete a specific notification.

        Args:
            notification_id: String representation of the notification's MongoDB ObjectId

        Returns:
            True if deletion was successful, False otherwise

        Raises:
            ValueError: If notification_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(notification_id):
                logger.warning(f"Invalid ObjectId format: {notification_id}")
                raise ValueError(f"Invalid ObjectId: {notification_id}")

            logger.info(f"Deleting notification {notification_id}")

            result = await self.collection.delete_one({"_id": ObjectId(notification_id)})

            if result.deleted_count > 0:
                logger.info(f"Successfully deleted notification {notification_id}")
                return True
            else:
                logger.warning(f"No notification found to delete: {notification_id}")
                return False

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in delete_notification: {pe}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in delete_notification: {e}", exc_info=True)
            return False
