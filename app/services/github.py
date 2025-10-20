"""GitHub API service for OAuth authentication and API interactions.

This module provides a comprehensive service layer for interacting with GitHub's
REST API, including OAuth flow, user information retrieval, repository management,
and webhook operations.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

# Initialize logger
logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""

    def __init__(self, message: str, status_code: int, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class GitHubAuthenticationError(GitHubAPIError):
    """Exception raised for GitHub authentication failures."""

    pass


class GitHubRateLimitError(GitHubAPIError):
    """Exception raised when GitHub API rate limit is exceeded."""

    pass


class GitHubService:
    """Service for interacting with GitHub API.

    This service handles all GitHub API operations including OAuth authentication,
    user data retrieval, repository management, and webhook configuration.

    Attributes:
        BASE_URL: GitHub API base URL
        OAUTH_URL: GitHub OAuth base URL
        DEFAULT_TIMEOUT: Default timeout for HTTP requests in seconds
        _client: Shared httpx.AsyncClient instance
    """

    BASE_URL: str = "https://api.github.com"
    OAUTH_URL: str = "https://github.com/login/oauth"
    DEFAULT_TIMEOUT: float = 30.0

    def __init__(self) -> None:
        """Initialize the GitHub service."""
        self._client: Optional[httpx.AsyncClient] = None
        self._settings = get_settings()
        logger.info("GitHubService initialized")

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client.

        Returns:
            httpx.AsyncClient: Configured async HTTP client
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.DEFAULT_TIMEOUT),
                follow_redirects=True,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "GitHub-Activity-Tracker/1.0"
                }
            )
            logger.debug("Created new httpx.AsyncClient")
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("Closed httpx.AsyncClient")

    @asynccontextmanager
    async def _get_client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Context manager for getting a temporary HTTP client.

        Yields:
            httpx.AsyncClient: Configured async HTTP client
        """
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.DEFAULT_TIMEOUT),
            follow_redirects=True,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "GitHub-Activity-Tracker/1.0"
            }
        )
        try:
            yield client
        finally:
            await client.aclose()

    def _handle_github_error(
        self,
        response: httpx.Response,
        default_message: str,
        auth_error: bool = False
    ) -> None:
        """Handle GitHub API error responses.

        Args:
            response: HTTP response from GitHub API
            default_message: Default error message if response doesn't contain details
            auth_error: Whether this is an authentication error

        Raises:
            GitHubAuthenticationError: For authentication failures
            GitHubRateLimitError: For rate limit errors
            GitHubAPIError: For other API errors
        """
        try:
            error_data = response.json()
        except Exception:
            error_data = {"message": response.text}

        error_message = error_data.get("message", default_message)

        logger.error(
            f"GitHub API error: status={response.status_code}, "
            f"message={error_message}, data={error_data}"
        )

        # Check for rate limiting
        if response.status_code == 403 and "rate limit" in error_message.lower():
            raise GitHubRateLimitError(
                message="GitHub API rate limit exceeded",
                status_code=response.status_code,
                response_data=error_data
            )

        # Check for authentication errors
        if auth_error or response.status_code == 401:
            raise GitHubAuthenticationError(
                message=error_message,
                status_code=response.status_code,
                response_data=error_data
            )

        # Generic API error
        raise GitHubAPIError(
            message=error_message,
            status_code=response.status_code,
            response_data=error_data
        )

    def get_authorization_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            state: CSRF protection state token

        Returns:
            str: Complete GitHub OAuth authorization URL

        Example:
            >>> service = GitHubService()
            >>> url = service.get_authorization_url("random-state-token")
            >>> print(url)
            https://github.com/login/oauth/authorize?client_id=...
        """
        params = {
            "client_id": self._settings.github_client_id,
            "redirect_uri": self._settings.github_redirect_uri,
            "scope": "repo read:user user:email admin:repo_hook",
            "state": state
        }

        query_string = urlencode(params)
        auth_url = f"{self.OAUTH_URL}/authorize?{query_string}"

        logger.info(f"Generated authorization URL for state: {state}")
        return auth_url

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for access token.

        Args:
            code: OAuth authorization code from GitHub callback

        Returns:
            Dict[str, Any]: Token response containing access_token, token_type, and scope

        Raises:
            GitHubAuthenticationError: If code exchange fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> token_data = await service.exchange_code_for_token("oauth-code")
            >>> print(token_data["access_token"])
        """
        logger.info("Exchanging OAuth code for access token")

        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.OAUTH_URL}/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": self._settings.github_client_id,
                        "client_secret": self._settings.github_client_secret,
                        "code": code,
                        "redirect_uri": self._settings.github_redirect_uri
                    }
                )

                if response.status_code != 200:
                    self._handle_github_error(
                        response,
                        "Failed to exchange code for token",
                        auth_error=True
                    )

                token_data = response.json()

                # Check for error in response
                if "error" in token_data:
                    logger.error(f"OAuth error: {token_data.get('error_description', token_data['error'])}")
                    raise GitHubAuthenticationError(
                        message=token_data.get("error_description", token_data["error"]),
                        status_code=400,
                        response_data=token_data
                    )

                logger.info("Successfully exchanged code for access token")
                return token_data

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while exchanging code for token: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during code exchange: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during authentication"
            )

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated user information from GitHub.

        Args:
            access_token: GitHub OAuth access token

        Returns:
            Dict[str, Any]: User information including id, login, name, email, etc.

        Raises:
            GitHubAuthenticationError: If token is invalid
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> user_info = await service.get_user_info("github_token")
            >>> print(user_info["login"])
        """
        logger.info("Fetching user information from GitHub")

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                if response.status_code != 200:
                    self._handle_github_error(
                        response,
                        "Invalid GitHub token",
                        auth_error=True
                    )

                user_data = response.json()
                logger.info(f"Successfully fetched user info for: {user_data.get('login')}")
                return user_data

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while fetching user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while fetching user information"
            )

    async def verify_token_validity(self, access_token: str) -> bool:
        """Verify if a GitHub access token is valid.

        Args:
            access_token: GitHub OAuth access token to verify

        Returns:
            bool: True if token is valid, False otherwise

        Example:
            >>> service = GitHubService()
            >>> is_valid = await service.verify_token_validity("token")
            >>> print(is_valid)
            True
        """
        logger.debug("Verifying GitHub token validity")

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                is_valid = response.status_code == 200
                logger.debug(f"Token validity check result: {is_valid}")
                return is_valid

        except httpx.TimeoutException as e:
            logger.warning(f"Timeout during token verification: {e}")
            return False
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error during token verification: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error during token verification: {e}")
            return False

    async def get_user_repos(
        self,
        access_token: str,
        sort: str = "updated",
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get repositories for the authenticated user.

        Args:
            access_token: GitHub OAuth access token
            sort: Sort order (created, updated, pushed, full_name)
            per_page: Number of results per page (max 100)

        Returns:
            List[Dict[str, Any]]: List of repository objects

        Raises:
            GitHubAPIError: If request fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> repos = await service.get_user_repos("token")
            >>> print(len(repos))
        """
        logger.info(f"Fetching user repositories (sort={sort}, per_page={per_page})")

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/user/repos",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"sort": sort, "per_page": per_page}
                )

                if response.status_code != 200:
                    self._handle_github_error(
                        response,
                        "Failed to fetch repositories"
                    )

                repos = response.json()
                logger.info(f"Successfully fetched {len(repos)} repositories")
                return repos

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while fetching repositories: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching repositories: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while fetching repositories"
            )

    async def get_user_activity(
        self,
        access_token: str,
        username: str,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent activity events for a user.

        Args:
            access_token: GitHub OAuth access token
            username: GitHub username
            per_page: Number of results per page (max 100)

        Returns:
            List[Dict[str, Any]]: List of activity event objects

        Raises:
            GitHubAPIError: If request fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> events = await service.get_user_activity("token", "username")
            >>> print(len(events))
        """
        logger.info(f"Fetching activity for user: {username} (per_page={per_page})")

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/{username}/events",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"per_page": per_page}
                )

                if response.status_code != 200:
                    self._handle_github_error(
                        response,
                        f"Failed to fetch activity for user {username}"
                    )

                events = response.json()
                logger.info(f"Successfully fetched {len(events)} activity events for {username}")
                return events

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while fetching user activity: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error fetching user activity: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while fetching user activity"
            )

    async def create_webhook(
        self,
        access_token: str,
        owner: str,
        repo: str,
        events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a webhook on a GitHub repository.

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo: Repository name
            events: List of events to subscribe to (defaults to common events)

        Returns:
            Dict[str, Any]: Created webhook object

        Raises:
            GitHubAPIError: If webhook creation fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> webhook = await service.create_webhook("token", "owner", "repo")
            >>> print(webhook["id"])
        """
        if events is None:
            events = [
                "push",
                "pull_request",
                "issues",
                "issue_comment",
                "commit_comment",
                "create",
                "delete",
                "fork",
                "star",
                "watch",
                "release"
            ]

        logger.info(f"Creating webhook for {owner}/{repo} with events: {events}")

        webhook_config = {
            "name": "web",
            "active": True,
            "events": events,
            "config": {
                "url": self._settings.webhook_url,
                "content_type": "json",
                "secret": self._settings.github_webhook_secret,
                "insecure_ssl": "0"
            }
        }

        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/hooks",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json=webhook_config
                )

                if response.status_code not in [200, 201]:
                    self._handle_github_error(
                        response,
                        f"Failed to create webhook on {owner}/{repo}"
                    )

                webhook = response.json()
                logger.info(f"Successfully created webhook {webhook.get('id')} for {owner}/{repo}")
                return webhook

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while creating webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error creating webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while creating webhook"
            )

    async def list_webhooks(
        self,
        access_token: str,
        owner: str,
        repo: str
    ) -> List[Dict[str, Any]]:
        """List all webhooks configured on a repository.

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo: Repository name

        Returns:
            List[Dict[str, Any]]: List of webhook objects

        Raises:
            GitHubAPIError: If request fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> webhooks = await service.list_webhooks("token", "owner", "repo")
            >>> print(len(webhooks))
        """
        logger.info(f"Listing webhooks for {owner}/{repo}")

        try:
            async with self._get_client() as client:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/hooks",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                if response.status_code != 200:
                    self._handle_github_error(
                        response,
                        f"Failed to list webhooks for {owner}/{repo}"
                    )

                webhooks = response.json()
                logger.info(f"Successfully listed {len(webhooks)} webhooks for {owner}/{repo}")
                return webhooks

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while listing webhooks: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except (GitHubAuthenticationError, GitHubAPIError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error listing webhooks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while listing webhooks"
            )

    async def delete_webhook(
        self,
        access_token: str,
        owner: str,
        repo: str,
        hook_id: int
    ) -> bool:
        """Delete a webhook from a repository.

        Args:
            access_token: GitHub OAuth access token
            owner: Repository owner username
            repo: Repository name
            hook_id: Webhook ID to delete

        Returns:
            bool: True if webhook was deleted successfully

        Raises:
            GitHubAPIError: If deletion fails
            httpx.TimeoutException: If request times out

        Example:
            >>> service = GitHubService()
            >>> success = await service.delete_webhook("token", "owner", "repo", 12345)
            >>> print(success)
            True
        """
        logger.info(f"Deleting webhook {hook_id} from {owner}/{repo}")

        try:
            async with self._get_client() as client:
                response = await client.delete(
                    f"{self.BASE_URL}/repos/{owner}/{repo}/hooks/{hook_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                success = response.status_code == 204

                if not success:
                    logger.warning(
                        f"Failed to delete webhook {hook_id} from {owner}/{repo}: "
                        f"status={response.status_code}"
                    )
                else:
                    logger.info(f"Successfully deleted webhook {hook_id} from {owner}/{repo}")

                return success

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while deleting webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="GitHub API request timed out"
            )
        except httpx.HTTPError as e:
            logger.exception(f"HTTP error while deleting webhook: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting webhook: {e}")
            return False


# Singleton removed - use dependency injection via get_github_service() in dependencies.py
