"""
User service for managing user data and operations.

This module provides the UserService class which handles all user-related
database operations including creation, updates, retrieval, and token verification.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.models import UserInDB
from app.services.github import GitHubService

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related database operations.

    This service handles all CRUD operations for users, including OAuth token
    management and webhook configuration status.
    """

    def __init__(self, db: AsyncIOMotorDatabase, github_service: Optional[GitHubService] = None) -> None:
        """
        Initialize the UserService.

        Args:
            db: AsyncIO Motor database instance
            github_service: Optional GitHubService instance for token verification
        """
        self.collection = db["users"]
        self._github_service = github_service
        logger.info("UserService initialized")

    async def create_or_update_user(
        self,
        github_user: Dict[str, Any],
        github_token: str,
        token_expires_at: Optional[datetime] = None
    ) -> Optional[UserInDB]:
        """
        Create a new user or update an existing user in the database.

        This method handles the OAuth flow by creating new users or updating
        existing users with fresh GitHub data and access tokens.

        Args:
            github_user: Dictionary containing GitHub user information with keys:
                - id: GitHub user ID (required)
                - login: GitHub username (required)
                - name: User's full name (optional)
                - avatar_url: Profile picture URL (optional)
                - email: User's email (optional)
                - html_url: GitHub profile URL (required)
            github_token: GitHub OAuth access token
            token_expires_at: Optional expiration datetime for the token

        Returns:
            UserInDB object representing the created or updated user,
            or None if the operation fails

        Raises:
            ValueError: If required fields are missing from github_user
        """
        try:
            # Validate required fields
            if "id" not in github_user or "login" not in github_user:
                logger.error("Missing required fields in github_user data")
                raise ValueError("github_user must contain 'id' and 'login' fields")

            user_data = {
                "github_id": github_user["id"],
                "username": github_user["login"],
                "name": github_user.get("name"),
                "avatar_url": github_user.get("avatar_url"),
                "email": github_user.get("email"),
                "profile_url": github_user.get("html_url", ""),
                "github_access_token": github_token,
                "github_token_expires_at": token_expires_at,
                "updated_at": datetime.now(timezone.utc)
            }

            logger.debug(f"Attempting to create or update user with github_id={github_user['id']}")

            existing_user = await self.collection.find_one({"github_id": github_user["id"]})

            if existing_user:
                logger.info(f"Updating existing user: {existing_user.get('username')}")

                await self.collection.update_one(
                    {"_id": existing_user["_id"]},
                    {"$set": user_data}
                )

                user_data["_id"] = existing_user["_id"]
                user_data["created_at"] = existing_user["created_at"]
                user_data["webhook_configured"] = existing_user.get("webhook_configured", False)
            else:
                logger.info(f"Creating new user: {github_user['login']}")

                user_data["created_at"] = datetime.now(timezone.utc)
                user_data["webhook_configured"] = False

                result = await self.collection.insert_one(user_data)
                user_data["_id"] = result.inserted_id

            logger.info(f"Successfully {'updated' if existing_user else 'created'} user: {user_data['username']}")
            return UserInDB(**user_data)

        except ValueError as ve:
            logger.error(f"Validation error in create_or_update_user: {ve}")
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in create_or_update_user: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in create_or_update_user: {e}", exc_info=True)
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Retrieve a user by their MongoDB ObjectId.

        Args:
            user_id: String representation of the user's MongoDB ObjectId

        Returns:
            UserInDB object if found, None otherwise

        Raises:
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            logger.debug(f"Fetching user by id: {user_id}")
            user = await self.collection.find_one({"_id": ObjectId(user_id)})

            if user:
                logger.debug(f"Found user: {user.get('username')}")
                return UserInDB(**user)

            logger.debug(f"User not found with id: {user_id}")
            return None

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in get_user_by_id: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_by_id: {e}", exc_info=True)
            return None

    async def get_user_by_github_id(self, github_id: int) -> Optional[UserInDB]:
        """
        Retrieve a user by their GitHub user ID.

        Args:
            github_id: GitHub user ID (integer)

        Returns:
            UserInDB object if found, None otherwise
        """
        try:
            logger.debug(f"Fetching user by github_id: {github_id}")
            user = await self.collection.find_one({"github_id": github_id})

            if user:
                logger.debug(f"Found user: {user.get('username')}")
                return UserInDB(**user)

            logger.debug(f"User not found with github_id: {github_id}")
            return None

        except PyMongoError as pe:
            logger.error(f"Database error in get_user_by_github_id: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_by_github_id: {e}", exc_info=True)
            return None

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Retrieve a user by their GitHub username.

        Args:
            username: GitHub username (login)

        Returns:
            UserInDB object if found, None otherwise
        """
        try:
            if not username:
                logger.warning("Empty username provided")
                return None

            logger.debug(f"Fetching user by username: {username}")
            user = await self.collection.find_one({"username": username})

            if user:
                logger.debug(f"Found user: {username}")
                return UserInDB(**user)

            logger.debug(f"User not found with username: {username}")
            return None

        except PyMongoError as pe:
            logger.error(f"Database error in get_user_by_username: {pe}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_user_by_username: {e}", exc_info=True)
            return None

    async def update_webhook_status(self, user_id: str, configured: bool) -> bool:
        """
        Update the webhook configuration status for a user.

        Args:
            user_id: String representation of the user's MongoDB ObjectId
            configured: Boolean indicating whether webhook is configured

        Returns:
            True if update was successful, False otherwise

        Raises:
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            logger.info(f"Updating webhook status for user {user_id} to {configured}")

            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "webhook_configured": configured,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )

            if result.modified_count > 0:
                logger.info(f"Successfully updated webhook status for user {user_id}")
                return True
            else:
                logger.warning(f"No user found or no changes made for user_id: {user_id}")
                return False

        except ValueError:
            raise
        except PyMongoError as pe:
            logger.error(f"Database error in update_webhook_status: {pe}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in update_webhook_status: {e}", exc_info=True)
            return False

    async def verify_user_tokens(self, user_id: str) -> bool:
        """
        Verify that a user's GitHub access token is still valid.

        This method checks both the token expiration time (if set) and
        validates the token with GitHub's API.

        Args:
            user_id: String representation of the user's MongoDB ObjectId

        Returns:
            True if tokens are valid, False otherwise

        Raises:
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            if not ObjectId.is_valid(user_id):
                logger.warning(f"Invalid ObjectId format: {user_id}")
                raise ValueError(f"Invalid ObjectId: {user_id}")

            logger.debug(f"Verifying tokens for user: {user_id}")

            user = await self.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User not found for token verification: {user_id}")
                return False

            # Check token expiration if set
            if user.github_token_expires_at:
                if datetime.now(timezone.utc) > user.github_token_expires_at:
                    logger.info(f"Token expired for user: {user.username}")
                    return False

            # Verify token validity with GitHub
            # Create temporary service if not injected
            github_service = self._github_service or GitHubService()
            try:
                is_valid = await github_service.verify_token_validity(user.github_access_token)

                if is_valid:
                    logger.debug(f"Token valid for user: {user.username}")
                else:
                    logger.warning(f"Token invalid for user: {user.username}")

                return is_valid
            finally:
                # Clean up if we created a temporary service
                if self._github_service is None:
                    await github_service.close()

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in verify_user_tokens: {e}", exc_info=True)
            return False
