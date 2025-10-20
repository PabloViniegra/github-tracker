# GitHub Activity Tracker API - Test Suite

Comprehensive test suite for the GitHub Activity Tracker API application.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── pytest.ini            # Pytest configuration
├── unit/                 # Unit tests
│   ├── test_security.py       # Security function tests (JWT, signatures)
│   ├── test_user_service.py   # UserService tests
│   ├── test_webhook_service.py # WebhookService tests
│   ├── test_github_service.py  # GitHubService tests
│   ├── test_auth_routes.py     # Authentication route tests
│   ├── test_webhook_routes.py  # Webhook route tests
│   └── test_activity_routes.py # Activity route tests
└── integration/          # Integration tests
    └── test_api_integration.py # End-to-end API tests
```

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

Required test dependencies:
- pytest==7.4.4
- pytest-asyncio==0.23.3
- pytest-cov==4.1.0
- pytest-mock==3.12.0
- httpx==0.26.0
- mongomock-motor==0.0.21
- faker==22.2.0

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Security tests
pytest -m security

# Service tests
pytest -m services

# Route tests
pytest -m routes
```

### Run Specific Test Files

```bash
# Security tests
pytest tests/unit/test_security.py

# User service tests
pytest tests/unit/test_user_service.py

# Authentication route tests
pytest tests/unit/test_auth_routes.py
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Run with Verbose Output

```bash
pytest -v

# Extra verbose with test output
pytest -vv -s
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.security` - Security function tests
- `@pytest.mark.services` - Service layer tests
- `@pytest.mark.routes` - API route tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.webhooks` - Webhook tests
- `@pytest.mark.activity` - Activity tests
- `@pytest.mark.slow` - Slow running tests

Run tests by marker:

```bash
pytest -m "unit and security"
pytest -m "services or routes"
pytest -m "not slow"
```

## Test Coverage Goals

- **Overall Coverage**: 50%+ (current goal)
- **Critical Paths**: 80%+
  - Authentication flow
  - JWT token management
  - Webhook signature verification
  - User CRUD operations

## Writing Tests

### Test Structure

Follow the AAA pattern:
- **Arrange**: Set up test data and mocks
- **Act**: Execute the function being tested
- **Assert**: Verify the results

Example:

```python
@pytest.mark.unit
@pytest.mark.services
async def test_create_user_success(mock_db, sample_github_user):
    # Arrange
    mock_db.users.insert_one = AsyncMock(return_value=Mock(inserted_id=ObjectId()))
    service = UserService(mock_db)

    # Act
    user = await service.create_or_update_user(
        sample_github_user,
        "test_token",
        None
    )

    # Assert
    assert user is not None
    assert user.username == sample_github_user["login"]
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_example(
    sample_user_in_db,      # Sample user data
    sample_access_token,     # JWT access token
    mock_github_service,     # Mocked GitHub service
    auth_headers            # Authorization headers
):
    # Test code using fixtures
    pass
```

### Mocking External Services

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mocked_service():
    with patch("app.services.github.GitHubService.get_user_info") as mock:
        mock.return_value = {"id": 123, "login": "testuser"}
        # Test code
```

## Test Data

Test fixtures provide realistic test data:

- **Users**: `sample_github_user`, `sample_user_in_db`
- **Tokens**: `sample_access_token`, `sample_refresh_token`
- **Repositories**: `sample_github_repos`
- **Events**: `sample_github_events`
- **Webhooks**: `sample_webhook_payload`, `sample_webhook_notification`
- **OAuth**: `oauth_state`, `oauth_code`, `github_token_response`

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Debugging Tests

### Run Single Test

```bash
pytest tests/unit/test_security.py::TestJWTTokenCreation::test_create_access_token_success -v
```

### Run with PDB

```bash
pytest --pdb  # Drop into debugger on failures
pytest --trace # Drop into debugger at start
```

### Show Print Statements

```bash
pytest -s  # Show print statements
```

### Show Detailed Output

```bash
pytest -vv --tb=long  # Verbose with long tracebacks
```

## Common Issues

### Import Errors

Ensure the project root is in PYTHONPATH:

```bash
export PYTHONPATH=.
pytest
```

### Async Test Failures

Ensure pytest-asyncio is installed and tests are marked with `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Database Connection Issues

Tests use mongomock and shouldn't require a real MongoDB instance. If issues persist, check that `mongomock-motor` is installed.

### Settings/Configuration Issues

Tests use test settings defined in `conftest.py`. If you need custom settings for a test:

```python
def test_with_custom_settings(test_settings):
    test_settings.jwt_secret_key = "custom_secret"
    # Test code
```

## Test Maintenance

### Adding New Tests

1. Create test file in appropriate directory (`unit/` or `integration/`)
2. Add appropriate markers
3. Use existing fixtures when possible
4. Follow naming conventions: `test_<feature>_<scenario>.py`
5. Run tests to ensure they pass
6. Check coverage: `pytest --cov=app`

### Updating Fixtures

Fixtures are in `conftest.py`. When adding new fixtures:

1. Add clear docstring
2. Use appropriate scope (`function`, `session`)
3. Consider dependencies between fixtures
4. Update this README if adding commonly-used fixtures

## Performance

- Unit tests should complete in < 5 seconds
- Integration tests may take longer (< 30 seconds)
- Use `-n auto` for parallel execution (requires pytest-xdist):

```bash
pip install pytest-xdist
pytest -n auto
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Current Test Status

As of the latest run:

- **Total Tests**: 22 (in test_security.py)
- **Passing**: 18
- **Failing**: 4 (being fixed)
- **Coverage**: ~30% (work in progress)

Target for completion:
- [ ] Fix all security tests
- [ ] Complete service layer tests
- [ ] Complete route handler tests
- [ ] Add integration tests
- [ ] Achieve 80% overall coverage
