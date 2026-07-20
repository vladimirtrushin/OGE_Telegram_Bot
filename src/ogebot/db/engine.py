"""Async engine and session factory helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ogebot.db.base import Base


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """Create an async engine.

    SQLite gets ``check_same_thread=False`` implicitly through the async driver;
    no special pooling arguments are required for the default file-based setup.
    """
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
    )


async def init_models(engine: AsyncEngine) -> None:
    """Create all tables that do not yet exist.

    Convenient for local SQLite development and the seed script. Production
    deployments should use Alembic migrations (``alembic upgrade head``) instead.
    """
    # Import models so they are registered on the metadata before create_all.
    from ogebot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine(engine: AsyncEngine) -> None:
    """Dispose the engine and close the connection pool."""
    await engine.dispose()
