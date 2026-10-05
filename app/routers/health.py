"""
Health check and system status endpoints.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.models.database import db_manager
from app.services.ai_engine import get_ai_engine

logger = logging.getLogger(__name__)
settings = get_settings()

VERSION = "2.0.0"

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check", description="Basic health check endpoint")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat(), "version": VERSION}


@router.get(
    "/health/detailed", summary="Detailed health check", description="Check status of all services"
)
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check with service status."""

    # Check database
    db_healthy = await db_manager.health_check()
    db_pool = await db_manager.get_pool_status()

    # Check AI engine
    ai_engine = get_ai_engine()
    ai_status = await ai_engine.health_check()

    # Overall status
    all_healthy = db_healthy and ai_status.get("gemini_api", False)

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": VERSION,
        "services": {
            "database": {"status": "healthy" if db_healthy else "unhealthy", "pool": db_pool},
            "ai_engine": ai_status,
        },
        "config": {
            "debug": settings.debug,
            "log_level": settings.log_level,
        },
    }


@router.get(
    "/ready", summary="Readiness check", description="Check if service is ready to handle requests"
)
async def readiness_check(response: Response):
    """Kubernetes readiness probe: 503 when the database is unreachable."""
    if not await db_manager.health_check():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"ready": False, "reason": "Database not ready"}
    return {"ready": True}


@router.get("/live", summary="Liveness check", description="Check if service is alive")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"alive": True}
