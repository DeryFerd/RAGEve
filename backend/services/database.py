"""
Database connection manager for Peewee.

Provides async-compatible interface for FastAPI.
Wraps the synchronous Peewee database with thread pool execution.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from backend.models_peewee import get_database

# Thread pool for running synchronous Peewee operations in async context
_executor = ThreadPoolExecutor(max_workers=10)


async def run_db_operation(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Run a synchronous database operation in a thread pool.

    Usage:
        result = await run_db_operation(User.select().where, User.id == user_id)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


async def connect() -> None:
    """Initialize database connection (called on startup)."""
    # This will create the database connection and bind models
    database = get_database()
    # Test connection
    await run_db_operation(database.connect)


async def close() -> None:
    """Close database connection pool (called on shutdown)."""
    database = get_database()
    await run_db_operation(database.close)
    _executor.shutdown(wait=True)


def get_connection():
    """Get the raw Peewee database connection (for synchronous operations)."""
    return get_database().connection_context()
