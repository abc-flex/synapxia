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


# Workflow actions carry a ``workflow_status`` (PENDING/HANDLED); the verb must
# reflect the *step*, otherwise both PUBLICATION rows read "published the asset".
# The UI localizes by ``{type}_{workflow_status}`` and falls back to these.
# HANDLED reuses the terminal verb in _HISTORY_SUMMARIES.
#
# There is deliberately no "notified" variant: viewing an item is read state, not
# work state, and it is no longer recorded anywhere (see WORKFLOW_STATUS below).
_WORKFLOW_SUMMARIES = {
    ("PROPOSAL", "PENDING"): "was assigned to propose the asset",
    ("PROPOSAL", "HANDLED"): "proposed the asset",
    ("REVIEW", "PENDING"): "was assigned to review the asset",
    ("REVIEW", "HANDLED"): "reviewed the asset",
    ("PUBLICATION", "PENDING"): "was assigned to publish the asset",
    ("PUBLICATION", "HANDLED"): "published the asset",
    ("MODIFICATION", "PENDING"): "was assigned a modification",
    ("MODIFICATION", "HANDLED"): "modified the asset",
    ("REJECTION", "PENDING"): "was notified of a rejection",
    ("REJECTION", "HANDLED"): "rejected the asset",
    ("DEPRECATION", "HANDLED"): "deprecated the asset",
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
# Workflow requests — assignments surfaced to the user they are directed at.
#
# An assignment is a review-workflow action (REVIEW/MODIFICATION/PUBLICATION/
# REJECTION) directed at a user, whose lifecycle is tracked by INSERTING
# successive ``actions`` rows — each transition is a new row, never an update,
# so the activity history stays complete.
#
# There are exactly TWO states. A thread is PENDING while it still awaits its
# recipient's action and HANDLED once it no longer does. There is deliberately
# no third "seen/notified" state: that recorded only that the user had *looked*
# at an item, which is read state, not work state. Mixing the two is what forced
# the old dismiss carve-out — dismissing wrote the same terminal row that
# review_asset()/resubmit_asset() use to mean "already decided", so hiding an
# unresolved assignment silently revoked the assignee's ability to act. Read
# state now lives entirely in the client (a per-device concern) and never here.
#
# This service is the read + transition side only. The actions that *generate*
# assignments come from the propose/review workflow (HU-Propose/Review/Modify).
# ---------------------------------------------------------------------------

TYPE_PROPOSAL = "PROPOSAL"
TYPE_REVIEW = "REVIEW"
TYPE_MODIFICATION = "MODIFICATION"
TYPE_PUBLICATION = "PUBLICATION"
TYPE_REJECTION = "REJECTION"
# Types that can be directed at a user and awaited by them. PROPOSAL is
# deliberately absent: it is written already-terminal and is never owed.
NOTIFICATION_TYPES = (TYPE_REVIEW, TYPE_MODIFICATION, TYPE_PUBLICATION, TYPE_REJECTION)
# Every type that counts as the caller having taken part in an asset.
PARTICIPATION_TYPES = (TYPE_PROPOSAL,) + NOTIFICATION_TYPES

WORKFLOW_PENDING = "PENDING"
WORKFLOW_HANDLED = "HANDLED"

# Asset statuses that mean the workflow is still moving. Anything else is
# terminal. Mirrors the ASSET_STATUS list seeded in db/sql/41-lib-ddl.sql.
IN_MOTION_ASSET_STATUSES = ("PROPOSED", "FEEDBACK")

# Awaited-party values on a participation still in motion.
AWAITED_SELF = "SELF"
AWAITED_OTHER = "OTHER"

# Types whose terminal row is reached by the recipient simply taking note, with
# no work to perform. Only these can be acknowledged; REVIEW and MODIFICATION
# are resolved by actually reviewing or resubmitting.
ACKNOWLEDGEABLE_TYPES = (TYPE_PUBLICATION, TYPE_REJECTION)


class NotificationNotAcknowledgeable(Exception):
    """Raised when acknowledging a REVIEW/MODIFICATION assignment is attempted
    (→ 400) — those are resolved via review/resubmit, not acknowledged."""


def _latest_threads(session: Session, user_id: int, types) -> List[Action]:
    """The latest row of each of the user's (asset, type) workflow threads.

    Every transition inserts a new row rather than updating the previous one, so
    a thread's current state is simply its newest row. Rows come back ascending,
    so the last one seen per key wins.
    """
    rows = session.exec(
        select(Action)
        .where(
            Action.user_id == user_id,
            Action.is_active == True,  # noqa: E712
            Action.type.in_(types),
            Action.workflow_status.is_not(None),
        )
        .order_by(Action.created_at.asc(), Action.id.asc())
    ).all()

    latest: dict = {}
    for r in rows:
        latest[(r.asset, r.type)] = r
    return list(latest.values())


def _participations(session: Session, user_id: int) -> List[dict]:
    """Every asset the user has taken part in, one entry per asset.

    Grouping by ASSET (not by (asset, type)) is what keeps a single asset from
    appearing twice — e.g. once because the user proposed it and again because
    they were sent its publication notice. Collapsing here rather than in the UI
    also keeps the notification count honest, since the feed is defined as this
    list filtered to the entries awaiting the caller.

    Derivation, in this order (the order matters):
      1. If any request thread for this user is still PENDING → the caller owes
         something: in motion, awaited by SELF.
      2. Otherwise, if the asset itself is still moving → in motion, awaited by
         someone else (e.g. the user proposed it and the reviewer has not acted).
      3. Otherwise → handled.

    Step 1 MUST precede step 2: an asset that is already PUBLISHED but whose
    publication notice the user has not acknowledged is still awaiting them. Were
    the asset status checked first, that notice would read as closed and the user
    would never learn the outcome.

    Three statements total regardless of row count — the thread query, one
    batched asset fetch, and nothing per row (no N+1).
    """
    threads = _latest_threads(session, user_id, PARTICIPATION_TYPES)
    if not threads:
        return []

    assets = session.exec(
        select(Asset).where(Asset.id.in_({t.asset for t in threads}))
    ).all()
    by_id = {a.id: a for a in assets}

    grouped: dict = {}
    for t in threads:
        grouped.setdefault(t.asset, []).append(t)

    items: List[dict] = []
    for asset_id, rows in grouped.items():
        asset = by_id.get(asset_id)

        # The newest still-pending request directed at this user, if any. Only
        # NOTIFICATION_TYPES qualify — a PROPOSAL is never owed by anyone.
        pending = [
            r for r in rows
            if r.type in NOTIFICATION_TYPES and r.workflow_status == WORKFLOW_PENDING
        ]
        pending.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        owed = pending[0] if pending else None

        if owed is not None:
            state, awaited = WORKFLOW_PENDING, AWAITED_SELF
        elif asset is not None and asset.status in IN_MOTION_ASSET_STATUSES:
            state, awaited = WORKFLOW_PENDING, AWAITED_OTHER
        else:
            state, awaited = WORKFLOW_HANDLED, None

        roles = []
        if any(r.type == TYPE_PROPOSAL for r in rows):
            roles.append("PROPOSER")
        if any(r.type == TYPE_REVIEW for r in rows):
            roles.append("REVIEWER")

        items.append({
            "asset": asset_id,
            "asset_name": asset.name if asset else None,
            "asset_status": asset.status if asset else None,
            "category": asset.category if asset else None,
            "roles": roles,
            "state": state,
            "awaited_party": awaited,
            "pending_action_id": owed.id if owed else None,
            "pending_action_type": owed.type if owed else None,
            "last_change_at": max(r.created_at for r in rows),
        })

    items.sort(key=lambda i: i["last_change_at"], reverse=True)
    return items


def list_participations(
    session: Session,
    user_id: int,
    state: str = WORKFLOW_PENDING,
    skip: int = 0,
    limit: int = 50,
) -> List[dict]:
    """The user's participations in the requested state, newest change first.

    Pagination is applied after grouping, so ``skip``/``limit`` bound entries the
    caller actually sees rather than raw rows.
    """
    wanted = (state or WORKFLOW_PENDING).upper()
    rows = [i for i in _participations(session, user_id) if i["state"] == wanted]
    return rows[skip: skip + limit]


def list_notifications(session: Session, user_id: int, limit: int = 5) -> dict:
    """The caller's feed: exactly the participations awaiting them.

    Returned as ``{items, total}`` so the panel can cap what it renders while
    still reporting how many are outstanding. Deriving it from the same pass as
    list_participations is what guarantees the feed can never contain something
    the requests page does not show — it is a strict subset by construction.
    """
    owed = [
        i for i in _participations(session, user_id)
        if i["awaited_party"] == AWAITED_SELF
    ]
    items = [
        {
            "id": i["pending_action_id"],
            "asset": i["asset"],
            "asset_name": i["asset_name"],
            "type": i["pending_action_type"],
            "created_at": i["last_change_at"],
        }
        for i in owed[:limit]
    ]
    return {"items": items, "total": len(owed)}


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


def acknowledge_notification(session: Session, action: Action) -> Action:
    """Record that the recipient has taken note of an outcome (insert HANDLED).

    Acknowledging IS resolving, for the two types where there is nothing to do
    but read: PUBLICATION and REJECTION. REVIEW and MODIFICATION are resolved by
    actually reviewing or resubmitting, and attempting to acknowledge one raises
    NotificationNotAcknowledgeable (mapped to 400 by the route) — writing the
    terminal row here would mean the same thing review_asset()/resubmit_asset()
    write to mean "already decided", silently consuming the assignee's turn.

    Opening an item never calls this: viewing is not acknowledging.
    """
    if action.type not in ACKNOWLEDGEABLE_TYPES:
        raise NotificationNotAcknowledgeable(
            f"'{action.type}' assignments must be resolved, not acknowledged."
        )
    if action.workflow_status == WORKFLOW_HANDLED:
        return action  # idempotent — already acknowledged
    return _insert_status(session, action, WORKFLOW_HANDLED)
