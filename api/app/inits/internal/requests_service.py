"""Initiative requests & notifications (HU-IN13 / HU-IN14 / HU-IN17).

The `collaborations` twin of lib's ``actions_service`` participations
(specs/005 research R7), with the initiative equivalences:

  asset side                        initiative side
  REVIEW / MODIFICATION             DIAGNOSIS / MODIFICATION
  PUBLICATION / REJECTION           ACCEPTANCE / REJECTION
  PROPOSAL                          ACTIVATION
  status PROPOSED / FEEDBACK        status ACTIVATED / FEEDBACK

Every transition inserts a new row, so a thread `(init, user, type)`'s current
state is its newest row. KICKOFF / DELIVERY / ARCHIVING (HANDLED log rows from
Initiative Management) and the community types are not participation types:
they never open or close a thread.
"""
import logging
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Collaboration, Initiative

logger = logging.getLogger(__name__)

TYPE_ACTIVATION = "ACTIVATION"
TYPE_DIAGNOSIS = "DIAGNOSIS"
TYPE_MODIFICATION = "MODIFICATION"
TYPE_ACCEPTANCE = "ACCEPTANCE"
TYPE_REJECTION = "REJECTION"
# Types that can be directed at a user and awaited by them. ACTIVATION is
# written already-terminal and is never owed.
NOTIFICATION_TYPES = (TYPE_DIAGNOSIS, TYPE_MODIFICATION, TYPE_ACCEPTANCE, TYPE_REJECTION)
PARTICIPATION_TYPES = (TYPE_ACTIVATION,) + NOTIFICATION_TYPES
# Resolved by the recipient simply taking note (no work to perform).
ACKNOWLEDGEABLE_TYPES = (TYPE_ACCEPTANCE, TYPE_REJECTION)
# Initiative statuses where the diagnosis workflow is still moving.
IN_MOTION_STATUSES = ("ACTIVATED", "FEEDBACK")

WORKFLOW_PENDING = "PENDING"
WORKFLOW_HANDLED = "HANDLED"
AWAITED_SELF = "SELF"
AWAITED_OTHER = "OTHER"


class NotificationNotAcknowledgeable(ValueError):
    """A DIAGNOSIS / MODIFICATION is resolved by deciding / resubmitting, never
    by acknowledging (→ 400)."""


def _latest_threads(session: Session, user_id: int, types) -> List[Collaboration]:
    rows = session.exec(
        select(Collaboration)
        .where(
            Collaboration.user_id == user_id,
            Collaboration.is_active == True,  # noqa: E712
            Collaboration.type.in_(types),
            Collaboration.workflow_status.is_not(None),
        )
        .order_by(Collaboration.created_at.asc(), Collaboration.id.asc())
    ).all()
    latest: dict = {}
    for r in rows:
        latest[(r.init, r.type)] = r
    return list(latest.values())


def _participations(session: Session, user_id: int) -> List[dict]:
    """Every initiative the user took part in, one entry per initiative.

    Derivation order matters (FR-034): "does the caller owe something?" is
    evaluated BEFORE the initiative's status, so an ACCEPTED initiative whose
    acceptance notice is unacknowledged still reads as awaiting the caller.
    Two statements regardless of row count (threads + one batched fetch).
    """
    threads = _latest_threads(session, user_id, PARTICIPATION_TYPES)
    if not threads:
        return []
    inits = session.exec(
        select(Initiative).where(Initiative.id.in_({t.init for t in threads}))
    ).all()
    by_id = {i.id: i for i in inits}

    grouped: dict = {}
    for t in threads:
        grouped.setdefault(t.init, []).append(t)

    items: List[dict] = []
    for init_id, rows in grouped.items():
        initiative = by_id.get(init_id)
        pending = [
            r for r in rows
            if r.type in NOTIFICATION_TYPES and r.workflow_status == WORKFLOW_PENDING
        ]
        pending.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        owed = pending[0] if pending else None

        if owed is not None:
            state, awaited = WORKFLOW_PENDING, AWAITED_SELF
        elif initiative is not None and initiative.status in IN_MOTION_STATUSES:
            state, awaited = WORKFLOW_PENDING, AWAITED_OTHER
        else:
            state, awaited = WORKFLOW_HANDLED, None

        roles = []
        if any(r.type == TYPE_ACTIVATION for r in rows):
            roles.append("PROPOSER")
        if any(r.type == TYPE_DIAGNOSIS for r in rows):
            roles.append("REVIEWER")

        items.append({
            "init": init_id,
            "init_name": initiative.name if initiative else None,
            "init_status": initiative.status if initiative else None,
            "roles": roles,
            "state": state,
            "awaited_party": awaited,
            "pending_collab_id": owed.id if owed else None,
            "pending_collab_type": owed.type if owed else None,
            "last_change_at": max(r.created_at for r in rows),
        })

    items.sort(key=lambda i: i["last_change_at"], reverse=True)
    return items


def list_participations(
    session: Session, user_id: int, state: str = WORKFLOW_PENDING,
    skip: int = 0, limit: int = 50,
) -> List[dict]:
    """The user's initiative requests in `state`, newest change first; paginated
    after grouping so `skip`/`limit` bound what the caller sees."""
    wanted = (state or WORKFLOW_PENDING).upper()
    rows = [i for i in _participations(session, user_id) if i["state"] == wanted]
    return rows[skip: skip + limit]


def list_notifications(session: Session, user_id: int, limit: int = 5) -> dict:
    """The bell's Initiatives feed: exactly the participations awaiting the
    caller — a strict subset of My Initiative Requests by construction."""
    owed = [i for i in _participations(session, user_id) if i["awaited_party"] == AWAITED_SELF]
    items = [
        {
            "id": i["pending_collab_id"],
            "init": i["init"],
            "init_name": i["init_name"],
            "type": i["pending_collab_type"],
            "created_at": i["last_change_at"],
        }
        for i in owed[:limit]
    ]
    return {"items": items, "total": len(owed)}


def current_thread_row(session: Session, row: Collaboration) -> Collaboration:
    """The newest row of `row`'s thread — its current state."""
    return session.exec(
        select(Collaboration).where(
            Collaboration.init == row.init,
            Collaboration.user_id == row.user_id,
            Collaboration.type == row.type,
            Collaboration.is_active == True,  # noqa: E712
            Collaboration.workflow_status.is_not(None),
        ).order_by(Collaboration.created_at.desc(), Collaboration.id.desc())
    ).first() or row


def acknowledge(session: Session, row: Collaboration) -> Collaboration:
    """Record that the recipient took note of an ACCEPTANCE / REJECTION.

    Idempotent: an already-handled thread returns its current row. Opening a
    notice never calls this — reading is not acknowledging.
    """
    if row.type not in ACKNOWLEDGEABLE_TYPES:
        raise NotificationNotAcknowledgeable(
            f"'{row.type}' assignments must be resolved, not acknowledged.")
    current = current_thread_row(session, row)
    if current.workflow_status == WORKFLOW_HANDLED:
        return current
    handled = Collaboration(
        init=row.init, user_id=row.user_id, type=row.type,
        workflow_status=WORKFLOW_HANDLED, parent=row.parent, reference=row.reference,
    )
    try:
        session.add(handled)
        session.commit()
        session.refresh(handled)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error acknowledging collaboration %s", row.id)
        raise
    return handled
