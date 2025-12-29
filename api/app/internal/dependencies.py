import os
import logging
from contextlib import contextmanager

import psycopg2
from sqlmodel import create_engine, Session
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

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

# Configurar echo solo en desarrollo
echo_sql = os.getenv("APP_ENV", "development") == "development"
engine = create_engine(DATABASE_URL, echo=echo_sql)


@contextmanager
def get_db_connection():
    """
    Context manager para conexión directa a PostgreSQL.
    Útil para operaciones que requieren psycopg2 directamente.
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
    Dependency de FastAPI para obtener sesión de SQLModel.
    
    Maneja automáticamente:
    - Commit en éxito
    - Rollback en error
    - Cierre de sesión
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
