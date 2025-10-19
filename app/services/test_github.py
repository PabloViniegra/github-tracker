"""Unit tests for GitHub service.

This module contains comprehensive tests for the GitHubService class,
including OAuth flow, API interactions, error handling, and edge cases.
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException

from app.services.github import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubService,
    get_github_service,
    cleanup_github_service,
)


@pytest.fixture
def github_service():
    """Fixture providing a GitHubService instance."""
    service = GitHubService()
    yield service
    # Cleanup
    if service._client and not service._client.is_closed:
        import asyncio
        asyncio.run(service.close())


@pytest.fixture
def mock_settings():
    """Fixture providing mock settings."""
    with patch("app.services.github.get_settings") as mock:
        settings = MagicMock()
        settings.github_client_id = "test_client_id"
        settings.github_client_secret = "test_client_secret"
        settings.github_redirect_uri = "http://localhost/callback"
        settings.github_webhook_secret = "test_webhook_secret"
        settings.webhook_url = "http://localhost/webhooks"
        mock.return_value = settings
        yield settings


class TestGitHubServiceInit:
    """Tests for GitHubService initialization."""

    def test_init(self, mock_settings):
        """Test service initialization."""
        service = GitHubService()
        assert service._client is None
        assert service.BASE_URL == "https://api.github.com"
        assert service.OAUTH_URL == "https://github.com/login/oauth"
        assert service.DEFAULT_TIMEOUT == 30.0

    def test_client_property_creates_client(self, github_service):
        """Test that client property creates an httpx.AsyncClient."""
        client = github_service.client
        assert isinstance(client, httpx.AsyncClient)
        assert client.timeout.read == 30.0

    def test_client_property_reuses_client(self, github_service):
        """Test that client property reuses the same client."""
        client1 = github_service.client
        client2 = github_service.client
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close(self, github_service):
        """Test closing the service."""
        # Access client to create it
        _ = github_service.client
        assert github_service._client is not None

        await github_service.close()
        assert github_service._client.is_closed


class TestGetAuthorizationUrl:
    """Tests for get_authorization_url method."""

    def test_get_authorization_url(self, github_service, mock_settings):
        """Test generating authorization URL."""
        state = "test_state_token"
        url = github_service.get_authorization_url(state)

        assert url.startswith("https://github.com/login/oauth/authorize?")
        assert "client_id=test_client_id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
        assert "state=test_state_token" in url
        assert "scope=repo" in url
        assert "admin%3Arepo_hook" in url

    def test_get_authorization_url_different_states(self, github_service, mock_settings):
        """Test that different states produce different URLs."""
        url1 = github_service.get_authorization_url("state1")
        url2 = github_service.get_authorization_url("state2")

        assert "state=state1" in url1
        assert "state=state2" in url2
        assert url1 != url2


class TestExchangeCodeForToken:
    """Tests for exchange_code_for_token method."""

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, github_service, mock_settings):
        """Test successful code exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "token_type": "bearer",
            "scope": "repo,user"
        }

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.exchange_code_for_token("test_code")

            assert result["access_token"] == "test_token"
            assert result["token_type"] == "bearer"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_code_error_in_response(self, github_service, mock_settings):
        """Test code exchange with error in response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired."
        }

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GitHubAuthenticationError) as exc_info:
                await github_service.exchange_code_for_token("bad_code")

            assert "incorrect or expired" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_exchange_code_timeout(self, github_service, mock_settings):
        """Test code exchange timeout."""
        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_get_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await github_service.exchange_code_for_token("test_code")

            assert exc_info.value.status_code == 504


class TestGetUserInfo:
    """Tests for get_user_info method."""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, github_service):
        """Test successful user info retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.get_user_info("test_token")

            assert result["login"] == "testuser"
            assert result["id"] == 12345

    @pytest.mark.asyncio
    async def test_get_user_info_invalid_token(self, github_service):
        """Test user info with invalid token."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}
        mock_response.text = "Bad credentials"

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GitHubAuthenticationError) as exc_info:
                await github_service.get_user_info("invalid_token")

            assert exc_info.value.status_code == 401


class TestVerifyTokenValidity:
    """Tests for verify_token_validity method."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, github_service):
        """Test verification of valid token."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.verify_token_validity("valid_token")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, github_service):
        """Test verification of invalid token."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.verify_token_validity("invalid_token")
            assert result is False

    @pytest.mark.asyncio
    async def test_verify_token_timeout(self, github_service):
        """Test token verification timeout returns False."""
        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.verify_token_validity("test_token")
            assert result is False


class TestGetUserRepos:
    """Tests for get_user_repos method."""

    @pytest.mark.asyncio
    async def test_get_user_repos_success(self, github_service):
        """Test successful repository retrieval."""
        mock_repos = [
            {"id": 1, "name": "repo1", "full_name": "user/repo1"},
            {"id": 2, "name": "repo2", "full_name": "user/repo2"}
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_repos

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.get_user_repos("test_token")

            assert len(result) == 2
            assert result[0]["name"] == "repo1"

    @pytest.mark.asyncio
    async def test_get_user_repos_with_custom_params(self, github_service):
        """Test repository retrieval with custom parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            await github_service.get_user_repos("test_token", sort="created", per_page=50)

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["sort"] == "created"
            assert call_args.kwargs["params"]["per_page"] == 50


class TestCreateWebhook:
    """Tests for create_webhook method."""

    @pytest.mark.asyncio
    async def test_create_webhook_success(self, github_service, mock_settings):
        """Test successful webhook creation."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "name": "web",
            "active": True,
            "events": ["push"]
        }

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.create_webhook("token", "owner", "repo")

            assert result["id"] == 12345
            assert result["active"] is True

    @pytest.mark.asyncio
    async def test_create_webhook_custom_events(self, github_service, mock_settings):
        """Test webhook creation with custom events."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 12345}

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            custom_events = ["push", "pull_request"]
            await github_service.create_webhook("token", "owner", "repo", events=custom_events)

            call_args = mock_client.post.call_args
            webhook_config = call_args.kwargs["json"]
            assert webhook_config["events"] == custom_events


class TestDeleteWebhook:
    """Tests for delete_webhook method."""

    @pytest.mark.asyncio
    async def test_delete_webhook_success(self, github_service):
        """Test successful webhook deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.delete_webhook("token", "owner", "repo", 12345)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_webhook_not_found(self, github_service):
        """Test webhook deletion when webhook not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            result = await github_service.delete_webhook("token", "owner", "repo", 99999)
            assert result is False


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, github_service):
        """Test handling of rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "API rate limit exceeded"
        }
        mock_response.text = "API rate limit exceeded"

        with patch.object(github_service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value.__aenter__.return_value = mock_client

            with pytest.raises(GitHubRateLimitError) as exc_info:
                await github_service.get_user_info("token")

            assert exc_info.value.status_code == 403

    def test_handle_github_error_creates_appropriate_exception(self, github_service):
        """Test that _handle_github_error creates appropriate exception types."""
        # Test rate limit error
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "API rate limit exceeded"}
        mock_response.text = "API rate limit exceeded"

        with pytest.raises(GitHubRateLimitError):
            github_service._handle_github_error(mock_response, "Default message")

        # Test authentication error
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}

        with pytest.raises(GitHubAuthenticationError):
            github_service._handle_github_error(mock_response, "Default message")


class TestGlobalServiceManagement:
    """Tests for global service instance management."""

    def test_get_github_service_creates_instance(self):
        """Test that get_github_service creates an instance."""
        service = get_github_service()
        assert isinstance(service, GitHubService)

    def test_get_github_service_returns_singleton(self):
        """Test that get_github_service returns the same instance."""
        service1 = get_github_service()
        service2 = get_github_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_cleanup_github_service(self):
        """Test cleanup of global service instance."""
        # Create service
        service = get_github_service()
        _ = service.client  # Initialize client

        await cleanup_github_service()

        # Service should be cleaned up
        new_service = get_github_service()
        assert new_service is not service
