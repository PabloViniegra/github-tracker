"""
GitHub Activity Tracker API

A FastAPI application for tracking GitHub activity using OAuth authentication
and real-time webhooks.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings, logger
from app.core.database import close_mongo_connection, connect_to_mongo, db
from app.middleware import RateLimitHeadersMiddleware, limiter
from app.routes import activity_router, auth_router, webhook_router
from app.services.github import cleanup_github_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting GitHub Activity Tracker API...")

    try:
        # Connect to MongoDB
        await connect_to_mongo()

        # Create database indexes
        mongodb = db.client[settings.mongodb_db_name]

        try:
            # User collection indexes
            await mongodb.users.create_index("github_id", unique=True)
            await mongodb.users.create_index("username")

            # Webhook notifications indexes
            await mongodb.webhook_notifications.create_index(
                [("user_id", 1), ("created_at", -1)]
            )
            await mongodb.webhook_notifications.create_index(
                [("user_id", 1), ("processed", 1)]
            )

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.warning(f"Index creation warning (may already exist): {str(e)}")

        logger.info("Application startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down GitHub Activity Tracker API...")

    try:
        await cleanup_github_service()
        await close_mongo_connection()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="API for tracking GitHub activity with real-time webhooks",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)

# Rate Limiting Middleware
app.add_middleware(RateLimitHeadersMiddleware)

# Register limiter with app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include API routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(activity_router, prefix=settings.api_v1_prefix)
app.include_router(webhook_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Root"])
@limiter.limit("20/minute")
async def root(request: Request) -> dict:
    """
    Root endpoint with API information.

    Returns:
        dict: API metadata and available endpoints
    """
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "features": [
            "GitHub OAuth Authentication",
            "JWT Token-based Auth",
            "Per-user Rate Limiting",
            "Real-time Webhooks",
            "Activity Tracking",
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "api": settings.api_v1_prefix,
        },
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Application health status
    """
    try:
        # Check database connection
        if db.client:
            await db.client.admin.command("ping")
            db_status = "healthy"
        else:
            db_status = "disconnected"
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.app_version,
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
