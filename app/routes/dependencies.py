"""
FastAPI route dependencies for authentication and authorization.

This module provides reusable dependencies that can be injected into
route handlers to enforce authentication and other common requirements.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.database import get_database
from app.core.security import security, verify_token
from app.models.user import UserInDB
from app.services.user import UserService

# Configure logging
logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_database)
) -> UserInDB:
    """
    Dependency to get the currently authenticated user.

    This dependency:
    1. Extracts and validates the JWT access token from the Authorization header
    2. Verifies the token hasn't expired
    3. Retrieves the user from the database
    4. Validates the user's GitHub token is still valid
    5. Stores user_id in request.state for rate limiting

    Args:
        request: FastAPI request object
        credentials: HTTPBearer credentials from Authorization header
        db: Database connection

    Returns:
        UserInDB: The authenticated user object

    Raises:
        HTTPException:
            - 401 if token is invalid, expired, or user not found
            - 401 if user's GitHub token is invalid

    Example:
        ```python
        @router.get("/protected")
        async def protected_route(
            current_user: UserInDB = Depends(get_current_user)
        ):
            return {"user": current_user.username}
        ```
    """
    try:
        # Extract token from credentials
        token = credentials.credentials

        # Verify JWT token and extract payload
        token_data = verify_token(token, token_type="access")

        if not token_data or not token_data.sub:
            logger.warning("Invalid token data: missing subject")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Retrieve user from database
        user_service = UserService(db)
        user = await user_service.get_user_by_id(token_data.sub)

        if not user:
            logger.warning(f"User not found for token subject: {token_data.sub}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user's GitHub token is still valid
        tokens_valid = await user_service.verify_user_tokens(str(user.id))

        if not tokens_valid:
            logger.warning(
                f"Invalid or expired GitHub token for user: {user.username}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub session expired. Please re-authenticate.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store user_id in request state for rate limiting
        request.state.user_id = str(user.id)

        logger.debug(f"User authenticated successfully: {user.username}")

        return user

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db=Depends(get_database)
) -> Optional[UserInDB]:
    """
    Dependency to optionally get the authenticated user.

    Similar to get_current_user but returns None if no valid credentials
    are provided instead of raising an exception. Useful for endpoints
    that work differently for authenticated vs anonymous users.

    Args:
        request: FastAPI request object
        credentials: Optional HTTPBearer credentials
        db: Database connection

    Returns:
        Optional[UserInDB]: The authenticated user or None

    Example:
        ```python
        @router.get("/public")
        async def public_route(
            current_user: Optional[UserInDB] = Depends(get_optional_user)
        ):
            if current_user:
                return {"message": f"Hello {current_user.username}"}
            return {"message": "Hello anonymous"}
        ```
    """
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        # Don't raise exception for optional auth
        return None
    except Exception as e:
        logger.debug(f"Optional auth failed: {str(e)}")
        return None
