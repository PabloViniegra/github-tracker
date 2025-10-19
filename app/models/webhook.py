"""Webhook data models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.models.base import PyObjectId


class WebhookEventType(str, Enum):
    """Supported GitHub webhook event types."""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    COMMIT_COMMENT = "commit_comment"
    CREATE = "create"
    DELETE = "delete"
    FORK = "fork"
    STAR = "star"
    WATCH = "watch"
    RELEASE = "release"


class WebhookNotification(BaseModel):
    """Webhook notification as stored in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    repository: str
    event_type: str
    action: Optional[str] = None
    payload: Dict[str, Any]
    processed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )


class WebhookNotificationResponse(BaseModel):
    """Webhook notification response for API."""

    id: str = Field(..., description="Notification ID")
    repository: str = Field(..., description="Repository full name")
    event_type: str = Field(..., description="GitHub event type")
    action: Optional[str] = Field(None, description="Event action")
    created_at: datetime = Field(..., description="Notification creation timestamp")
    processed: bool = Field(False, description="Whether notification has been processed")

    model_config = ConfigDict(json_encoders={ObjectId: str, datetime: lambda v: v.isoformat()})


class NotificationsResponse(BaseModel):
    """Response model for notifications list endpoint."""

    notifications: List[WebhookNotificationResponse] = Field(
        ...,
        description="List of webhook notifications"
    )


class WebhookSetupResponse(BaseModel):
    """Response model for webhook setup endpoint."""

    message: str = Field(..., description="Success message")
    webhook_id: int = Field(..., description="GitHub webhook ID")
    repository: str = Field(..., description="Repository full name")
    events: List[str] = Field(..., description="List of subscribed events")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Webhook configured successfully",
                "webhook_id": 123456789,
                "repository": "owner/repo",
                "events": [
                    "push",
                    "pull_request",
                    "issues",
                    "issue_comment",
                    "commit_comment",
                    "create",
                    "delete",
                    "fork",
                    "star",
                    "watch",
                    "release"
                ]
            }
        }
    )


class WebhookListResponse(BaseModel):
    """Response model for webhook list endpoint."""

    webhooks: List[Dict[str, Any]] = Field(
        ...,
        description="List of configured webhooks"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "webhooks": [
                    {
                        "id": 123456789,
                        "name": "web",
                        "active": True,
                        "events": ["push", "pull_request"],
                        "config": {
                            "url": "https://example.com/webhook",
                            "content_type": "json"
                        },
                        "updated_at": "2024-01-01T00:00:00Z",
                        "created_at": "2023-01-01T00:00:00Z"
                    }
                ]
            }
        }
    )
