import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, SQLModel
from sqlalchemy import cast, String

from ..internal import permissions_service, status_service
from ..internal.diagnostics_service import get_diagnostics
from ..internal.models import (
    DiagnosticsResponse, FavoriteInit, FavoriteState, Initiative, InitiativeUpdate,
    InitiativeWithAccess,
)
from ..internal.dependencies import get_db_session
from ...internal.permissions import require_privilege, check_any_privilege
from ...auth.routes import current_active_user
from ...admin.internal.models import ListItem, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/initiatives", tags=["initiatives"])

# Initiatives are never created here — they are only proposed (future propose
# flow). Initiative Management (specs/004-initiative-management) lists the
# initiatives the caller can access and edits them tab by tab; status changes
# are limited to the owner moves in inits/internal/status_service.py.

# List-backed core fields and the list each value must come from.
_LIST_FIELDS = {
    "type": "INITIATIVE_TYPE",
    "expected_impact": "EXPECTED_IMPACT",
    "priority_level": "PRIORITY_LEVEL",
}
_REQUIRED_FIELDS = ("name", "expected_impact", "priority_level")


class InitiativeBasic(SQLModel):
    value: str
    label: str


def _ensure_manage(session: Session, user: User, init_id: int) -> None:
    try:
        permissions_service.require_init_manage(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _ensure_view(session: Session, user: User, init_id: int) -> None:
    try:
        permissions_service.require_init_view(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _with_access(
    initiative: Initiative, access: str, favorite: bool, scopes: List[str] | None = None,
) -> InitiativeWithAccess:
    return InitiativeWithAccess(
        **initiative.model_dump(),
        my_access=access,
        is_favorite=favorite,
        allowed_statuses=status_service.allowed_statuses_for(initiative.status),
        permission_scopes=scopes or [],
    )


def _favorite_ids(session: Session, user: User, init_ids: List[int]) -> set:
    if not init_ids:
        return set()
    return set(session.exec(
        select(FavoriteInit.init).where(
            FavoriteInit.user_id == user.id,
            FavoriteInit.is_active == True,  # noqa: E712
            FavoriteInit.init.in_(init_ids),
        )
    ).all())


@router.get("/select", response_model=List[InitiativeBasic])
def get_select(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(current_active_user),
) -> List[InitiativeBasic]:
    """
    Lightweight list of active initiatives for UI dropdowns: value = id, label = name.

    Read access: `INITS/INITIATIVES` (initiative managers) OR `INITS/EXPLORE`
    (the read-only browse privilege COLLABORATOR/REVIEWER hold) — backs the
    "Related Inits" tab's target dropdown from both the Asset Management edit
    modal and the read-only Explore detail modal.
    """
    check_any_privilege(session, current_user, "INITS", ["INITIATIVES", "EXPLORE"])
    rows = session.exec(
        select(
            cast(Initiative.id, String).label("value"),
            Initiative.name.label("label"),
        )
        .where(Initiative.is_active == True)
        .order_by(Initiative.name)
    ).all()
    return rows


@router.get("/with-access", response_model=List[InitiativeWithAccess])
def get_all_with_access(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False)),
) -> List[InitiativeWithAccess]:
    """
    Active initiatives the caller can access (Initiative Management list).

    Non-superusers only see initiatives with a live `init_permissions` grant
    reaching them; the access filter is applied BEFORE `skip`/`limit` so pages
    stay full. Each row carries the caller's `my_access` (MANAGE/VIEW),
    `is_favorite`, and `allowed_statuses` (current status + owner moves).
    """
    query = select(Initiative).where(Initiative.is_active == True)  # noqa: E712
    access_map: Dict[int, str] = {}
    if not current.is_superuser:
        access_map = permissions_service.accessible_inits(session, current)
        if not access_map:
            return []
        query = query.where(Initiative.id.in_(list(access_map)))

    rows = session.exec(
        query.order_by(Initiative.name).offset(skip).limit(limit)
    ).all()
    ids = [r.id for r in rows]
    favorites = _favorite_ids(session, current, ids)
    scopes = permissions_service.inits_user_scopes(session, current, ids)
    return [
        _with_access(
            r,
            permissions_service.ACCESS_MANAGE if current.is_superuser else access_map[r.id],
            r.id in favorites,
            scopes.get(r.id, []),
        )
        for r in rows
    ]


@router.get("/", response_model=List[Initiative])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False))
) -> List[Initiative]:
    """
    List all initiatives with pagination (active only).

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    initiatives = session.exec(
        select(Initiative).where(Initiative.is_active == True)
        .offset(skip).limit(limit)
        .order_by(Initiative.name)
    ).all()
    return initiatives


@router.get("/{init_id}/diagnostics", response_model=DiagnosticsResponse)
def get_initiative_diagnostics(
    init_id: int,
    lang: str = Query("en", pattern="^(en|es)$"),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DiagnosticsResponse:
    """
    The initiative's Diagnosis Questions: one row per criterion with the
    proposer's and reviewer's answers as labels in `lang` (fallback `en`).
    Read-only. Requires `INITS/INITIATIVES` or `INITS/EXPLORE` and VIEW on the
    initiative.
    """
    check_any_privilege(session, current, "INITS", ["INITIATIVES", "EXPLORE"])
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise HTTPException(status_code=404, detail="Initiative not found")
    _ensure_view(session, current, init_id)
    return get_diagnostics(session, initiative, lang)


def _set_favorite(session: Session, user: User, init_id: int, on: bool) -> FavoriteState:
    """Mark / clear the caller's favorite. Favoriting is personal, not an edit:
    read-level module access + VIEW on the initiative suffice. Idempotent."""
    check_any_privilege(session, user, "INITS", ["INITIATIVES", "EXPLORE"])
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise HTTPException(status_code=404, detail="Initiative not found")
    _ensure_view(session, user, init_id)
    row = session.get(FavoriteInit, (user.id, init_id))
    if row is None and on:
        session.add(FavoriteInit(user_id=user.id, init=init_id))
    elif row is not None and row.is_active != on:
        row.is_active = on
        row.updated_at = datetime.utcnow()
        session.add(row)
    session.commit()
    return FavoriteState(init=init_id, is_favorite=on)


@router.put("/{init_id}/favorite", response_model=FavoriteState)
def add_favorite(
    init_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> FavoriteState:
    """Mark the initiative as one of the caller's favorites."""
    return _set_favorite(session, current, init_id, True)


@router.delete("/{init_id}/favorite", response_model=FavoriteState)
def remove_favorite(
    init_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> FavoriteState:
    """Remove the initiative from the caller's favorites."""
    return _set_favorite(session, current, init_id, False)


@router.get("/{init_id}", response_model=Initiative)
def get(
    init_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=False))
) -> Initiative:
    """
    Get an initiative by its id.

    - **init_id**: Initiative id
    """
    initiative = session.get(Initiative, init_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    elif not initiative.is_active:
        raise HTTPException(status_code=400, detail=f"Initiative with id '{init_id}' is inactive")
    return initiative


def _validate_list_values(session: Session, updates: dict) -> None:
    """400 when a list-backed field carries a value its list does not define
    (any language row counts — values are language-independent)."""
    for field, list_code in _LIST_FIELDS.items():
        value = updates.get(field)
        if value is None:
            continue
        known = session.exec(
            select(ListItem.value).where(
                ListItem.list == list_code, ListItem.value == value)
        ).first()
        if known is None:
            raise HTTPException(
                status_code=400,
                detail=f"'{value}' is not a valid {list_code} value")


@router.put("/{init_id}", response_model=InitiativeWithAccess)
def update(
    init_id: int,
    payload: InitiativeUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitiativeWithAccess:
    """
    Update an initiative's core fields (Initiative Management → Core Fields).

    Only sent keys are applied. Requires MANAGE on the initiative. A status
    change is accepted only for the owner moves (ACCEPTED → IN_PROGRESS /
    DELIVERED / ARCHIVED, IN_PROGRESS → DELIVERED / ARCHIVED, DELIVERED →
    ARCHIVED); each writes a KICKOFF / DELIVERY / ARCHIVING collaboration
    (HANDLED, no notice) in the same transaction. Anything else → 400.
    """
    initiative = session.exec(
        select(Initiative).where(Initiative.id == init_id).with_for_update()
    ).first()
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    _ensure_manage(session, current, init_id)
    if not initiative.is_active:
        raise HTTPException(status_code=400, detail=f"Initiative with id '{init_id}' is inactive")

    updates = payload.model_dump(exclude_unset=True)
    for field in _REQUIRED_FIELDS:
        if field in updates and not (updates[field] or "").strip():
            raise HTTPException(status_code=400, detail=f"'{field}' cannot be blank")
    _validate_list_values(session, updates)

    collab_type = None
    if "status" in updates:
        try:
            collab_type = status_service.validate_transition(
                initiative.status, updates["status"])
        except status_service.StatusTransitionForbidden as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        if collab_type is None:
            updates.pop("status")
        else:
            updates["status"] = status_service.normalize(updates["status"])

    for key, value in updates.items():
        setattr(initiative, key, value)
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)
    if collab_type:
        status_service.log_status_collaboration(session, init_id, current.id, collab_type)
    session.commit()
    session.refresh(initiative)

    access = permissions_service.user_init_access(session, current, init_id)
    favorite = init_id in _favorite_ids(session, current, [init_id])
    scopes = permissions_service.inits_user_scopes(session, current, [init_id]).get(init_id, [])
    return _with_access(initiative, access or permissions_service.ACCESS_MANAGE, favorite, scopes)


@router.delete("/{init_id}", response_model=Initiative)
def delete(
    init_id: int,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> Initiative:
    """Logically delete an initiative (`is_active=False`). Requires MANAGE."""
    initiative = session.get(Initiative, init_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    _ensure_manage(session, current, init_id)
    if not initiative.is_active:
        raise HTTPException(status_code=400, detail=f"Initiative with id '{init_id}' is already inactive")
    initiative.is_active = False
    initiative.updated_at = datetime.utcnow()
    session.add(initiative)
    session.commit()
    session.refresh(initiative)
    return initiative
