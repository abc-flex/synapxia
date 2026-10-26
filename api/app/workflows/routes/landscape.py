"""Process landscape (Value Chain + Process Map — specs/010-process-landscape-views).

The one shared read both views draw from, plus the read-only detail panel.
Access is PROC/VALUE_CHAIN or PROC/MAP at read level, never PROC/PROCESSES, so
view-only profiles (Collaborator, Reviewer) can use them. No write route.

Registered in main.py BEFORE processes.py: otherwise `/api/processes/{code}`
would capture `landscape` and answer with Process Management's gate.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..internal import landscape_service
from ..internal.dependencies import get_db_session
from ..internal.models import LandscapeProcessDetail, ProcessLandscape
from ...admin.internal.models import User
from ...auth.routes import current_active_user
from ...internal.permissions import check_any_privilege

router = APIRouter(prefix="/api/processes", tags=["processes"])

VIEW_OPTIONS = ["VALUE_CHAIN", "MAP"]


@router.get("/landscape", response_model=ProcessLandscape)
def get_landscape(
    unit: Optional[str] = None,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> ProcessLandscape:
    """Shown processes, their relations, rolled-up asset / initiative counts and
    the chain order; optionally narrowed to a business unit (plus the ancestors
    needed to place its processes). Bounded by a cap, flagged `truncated`."""
    check_any_privilege(session, current, "PROC", VIEW_OPTIONS)
    try:
        return landscape_service.build_landscape(session, current, unit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/landscape/{code}", response_model=LandscapeProcessDetail)
def get_landscape_detail(
    code: str,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> LandscapeProcessDetail:
    """The detail panel: core fields, relations both ways, and the asset /
    initiative links of the process and its shown sub-processes."""
    check_any_privilege(session, current, "PROC", VIEW_OPTIONS)
    try:
        return landscape_service.build_detail(session, code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
