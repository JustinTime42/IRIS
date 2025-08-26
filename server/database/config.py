"""
Database configuration utilities.

Reads environment variables and constructs async database URLs.
"""
from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Default to local Postgres; override via env
DEFAULT_DB_NAME = os.getenv("POSTGRES_DB", "iris")
DEFAULT_DB_USER = os.getenv("POSTGRES_USER", "postgres")
DEFAULT_DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DEFAULT_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DEFAULT_DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


def get_database_url() -> str:
    """
    Build the async database URL for SQLAlchemy using asyncpg.

    Returns:
        str: The async database URL.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        # If user provided a sync URL, convert to async if needed
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            return url.replace("postgresql://", "postgresql+asyncpg://").replace(
                "postgres://", "postgresql+asyncpg://"
            )
        return url

    return (
        f"postgresql+asyncpg://{DEFAULT_DB_USER}:{DEFAULT_DB_PASSWORD}"
        f"@{DEFAULT_DB_HOST}:{DEFAULT_DB_PORT}/{DEFAULT_DB_NAME}"
    )
