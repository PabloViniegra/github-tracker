"""
Authentication-related Pydantic models.

This module contains models for OAuth state management and
authentication-related data structures.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OAuthState(BaseModel):
    """
    OAuth state tracking model.

    Used to track OAuth state tokens during the GitHub OAuth flow
    and prevent CSRF attacks.
    """

    created_at: datetime = Field(
        ...,
        description="Timestamp when the state was created"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
