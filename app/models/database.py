"""
Async database configuration with connection pooling for high concurrency.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Create async engine with connection pooling for high concurrency
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,           # Base pool size
    max_overflow=30,        # Additional connections when pool is exhausted
    pool_timeout=30,        # Timeout waiting for connection
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True,     # Verify connection before using
)

# Async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    Ensures proper cleanup on errors.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints.
    Yields an async database session.
    """
    async with get_db_context() as session:
        yield session


class DatabaseManager:
    """
    Database manager for handling connections with high concurrency.
    Implements connection pooling and health checks.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with get_db_context() as session:
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    async def get_pool_status(self) -> dict:
        """Get connection pool statistics."""
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0,
        }


db_manager = DatabaseManager()
