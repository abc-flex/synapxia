"""Initiative History (read-only) and Discussion (interactive) — Initiative
Management.

Discussion writes mirror the asset side's comment/question/answer/delete, with
two deliberate differences: the author always comes from the session (the body
carries no user id), and only an entry's author (or a superuser) may delete it.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ..internal import collaborations_service, permissions_service
from ..internal.dependencies import get_db_session
from ..internal.models import (
    Collaboration, InitAnswerCreate, InitDiscussionItem, InitParticipationCreate, Initiative,
)
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


def _gate_write(session: Session, user: User, init_id: int) -> None:
    """Posting needs edit intent on the module (INITIATIVES or EXPLORE) plus
    VIEW on the initiative — you can discuss what you can see."""
    check_any_privilege(session, user, "INITS", ["INITIATIVES", "EXPLORE"], can_edit=True)
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise HTTPException(status_code=400, detail=f"Initiative with id '{init_id}' does not exist")
    try:
        permissions_service.require_init_view(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _post(session: Session, user: User, init_id: int, create) -> dict:
    _gate_write(session, user, init_id)
    try:
        row = create()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return collaborations_service.discussion_item(session, row)


@router.post("/comments", response_model=InitDiscussionItem, status_code=201)
def add_comment(
    payload: InitParticipationCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> dict:
    """Post a comment on an initiative, as the signed-in user."""
    return _post(session, current, payload.init, lambda: collaborations_service.add_comment(
        session, current.id, payload.init, payload.content))


@router.post("/questions", response_model=InitDiscussionItem, status_code=201)
def add_question(
    payload: InitParticipationCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> dict:
    """Ask a question on an initiative, as the signed-in user."""
    return _post(session, current, payload.init, lambda: collaborations_service.add_question(
        session, current.id, payload.init, payload.content))


@router.post("/answers", response_model=InitDiscussionItem, status_code=201)
def add_answer(
    payload: InitAnswerCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> dict:
    """Answer a question (the parent must be an active question on the same
    initiative, else 400), as the signed-in user."""
    return _post(session, current, payload.init, lambda: collaborations_service.add_answer(
        session, current.id, payload.init, payload.content, payload.parent))


@router.delete("/{collab_id}", response_model=InitDiscussionItem)
def delete_participation(
    collab_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> dict:
    """Logically delete one of your own comments, questions or answers."""
    row = session.get(Collaboration, collab_id)
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    _gate_write(session, current, row.init)
    try:
        collaborations_service.delete_participation(session, current, row)
    except collaborations_service.ParticipationForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return collaborations_service.discussion_item(session, row)
