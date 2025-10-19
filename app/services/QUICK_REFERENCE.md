# GitHub Service - Quick Reference Card

## Import

```python
from app.services import (
    get_github_service,
    GitHubAuthenticationError,
    GitHubRateLimitError,
    GitHubAPIError
)
```

## Basic Usage

```python
# Get service instance
github = get_github_service()
```

## OAuth Flow

```python
# 1. Generate authorization URL
state = "random-csrf-token"
auth_url = github.get_authorization_url(state)
# Returns: https://github.com/login/oauth/authorize?...

# 2. Exchange code for token (from callback)
token_data = await github.exchange_code_for_token(code)
access_token = token_data["access_token"]

# 3. Verify token is valid
is_valid = await github.verify_token_validity(access_token)
```

## User Operations

```python
# Get user info
user = await github.get_user_info(access_token)
# Returns: {"id": 123, "login": "username", "name": "User Name", ...}

# Get user repositories
repos = await github.get_user_repos(
    access_token,
    sort="updated",  # created, updated, pushed, full_name
    per_page=100     # max 100
)

# Get user activity
events = await github.get_user_activity(
    access_token,
    username="octocat",
    per_page=100
)
```

## Webhook Operations

```python
# Create webhook
webhook = await github.create_webhook(
    access_token,
    owner="username",
    repo="repository",
    events=["push", "pull_request"]  # optional
)
# Returns: {"id": 12345, "active": True, ...}

# List webhooks
webhooks = await github.list_webhooks(
    access_token,
    owner="username",
    repo="repository"
)

# Delete webhook
success = await github.delete_webhook(
    access_token,
    owner="username",
    repo="repository",
    hook_id=12345
)
# Returns: True if successful
```

## Error Handling

```python
try:
    user = await github.get_user_info(access_token)
except GitHubAuthenticationError as e:
    # Handle auth errors (401)
    print(f"Auth failed: {e.message}")
    print(f"Status: {e.status_code}")
    print(f"Data: {e.response_data}")
except GitHubRateLimitError as e:
    # Handle rate limiting (403)
    print(f"Rate limited: {e.message}")
    reset_time = e.response_data.get("reset")
except GitHubAPIError as e:
    # Handle other API errors
    print(f"API error: {e.message}")
except HTTPException as e:
    # Handle HTTP exceptions (timeouts, etc.)
    print(f"HTTP error: {e.detail}")
```

## Cleanup

```python
from app.services import cleanup_github_service

# In application shutdown
await cleanup_github_service()
```

## Integration with FastAPI

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from app.services import get_github_service, cleanup_github_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await cleanup_github_service()

app = FastAPI(lifespan=lifespan)

@app.get("/repos")
async def get_repos(token: str):
    github = get_github_service()
    try:
        return await github.get_user_repos(token)
    except GitHubAuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Configuration

Required environment variables (in .env):
```bash
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/callback
GITHUB_WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_URL=https://your-domain.com/api/v1/webhooks/github
```

## Common Patterns

### Validate Token Before Use
```python
if not await github.verify_token_validity(token):
    raise HTTPException(status_code=401, detail="Token expired")
```

### Paginate Repositories
```python
all_repos = []
page = 1
while True:
    repos = await github.get_user_repos(token, per_page=100)
    if not repos:
        break
    all_repos.extend(repos)
    page += 1
```

### Handle Rate Limiting with Retry
```python
import asyncio

async def get_repos_with_retry(token, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await github.get_user_repos(token)
        except GitHubRateLimitError as e:
            if attempt < max_retries - 1:
                reset = e.response_data.get("reset", 60)
                await asyncio.sleep(reset)
            else:
                raise
```

## Webhook Events

Default events tracked:
- `push` - Code pushed
- `pull_request` - PR opened/closed/merged
- `issues` - Issue opened/closed
- `issue_comment` - Comment on issue
- `commit_comment` - Comment on commit
- `create` - Branch/tag created
- `delete` - Branch/tag deleted
- `fork` - Repository forked
- `star` - Repository starred
- `watch` - Repository watched
- `release` - Release published

## Constants

```python
github.BASE_URL = "https://api.github.com"
github.OAUTH_URL = "https://github.com/login/oauth"
github.DEFAULT_TIMEOUT = 30.0  # seconds
```

## Logging

The service logs at different levels:
- **INFO**: Method entry/exit, successful operations
- **WARNING**: Recoverable errors (invalid tokens, rate limits)
- **ERROR**: API errors, failed operations
- **DEBUG**: Detailed operation info

Enable logging:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Type Hints

All methods are fully typed:
```python
async def get_user_repos(
    self,
    access_token: str,
    sort: str = "updated",
    per_page: int = 100
) -> List[Dict[str, Any]]:
```

Use with mypy:
```bash
mypy app/services/github.py
```

## Testing

```bash
# Run tests
pytest app/services/test_github.py -v

# With coverage
pytest app/services/test_github.py --cov=app.services.github

# Specific test
pytest app/services/test_github.py::TestGetUserInfo::test_get_user_info_success -v
```

## Performance Tips

1. Reuse service instance (singleton pattern)
2. Let the service manage HTTP client lifecycle
3. Use appropriate per_page values to reduce requests
4. Handle rate limiting gracefully
5. Clean up service on application shutdown

## Security Notes

- Never log access tokens
- Always use HTTPS endpoints
- Verify webhook signatures (use `security.py` helper)
- Rotate tokens regularly
- Use minimal required OAuth scopes
