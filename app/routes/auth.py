"""
Authentication routes for GitHub OAuth flow and JWT token management.

This module handles:
- GitHub OAuth login flow with state verification
- Token refresh mechanism
- User logout
- Current user information retrieval
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import get_settings
from app.core.database import get_database
from app.core.security import (
    create_access_token,
    create_refresh_token,
    security,
    verify_token,
)
from app.core.state_manager import get_state_manager
from app.middleware.rate_limiting import limiter
from app.models.user import UserInDB, UserResponse
from app.models.token import TokenResponse
from app.routes.dependencies import get_current_user, get_github_service
from app.services.github import GitHubService
from app.services.user import UserService

# Configure logging
logger = logging.getLogger(__name__)

# Router configuration
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.get(
    "/github/login",
    response_model=Dict[str, str],
    summary="Initiate GitHub OAuth flow",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_settings().rate_limit_auth)
async def github_login(
    request: Request,
    github_service: GitHubService = Depends(get_github_service)
) -> Dict[str, str]:
    """
    Initiate the OAuth authentication flow with GitHub.

    This endpoint generates a secure state token and returns the GitHub
    authorization URL that the client should redirect to. The state is stored
    in Redis with automatic expiration.

    Args:
        request: FastAPI request object (required for rate limiting)
        github_service: GitHub service instance (dependency injected)

    Returns:
        Dict containing:
            - authorization_url: GitHub OAuth URL to redirect user to
            - state: Secure token to verify callback authenticity

    Raises:
        HTTPException:
            - 429 if rate limit exceeded
            - 500 if state storage fails

    Example:
        ```python
        response = await client.get("/api/v1/auth/github/login")
        # Redirect user to response["authorization_url"]
        ```
    """
    try:
        # Generate cryptographically secure state token
        state = secrets.token_urlsafe(32)

        # Store state in Redis
        state_manager = get_state_manager()
        success = await state_manager.create_state(state)

        if not success:
            logger.error("Failed to store OAuth state in Redis")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize OAuth flow. Please try again."
            )

        # Get GitHub authorization URL
        auth_url = github_service.get_authorization_url(state)

        logger.info(f"Generated OAuth login URL with state: {state[:8]}...")

        return {
            "authorization_url": auth_url,
            "state": state
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error generating OAuth URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@auth_router.get(
    "/github/callback",
    response_model=TokenResponse,
    summary="GitHub OAuth callback handler",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_settings().rate_limit_auth)
async def github_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code from GitHub"),
    state: str = Query(..., description="State token for CSRF protection"),
    db=Depends(get_database),
    github_service: GitHubService = Depends(get_github_service)
) -> TokenResponse:
    """
    Handle the OAuth callback from GitHub after user authorization.

    This endpoint:
    1. Validates the state token to prevent CSRF attacks
    2. Exchanges the authorization code for a GitHub access token
    3. Fetches user information from GitHub
    4. Creates or updates the user in the database
    5. Generates JWT access and refresh tokens

    Args:
        request: FastAPI request object (required for rate limiting)
        code: Authorization code from GitHub
        state: State token for verification
        db: Database connection

    Returns:
        TokenResponse containing access_token, refresh_token, and expires_in

    Raises:
        HTTPException:
            - 400 if state is invalid or expired
            - 401 if GitHub token exchange fails
            - 500 for unexpected errors
    """
    try:
        # Verify and consume state from Redis
        state_manager = get_state_manager()
        state_valid = await state_manager.verify_and_consume_state(state)

        if not state_valid:
            logger.warning(f"Invalid or expired OAuth state: {state[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter. Please try logging in again."
            )

        # Exchange code for GitHub access token
        logger.info("Exchanging authorization code for GitHub token")
        token_response = await github_service.exchange_code_for_token(code)

        if "access_token" not in token_response:
            logger.error("GitHub token exchange did not return access_token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to obtain access token from GitHub"
            )

        github_token = token_response["access_token"]

        # Get user information from GitHub
        logger.info("Fetching user information from GitHub")
        github_user = await github_service.get_user_info(github_token)

        # Calculate GitHub token expiration if provided
        github_token_expires: Optional[datetime] = None
        if "expires_in" in token_response:
            github_token_expires = datetime.now(timezone.utc) + timedelta(
                seconds=token_response["expires_in"]
            )

        # Create or update user in database
        user_service = UserService(db)
        user = await user_service.create_or_update_user(
            github_user,
            github_token,
            github_token_expires
        )

        logger.info(f"User authenticated successfully: {user.username} (ID: {user.id})")

        # Generate JWT tokens
        access_token, access_expires = create_access_token(str(user.id))
        refresh_token, refresh_expires = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=get_settings().jwt_access_token_expire_minutes * 60,
            token_type="bearer"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error in OAuth callback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed. Please try again."
        )


@auth_router.post(
    "/refresh",
    response_model=Dict[str, str],
    summary="Refresh access token",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def refresh_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_database)
) -> Dict[str, str]:
    """
    Refresh an expired access token using a valid refresh token.

    This endpoint verifies the refresh token and issues a new access token
    if the user's session is still valid.

    Args:
        request: FastAPI request object (required for rate limiting)
        credentials: Bearer token credentials (refresh token)
        db: Database connection

    Returns:
        Dict containing:
            - access_token: New JWT access token
            - token_type: Token type (always "bearer")

    Raises:
        HTTPException:
            - 401 if refresh token is invalid or session expired
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = await client.post("/api/v1/auth/refresh", headers=headers)
        ```
    """
    try:
        refresh_token = credentials.credentials

        # Verify refresh token
        logger.info("Verifying refresh token")
        token_data = verify_token(refresh_token, token_type="refresh")

        # Verify user still exists and tokens are valid
        user_service = UserService(db)
        tokens_valid = await user_service.verify_user_tokens(token_data.sub)

        if not tokens_valid:
            logger.warning(f"Invalid session for user: {token_data.sub}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please login again."
            )

        # Generate new access token
        access_token, _ = create_access_token(token_data.sub)

        logger.info(f"Access token refreshed for user: {token_data.sub}")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@auth_router.post(
    "/logout",
    response_model=Dict[str, str],
    summary="Logout user",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout the current user.

    Note: Currently, this is a stateless operation as JWT tokens are not
    invalidated server-side. The client should delete the tokens locally.
    For production, consider implementing token blacklisting with Redis.

    Args:
        request: FastAPI request object (required for rate limiting)
        current_user: Authenticated user from dependency

    Returns:
        Dict with success message

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post("/api/v1/auth/logout", headers=headers)
        ```
    """
    logger.info(f"User logged out: {current_user.username} (ID: {current_user.id})")

    # TODO: Implement token blacklisting for enhanced security
    # For now, client-side token deletion is sufficient

    return {"message": "Logged out successfully"}


@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user information",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def get_current_user_info(
    request: Request,
    current_user: UserInDB = Depends(get_current_user)
) -> UserResponse:
    """
    Get information about the currently authenticated user.

    Args:
        request: FastAPI request object (required for rate limiting)
        current_user: Authenticated user from dependency

    Returns:
        UserResponse with user profile information

    Raises:
        HTTPException: 401 if not authenticated

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        ```
    """
    logger.debug(f"User info requested: {current_user.username}")

    return UserResponse(
        id=str(current_user.id),
        github_id=current_user.github_id,
        username=current_user.username,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        email=current_user.email,
        profile_url=current_user.profile_url,
        created_at=current_user.created_at,
        webhook_configured=current_user.webhook_configured
    )
