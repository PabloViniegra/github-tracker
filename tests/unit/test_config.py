"""
Unit tests for configuration management.

Tests settings loading and validation.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Test Settings model."""

    def test_settings_creation_with_defaults(self):
        """Test Settings creation with default values."""
        settings = Settings(
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_client_id",
            github_client_secret="test_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert settings.app_name == "GitHub Activity Tracker"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_access_token_expire_minutes == 15
        assert settings.jwt_refresh_token_expire_days == 7

    def test_settings_custom_values(self):
        """Test Settings with custom values."""
        settings = Settings(
            app_name="Custom App",
            app_version="2.0.0",
            debug=True,
            log_level="DEBUG",
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="custom_db",
            github_client_id="custom_client",
            github_client_secret="custom_secret",
            github_redirect_uri="http://example.com/callback",
            github_webhook_secret="custom_webhook_secret",
            webhook_url="http://example.com/webhooks",
            jwt_secret_key="custom_jwt_secret_12345678abcdefghijklmnop",
            jwt_algorithm="HS512",
            jwt_access_token_expire_minutes=30,
            jwt_refresh_token_expire_days=14,
            frontend_url="http://example.com"
        )

        assert settings.app_name == "Custom App"
        assert settings.app_version == "2.0.0"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.jwt_algorithm == "HS512"
        assert settings.jwt_access_token_expire_minutes == 30
        assert settings.jwt_refresh_token_expire_days == 14

    def test_get_settings_returns_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Both should be the same instance
        assert settings1 is settings2

    def test_settings_api_v1_prefix(self):
        """Test that API v1 prefix is correctly set."""
        settings = Settings(
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_client",
            github_client_secret="test_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert settings.api_v1_prefix == "/api/v1"

    def test_settings_rate_limiting_defaults(self):
        """Test rate limiting default settings."""
        settings = Settings(
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_client",
            github_client_secret="test_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_default == "100/minute"
        assert settings.rate_limit_auth == "5/minute"
        assert settings.rate_limit_activity == "50/minute"


@pytest.mark.unit
class TestDatabaseConfig:
    """Test database configuration."""

    def test_mongodb_url_format(self):
        """Test MongoDB URL format validation."""
        settings = Settings(
            mongodb_url="mongodb://user:pass@localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_client",
            github_client_secret="test_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert "mongodb://" in settings.mongodb_url
        assert settings.mongodb_db_name == "test_db"


@pytest.mark.unit
class TestSecurityConfig:
    """Test security configuration."""

    def test_jwt_settings(self):
        """Test JWT configuration settings."""
        settings = Settings(
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_client",
            github_client_secret="test_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert settings.jwt_secret_key
        assert settings.jwt_algorithm
        assert settings.jwt_access_token_expire_minutes > 0
        assert settings.jwt_refresh_token_expire_days > 0

    def test_github_oauth_settings(self):
        """Test GitHub OAuth configuration."""
        settings = Settings(
            mongodb_url="mongodb://localhost:27017",
            mongodb_db_name="test_db",
            github_client_id="test_github_client",
            github_client_secret="test_github_secret",
            github_redirect_uri="http://localhost:8000/callback",
            github_webhook_secret="test_webhook_secret",
            webhook_url="http://localhost:8000/webhooks",
            jwt_secret_key="test_jwt_secret_key_1234567890abcdefghijklmnop",
            frontend_url="http://localhost:3000"
        )

        assert settings.github_client_id == "test_github_client"
        assert settings.github_client_secret == "test_github_secret"
        assert "callback" in settings.github_redirect_uri
        assert settings.github_webhook_secret
        assert settings.webhook_url
