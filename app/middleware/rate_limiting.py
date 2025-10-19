"""Rate limiting middleware and configuration."""

from typing import Callable

from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings


def get_user_identifier(request: Request) -> str:
    """
    Identify user for rate limiting.

    Priority: user_id > IP address

    Args:
        request: FastAPI request object

    Returns:
        str: User identifier for rate limiting
    """
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    return f"ip:{get_remote_address(request)}"


# Create limiter with in-memory storage
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[get_settings().rate_limit_default],
    enabled=get_settings().rate_limit_enabled,
)


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limiting headers to responses."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and add rate limit headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        response = await call_next(request)

        if hasattr(request.state, "view_rate_limit"):
            limit_info = request.state.view_rate_limit
            # Check if limit_info is a dict before accessing
            if isinstance(limit_info, dict):
                response.headers["X-RateLimit-Limit"] = str(
                    limit_info.get("limit", "")
                )
                response.headers["X-RateLimit-Remaining"] = str(
                    limit_info.get("remaining", "")
                )
                response.headers["X-RateLimit-Reset"] = str(
                    limit_info.get("reset", "")
                )

        return response
