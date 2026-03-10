"""
Centralized Database Dependencies

This module provides a single source of truth for database connections
and session management across the entire application.

All modules should import from here instead of maintaining duplicate
dependencies.py files.
"""

import os
import logging
from contextlib import contextmanager

import psycopg2
from sqlmodel import create_engine, Session
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# ==================== Database Configuration ====================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_SCHEMA", "synapxia"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", "5432"),
}

DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Configure SQL echo only in development
echo_sql = os.getenv("APP_ENV", "development") == "development"
engine = create_engine(DATABASE_URL, echo=echo_sql)


# ==================== Database Connection Functions ====================

@contextmanager
def get_db_connection():
    """
    Context manager for direct PostgreSQL connection via psycopg2.

    Useful for operations that require direct psycopg2 access.

    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            results = cursor.fetchall()

    Yields:
        psycopg2 connection object

    Raises:
        psycopg2.Error: Database connection errors
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db_session():
    """
    FastAPI dependency for obtaining SQLModel session.

    Automatically handles:
    - Commit on success
    - Rollback on error
    - Session closure

    This is the preferred method for FastAPI route dependencies
    as it integrates with FastAPI's dependency injection system.

    Usage in routes:
        @app.get("/endpoint")
        def my_endpoint(session: Session = Depends(get_db_session)):
            # Your code here
            pass

    Yields:
        SQLModel Session object

    Raises:
        HTTPException: 500 error if database error occurs
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error occurred"
        )
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        session.close()


__all__ = [
    "get_db_session",
    "get_db_connection",
    "engine",
    "DATABASE_URL",
    "DB_CONFIG",
]
