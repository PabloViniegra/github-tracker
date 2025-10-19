"""FastAPI dependencies for request handling."""

import logging
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.security import security, verify_token
from app.models.user import UserInDB
from app.services.user import UserService

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> UserInDB:
    """
    Get current authenticated user from JWT token.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        db: Database instance

    Returns:
        UserInDB: Authenticated user object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = verify_token(token, token_type="access")

    # Store user_id in request state for rate limiting
    request.state.user_id = token_data.sub

    user_service = UserService(db)
    user = await user_service.get_user_by_id(token_data.sub)

    if not user:
        logger.warning(f"User not found for token sub: {token_data.sub}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify GitHub token is still valid
    tokens_valid = await user_service.verify_user_tokens(str(user.id))
    if not tokens_valid:
        logger.warning(f"Invalid tokens for user: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
