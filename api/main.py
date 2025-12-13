from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from contextlib import contextmanager

app = FastAPI(
    title="SynapxIA API",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints"
        },
        {
            "name": "roles",
            "description": "Role management operations - CRUD operations for roles"
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "synapxia"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "port": os.getenv("DB_PORT", "5432")
}

# Database connection


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Pydantic models


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    start: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start: Optional[str] = None


class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True

# Root endpoint


@app.get("/")
def read_root():
    return {
        "message": "SynapxIA API - Role Management System",
        "version": "1.0.0",
        "endpoints": {
            "roles": "/api/roles",
            "docs": "/docs"
        }
    }

# Health check


@app.get("/health", tags=["health"])
def health_check():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Database connection failed: {str(e)}")

# CREATE - Create a new role


@app.post("/api/roles", response_model=Role, status_code=201, tags=["roles"])
def create_role(role: RoleCreate):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO roles (name, description, start)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, description, start
                    """,
                    (role.name, role.description, role.start)
                )
                new_role = cur.fetchone()
                return new_role
    except psycopg2.IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Role with this name might already exist")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# READ - Get all roles


@app.get("/api/roles", response_model=List[Role], tags=["roles"])
def get_roles(skip: int = 0, limit: int = 100):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, description, start
                    FROM roles
                    ORDER BY id
                    LIMIT %s OFFSET %s
                    """,
                    (limit, skip)
                )
                roles = cur.fetchall()
                return roles
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# READ - Get role by ID


@app.get("/api/roles/{role_id}", response_model=Role, tags=["roles"])
def get_role(role_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, description, start
                    FROM roles
                    WHERE id = %s
                    """,
                    (role_id,)
                )
                role = cur.fetchone()
                if not role:
                    raise HTTPException(
                        status_code=404, detail="Role not found")
                return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# UPDATE - Update a role


@app.put("/api/roles/{role_id}", response_model=Role, tags=["roles"])
def update_role(role_id: int, role: RoleUpdate):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if role exists
                cur.execute(
                    "SELECT id FROM roles WHERE id = %s", (role_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Role not found")

                # Build dynamic update query
                update_fields = []
                values = []

                if role.name is not None:
                    update_fields.append("name = %s")
                    values.append(role.name)
                if role.description is not None:
                    update_fields.append("description = %s")
                    values.append(role.description)
                if role.start is not None:
                    update_fields.append("start = %s")
                    values.append(role.start)

                if not update_fields:
                    raise HTTPException(
                        status_code=400, detail="No fields to update")

                values.append(role_id)
                query = f"UPDATE roles SET {', '.join(update_fields)} WHERE id = %s RETURNING id, name, description, start"

                cur.execute(query, values)
                updated_role = cur.fetchone()
                return updated_role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DELETE - Delete a role


@app.delete("/api/roles/{role_id}", status_code=204, tags=["roles"])
def delete_role(role_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM roles WHERE id = %s", (role_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Role not found")

                cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
                return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
