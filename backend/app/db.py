"""Database configuration and session management."""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./azzurro.db")

# Allow sync fallback for migrations/scripts
SYNC_DATABASE_URL = os.environ.get("SYNC_DATABASE_URL", "sqlite:///./azzurro.db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding an async database session."""
    async with async_session_maker() as session:
        yield session


async def init_db() -> None:
    """Create all tables (used during startup and tests)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose the engine (used during shutdown)."""
    await engine.dispose()