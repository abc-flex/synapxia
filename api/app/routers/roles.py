from typing import List

from fastapi import APIRouter, HTTPException
from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor

from ..internal.dependencies import get_db_connection
from ..internal.schemas import Role, RoleCreate, RoleUpdate

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("/", response_model=Role, status_code=201)
def create_role(role: RoleCreate) -> Role:
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO roles (name, description, start)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, description, start
                    """,
                    (role.name, role.description, role.start),
                )
                return cur.fetchone()
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Role with this name might already exist"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=List[Role])
def list_roles(skip: int = 0, limit: int = 100) -> List[Role]:
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
                    (limit, skip),
                )
                return cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{role_id}", response_model=Role)
def get_role(role_id: int) -> Role:
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, description, start
                    FROM roles
                    WHERE id = %s
                    """,
                    (role_id,),
                )
                role = cur.fetchone()
                if not role:
                    raise HTTPException(
                        status_code=404, detail="Role not found")
                return role
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{role_id}", response_model=Role)
def update_role(role_id: int, role: RoleUpdate) -> Role:
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Role not found")

                update_fields: list[str] = []
                values: list[str | int | None] = []

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
                        status_code=400, detail="No fields to update"
                    )

                values.append(role_id)
                query = (
                    f"UPDATE roles SET {', '.join(update_fields)}"
                    " WHERE id = %s RETURNING id, name, description, start"
                )

                cur.execute(query, values)
                return cur.fetchone()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: int) -> None:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Role not found")

                cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
