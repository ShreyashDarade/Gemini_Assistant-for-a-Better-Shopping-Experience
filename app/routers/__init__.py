"""Routers package."""

from app.routers.chat import router as chat_router
from app.routers.products import router as products_router
from app.routers.media import router as media_router
from app.routers.health import router as health_router

__all__ = [
    "chat_router",
    "products_router",
    "media_router",
    "health_router",
]
