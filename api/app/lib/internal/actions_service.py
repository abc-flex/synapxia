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

from sqlmodel import Session, select

from .models import Action, Asset

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
