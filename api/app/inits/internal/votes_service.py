"""Initiative votes (HU-IN04) — `collaborations` rows of type VOTE.

Mirrors lib's asset votes: `content` is POSITIVE or NEGATIVE, a user holds at
most one active vote per initiative, re-sending the vote already held withdraws
it, and the other value switches it. Votes carry no `workflow_status`, so they
never enter the notification threads. The voter is always the session user.
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from .models import Collaboration, InitVoteTally

TYPE_VOTE = "VOTE"
POSITIVE = "POSITIVE"
NEGATIVE = "NEGATIVE"
VOTE_VALUES = (POSITIVE, NEGATIVE)


def _active_vote(session: Session, user_id: int, init_id: int) -> Optional[Collaboration]:
    return session.exec(
        select(Collaboration).where(
            Collaboration.init == init_id,
            Collaboration.user_id == user_id,
            Collaboration.type == TYPE_VOTE,
            Collaboration.is_active == True,  # noqa: E712
        ).order_by(Collaboration.id.desc())
    ).first()


def tallies_for(
    session: Session, init_ids: List[int], user_id: Optional[int] = None,
) -> Dict[int, InitVoteTally]:
    """One tally per initiative id: a grouped count plus the caller's own votes."""
    tallies = {i: InitVoteTally(init=i) for i in init_ids}
    if not init_ids:
        return tallies
    rows = session.exec(
        select(Collaboration.init, Collaboration.content, func.count())
        .where(
            Collaboration.init.in_(init_ids),
            Collaboration.type == TYPE_VOTE,
            Collaboration.is_active == True,  # noqa: E712
        )
        .group_by(Collaboration.init, Collaboration.content)
    ).all()
    for init_id, content, n in rows:
        if content == POSITIVE:
            tallies[init_id].positive = n
        elif content == NEGATIVE:
            tallies[init_id].negative = n
    if user_id is not None:
        mine = session.exec(
            select(Collaboration.init, Collaboration.content).where(
                Collaboration.init.in_(init_ids),
                Collaboration.user_id == user_id,
                Collaboration.type == TYPE_VOTE,
                Collaboration.is_active == True,  # noqa: E712
            )
        ).all()
        for init_id, content in mine:
            tallies[init_id].my_vote = content
    for tally in tallies.values():
        tally.score = tally.positive - tally.negative
    return tallies


def get_vote_tally(session: Session, init_id: int, user_id: Optional[int] = None) -> InitVoteTally:
    return tallies_for(session, [init_id], user_id)[init_id]


def set_vote(session: Session, user_id: int, init_id: int, content: str) -> InitVoteTally:
    """Cast, switch or withdraw (same value again) the user's vote."""
    value = (content or "").strip().upper()
    if value not in VOTE_VALUES:
        raise ValueError("Vote must be POSITIVE or NEGATIVE.")
    existing = _active_vote(session, user_id, init_id)
    if existing is not None:
        existing.is_active = False
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    if existing is None or existing.content != value:
        session.add(Collaboration(
            init=init_id, user_id=user_id, type=TYPE_VOTE, content=value))
    session.commit()
    return get_vote_tally(session, init_id, user_id)


def clear_vote(session: Session, user_id: int, init_id: int) -> InitVoteTally:
    """Withdraw the user's vote. LookupError when there is none."""
    existing = _active_vote(session, user_id, init_id)
    if existing is None:
        raise LookupError("You have not voted on this initiative.")
    existing.is_active = False
    existing.updated_at = datetime.utcnow()
    session.add(existing)
    session.commit()
    return get_vote_tally(session, init_id, user_id)
