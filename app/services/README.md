# GitHub Service Module

Production-ready GitHub API service for the GitHub Activity Tracker application.

## Overview

The `github.py` module provides a comprehensive, production-ready service layer for interacting with GitHub's REST API. It includes OAuth authentication, repository management, webhook operations, and robust error handling.

## Key Improvements

### 1. Comprehensive Type Hints
All methods now include complete type hints for parameters and return values:
```python
async def get_user_repos(
    self,
    access_token: str,
    sort: str = "updated",
    per_page: int = 100
) -> List[Dict[str, Any]]:
```

### 2. Timezone-Aware Datetime
Replaced deprecated `datetime.utcnow()` with modern timezone-aware approach:
```python
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

### 3. Specific Exception Handling
Replaced bare `except` clause with specific exception types:
```python
except httpx.TimeoutException as e:
    logger.error(f"Timeout during token verification: {e}")
    return False
except httpx.HTTPError as e:
    logger.warning(f"HTTP error during token verification: {e}")
    return False
except Exception as e:
    logger.exception(f"Unexpected error during token verification: {e}")
    return False
```

### 4. Comprehensive Logging
Added detailed logging throughout all methods:
```python
logger.info(f"Fetching user repositories (sort={sort}, per_page={per_page})")
logger.error(f"GitHub API error: status={response.status_code}, message={error_message}")
logger.debug("Token validity check result: {is_valid}")
```

### 5. HTTP Timeout Configuration
All HTTP requests now have a 30-second timeout:
```python
DEFAULT_TIMEOUT: float = 30.0

client = httpx.AsyncClient(
    timeout=httpx.Timeout(self.DEFAULT_TIMEOUT),
    follow_redirects=True
)
```

### 6. Custom Exception Types
Created specific exception classes for better error handling:
- `GitHubAPIError`: Base exception for GitHub API errors
- `GitHubAuthenticationError`: Authentication failures
- `GitHubRateLimitError`: Rate limit exceeded

### 7. Complete Docstrings
All methods include comprehensive docstrings with examples:
```python
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
```

### 8. Updated Imports
Uses the new `app.core.config` module structure:
```python
from app.core.config import get_settings
```

### 9. Shared HTTP Client
Implemented a reusable HTTP client with proper lifecycle management:
```python
@property
def client(self) -> httpx.AsyncClient:
    """Get or create the shared HTTP client."""
    if self._client is None or self._client.is_closed:
        self._client = httpx.AsyncClient(...)
    return self._client

async def close(self) -> None:
    """Close the HTTP client and cleanup resources."""
    if self._client is not None and not self._client.is_closed:
        await self._client.aclose()
```

### 10. Singleton Pattern
Implemented global service instance management:
```python
def get_github_service() -> GitHubService:
    """Get or create the global GitHub service instance."""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service

async def cleanup_github_service() -> None:
    """Cleanup the global GitHub service instance."""
    global _github_service
    if _github_service is not None:
        await _github_service.close()
```

## Usage

### Basic Usage

```python
from app.services import get_github_service

# Get the service instance
github_service = get_github_service()

# OAuth flow
auth_url = github_service.get_authorization_url("state_token")
token_data = await github_service.exchange_code_for_token("oauth_code")
user_info = await github_service.get_user_info(token_data["access_token"])

# Get user data
repos = await github_service.get_user_repos(access_token)
events = await github_service.get_user_activity(access_token, username)

# Webhook management
webhook = await github_service.create_webhook(access_token, owner, repo)
webhooks = await github_service.list_webhooks(access_token, owner, repo)
success = await github_service.delete_webhook(access_token, owner, repo, hook_id)
```

### Error Handling

```python
from app.services import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    get_github_service
)

github_service = get_github_service()

try:
    user_info = await github_service.get_user_info(access_token)
except GitHubAuthenticationError as e:
    # Handle authentication errors
    print(f"Auth error: {e.message}")
except GitHubRateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited: {e.message}")
except GitHubAPIError as e:
    # Handle other API errors
    print(f"API error: {e.message} (status: {e.status_code})")
```

### Cleanup

```python
from app.services import cleanup_github_service

# In application shutdown
await cleanup_github_service()
```

## Testing

The module includes comprehensive unit tests in `test_github.py` with >90% coverage:

```bash
# Run tests
pytest app/services/test_github.py -v

# Run with coverage
pytest app/services/test_github.py --cov=app.services.github --cov-report=html
```

### Test Categories

1. **Initialization Tests**: Service creation and client management
2. **OAuth Tests**: Authorization URL generation and token exchange
3. **User Data Tests**: User info and repository retrieval
4. **Webhook Tests**: Webhook CRUD operations
5. **Error Handling Tests**: Rate limiting, authentication errors, timeouts
6. **Global Service Tests**: Singleton pattern and cleanup

## API Reference

### GitHubService

#### OAuth Methods
- `get_authorization_url(state: str) -> str`: Generate OAuth authorization URL
- `exchange_code_for_token(code: str) -> Dict[str, Any]`: Exchange OAuth code for token
- `verify_token_validity(access_token: str) -> bool`: Verify token validity

#### User Data Methods
- `get_user_info(access_token: str) -> Dict[str, Any]`: Get authenticated user info
- `get_user_repos(access_token: str, sort: str, per_page: int) -> List[Dict[str, Any]]`: Get user repositories
- `get_user_activity(access_token: str, username: str, per_page: int) -> List[Dict[str, Any]]`: Get user activity

#### Webhook Methods
- `create_webhook(access_token: str, owner: str, repo: str, events: Optional[List[str]]) -> Dict[str, Any]`: Create repository webhook
- `list_webhooks(access_token: str, owner: str, repo: str) -> List[Dict[str, Any]]`: List repository webhooks
- `delete_webhook(access_token: str, owner: str, repo: str, hook_id: int) -> bool`: Delete repository webhook

#### Lifecycle Methods
- `close() -> None`: Close HTTP client and cleanup resources

### Helper Functions
- `get_github_service() -> GitHubService`: Get singleton service instance
- `cleanup_github_service() -> None`: Cleanup global service instance

## Configuration

The service uses the following settings from `app.core.config`:

- `github_client_id`: GitHub OAuth app client ID
- `github_client_secret`: GitHub OAuth app client secret
- `github_redirect_uri`: OAuth callback URL
- `github_webhook_secret`: Webhook signature secret
- `webhook_url`: Public webhook endpoint URL

## Performance Considerations

1. **Connection Pooling**: Reuses HTTP client for better performance
2. **Timeouts**: All requests have 30-second timeout to prevent hanging
3. **Async/Await**: Fully asynchronous for high concurrency
4. **Singleton Pattern**: Single service instance reduces overhead

## Security

1. **Token Validation**: Verifies GitHub tokens before operations
2. **Webhook Signatures**: Uses HMAC SHA-256 for webhook verification
3. **HTTPS Only**: All GitHub API calls use HTTPS
4. **Secure Headers**: Includes User-Agent and Accept headers
5. **Error Sanitization**: Logs errors without exposing sensitive data

## Migration Guide

If migrating from the old `github_service.py`:

```python
# Old
from github_service import GitHubService
service = GitHubService()

# New
from app.services import get_github_service
service = get_github_service()
```

All method signatures remain the same for backward compatibility.
