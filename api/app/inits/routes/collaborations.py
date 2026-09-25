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

from sqlalchemy.exc import IntegrityError

from ..internal import (
    collaborations_service, permissions_service, requests_service, votes_service,
)
from ..internal.dependencies import get_db_session
from ..internal.models import (
    Collaboration, CollaborationDetail, InitAnswerCreate, InitDiscussionItem,
    InitiativeRequest, InitNotificationFeed, InitParticipationCreate, Initiative,
    InitVoteRequest, InitVoteTally,
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


# ── Votes (specs/005-explore-initiatives, contract #7–#9) ─────────────────────
# One active VOTE row per (user, initiative); the voter is the session user.


@router.get("/votes/init/{init_id}", response_model=InitVoteTally)
def get_votes(
    init_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> InitVoteTally:
    """The initiative's vote tally plus the caller's own vote."""
    _gate_read(session, current, init_id)
    return votes_service.get_vote_tally(session, init_id, current.id)


@router.put("/votes/init/{init_id}", response_model=InitVoteTally)
def put_vote(
    init_id: int,
    payload: InitVoteRequest,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> InitVoteTally:
    """Cast or switch the caller's vote; re-sending the vote already held
    withdraws it."""
    _gate_write(session, current, init_id)
    try:
        return votes_service.set_vote(session, current.id, init_id, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Could not register the vote due to a data conflict")


@router.delete("/votes/init/{init_id}", response_model=InitVoteTally)
def delete_vote(
    init_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> InitVoteTally:
    """Withdraw the caller's vote (404 when there is none)."""
    _gate_write(session, current, init_id)
    try:
        return votes_service.clear_vote(session, current.id, init_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Could not withdraw the vote due to a data conflict")


# ── Requests & notifications (contract #10–#12) ──────────────────────────────
# Scoped to the caller: no privilege gate beyond authentication, since every
# row returned is the caller's own (same as the asset-side equivalents).


@router.get("/requests", response_model=List[InitiativeRequest])
def get_requests(
    state: str = Query("PENDING", pattern="^(PENDING|HANDLED)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[dict]:
    """My Initiative Requests: one row per initiative the caller took part in."""
    return requests_service.list_participations(session, current.id, state, skip, limit)


@router.get("/notifications", response_model=InitNotificationFeed)
def get_notifications(
    limit: int = Query(5, ge=1, le=50),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> dict:
    """The bell's Initiatives feed — the requests awaiting the caller."""
    return requests_service.list_notifications(session, current.id, limit)


@router.post("/notifications/{collab_id}/acknowledge", response_model=Collaboration)
def acknowledge_notification(
    collab_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Collaboration:
    """Acknowledge an ACCEPTANCE / REJECTION notice (idempotent). 404 unless the
    row is the caller's own notification; 400 for DIAGNOSIS / MODIFICATION."""
    row = session.get(Collaboration, collab_id)
    if (not row or row.user_id != current.id
            or row.type not in requests_service.NOTIFICATION_TYPES):
        raise HTTPException(status_code=404, detail="Notification not found")
    try:
        return requests_service.acknowledge(session, row)
    except requests_service.NotificationNotAcknowledgeable as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Could not acknowledge due to a data conflict")


# ── Single collaboration (specs/005-explore-initiatives, contract #13) ───────
# Declared LAST on purpose: every static path above (/requests, /notifications,
# /votes/...) must win over this `/{collab_id}` catch-all.


@router.get("/{collab_id}", response_model=CollaborationDetail)
def get_collaboration(
    collab_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> CollaborationDetail:
    """One workflow collaboration row, for its owner (or a superuser) only — 404
    otherwise, so a foreign id reveals nothing. Embeds the initiative so the
    diagnose / modify / outcome pages never need the INITIATIVES-only
    GET /api/initiatives/{id}."""
    row = session.get(Collaboration, collab_id)
    # Only WORKFLOW rows (the ones the action pages open) — a comment or vote
    # must not become a way to read an initiative after one's access is revoked.
    if (not row or row.workflow_status is None
            or (row.user_id != current.id and not current.is_superuser)):
        raise HTTPException(status_code=404, detail="Collaboration not found")
    actor = session.get(User, row.user_id)
    return CollaborationDetail(
        **row.model_dump(),
        actor_name=actor.username if actor else None,
        initiative=session.get(Initiative, row.init),
        current_status=(
            requests_service.current_thread_row(session, row).workflow_status
            if row.workflow_status else None),
    )
