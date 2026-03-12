"""
Workflows module dependencies

For backward compatibility, this module re-exports from the centralized
dependencies module. All new code should import directly from:

    from app.internal import get_db_session, get_db_connection

But existing code that imports from this location will continue to work.
"""

from ...internal.dependencies import (
    get_db_session,
    get_db_connection,
    engine,
    DATABASE_URL,
    DB_CONFIG,
)

__all__ = [
    "get_db_session",
    "get_db_connection",
    "engine",
    "DATABASE_URL",
    "DB_CONFIG",
]
