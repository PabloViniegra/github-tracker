"""Security headers middleware.

This middleware adds security headers to all HTTP responses to protect against
common web vulnerabilities.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables XSS filter in older browsers
    - Strict-Transport-Security: Enforces HTTPS connections
    - X-Request-ID: Unique identifier for request tracking

    The HSTS header is only added for HTTPS requests to avoid browser warnings
    during local development.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add security headers to the response.

        Args:
            request: The incoming FastAPI request
            call_next: The next middleware or route handler

        Returns:
            Response with security headers added
        """
        # Generate unique request ID for tracking
        request_id = str(uuid.uuid4())

        # Add request ID to request state for logging
        request.state.request_id = request_id

        # Process the request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Request-ID"] = request_id

        # Add HSTS only for HTTPS connections
        # This prevents browser warnings during local HTTP development
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        logger.debug(f"Added security headers to response for request {request_id}")

        return response
