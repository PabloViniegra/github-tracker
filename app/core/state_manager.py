"""OAuth state management using Redis.

This module provides a distributed state manager for OAuth flows using Redis
as the backing store. This allows for horizontal scaling of the application
without losing OAuth state between instances.
"""

import logging
from typing import Optional

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OAuthStateManager:
    """
    Manages OAuth state tokens using Redis for distributed storage.

    This class handles the storage, verification, and automatic expiration
    of OAuth state tokens. Using Redis allows multiple application instances
    to share state, enabling horizontal scaling.

    Attributes:
        OAUTH_STATE_TTL: Time-to-live for state tokens in seconds (10 minutes)
        STATE_KEY_PREFIX: Redis key prefix for OAuth states
    """

    OAUTH_STATE_TTL: int = 600  # 10 minutes in seconds
    STATE_KEY_PREFIX: str = "oauth_state:"

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        """
        Initialize the OAuth state manager.

        Args:
            redis_client: Optional Redis client instance. If not provided,
                         a new client will be created from settings.
        """
        self._redis_client = redis_client
        self._owned_client = redis_client is None
        logger.info("OAuthStateManager initialized")

    @property
    def redis_client(self) -> redis.Redis:
        """
        Get or create the Redis client instance.

        Returns:
            redis.Redis: Async Redis client instance

        Raises:
            RuntimeError: If Redis client creation fails
        """
        if self._redis_client is None:
            try:
                settings = get_settings()
                self._redis_client = redis.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                )
                logger.debug("Created new Redis client for OAuthStateManager")
            except Exception as e:
                logger.error(f"Failed to create Redis client: {str(e)}")
                raise RuntimeError(f"Redis client initialization failed: {str(e)}")
        return self._redis_client

    async def close(self) -> None:
        """
        Close the Redis client and cleanup resources.

        Only closes the client if it was created by this instance.
        """
        if self._owned_client and self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None
            logger.debug("Closed Redis client")

    def _get_key(self, state: str) -> str:
        """
        Generate the Redis key for a given state token.

        Args:
            state: OAuth state token

        Returns:
            str: Redis key with prefix
        """
        return f"{self.STATE_KEY_PREFIX}{state}"

    async def create_state(self, state: str) -> bool:
        """
        Create and store an OAuth state token in Redis.

        The state token is stored with automatic expiration based on OAUTH_STATE_TTL.

        Args:
            state: OAuth state token to store

        Returns:
            bool: True if successfully stored, False otherwise

        Example:
            ```python
            state_manager = OAuthStateManager()
            state = secrets.token_urlsafe(32)
            success = await state_manager.create_state(state)
            ```
        """
        try:
            key = self._get_key(state)
            # Store with SETEX for atomic set-with-expiration
            await self.redis_client.setex(
                key,
                self.OAUTH_STATE_TTL,
                "1"  # Value doesn't matter, we just check existence
            )
            logger.debug(
                f"Created OAuth state: {state[:8]}... "
                f"(expires in {self.OAUTH_STATE_TTL}s)"
            )
            return True

        except RedisError as e:
            logger.error(f"Redis error creating state {state[:8]}...: {str(e)}")
            return False

        except Exception as e:
            logger.error(
                f"Unexpected error creating state {state[:8]}...: {str(e)}",
                exc_info=True
            )
            return False

    async def verify_and_consume_state(self, state: str) -> bool:
        """
        Verify that an OAuth state exists and atomically consume it.

        This method checks if the state exists in Redis and, if so, deletes it
        in a single operation to prevent replay attacks. The state can only be
        consumed once.

        Args:
            state: OAuth state token to verify and consume

        Returns:
            bool: True if state was valid and consumed, False otherwise

        Example:
            ```python
            state_manager = OAuthStateManager()
            if await state_manager.verify_and_consume_state(state):
                # State is valid, proceed with OAuth flow
                pass
            else:
                # Invalid or expired state, reject request
                raise HTTPException(status_code=400, detail="Invalid state")
            ```
        """
        try:
            key = self._get_key(state)
            # Use DEL to atomically remove and return count of deleted keys
            deleted_count = await self.redis_client.delete(key)

            if deleted_count > 0:
                logger.debug(f"Verified and consumed OAuth state: {state[:8]}...")
                return True
            else:
                logger.warning(
                    f"OAuth state not found or already consumed: {state[:8]}..."
                )
                return False

        except RedisError as e:
            logger.error(
                f"Redis error verifying state {state[:8]}...: {str(e)}"
            )
            return False

        except Exception as e:
            logger.error(
                f"Unexpected error verifying state {state[:8]}...: {str(e)}",
                exc_info=True
            )
            return False

    async def health_check(self) -> bool:
        """
        Check if the Redis connection is healthy.

        Returns:
            bool: True if Redis is accessible, False otherwise

        Example:
            ```python
            state_manager = OAuthStateManager()
            if await state_manager.health_check():
                print("Redis connection healthy")
            ```
        """
        try:
            await self.redis_client.ping()
            logger.debug("Redis health check passed")
            return True

        except RedisError as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error in health check: {str(e)}")
            return False


# Global state manager instance
_state_manager: Optional[OAuthStateManager] = None


def get_state_manager() -> OAuthStateManager:
    """
    Get or create the global OAuth state manager instance.

    This function provides a singleton state manager that reuses the same
    Redis connection pool across the application.

    Returns:
        OAuthStateManager: Global state manager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = OAuthStateManager()
    return _state_manager


async def cleanup_state_manager() -> None:
    """
    Cleanup the global OAuth state manager instance.

    Should be called during application shutdown to properly close
    Redis connections.
    """
    global _state_manager
    if _state_manager is not None:
        await _state_manager.close()
        _state_manager = None
        logger.info("OAuth state manager cleaned up")
