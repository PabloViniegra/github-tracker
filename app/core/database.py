"""Database connection and utilities."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""

    client: Optional[AsyncIOMotorClient] = None


db = Database()


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    if db.client is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return db.client[get_settings().mongodb_db_name]


async def connect_to_mongo() -> None:
    """Connect to MongoDB."""
    try:
        settings = get_settings()
        db.client = AsyncIOMotorClient(settings.mongodb_url)
        # Verify connection
        await db.client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise


async def close_mongo_connection() -> None:
    """Close MongoDB connection."""
    if db.client:
        db.client.close()
        logger.info("Closed MongoDB connection")
