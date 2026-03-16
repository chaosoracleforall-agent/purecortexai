"""Async database session management for PURECORTEX."""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.settings import get_settings


def normalize_async_database_url(url: str) -> str:
    """Normalize common Postgres URLs for SQLAlchemy asyncio."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    if url.startswith("postgresql+"):
        return url
    return url


def normalize_sync_database_url(url: str) -> str:
    """Normalize common Postgres URLs for Alembic / sync tooling."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql+asyncpg://")
    return url


class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        normalized = normalize_async_database_url(database_url)
        self.engine: AsyncEngine = create_async_engine(
            normalized,
            pool_pre_ping=True,
            future=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def session(self):
        async with self.session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()


@lru_cache(maxsize=1)
def get_database_manager() -> DatabaseManager | None:
    settings = get_settings()
    if not settings.database_url:
        return None
    return DatabaseManager(settings.database_url)


def database_available() -> bool:
    return get_database_manager() is not None
