"""
Health check and system status endpoints.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter

from app.config import get_settings
from app.models.database import db_manager
from app.services.ai_engine import get_ai_engine

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Basic health check endpoint"
)
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get(
    "/health/detailed",
    summary="Detailed health check",
    description="Check status of all services"
)
async def detailed_health_check() -> Dict[str, Any]:
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
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "services": {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "pool": db_pool
            },
            "ai_engine": ai_status,
        },
        "config": {
            "debug": settings.debug,
            "log_level": settings.log_level,
        }
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Check if service is ready to handle requests"
)
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check critical services
        db_healthy = await db_manager.health_check()
        
        if not db_healthy:
            return {"ready": False, "reason": "Database not ready"}
        
        return {"ready": True}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False, "reason": str(e)}


@router.get(
    "/live",
    summary="Liveness check",
    description="Check if service is alive"
)
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"alive": True}
