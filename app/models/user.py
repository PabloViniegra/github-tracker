"""User data models."""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId


class UserBase(BaseModel):
    """Base user model with common fields."""

    github_id: int
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    profile_url: str


class UserInDB(UserBase):
    """User model as stored in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    github_access_token: str
    github_token_expires_at: Optional[datetime] = None
    webhook_configured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class UserResponse(UserBase):
    """User response model for API."""

    id: str
    created_at: datetime
    webhook_configured: bool

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
    )
