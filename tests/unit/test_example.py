"""Example unit test."""

import pytest
from app.core.config import get_settings


def test_settings():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings is not None
    assert settings.app_name == "GitHub Activity Tracker"
    assert settings.api_v1_prefix == "/api/v1"


def test_jwt_algorithm():
    """Test JWT algorithm configuration."""
    settings = get_settings()
    assert settings.jwt_algorithm == "HS256"


@pytest.mark.asyncio
async def test_example_async():
    """Example async test."""
    result = await async_example()
    assert result is True


async def async_example():
    """Example async function."""
    return True
