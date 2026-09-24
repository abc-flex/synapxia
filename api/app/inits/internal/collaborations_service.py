"""Read side of the initiatives' ``collaborations`` substrate: the History
timeline and the Discussion thread of an initiative.

Mirrors lib's ``actions_service.get_asset_history`` / ``list_discussion`` so the
UI can reuse the same timeline and forum renderers — same response shapes,
actor usernames resolved with one batched query (no N+1), a synthetic CREATED
marker from ``initiatives.created_at``.
"""
from typing import List, Optional

from sqlmodel import Session, select

from .models import Collaboration, Initiative
from ...admin.internal.models import User

TYPE_ACTIVATION = "ACTIVATION"
TYPE_DIAGNOSIS = "DIAGNOSIS"
TYPE_MODIFICATION = "MODIFICATION"
TYPE_ACCEPTANCE = "ACCEPTANCE"
TYPE_REJECTION = "REJECTION"
TYPE_KICKOFF = "KICKOFF"
TYPE_DELIVERY = "DELIVERY"
TYPE_ARCHIVING = "ARCHIVING"
TYPE_VOTE = "VOTE"
TYPE_COMMENT = "COMMENT"
TYPE_QUESTION = "QUESTION"
TYPE_ANSWER = "ANSWER"

DISCUSSION_TYPES = (TYPE_COMMENT, TYPE_QUESTION, TYPE_ANSWER)
HISTORY_CREATED = "CREATED"

# Canonical English summaries (the UI localizes via `initiative_history.action.*`
# and falls back to these).
_HISTORY_SUMMARIES = {
    TYPE_ACTIVATION: "proposed the initiative",
    TYPE_DIAGNOSIS: "diagnosed the initiative",
    TYPE_MODIFICATION: "modified the initiative",
    TYPE_ACCEPTANCE: "accepted the initiative",
    TYPE_REJECTION: "rejected the initiative",
    TYPE_KICKOFF: "kicked off the initiative",
    TYPE_DELIVERY: "delivered the initiative",
    TYPE_ARCHIVING: "archived the initiative",
    TYPE_VOTE: "voted",
    TYPE_COMMENT: "commented",
    TYPE_QUESTION: "asked a question",
    TYPE_ANSWER: "answered a question",
    HISTORY_CREATED: "created the initiative",
}

_WORKFLOW_SUMMARIES = {
    (TYPE_DIAGNOSIS, "PENDING"): "was asked to diagnose the initiative",
    (TYPE_MODIFICATION, "PENDING"): "was asked to modify the initiative",
    (TYPE_ACCEPTANCE, "PENDING"): "was notified of the acceptance",
    (TYPE_ACCEPTANCE, "HANDLED"): "acknowledged the acceptance",
    (TYPE_REJECTION, "PENDING"): "was notified of the rejection",
    (TYPE_REJECTION, "HANDLED"): "acknowledged the rejection",
    (TYPE_DELIVERY, "PENDING"): "was notified of the delivery",
}


def _summary(type_: str, workflow_status: Optional[str]) -> str:
    if workflow_status:
        combined = _WORKFLOW_SUMMARIES.get((type_, workflow_status))
        if combined:
            return combined
    return _HISTORY_SUMMARIES.get(type_, type_.lower())


def _usernames(session: Session, user_ids: set) -> dict:
    if not user_ids:
        return {}
    users = session.exec(select(User).where(User.id.in_(list(user_ids)))).all()
    return {u.id: u.username for u in users}


def get_initiative_history(session: Session, init_id: int) -> List[dict]:
    """Activity timeline for an initiative, newest first (HistoryEntry shape)."""
    rows = session.exec(
        select(Collaboration).where(
            Collaboration.init == init_id,
            Collaboration.is_active == True,  # noqa: E712
        )
    ).all()
    authors = _usernames(session, {r.user_id for r in rows if r.user_id is not None})

    entries: List[dict] = [
        {
            "id": r.id,
            "type": r.type,
            "actor": authors.get(r.user_id),
            "summary": _summary(r.type, r.workflow_status),
            "content": r.content if r.type in DISCUSSION_TYPES else None,
            "workflow_status": r.workflow_status,
            "created_at": r.created_at,
        }
        for r in rows
    ]

    initiative = session.get(Initiative, init_id)
    if initiative is not None and initiative.created_at is not None:
        entries.append({
            "id": None,
            "type": HISTORY_CREATED,
            "actor": None,
            "summary": _summary(HISTORY_CREATED, None),
            "content": None,
            "workflow_status": None,
            "created_at": initiative.created_at,
        })

    # Newest first; tie-break by id (seeded threads share one NOW()), with the
    # synthetic CREATED marker (id None) sorting oldest on a tie.
    entries.sort(
        key=lambda e: (e["created_at"], e["id"] if e["id"] is not None else -1),
        reverse=True,
    )
    return entries


def list_discussion(session: Session, init_id: int) -> List[dict]:
    """Active COMMENT/QUESTION/ANSWER collaborations, oldest first, each with
    the author's username. Answers thread to their question via ``parent``."""
    rows = session.exec(
        select(Collaboration)
        .where(
            Collaboration.init == init_id,
            Collaboration.is_active == True,  # noqa: E712
            Collaboration.type.in_(DISCUSSION_TYPES),
        )
        .order_by(Collaboration.created_at.asc(), Collaboration.id.asc())
    ).all()
    authors = _usernames(session, {r.user_id for r in rows})
    return [
        {
            "id": r.id,
            "init": r.init,
            "user_id": r.user_id,
            "author": authors.get(r.user_id),
            "type": r.type,
            "content": r.content,
            "parent": r.parent,
            "created_at": r.created_at,
        }
        for r in rows
    ]
