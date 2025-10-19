# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Activity Tracker API - A FastAPI application that tracks GitHub activity using OAuth authentication and real-time webhooks. Users authenticate via GitHub OAuth, and the API sets up webhooks to receive real-time notifications about repository events.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows Git Bash)
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Run development server
uvicorn main:app --reload

# Run on specific host/port
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables
The application requires a `.env` file with the following variables (see config.py:6-33):
- `MONGODB_URL` - MongoDB connection string
- `MONGODB_DB_NAME` - Database name
- `GITHUB_CLIENT_ID` - GitHub OAuth app client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth app client secret
- `GITHUB_REDIRECT_URI` - OAuth callback URL
- `GITHUB_WEBHOOK_SECRET` - Secret for webhook signature verification
- `WEBHOOK_URL` - Public URL where GitHub will send webhooks
- `JWT_SECRET_KEY` - Secret key for JWT signing
- `FRONTEND_URL` - Frontend URL for CORS

## Architecture

### Core Flow

1. **Authentication Flow** (auth_routes.py):
   - User initiates OAuth via `/api/v1/auth/github/login` which generates a state token
   - GitHub redirects to callback with code
   - Backend exchanges code for GitHub access token via GitHubService
   - Creates/updates user in MongoDB with GitHub token
   - Returns JWT access + refresh tokens to client

2. **Webhook Flow** (webhook_routes.py):
   - User sets up webhook on a repo via `/api/v1/webhooks/setup/{owner}/{repo}`
   - GitHubService creates webhook on GitHub pointing to our webhook endpoint
   - GitHub sends events to `/api/v1/webhooks/github`
   - Webhook signature is verified using HMAC SHA256 (security.py:81-98)
   - WebhookService stores notification in MongoDB
   - User can query notifications via `/api/v1/webhooks/notifications`

### Key Components

**Database Layer** (database.py):
- Uses Motor (async MongoDB driver)
- Global `db` instance initialized on startup
- Indexes created in main.py lifespan (main.py:11-22):
  - `users.github_id` (unique)
  - `users.username`
  - `webhook_notifications` by `(user_id, created_at)` and `(user_id, processed)`

**Models** (models.py):
- Uses Pydantic for validation
- `PyObjectId` custom type for MongoDB ObjectId handling
- Main models: `UserInDB`, `WebhookNotification`
- Response models: `UserResponse`, `WebhookNotificationResponse`, `TokenResponse`

**Security** (security.py):
- JWT tokens: 15min access tokens, 7-day refresh tokens
- Two token types validated: "access" and "refresh"
- GitHub webhook signatures verified via HMAC SHA256
- HTTPBearer authentication scheme

**Dependencies** (dependencies.py):
- `get_current_user` dependency validates JWT, fetches user from DB
- Verifies both JWT validity and GitHub token validity
- Stores user_id in request.state for rate limiting

**Rate Limiting** (rate_limiter.py, middleware.py):
- Uses SlowAPI library
- Per-user rate limiting based on user_id from request.state
- Different limits for auth (5/min), activity (50/min), general (100/min)
- Rate limit headers added via RateLimitHeadersMiddleware

**GitHub Integration** (github_service.py):
- All GitHub API interactions centralized in GitHubService
- OAuth flow methods: get_authorization_url, exchange_code_for_token
- User data: get_user_info, get_user_repos, get_user_activity
- Webhook management: create_webhook, list_webhooks, delete_webhook
- Webhook events tracked: push, pull_request, issues, issue_comment, commit_comment, create, delete, fork, star, watch, release

### Route Structure

All routes prefixed with `/api/v1` (config.py:32):
- `/api/v1/auth/*` - Authentication endpoints
- `/api/v1/activity/*` - User repositories and events
- `/api/v1/webhooks/*` - Webhook setup and notifications

### Import Dependencies

Files have circular import dependencies resolved by importing at module level. Key imports used across files:
- auth_routes.py needs: GitHubService, UserService, create_access_token, create_refresh_token, verify_token, limiter, get_settings, get_database, get_current_user
- webhook_routes.py needs: GitHubService, UserService, WebhookService, verify_github_signature, limiter, get_settings, get_database, get_current_user
- main.py imports: connect_to_mongo, close_mongo_connection, get_settings, db, RateLimitHeadersMiddleware, limiter, RateLimitExceeded, _rate_limit_exceeded_handler, auth_router, activity_router, webhook_router

When editing routes, check main.py for missing imports that may need to be added at the top of route files.

### Testing Webhook Integration

To test webhooks locally:
1. Use a tool like ngrok to expose local server: `ngrok http 8000`
2. Set WEBHOOK_URL in .env to the ngrok URL + `/api/v1/webhooks/github`
3. GitHub will send webhooks to this URL with signature in `X-Hub-Signature-256` header
