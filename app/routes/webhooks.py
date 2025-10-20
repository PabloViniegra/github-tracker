"""
GitHub webhook routes for setup, management, and notification handling.

This module handles:
- GitHub webhook event reception and verification
- Webhook setup on repositories
- Webhook listing and deletion
- Notification retrieval and management
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from app.core.config import get_settings
from app.core.database import get_database
from app.core.security import verify_github_signature
from app.middleware.rate_limiting import limiter
from app.models.user import UserInDB
from app.models.webhook import (
    WebhookNotificationResponse,
    WebhookSetupResponse,
    WebhookListResponse,
    NotificationsResponse,
)
from app.routes.dependencies import get_current_user
from app.services.github import GitHubService
from app.services.user import UserService
from app.services.webhook import WebhookService

# Configure logging
logger = logging.getLogger(__name__)

# Router configuration
webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhook_router.post(
    "/github",
    response_model=Dict[str, Any],
    summary="Receive GitHub webhook events",
    status_code=status.HTTP_200_OK,
    include_in_schema=True,
)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., description="GitHub event type"),
    x_hub_signature_256: Optional[str] = Header(None, description="Webhook signature"),
    db=Depends(get_database)
) -> Dict[str, Any]:
    """
    Receive and process webhook events from GitHub.

    This endpoint is called by GitHub when events occur in repositories
    where webhooks are configured. It verifies the webhook signature,
    extracts relevant information, and stores notifications.

    Args:
        request: FastAPI request object
        x_github_event: Type of GitHub event (e.g., 'push', 'pull_request')
        x_hub_signature_256: HMAC signature for verification
        db: Database connection

    Returns:
        Dict with processing status and event information

    Raises:
        HTTPException:
            - 401 if webhook signature is invalid
            - 500 for unexpected errors

    Note:
        This endpoint is called by GitHub servers, not by clients.
        The webhook URL must be publicly accessible.
    """
    try:
        # Read request body
        body = await request.body()

        # Verify webhook signature
        if not verify_github_signature(body, x_hub_signature_256):
            logger.warning(
                f"Invalid webhook signature for event: {x_github_event}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        # Parse JSON payload
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )

        # Extract repository information
        repository = payload.get("repository", {})
        repo_full_name = repository.get("full_name")
        repo_owner = repository.get("owner", {}).get("login")

        if not repo_owner:
            logger.warning(f"Webhook received without repository owner: {x_github_event}")
            return {"message": "Repository owner not found, webhook ignored"}

        # Find user by GitHub username
        user_service = UserService(db)
        user = await user_service.get_user_by_username(repo_owner)

        if not user:
            logger.info(
                f"Webhook received for unknown user: {repo_owner}. Event: {x_github_event}"
            )
            return {"message": "User not found, webhook ignored"}

        # Extract action from payload
        action = payload.get("action")

        # Create webhook notification
        webhook_service = WebhookService(db)
        await webhook_service.create_notification(
            user_id=user.id,
            repository=repo_full_name,
            event_type=x_github_event,
            action=action,
            payload=payload
        )

        logger.info(
            f"Webhook processed successfully. User: {repo_owner}, "
            f"Event: {x_github_event}, Repo: {repo_full_name}, Action: {action}"
        )

        return {
            "message": "Webhook received successfully",
            "event": x_github_event,
            "repository": repo_full_name,
            "action": action
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error processing webhook. Event: {x_github_event}, Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@webhook_router.post(
    "/setup/{owner}/{repo}",
    response_model=WebhookSetupResponse,
    summary="Configure webhook on repository",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def setup_webhook(
    request: Request,
    owner: str,
    repo: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
) -> WebhookSetupResponse:
    """
    Configure a webhook on a GitHub repository.

    This endpoint creates a new webhook on the specified repository
    that will send events to our webhook endpoint. The authenticated
    user must have admin permissions on the repository.

    Args:
        request: FastAPI request object (required for rate limiting)
        owner: Repository owner username
        repo: Repository name
        current_user: Authenticated user from dependency
        db: Database connection

    Returns:
        WebhookSetupResponse with webhook details

    Raises:
        HTTPException:
            - 401 if GitHub token is invalid
            - 403 if user lacks admin permissions on repository
            - 404 if repository not found
            - 422 if webhook already exists
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post(
            "/api/v1/webhooks/setup/owner/repo",
            headers=headers
        )
        ```
    """
    try:
        logger.info(
            f"Setting up webhook for {owner}/{repo} by user {current_user.username}"
        )

        # Create webhook on GitHub
        github_service = GitHubService()
        webhook = await github_service.create_webhook(
            current_user.github_access_token,
            owner,
            repo
        )

        # Update user's webhook configuration status
        user_service = UserService(db)
        await user_service.update_webhook_status(str(current_user.id), True)

        logger.info(
            f"Webhook configured successfully for {owner}/{repo}. "
            f"Webhook ID: {webhook.get('id')}"
        )

        return WebhookSetupResponse(
            message="Webhook configured successfully",
            webhook_id=webhook["id"],
            repository=f"{owner}/{repo}",
            events=webhook.get("events", [])
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions from GitHubService
        logger.error(
            f"Failed to setup webhook for {owner}/{repo}: {e.detail}"
        )
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error setting up webhook for {owner}/{repo}: {str(e)}",
            exc_info=True
        )

        # Provide user-friendly error messages
        error_message = "Failed to configure webhook"
        if "403" in str(e) or "Forbidden" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Admin access required for this repository."
            )
        elif "404" in str(e) or "Not Found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found"
            )
        elif "422" in str(e) or "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Webhook already exists for this repository"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )


@webhook_router.get(
    "/list/{owner}/{repo}",
    response_model=WebhookListResponse,
    summary="List repository webhooks",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def list_webhooks(
    request: Request,
    owner: str,
    repo: str,
    current_user: UserInDB = Depends(get_current_user)
) -> WebhookListResponse:
    """
    List all webhooks configured on a repository.

    Args:
        request: FastAPI request object (required for rate limiting)
        owner: Repository owner username
        repo: Repository name
        current_user: Authenticated user from dependency

    Returns:
        WebhookListResponse containing list of webhooks

    Raises:
        HTTPException:
            - 401 if GitHub token is invalid
            - 403 if user lacks permissions
            - 404 if repository not found
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(
            "/api/v1/webhooks/list/owner/repo",
            headers=headers
        )
        ```
    """
    try:
        logger.info(
            f"Listing webhooks for {owner}/{repo} by user {current_user.username}"
        )

        github_service = GitHubService()
        webhooks = await github_service.list_webhooks(
            current_user.github_access_token,
            owner,
            repo
        )

        logger.info(
            f"Retrieved {len(webhooks)} webhooks for {owner}/{repo}"
        )

        return WebhookListResponse(webhooks=webhooks)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error listing webhooks for {owner}/{repo}: {str(e)}",
            exc_info=True
        )

        if "403" in str(e) or "Forbidden" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to list webhooks for this repository"
            )
        elif "404" in str(e) or "Not Found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{owner}/{repo}' not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list webhooks"
            )


@webhook_router.delete(
    "/remove/{owner}/{repo}/{hook_id}",
    response_model=Dict[str, str],
    summary="Remove webhook from repository",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def remove_webhook(
    request: Request,
    owner: str,
    repo: str,
    hook_id: int,
    current_user: UserInDB = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Delete a webhook from a GitHub repository.

    Args:
        request: FastAPI request object (required for rate limiting)
        owner: Repository owner username
        repo: Repository name
        hook_id: Webhook ID to delete
        current_user: Authenticated user from dependency

    Returns:
        Dict with success message

    Raises:
        HTTPException:
            - 401 if GitHub token is invalid
            - 403 if user lacks admin permissions
            - 404 if webhook or repository not found
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.delete(
            "/api/v1/webhooks/remove/owner/repo/123",
            headers=headers
        )
        ```
    """
    try:
        logger.info(
            f"Removing webhook {hook_id} from {owner}/{repo} "
            f"by user {current_user.username}"
        )

        github_service = GitHubService()
        success = await github_service.delete_webhook(
            current_user.github_access_token,
            owner,
            repo,
            hook_id
        )

        if not success:
            logger.warning(
                f"Failed to delete webhook {hook_id} from {owner}/{repo}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found or already deleted"
            )

        logger.info(
            f"Webhook {hook_id} deleted successfully from {owner}/{repo}"
        )

        return {"message": "Webhook deleted successfully"}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error deleting webhook {hook_id} from {owner}/{repo}: {str(e)}",
            exc_info=True
        )

        if "403" in str(e) or "Forbidden" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Admin access required."
            )
        elif "404" in str(e) or "Not Found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {hook_id} not found on repository '{owner}/{repo}'"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete webhook"
            )


@webhook_router.get(
    "/notifications",
    response_model=NotificationsResponse,
    summary="Get user webhook notifications",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def get_notifications(
    request: Request,
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    limit: int = Query(50, le=100, ge=1, description="Maximum number of notifications"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
) -> NotificationsResponse:
    """
    Retrieve webhook notifications for the authenticated user.

    This endpoint returns notifications generated from GitHub webhook events,
    useful for displaying real-time updates in the frontend.

    Args:
        request: FastAPI request object (required for rate limiting)
        processed: Filter by processed status (None = all, True = processed, False = unprocessed)
        limit: Maximum number of notifications to return (1-100)
        current_user: Authenticated user from dependency
        db: Database connection

    Returns:
        NotificationsResponse containing list of notifications

    Raises:
        HTTPException: 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        # Get unprocessed notifications
        response = await client.get(
            "/api/v1/webhooks/notifications?processed=false&limit=20",
            headers=headers
        )
        ```
    """
    try:
        logger.debug(
            f"Fetching notifications for user {current_user.username}. "
            f"Processed: {processed}, Limit: {limit}"
        )

        webhook_service = WebhookService(db)
        notifications = await webhook_service.get_user_notifications(
            str(current_user.id),
            processed=processed,
            limit=limit
        )

        logger.info(
            f"Retrieved {len(notifications)} notifications for user {current_user.username}"
        )

        return NotificationsResponse(
            notifications=[
                WebhookNotificationResponse(
                    id=str(notif.id),
                    repository=notif.repository,
                    event_type=notif.event_type,
                    action=notif.action,
                    created_at=notif.created_at,
                    processed=notif.processed
                )
                for notif in notifications
            ]
        )

    except Exception as e:
        logger.error(
            f"Error fetching notifications for user {current_user.username}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notifications"
        )


@webhook_router.post(
    "/notifications/{notification_id}/mark-processed",
    response_model=Dict[str, str],
    summary="Mark notification as processed",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
async def mark_notification_processed(
    request: Request,
    notification_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
) -> Dict[str, str]:
    """
    Mark a specific notification as processed.

    Args:
        request: FastAPI request object (required for rate limiting)
        notification_id: MongoDB ObjectId of the notification
        current_user: Authenticated user from dependency
        db: Database connection

    Returns:
        Dict with success message

    Raises:
        HTTPException:
            - 404 if notification not found
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post(
            "/api/v1/webhooks/notifications/507f1f77bcf86cd799439011/mark-processed",
            headers=headers
        )
        ```
    """
    try:
        logger.debug(
            f"Marking notification {notification_id} as processed "
            f"for user {current_user.username}"
        )

        webhook_service = WebhookService(db)
        await webhook_service.mark_as_processed(notification_id)

        logger.info(
            f"Notification {notification_id} marked as processed "
            f"by user {current_user.username}"
        )

        return {"message": "Notification marked as processed"}

    except ValueError as e:
        logger.warning(f"Invalid notification ID: {notification_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    except Exception as e:
        logger.error(
            f"Error marking notification {notification_id} as processed: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as processed"
        )


@webhook_router.post(
    "/notifications/mark-all-processed",
    response_model=Dict[str, str],
    summary="Mark all notifications as processed",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def mark_all_notifications_processed(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
) -> Dict[str, str]:
    """
    Mark all notifications for the user as processed.

    Args:
        request: FastAPI request object (required for rate limiting)
        current_user: Authenticated user from dependency
        db: Database connection

    Returns:
        Dict with success message

    Raises:
        HTTPException: 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post(
            "/api/v1/webhooks/notifications/mark-all-processed",
            headers=headers
        )
        ```
    """
    try:
        logger.info(
            f"Marking all notifications as processed for user {current_user.username}"
        )

        webhook_service = WebhookService(db)
        await webhook_service.mark_all_as_processed(str(current_user.id))

        logger.info(
            f"All notifications marked as processed for user {current_user.username}"
        )

        return {"message": "All notifications marked as processed"}

    except Exception as e:
        logger.error(
            f"Error marking all notifications as processed "
            f"for user {current_user.username}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications as processed"
        )
