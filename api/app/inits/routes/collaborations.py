"""Initiative History and Discussion (read-only) — Initiative Management.

Posting to a discussion belongs to Explore Initiatives (future scope); here both
tabs are read-only, so this router exposes no writes.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..internal import collaborations_service, permissions_service
from ..internal.dependencies import get_db_session
from ..internal.models import InitDiscussionItem, Initiative
from ...admin.internal.models import User
from ...auth.routes import current_active_user
from ...internal.permissions import check_any_privilege
from ...lib.internal.models import HistoryEntry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/collaborations", tags=["collaborations"])


def _gate_read(session: Session, user: User, init_id: int) -> None:
    """Outer RBAC (INITS/INITIATIVES or INITS/EXPLORE) + per-initiative VIEW."""
    check_any_privilege(session, user, "INITS", ["INITIATIVES", "EXPLORE"])
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise HTTPException(status_code=404, detail="Initiative not found")
    try:
        permissions_service.require_init_view(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/history/init/{init_id}", response_model=List[HistoryEntry])
def get_history(
    init_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[HistoryEntry]:
    """An initiative's activity timeline, newest first (incl. a CREATED marker)."""
    _gate_read(session, current, init_id)
    entries = collaborations_service.get_initiative_history(session, init_id)
    return entries[skip:skip + limit]


@router.get("/discussion/init/{init_id}", response_model=List[InitDiscussionItem])
def get_discussion(
    init_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[InitDiscussionItem]:
    """An initiative's comments, questions and answers, oldest first."""
    _gate_read(session, current, init_id)
    items = collaborations_service.list_discussion(session, init_id)
    return items[skip:skip + limit]
