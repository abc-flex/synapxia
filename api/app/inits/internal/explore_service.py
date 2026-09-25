"""Explore Initiatives listing (HU-IN04, specs/005 research R5).

The living portfolio: active initiatives in EXPLORE_STATUSES that a live grant
reaches the caller through (superusers: all), filtered BEFORE skip/limit. Each
row carries the card's counters, computed with a constant number of grouped
queries over the page's ids — no N+1, portable to SQLite.
"""
from typing import Dict, List

from sqlalchemy import func
from sqlmodel import Session, select

from . import permissions_service, votes_service
from .collaborations_service import DISCUSSION_TYPES
from .models import Collaboration, FavoriteInit, Initiative, InitiativeExploreItem
from ...admin.internal.models import User
from ...lib.internal.models import AssetInit

# Past a positive diagnosis and not yet archived (spec clarification 2026-09-24).
EXPLORE_STATUSES = ("ACCEPTED", "IN_PROGRESS", "DELIVERED")


def _grouped_counts(session: Session, statement) -> Dict[int, int]:
    return {init_id: n for init_id, n in session.exec(statement).all()}


def list_explore(
    session: Session, user: User, skip: int = 0, limit: int = 100,
) -> List[InitiativeExploreItem]:
    query = select(Initiative).where(
        Initiative.is_active == True,  # noqa: E712
        Initiative.status.in_(EXPLORE_STATUSES),
    )
    access_map: Dict[int, str] = {}
    if not user.is_superuser:
        access_map = permissions_service.accessible_inits(session, user)
        if not access_map:
            return []
        query = query.where(Initiative.id.in_(list(access_map)))

    rows = session.exec(
        query.order_by(Initiative.created_at.desc(), Initiative.id.desc())
        .offset(skip).limit(limit)
    ).all()
    ids = [r.id for r in rows]
    if not ids:
        return []

    scopes = permissions_service.inits_user_scopes(session, user, ids)
    favorites = set(session.exec(
        select(FavoriteInit.init).where(
            FavoriteInit.user_id == user.id,
            FavoriteInit.is_active == True,  # noqa: E712
            FavoriteInit.init.in_(ids),
        )
    ).all())
    tallies = votes_service.tallies_for(session, ids, user.id)
    discussion = _grouped_counts(session, (
        select(Collaboration.init, func.count())
        .where(
            Collaboration.init.in_(ids),
            Collaboration.type.in_(DISCUSSION_TYPES),
            Collaboration.is_active == True,  # noqa: E712
        )
        .group_by(Collaboration.init)
    ))
    links = _grouped_counts(session, (
        select(AssetInit.init, func.count())
        .where(AssetInit.init.in_(ids), AssetInit.is_active == True)  # noqa: E712
        .group_by(AssetInit.init)
    ))

    manage = permissions_service.ACCESS_MANAGE
    return [
        InitiativeExploreItem(
            **r.model_dump(),
            my_access=manage if user.is_superuser else access_map[r.id],
            is_favorite=r.id in favorites,
            permission_scopes=scopes.get(r.id, []),
            votes=tallies[r.id],
            discussion_count=discussion.get(r.id, 0),
            related_assets_count=links.get(r.id, 0),
        )
        for r in rows
    ]
