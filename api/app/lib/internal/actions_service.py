"""Asset Action Service — shared helpers over the generic ``actions`` event log.

The ``actions`` table (db/sql/41-lib-ddl.sql) is the single substrate for asset
interactions (votes, comments, questions, answers) and review-workflow actions.
This module centralizes create / query / toggle / logical-delete logic so feature
routes don't duplicate it. It is the reusable foundation the lib roadmap builds on
(voting now; foro, history and notifications in later phases).

No new tables are ever introduced here — everything is a row in ``actions``.
"""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Action, Asset
from ...admin.internal.models import User

logger = logging.getLogger(__name__)

# Action types — mirror the ACTION_TYPE list seeded in db/sql/42-lib-insert.sql.
TYPE_VOTE = "VOTE"
TYPE_COMMENT = "COMMENT"
TYPE_QUESTION = "QUESTION"
TYPE_ANSWER = "ANSWER"

# Vote values stored in ``actions.content``.
VOTE_POSITIVE = "POSITIVE"
VOTE_NEGATIVE = "NEGATIVE"
VOTE_VALUES = {VOTE_POSITIVE, VOTE_NEGATIVE}


# ---------------------------------------------------------------------------
# Generic helpers (reused by votes now; foro / history / notifications later)
# ---------------------------------------------------------------------------

def asset_exists(session: Session, asset_id: int) -> bool:
    """Return True if the asset row exists (active or not)."""
    return session.get(Asset, asset_id) is not None


def list_actions_for_asset(
    session: Session,
    asset_id: int,
    type: Optional[str] = None,
    active_only: bool = True,
) -> List[Action]:
    """List an asset's actions, newest first, optionally filtered by type."""
    stmt = select(Action).where(Action.asset == asset_id)
    if active_only:
        stmt = stmt.where(Action.is_active == True)  # noqa: E712
    if type is not None:
        stmt = stmt.where(Action.type == type)
    return session.exec(stmt.order_by(Action.created_at.desc())).all()


# ---------------------------------------------------------------------------
# Voting (HU-LI05)
# ---------------------------------------------------------------------------

def get_user_vote(session: Session, user_id: int, asset_id: int) -> Optional[Action]:
    """Return the user's VOTE action for an asset (active or inactive), if any.

    The service keeps a single VOTE row per (user, asset): re-voting reuses it,
    so this returns the latest by ``created_at`` for safety.
    """
    return session.exec(
        select(Action)
        .where(
            Action.asset == asset_id,
            Action.user_id == user_id,
            Action.type == TYPE_VOTE,
        )
        .order_by(Action.created_at.desc())
    ).first()


def count_votes(session: Session, asset_id: int) -> dict:
    """Count active POSITIVE/NEGATIVE votes for an asset and the net score."""
    votes = list_actions_for_asset(
        session, asset_id, type=TYPE_VOTE, active_only=True)
    positive = sum(1 for v in votes if v.content == VOTE_POSITIVE)
    negative = sum(1 for v in votes if v.content == VOTE_NEGATIVE)
    return {"positive": positive, "negative": negative, "score": positive - negative}


def get_vote_tally(
    session: Session, asset_id: int, user_id: Optional[int] = None
) -> dict:
    """Vote summary for an asset, plus ``my_vote`` for ``user_id`` when given."""
    tally = count_votes(session, asset_id)
    my_vote = None
    if user_id is not None:
        existing = get_user_vote(session, user_id, asset_id)
        if existing and existing.is_active:
            my_vote = existing.content
    tally["my_vote"] = my_vote
    return tally


def set_vote(
    session: Session, user_id: int, asset_id: int, value: Optional[str]
) -> Optional[Action]:
    """Set / flip / clear a user's vote on an asset, reusing the single VOTE row.

    - ``value`` POSITIVE/NEGATIVE: create the vote, flip it, or reactivate a
      previously cleared one. Re-applying the *same* active value clears it
      (toggle off), mirroring the favorite-star toggle UX.
    - ``value`` None: clear (logical delete) the active vote.

    Returns the resulting active ``Action``, or None when the vote was cleared.
    Raises ValueError on an invalid vote value.
    """
    if value is not None and value not in VOTE_VALUES:
        raise ValueError(
            f"Invalid vote value '{value}'. Expected one of {sorted(VOTE_VALUES)}.")

    existing = get_user_vote(session, user_id, asset_id)

    # All writes share one IntegrityError guard: on a DB-constraint violation we
    # roll back and re-raise so the caller (vote routes) can map it to a 409
    # instead of letting it bubble up as a raw 500. Mirrors the favorites route.
    try:
        # Explicit clear.
        if value is None:
            if existing and existing.is_active:
                existing.is_active = False
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                logger.info("Vote cleared: user=%s asset=%s", user_id, asset_id)
            return None

        if existing is not None:
            # Same active value → toggle off.
            if existing.is_active and existing.content == value:
                existing.is_active = False
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                logger.info(
                    "Vote toggled off: user=%s asset=%s value=%s",
                    user_id, asset_id, value)
                return None
            # Otherwise set / flip / reactivate the existing row.
            existing.content = value
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            logger.info(
                "Vote set: user=%s asset=%s value=%s", user_id, asset_id, value)
            return existing

        # First vote for this (user, asset).
        action = Action(asset=asset_id, user_id=user_id,
                        type=TYPE_VOTE, content=value)
        session.add(action)
        session.commit()
        session.refresh(action)
        logger.info("Vote created: user=%s asset=%s value=%s",
                    user_id, asset_id, value)
        return action
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error setting vote: user=%s asset=%s value=%s",
            user_id, asset_id, value)
        raise


# ---------------------------------------------------------------------------
# Foro — comments / questions / answers (HU-LI06)
#
# All three are ``actions`` rows: COMMENT and QUESTION are top-level (parent
# NULL); an ANSWER threads to its QUESTION via ``parent``. No new table.
# ---------------------------------------------------------------------------

DISCUSSION_TYPES = (TYPE_COMMENT, TYPE_QUESTION, TYPE_ANSWER)


def discussion_item(session: Session, action: Action) -> dict:
    """Project a single participation ``Action`` to a discussion item (with the
    author's username resolved). Used for POST responses."""
    author = session.get(User, action.user_id)
    return {
        "id": action.id,
        "asset": action.asset,
        "user_id": action.user_id,
        "author": author.username if author else None,
        "type": action.type,
        "content": action.content,
        "parent": action.parent,
        "created_at": action.created_at,
    }


def list_discussion(session: Session, asset_id: int) -> List[dict]:
    """Active COMMENT/QUESTION/ANSWER rows for an asset, oldest first, each
    enriched with the author's username.

    Authors are resolved with a single batched ``IN`` query (no N+1). The
    frontend threads answers under their question via ``parent``.
    """
    rows = session.exec(
        select(Action)
        .where(
            Action.asset == asset_id,
            Action.is_active == True,  # noqa: E712
            Action.type.in_(DISCUSSION_TYPES),
        )
        .order_by(Action.created_at.asc())
    ).all()

    user_ids = {r.user_id for r in rows}
    authors: dict = {}
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        authors = {u.id: u.username for u in users}

    return [
        {
            "id": r.id,
            "asset": r.asset,
            "user_id": r.user_id,
            "author": authors.get(r.user_id),
            "type": r.type,
            "content": r.content,
            "parent": r.parent,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def _add_participation(
    session: Session,
    user_id: int,
    asset_id: int,
    type_: str,
    content: Optional[str],
    parent: Optional[int] = None,
) -> Action:
    """Create a COMMENT/QUESTION/ANSWER row. Validates non-empty content and
    rolls back + re-raises IntegrityError (so routes can map it to 409).

    Raises ValueError on empty content.
    """
    text = (content or "").strip()
    if not text:
        raise ValueError("Content must not be empty.")

    action = Action(
        asset=asset_id, user_id=user_id, type=type_, content=text, parent=parent)
    try:
        session.add(action)
        session.commit()
        session.refresh(action)
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error adding %s: user=%s asset=%s", type_, user_id, asset_id)
        raise
    logger.info("%s added: user=%s asset=%s", type_, user_id, asset_id)
    return action


def add_comment(session: Session, user_id: int, asset_id: int, content: str) -> Action:
    """Add a top-level comment on an asset."""
    return _add_participation(session, user_id, asset_id, TYPE_COMMENT, content)


def add_question(session: Session, user_id: int, asset_id: int, content: str) -> Action:
    """Add a top-level question on an asset."""
    return _add_participation(session, user_id, asset_id, TYPE_QUESTION, content)


def add_answer(
    session: Session, user_id: int, asset_id: int, content: str, parent: int
) -> Action:
    """Answer a question. ``parent`` must be an active QUESTION on the *same*
    asset, otherwise ValueError (→ 400)."""
    question = session.get(Action, parent)
    if (
        not question
        or not question.is_active
        or question.type != TYPE_QUESTION
        or question.asset != asset_id
    ):
        raise ValueError(
            "Answer parent must be an active question on the same asset.")
    return _add_participation(
        session, user_id, asset_id, TYPE_ANSWER, content, parent=parent)


# ---------------------------------------------------------------------------
# History (HU-LI10) — read-side timeline over the same ``actions`` substrate.
#
# Aggregates every active action on an asset (votes, comments, questions,
# answers, and any review-workflow actions) plus a synthetic CREATED marker from
# the asset row, newest first. Pure read aggregation — no new table, no writes.
# ---------------------------------------------------------------------------

# A synthetic timeline entry (not an ``actions`` row) marking asset creation.
HISTORY_CREATED = "CREATED"

# Canonical English summaries per action type (the UI localizes via
# `history.action.{type}` and falls back to these for any unmapped type).
_HISTORY_SUMMARIES = {
    "PROPOSAL": "proposed the asset",
    "REVIEW": "reviewed the asset",
    "MODIFICATION": "requested a modification",
    "PUBLICATION": "published the asset",
    "REJECTION": "rejected the asset",
    "DEPRECATION": "deprecated the asset",
    "VERSIONING": "created a new version",
    "USAGE": "used the asset",
    TYPE_COMMENT: "commented",
    TYPE_QUESTION: "asked a question",
    TYPE_ANSWER: "answered a question",
    HISTORY_CREATED: "created the asset",
}


# Workflow actions carry a ``workflow_status`` (ASSIGNED/NOTIFIED/FINISHED); the
# verb must reflect the *step*, otherwise the three PUBLICATION rows all read
# "published the asset". The UI localizes by ``{type}_{workflow_status}`` and
# falls back to these. FINISHED reuses the terminal verb in _HISTORY_SUMMARIES.
_WORKFLOW_SUMMARIES = {
    ("PROPOSAL", "ASSIGNED"): "was assigned to propose the asset",
    ("PROPOSAL", "NOTIFIED"): "was notified to propose the asset",
    ("PROPOSAL", "FINISHED"): "proposed the asset",
    ("REVIEW", "ASSIGNED"): "was assigned to review the asset",
    ("REVIEW", "NOTIFIED"): "was notified to review the asset",
    ("REVIEW", "FINISHED"): "reviewed the asset",
    ("PUBLICATION", "ASSIGNED"): "was assigned to publish the asset",
    ("PUBLICATION", "NOTIFIED"): "was notified to publish the asset",
    ("PUBLICATION", "FINISHED"): "published the asset",
    ("MODIFICATION", "ASSIGNED"): "was assigned a modification",
    ("MODIFICATION", "NOTIFIED"): "was notified of a modification",
    ("MODIFICATION", "FINISHED"): "modified the asset",
    ("REJECTION", "FINISHED"): "rejected the asset",
    ("DEPRECATION", "FINISHED"): "deprecated the asset",
}


def _history_summary(action: Action) -> str:
    """Derive a human summary for a timeline entry (server-side per the roadmap;
    the UI still localizes by ``type`` / ``type_workflow_status``)."""
    if action.type == TYPE_VOTE:
        if action.content == VOTE_POSITIVE:
            return "upvoted"
        if action.content == VOTE_NEGATIVE:
            return "downvoted"
        return "voted"
    if action.workflow_status:
        combined = _WORKFLOW_SUMMARIES.get((action.type, action.workflow_status))
        if combined:
            return combined
    return _HISTORY_SUMMARIES.get(action.type, action.type.lower())


def get_asset_history(session: Session, asset_id: int) -> List[dict]:
    """Activity timeline for an asset, newest first.

    Every active ``actions`` row (any type) becomes an entry; a synthetic
    CREATED entry is appended from the asset's ``created_at``. Actor usernames
    are resolved with a single batched ``IN`` query (no N+1). Comment/question/
    answer entries carry their ``content``; other types omit it.
    """
    actions = list_actions_for_asset(session, asset_id, active_only=True)

    user_ids = {a.user_id for a in actions if a.user_id is not None}
    authors: dict = {}
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        authors = {u.id: u.username for u in users}

    entries: List[dict] = [
        {
            "id": a.id,
            "type": a.type,
            "actor": authors.get(a.user_id),
            "summary": _history_summary(a),
            "content": a.content if a.type in DISCUSSION_TYPES else None,
            "workflow_status": a.workflow_status,
            "created_at": a.created_at,
        }
        for a in actions
    ]

    # Synthetic CREATED marker from the asset row (oldest event in the timeline).
    asset = session.get(Asset, asset_id)
    if asset is not None and asset.created_at is not None:
        entries.append({
            "id": None,
            "type": HISTORY_CREATED,
            "actor": None,
            "summary": _history_summary(
                Action(asset=asset_id, user_id=0, type=HISTORY_CREATED)),
            "content": None,
            "workflow_status": None,
            "created_at": asset.created_at,
        })

    # Newest first across actions + the synthetic marker. Tie-break by id (the
    # seed inserts a whole workflow thread at one NOW(), so timestamps collide —
    # without this the steps could render out of order, e.g. "reviewed" before
    # "assigned to review"). Synthetic CREATED (id None) sorts oldest on a tie.
    entries.sort(
        key=lambda e: (e["created_at"], e["id"] if e["id"] is not None else -1),
        reverse=True,
    )
    return entries


# Review-workflow action types whose latest occurrence defines the asset's
# current review stage (distinct from ``asset.status``). PROPOSAL/REVIEW/
# PUBLICATION are the happy path; the rest are off-ramps.
WORKFLOW_STAGE_TYPES = (
    "PROPOSAL", "REVIEW", "PUBLICATION",
    "MODIFICATION", "REJECTION", "DEPRECATION", "VERSIONING",
)


def get_workflow_stage(session: Session, asset_id: int) -> Optional[dict]:
    """The asset's current review stage: the most recent workflow action
    (PROPOSAL/REVIEW/PUBLICATION/…) with its ``workflow_status``. ``None`` when
    the asset has no workflow actions. Read-only and distinct from
    ``asset.status`` — surfaced as a badge so the review step is visible.
    """
    latest = session.exec(
        select(Action)
        .where(
            Action.asset == asset_id,
            Action.is_active == True,  # noqa: E712
            Action.type.in_(WORKFLOW_STAGE_TYPES),
        )
        .order_by(Action.created_at.desc(), Action.id.desc())
    ).first()
    if latest is None:
        return None
    actor = None
    if latest.user_id is not None:
        u = session.get(User, latest.user_id)
        actor = u.username if u else None
    return {
        "type": latest.type,
        "workflow_status": latest.workflow_status,
        "actor": actor,
        "created_at": latest.created_at,
    }


# ---------------------------------------------------------------------------
# Notifications (HU-LI11) — workflow assignments surfaced to the assignee.
#
# Per docs/user-stories/lib-status.md (HU-Notifications): an assignment is a
# review-workflow action (REVIEW/MODIFICATION/PUBLICATION/REJECTION) directed at
# a user, whose lifecycle is tracked by INSERTING successive ``actions`` rows
# with workflow_status ASSIGNED → NOTIFIED → FINISHED (matching the seed — each
# transition is a new row, never an update). A notification is the latest row of
# a per-(asset, type) assignment thread whose status is still ASSIGNED (bold) or
# NOTIFIED (seen, dismissible); FINISHED threads drop off the list.
#
# This service is the read + transition side only. The actions that *generate*
# assignments come from the propose/review workflow (HU-Propose/Review/Modify),
# which is out of scope here — notifications display whatever assignments exist.
# ---------------------------------------------------------------------------

TYPE_REVIEW = "REVIEW"
TYPE_MODIFICATION = "MODIFICATION"
TYPE_PUBLICATION = "PUBLICATION"
TYPE_REJECTION = "REJECTION"
NOTIFICATION_TYPES = (TYPE_REVIEW, TYPE_MODIFICATION, TYPE_PUBLICATION, TYPE_REJECTION)

WORKFLOW_ASSIGNED = "ASSIGNED"
WORKFLOW_NOTIFIED = "NOTIFIED"
WORKFLOW_FINISHED = "FINISHED"
# Statuses that keep a thread in the notification list (FINISHED removes it).
NOTIFICATION_OPEN_STATUSES = (WORKFLOW_ASSIGNED, WORKFLOW_NOTIFIED)


def list_notifications(session: Session, user_id: int) -> List[dict]:
    """The open workflow notifications for a user, newest first.

    Groups the user's workflow actions by (asset, type), takes the latest row of
    each thread, and keeps those whose status is ASSIGNED or NOTIFIED. Asset
    names are resolved with a single batched ``IN`` query (no N+1). ``unread`` is
    True while the thread is still ASSIGNED (the "bold" state in the UI).
    """
    rows = session.exec(
        select(Action)
        .where(
            Action.user_id == user_id,
            Action.is_active == True,  # noqa: E712
            Action.type.in_(NOTIFICATION_TYPES),
            Action.workflow_status.is_not(None),
        )
        .order_by(Action.created_at.asc(), Action.id.asc())
    ).all()

    # Collapse each (asset, type) thread to its latest row (rows are ascending,
    # so the last seen per key wins).
    latest: dict = {}
    for r in rows:
        latest[(r.asset, r.type)] = r

    threads = [
        r for r in latest.values()
        if r.workflow_status in NOTIFICATION_OPEN_STATUSES
    ]

    asset_ids = {r.asset for r in threads}
    names: dict = {}
    if asset_ids:
        assets = session.exec(select(Asset).where(Asset.id.in_(asset_ids))).all()
        names = {a.id: a.name for a in assets}

    items = [
        {
            "id": r.id,
            "asset": r.asset,
            "asset_name": names.get(r.asset),
            "type": r.type,
            "workflow_status": r.workflow_status,
            "unread": r.workflow_status == WORKFLOW_ASSIGNED,
            "created_at": r.created_at,
        }
        for r in threads
    ]
    items.sort(key=lambda i: i["created_at"], reverse=True)
    return items


def _insert_status(session: Session, action: Action, new_status: str) -> Action:
    """Insert a new row continuing ``action``'s assignment thread with
    ``new_status`` (carries asset/user/type/parent). Rolls back + re-raises
    IntegrityError so the route can map it to 409."""
    row = Action(
        asset=action.asset,
        user_id=action.user_id,
        type=action.type,
        workflow_status=new_status,
        parent=action.parent,
        reference=action.reference,
    )
    try:
        session.add(row)
        session.commit()
        session.refresh(row)
    except IntegrityError:
        session.rollback()
        logger.error(
            "Integrity error advancing notification to %s: asset=%s user=%s type=%s",
            new_status, action.asset, action.user_id, action.type)
        raise
    logger.info(
        "Notification %s: asset=%s user=%s type=%s",
        new_status, action.asset, action.user_id, action.type)
    return row


def mark_notified(session: Session, action: Action) -> Action:
    """Transition an ASSIGNED assignment to NOTIFIED (insert a NOTIFIED row).
    Idempotent: if the thread isn't ASSIGNED, returns the action unchanged."""
    if action.workflow_status != WORKFLOW_ASSIGNED:
        return action
    return _insert_status(session, action, WORKFLOW_NOTIFIED)


def dismiss_notification(session: Session, action: Action) -> Action:
    """Dismiss an assignment (insert a FINISHED row), removing it from the list."""
    return _insert_status(session, action, WORKFLOW_FINISHED)
