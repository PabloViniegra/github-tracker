"""
GitHub activity routes for retrieving user repositories and events.

This module provides endpoints to fetch:
- User's GitHub repositories
- User's recent GitHub activity/events
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.middleware.rate_limiting import limiter
from app.models.user import UserInDB
from app.models.activity import RepositoriesResponse, EventsResponse
from app.routes.dependencies import get_current_user, get_github_service
from app.services.github import GitHubService

# Configure logging
logger = logging.getLogger(__name__)

# Router configuration
activity_router = APIRouter(prefix="/activity", tags=["Activity"])


def filter_repositories(
    repositories: List[Dict[str, Any]],
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter repositories based on a search query.

    Performs case-insensitive partial matching across multiple fields:
    - Repository name
    - Repository description
    - Repository topics/tags
    - Repository language
    - Repository owner login

    Args:
        repositories: List of repository dictionaries from GitHub API
        query: Optional search string (None or empty string returns all repos)

    Returns:
        Filtered list of repositories matching the query

    Example:
        >>> repos = [{"name": "FastAPI-Project", "language": "Python"}]
        >>> filter_repositories(repos, "fastapi")
        [{"name": "FastAPI-Project", "language": "Python"}]
    """
    # If no query provided, return all repositories
    if not query or not query.strip():
        return repositories

    # Normalize query to lowercase for case-insensitive search
    search_term = query.strip().lower()
    filtered_repos = []

    for repo in repositories:
        # Extract searchable fields with None-safe handling
        name = (repo.get("name") or "").lower()
        description = (repo.get("description") or "").lower()
        language = (repo.get("language") or "").lower()
        owner_login = (repo.get("owner", {}).get("login") or "").lower()

        # Topics are a list, join them into a searchable string
        topics = repo.get("topics", []) or []
        topics_str = " ".join(str(topic).lower() for topic in topics)

        # Check if search term appears in any field
        if (
            search_term in name
            or search_term in description
            or search_term in language
            or search_term in owner_login
            or search_term in topics_str
        ):
            filtered_repos.append(repo)

    return filtered_repos


@activity_router.get(
    "/repositories",
    response_model=RepositoriesResponse,
    summary="Get user repositories",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_settings().rate_limit_activity)
async def get_user_repositories(
    request: Request,
    q: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    github_service: GitHubService = Depends(get_github_service)
) -> RepositoriesResponse:
    """
    Retrieve all repositories accessible to the authenticated user with optional search.

    This endpoint fetches repositories from GitHub using the user's
    access token. It includes both owned and accessible repositories.

    The optional 'q' parameter enables full-text search across:
    - Repository name
    - Repository description
    - Repository topics/tags
    - Repository language
    - Repository owner

    Args:
        request: FastAPI request object (required for rate limiting)
        q: Optional search query for filtering repositories (case-insensitive)
        current_user: Authenticated user from dependency

    Returns:
        RepositoriesResponse containing list of repositories (filtered if q provided)

    Raises:
        HTTPException:
            - 401 if GitHub token is invalid or expired
            - 403 if rate limit exceeded on GitHub API
            - 500 for unexpected errors

    Example:
        ```python
        # Get all repositories
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/activity/repositories", headers=headers)

        # Search for Python repositories
        response = await client.get(
            "/api/v1/activity/repositories?q=python",
            headers=headers
        )
        ```
    """
    try:
        # Log the request with search query if provided
        if q:
            logger.info(
                f"Fetching repositories for user: {current_user.username} "
                f"with search query: '{q}'"
            )
        else:
            logger.info(f"Fetching repositories for user: {current_user.username}")

        # Verify user has a valid GitHub token
        if not current_user.github_access_token:
            logger.error(f"User {current_user.username} has no GitHub access token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token not found. Please re-authenticate."
            )

        # Fetch repositories from GitHub
        repos = await github_service.get_user_repos(current_user.github_access_token)

        logger.info(
            f"Retrieved {len(repos)} repositories for user: {current_user.username}"
        )

        # Apply search filter if query provided
        if q:
            repos = filter_repositories(repos, q)
            logger.info(
                f"Filtered to {len(repos)} repositories matching query: '{q}'"
            )

        return RepositoriesResponse(repositories=repos)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error fetching repositories for user {current_user.username}: {str(e)}",
            exc_info=True
        )

        # Check if it's a GitHub API error
        error_detail = "Failed to fetch repositories"
        if "401" in str(e) or "Unauthorized" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub token expired. Please re-authenticate."
            )
        elif "403" in str(e) or "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )


@activity_router.get(
    "/events",
    response_model=EventsResponse,
    summary="Get user activity events",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_settings().rate_limit_activity)
async def get_user_activity(
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    github_service: GitHubService = Depends(get_github_service)
) -> EventsResponse:
    """
    Retrieve recent activity events for the authenticated user.

    This endpoint fetches the user's recent GitHub activity, including:
    - Pushes to repositories
    - Pull request actions
    - Issue creation and comments
    - Repository stars and forks
    - And other public events

    Args:
        request: FastAPI request object (required for rate limiting)
        current_user: Authenticated user from dependency

    Returns:
        EventsResponse containing list of recent events

    Raises:
        HTTPException:
            - 401 if GitHub token is invalid or expired
            - 403 if rate limit exceeded on GitHub API
            - 404 if user not found on GitHub
            - 500 for unexpected errors

    Example:
        ```python
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get("/api/v1/activity/events", headers=headers)
        ```
    """
    try:
        logger.info(f"Fetching activity events for user: {current_user.username}")

        # Verify user has a valid GitHub token
        if not current_user.github_access_token:
            logger.error(f"User {current_user.username} has no GitHub access token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token not found. Please re-authenticate."
            )

        # Fetch activity events from GitHub
        events = await github_service.get_user_activity(
            current_user.github_access_token,
            current_user.username
        )

        logger.info(
            f"Retrieved {len(events)} activity events for user: {current_user.username}"
        )

        return EventsResponse(events=events)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            f"Error fetching activity for user {current_user.username}: {str(e)}",
            exc_info=True
        )

        # Check if it's a GitHub API error
        error_detail = "Failed to fetch user activity"
        if "401" in str(e) or "Unauthorized" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub token expired. Please re-authenticate."
            )
        elif "403" in str(e) or "rate limit" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later."
            )
        elif "404" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub user '{current_user.username}' not found"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
