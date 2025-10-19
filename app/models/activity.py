"""
GitHub activity-related Pydantic models.

This module contains response models for GitHub activity endpoints
including repositories and events.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RepositoriesResponse(BaseModel):
    """Response model for user repositories endpoint."""

    repositories: List[Dict[str, Any]] = Field(
        ...,
        description="List of GitHub repositories",
        example=[
            {
                "id": 123456789,
                "name": "my-repo",
                "full_name": "username/my-repo",
                "private": False,
                "html_url": "https://github.com/username/my-repo",
                "description": "A sample repository",
                "fork": False,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "pushed_at": "2024-01-01T00:00:00Z",
                "stargazers_count": 10,
                "watchers_count": 10,
                "forks_count": 2,
                "language": "Python",
            }
        ]
    )


class EventsResponse(BaseModel):
    """Response model for user activity events endpoint."""

    events: List[Dict[str, Any]] = Field(
        ...,
        description="List of GitHub activity events",
        example=[
            {
                "id": "123456789",
                "type": "PushEvent",
                "actor": {
                    "id": 12345,
                    "login": "username",
                    "avatar_url": "https://avatars.githubusercontent.com/u/12345"
                },
                "repo": {
                    "id": 123456789,
                    "name": "username/my-repo",
                    "url": "https://api.github.com/repos/username/my-repo"
                },
                "payload": {
                    "push_id": 987654321,
                    "size": 1,
                    "commits": []
                },
                "public": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
    )
