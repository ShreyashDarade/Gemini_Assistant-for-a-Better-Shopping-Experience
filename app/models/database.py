"""
Async database configuration with connection pooling for high concurrency.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


def _build_engine():
    kwargs: dict = {"echo": settings.debug, "pool_pre_ping": True}
    if settings.database_url.startswith("sqlite"):
        # SQLite: file-level locking, so the default pool is the right choice.
        kwargs["connect_args"] = {"timeout": 30}
    else:
        kwargs.update(pool_size=20, max_overflow=30, pool_timeout=30, pool_recycle=1800)
    return create_async_engine(settings.database_url, **kwargs)


engine = _build_engine()

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()


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
async def get_db_context() -> AsyncGenerator[AsyncSession]:
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


async def get_db() -> AsyncGenerator[AsyncSession]:
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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            async with get_db_context() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    async def get_pool_status(self) -> dict:
        """Get connection pool statistics."""
        pool = engine.pool
        if not hasattr(pool, "size"):
            return {"pool": type(pool).__name__}
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalidatedcount() if hasattr(pool, "invalidatedcount") else 0,
        }


db_manager = DatabaseManager()
