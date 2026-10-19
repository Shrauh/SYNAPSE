"""
SYNAPSE Database — Async SQLAlchemy engine and session management.

Uses aiosqlite for development, easily swappable to asyncpg + PostgreSQL.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger("synapse.db")

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables. Called on application startup."""
    # Import all models so SQLAlchemy registers them with Base.metadata
    import app.db.models  # noqa: F401 — registers Incident, RCAResult, etc.
    import app.db.auth_models  # noqa: F401 — registers User, RefreshToken, PasswordResetToken
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def shutdown_db() -> None:
    """Dispose engine on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed.")


async def get_db() -> AsyncSession:
    """Dependency injection for FastAPI routes."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
