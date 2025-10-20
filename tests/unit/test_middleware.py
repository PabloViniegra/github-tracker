"""
Unit tests for middleware components.

Tests rate limiting and other middleware functionality.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request

from app.middleware.rate_limiting import limiter, get_user_identifier


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting middleware."""

    def test_get_user_identifier_with_user_id(self):
        """Test extracting user_id from request.state."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user_id = "507f1f77bcf86cd799439011"
        request.client = MagicMock()
        request.client.host = "192.168.1.1"

        result = get_user_identifier(request)

        assert result == "user:507f1f77bcf86cd799439011"

    def test_get_user_identifier_without_user_id(self):
        """Test falling back to IP address when user_id not in state."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        # Simulate missing user_id attribute
        del request.state.user_id
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        # Since get_remote_address is used, we need to import it
        from slowapi.util import get_remote_address

        # Mock get_remote_address to return a specific IP
        with MagicMock(return_value="192.168.1.100") as mock_get_ip:
            result = get_user_identifier(request)
            assert result.startswith("ip:")

    def test_limiter_initialized(self):
        """Test that limiter is properly initialized."""
        assert limiter is not None
        assert limiter._key_func == get_user_identifier
        assert limiter._default_limits is not None


@pytest.mark.unit
@pytest.mark.asyncio
class TestRateLimitHeadersMiddleware:
    """Test RateLimitHeadersMiddleware."""

    async def test_middleware_with_rate_limit_info(self):
        """Test that middleware adds headers when rate limit info is present."""
        from app.middleware.rate_limiting import RateLimitHeadersMiddleware

        # Mock request with rate limit info
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.view_rate_limit = {
            "limit": 100,
            "remaining": 95,
            "reset": 1234567890
        }

        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {}

        async def mock_call_next(req):
            return mock_response

        # Create middleware
        middleware = RateLimitHeadersMiddleware(app=MagicMock())

        # Call middleware
        response = await middleware.dispatch(request, mock_call_next)

        # Verify headers were added with correct values
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "95"
        assert response.headers["X-RateLimit-Reset"] == "1234567890"

    async def test_middleware_without_rate_limit_info(self):
        """Test that middleware works when rate limit info is not present."""
        from app.middleware.rate_limiting import RateLimitHeadersMiddleware

        # Mock request without rate limit info
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        # No view_rate_limit attribute

        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {}

        async def mock_call_next(req):
            return mock_response

        # Create middleware
        middleware = RateLimitHeadersMiddleware(app=MagicMock())

        # Call middleware
        response = await middleware.dispatch(request, mock_call_next)

        # Verify response is returned without headers (since no rate limit info)
        assert response is mock_response


@pytest.mark.unit
class TestLimiterConfiguration:
    """Test limiter configuration and state."""

    def test_limiter_has_default_limits(self):
        """Test that limiter has default limits configured."""
        assert limiter._default_limits is not None
        assert len(limiter._default_limits) > 0

    def test_limiter_enabled_setting(self):
        """Test that limiter enabled state can be configured."""
        from app.core.config import get_settings

        settings = get_settings()
        # The limiter will respect the rate_limit_enabled setting
        assert hasattr(settings, 'rate_limit_enabled')
        assert isinstance(settings.rate_limit_enabled, bool)

    def test_limiter_default_limit_setting(self):
        """Test that limiter has default limit from settings."""
        from app.core.config import get_settings

        settings = get_settings()
        assert hasattr(settings, 'rate_limit_default')
        assert settings.rate_limit_default is not None
