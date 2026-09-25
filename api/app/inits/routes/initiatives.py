import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, SQLModel
from sqlalchemy import cast, String

from sqlalchemy.exc import IntegrityError

from ..internal import (
    diagnosis_service, explore_service, modify_service, permissions_service,
    propose_service, status_service,
)
from ..internal.list_validation import REQUIRED_FIELDS, validate_core_fields
from ..internal.diagnostics_service import diagnosis_form, get_diagnostics
from ..internal.models import (
    DiagnosisForm, DiagnosticsResponse, FavoriteInit, FavoriteState, Initiative,
    InitiativeDiagnoseRequest, InitiativeExploreItem, InitiativeProposeRequest,
    InitiativeResubmitRequest, InitiativeUpdate, InitiativeWithAccess, LinkableAsset,
)
from ...internal import reviewers
from ...lib.internal import permissions_service as asset_permissions
from ...lib.internal.models import Asset, ReviewerOption
from ..internal.dependencies import get_db_session
from ...internal.permissions import require_privilege, check_any_privilege
from ...auth.routes import current_active_user
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/initiatives", tags=["initiatives"])

# Initiatives are never created here — they are only proposed (future propose
# flow). Initiative Management (specs/004-initiative-management) lists the
# initiatives the caller can access and edits them tab by tab; status changes
# are limited to the owner moves in inits/internal/status_service.py.

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


# ── Explore / Propose (specs/005-explore-initiatives) ────────────────────────
# Declared before every `/{init_id}` route so the static paths win.


def _gate_explore(session: Session, user: User, can_edit: bool = False) -> None:
    """Module RBAC for the Explore surface: INITS/EXPLORE or INITS/INITIATIVES."""
    check_any_privilege(session, user, "INITS", ["EXPLORE", "INITIATIVES"], can_edit=can_edit)


@router.get("/explore", response_model=List[InitiativeExploreItem])
def get_explore(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[InitiativeExploreItem]:
    """
    Explore Initiatives gallery: active ACCEPTED / IN_PROGRESS / DELIVERED
    initiatives a live grant reaches the caller through (superusers: all),
    filtered BEFORE `skip`/`limit`, newest first. Each row carries the caller's
    access, favorite flag, grant scopes, vote tally, discussion count and
    related-assets count.
    """
    _gate_explore(session, current)
    return explore_service.list_explore(session, current, skip, limit)


@router.get("/reviewers", response_model=List[ReviewerOption])
def get_reviewers(
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[ReviewerOption]:
    """Eligible reviewers for a proposal — the same rule as Propose an asset.
    A non-admin caller is left out of their own list."""
    _gate_explore(session, current)
    exclude_id = None if reviewers.is_admin(current) else current.id
    return [
        ReviewerOption(
            value=u.id,
            label=f"{u.first_name or ''} {u.last_name or ''}".strip() or u.username,
            profile=u.profile or "",
            is_superuser=bool(u.is_superuser),
        )
        for u in reviewers.list_reviewers(session, exclude_user_id=exclude_id)
    ]


@router.get("/linkable-assets", response_model=List[LinkableAsset])
def get_linkable_assets(
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[LinkableAsset]:
    """Active assets the caller can see (superusers: all), for the Propose
    wizard's Related Assets step. The proposal re-checks visibility."""
    _gate_explore(session, current)
    query = select(Asset).where(Asset.is_active == True)  # noqa: E712
    if not current.is_superuser:
        visible = asset_permissions.accessible_assets(session, current)
        if not visible:
            return []
        query = query.where(Asset.id.in_(list(visible)))
    return [
        LinkableAsset(value=a.id, label=a.name, category=a.category)
        for a in session.exec(query.order_by(Asset.name)).all()
    ]


@router.get("/diagnosis-form", response_model=DiagnosisForm)
def get_diagnosis_form(
    lang: str = Query("en", pattern="^(en|es)$"),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> DiagnosisForm:
    """The diagnosis questionnaire — active criteria plus each scale's options
    in `lang` — for proposers and reviewers who hold INITS/EXPLORE but not the
    INITS/CRITERIAS admin privilege."""
    _gate_explore(session, current)
    return diagnosis_form(session, lang)


@router.post("/propose", response_model=Initiative, status_code=201)
def propose(
    payload: InitiativeProposeRequest,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Initiative:
    """
    Propose an initiative and request its diagnosis — one transaction writes
    the initiative (ACTIVATED), the proposer's diagnosis answers, the related
    asset links, ACTIVATION/HANDLED + DIAGNOSIS/PENDING collaborations and
    MANAGE grants for the proposer and the reviewer. 400 on any validation
    problem (nothing is written).
    """
    _gate_explore(session, current, can_edit=True)
    try:
        return propose_service.propose_initiative(session, current, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Could not propose the initiative due to a data conflict")


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
    try:
        validate_core_fields(session, updates, required=REQUIRED_FIELDS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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


@router.post("/{init_id}/diagnose", response_model=Initiative)
def diagnose(
    init_id: int,
    payload: InitiativeDiagnoseRequest,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Initiative:
    """
    The assigned reviewer's decision (accept / reject / changes). The service
    enforces the rest: eligible reviewer holding the PENDING DIAGNOSIS (403),
    initiative ACTIVATED (409), complete in-scale answers and feedback for
    reject / changes (400).
    """
    try:
        return diagnosis_service.diagnose_initiative(session, current, init_id, payload)
    except diagnosis_service.DiagnosisForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except diagnosis_service.DiagnosisConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Could not save the diagnosis due to a data conflict")


@router.post("/{init_id}/resubmit", response_model=Initiative)
def resubmit(
    init_id: int,
    payload: InitiativeResubmitRequest,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> Initiative:
    """
    The proposer's resubmission after a change request. The service enforces
    the rest: proposer holding the PENDING MODIFICATION (403), initiative in
    FEEDBACK (409), valid fields and complete answers when sent (400).
    """
    try:
        return modify_service.resubmit_initiative(session, current, init_id, payload)
    except modify_service.ModifyForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except modify_service.ModifyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Could not resubmit the initiative due to a data conflict")


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
