"""Application configuration."""

import logging
from functools import lru_cache
from typing import Any, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "GitHub Activity Tracker"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # MongoDB
    mongodb_url: str
    mongodb_db_name: str
    mongodb_max_pool_size: int = 50
    mongodb_min_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # GitHub OAuth
    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str

    # GitHub Webhook
    github_webhook_secret: str
    webhook_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "5/minute"
    rate_limit_activity: str = "50/minute"

    # API
    api_v1_prefix: str = "/api/v1"
    frontend_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("mongodb_url")
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL format."""
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("Invalid MongoDB URL format")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key length."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Initialize logger
logger = setup_logging(get_settings().log_level)
