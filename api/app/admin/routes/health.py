from fastapi import APIRouter, HTTPException

from ..internal.dependencies import get_db_connection, IS_MANAGED_POSTGRES

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str | bool]:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "async_ready": True,
            "pooler": "detected" if IS_MANAGED_POSTGRES else "direct"
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Database connection failed: {exc}"
        )

