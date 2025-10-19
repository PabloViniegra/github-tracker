"""
API Routes Module

This module exports all API routers for the GitHub Activity Tracker application.
All routes are prefixed with /api/v1 when included in main.py.
"""

from app.routes.auth import auth_router
from app.routes.activity import activity_router
from app.routes.webhooks import webhook_router

__all__ = [
    "auth_router",
    "activity_router",
    "webhook_router",
]
