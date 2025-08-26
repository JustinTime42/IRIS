"""
Database initialization utilities.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from .engine import engine
from .models import Base


async def init_db(async_engine: AsyncEngine | None = None) -> None:
    """
    Initialize the database by creating all tables if they do not exist.

    Args:
        async_engine (AsyncEngine | None): Optional engine, defaults to package engine.
    """
    eng = async_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def db_health_check(async_engine: AsyncEngine | None = None) -> dict:
    """
    Perform a simple health check by issuing a lightweight query.

    Args:
        async_engine (AsyncEngine | None): Optional engine, defaults to package engine.

    Returns:
        dict: Result information with ok flag and server version.
    """
    eng = async_engine or engine
    async with eng.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        version_row = result.first()
        return {"ok": True, "version": version_row[0] if version_row else None}
