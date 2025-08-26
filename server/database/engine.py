"""
Async SQLAlchemy engine and session management.
"""
from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_database_url

# Create async engine
engine = create_async_engine(get_database_url(), echo=False, future=True)

# Async session factory
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to provide an AsyncSession.

    Yields:
        AsyncSession: The database session.
    """
    async with AsyncSessionLocal() as session:  # type: ignore[call-arg]
        yield session
