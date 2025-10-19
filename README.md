# GitHub Activity Tracker API

A production-ready FastAPI application for tracking GitHub activity using OAuth authentication and real-time webhooks.

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **GitHub OAuth Authentication** - Secure user authentication via GitHub OAuth
- **JWT Token-based Auth** - Access and refresh tokens with expiration
- **Real-time Webhooks** - Receive GitHub events in real-time
- **Activity Tracking** - Monitor repositories and user events
- **Per-user Rate Limiting** - Protect API from abuse
- **MongoDB Integration** - Async database operations with Motor
- **Comprehensive Logging** - Production-ready logging system
- **Type Safety** - Full type hints throughout the codebase
- **API Documentation** - Auto-generated OpenAPI/Swagger docs

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Prerequisites

- Python 3.12 or higher
- MongoDB 4.4 or higher
- GitHub OAuth App credentials
- ngrok or similar tool for local webhook testing

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/github-tracker.git
cd github-tracker
```

### 2. Create virtual environment

```bash
# Windows (Git Bash)
python -m venv venv
source venv/Scripts/activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install development dependencies (optional)

```bash
pip install pytest pytest-asyncio black flake8 mypy
```

## Configuration

### 1. Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=github_tracker

# GitHub OAuth (create at https://github.com/settings/developers)
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback

# GitHub Webhook
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
WEBHOOK_URL=https://your-domain.com/api/v1/webhooks/github

# JWT Configuration
JWT_SECRET_KEY=your_super_secret_jwt_key_at_least_32_characters_long
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_ACTIVITY=50/minute

# API Configuration
API_V1_PREFIX=/api/v1
FRONTEND_URL=http://localhost:3000

# Application Settings
APP_NAME=GitHub Activity Tracker
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
```

### 2. GitHub OAuth App Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: GitHub Activity Tracker
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/api/v1/auth/github/callback`
4. Save the Client ID and Client Secret to your `.env` file

### 3. MongoDB Setup

Make sure MongoDB is running:

```bash
# Check if MongoDB is running
mongosh

# Or start MongoDB service
# Windows
net start MongoDB

# macOS (Homebrew)
brew services start mongodb-community

# Linux (systemd)
sudo systemctl start mongod
```

## Running the Application

### Development Server

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using the script in main.py
python -m app.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Production Server

```bash
# Using gunicorn with uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Project Structure

```
github-tracker/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Application settings
│   │   ├── database.py           # MongoDB connection
│   │   ├── security.py           # JWT & signature verification
│   │   └── dependencies.py       # FastAPI dependencies
│   ├── models/                   # Pydantic models
│   │   ├── __init__.py
│   │   ├── base.py               # Base model utilities
│   │   ├── user.py               # User models
│   │   ├── token.py              # Token models
│   │   ├── webhook.py            # Webhook models
│   │   ├── auth.py               # Auth models
│   │   └── activity.py           # Activity models
│   ├── routes/                   # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── activity.py           # Activity endpoints
│   │   └── webhooks.py           # Webhook endpoints
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── github.py             # GitHub API integration
│   │   ├── user.py               # User CRUD operations
│   │   └── webhook.py            # Webhook management
│   └── middleware/               # Custom middleware
│       ├── __init__.py
│       └── rate_limiting.py      # Rate limiting logic
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── fixtures/                 # Test fixtures
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── CLAUDE.md                     # Claude Code instructions
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## API Endpoints

### Authentication

- `GET /api/v1/auth/github/login` - Initiate GitHub OAuth flow
- `GET /api/v1/auth/github/callback` - OAuth callback handler
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout user
- `GET /api/v1/auth/me` - Get current user info

### Activity

- `GET /api/v1/activity/repositories` - Get user repositories
- `GET /api/v1/activity/events` - Get user activity events

### Webhooks

- `POST /api/v1/webhooks/github` - Receive GitHub webhook events
- `POST /api/v1/webhooks/setup/{owner}/{repo}` - Setup webhook on repository
- `GET /api/v1/webhooks/list/{owner}/{repo}` - List webhooks for repository
- `DELETE /api/v1/webhooks/remove/{owner}/{repo}/{hook_id}` - Remove webhook
- `GET /api/v1/webhooks/notifications` - Get user notifications
- `POST /api/v1/webhooks/notifications/{id}/mark-processed` - Mark notification as processed
- `POST /api/v1/webhooks/notifications/mark-all-processed` - Mark all notifications as processed

### System

- `GET /` - API information
- `GET /health` - Health check endpoint

## Development

### Code Quality

```bash
# Format code with Black
black app/ tests/

# Lint with flake8
flake8 app/ tests/

# Type check with mypy
mypy app/
```

### Database Indexes

The application automatically creates the following indexes on startup:

**Users Collection:**
- `github_id` (unique)
- `username`

**Webhook Notifications Collection:**
- `(user_id, created_at)` - for sorting notifications
- `(user_id, processed)` - for filtering processed notifications

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_github_service.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── unit/                         # Unit tests for individual components
│   ├── test_github_service.py
│   ├── test_user_service.py
│   └── test_webhook_service.py
├── integration/                  # Integration tests
│   ├── test_auth_flow.py
│   └── test_webhook_flow.py
└── fixtures/                     # Shared test fixtures
    └── sample_data.py
```

## Deployment

### Using Docker (Recommended)

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t github-tracker .
docker run -p 8000:8000 --env-file .env github-tracker
```

### Environment Variables in Production

Make sure to set these in your production environment:
- Set `DEBUG=false`
- Use strong `JWT_SECRET_KEY` (min 32 characters)
- Set `LOG_LEVEL=INFO` or `WARNING`
- Use proper `FRONTEND_URL` for CORS
- Set secure `GITHUB_WEBHOOK_SECRET`

### Webhook Configuration for Production

1. Deploy your application to a public URL
2. Update `WEBHOOK_URL` in `.env` to point to your public endpoint
3. GitHub will send webhooks to `https://your-domain.com/api/v1/webhooks/github`

## Security Considerations

- JWT tokens are signed and verified
- GitHub webhook signatures are validated using HMAC SHA256
- Rate limiting prevents API abuse
- CORS is configured to only allow specified origins
- All passwords and secrets are hashed/encrypted
- Environment variables are used for sensitive data
- MongoDB queries use parameterized queries (no injection)

## Performance

- Async/await for non-blocking I/O
- Connection pooling for HTTP requests
- MongoDB indexes for fast queries
- Rate limiting to prevent overload
- Efficient pagination for large datasets

## Troubleshooting

### MongoDB Connection Issues

```bash
# Check MongoDB status
mongosh --eval "db.adminCommand('ping')"

# Check connection string
echo $MONGODB_URL
```

### OAuth Callback Issues

- Ensure `GITHUB_REDIRECT_URI` matches exactly in GitHub app settings
- Check that the callback URL is accessible
- Verify `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correct

### Webhook Not Receiving Events

- Ensure `WEBHOOK_URL` is publicly accessible
- Check GitHub webhook delivery logs
- Verify `GITHUB_WEBHOOK_SECRET` matches in both places
- Check application logs for signature verification errors

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastAPI for the excellent web framework
- Motor for async MongoDB support
- GitHub for the OAuth and Webhooks API

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

Built with ❤️ using FastAPI and Python
