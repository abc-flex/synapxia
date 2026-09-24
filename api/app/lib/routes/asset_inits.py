import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import AssetInit, AssetInitCreate, AssetInitUpdate, Asset
from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ...inits.internal.models import Initiative
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege, check_any_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_inits", tags=["asset_inits"])


def _ensure_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard (mirrors asset_relations): MANAGE grant or
    superuser required. Managed FROM the asset's detail tab, so writes guard
    on the asset only (the initiative need only exist)."""
    try:
        permissions_service.require_asset_manage(session, user, asset_id)
    except permissions_service.AssetAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/", response_model=List[AssetInit])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetInit]:
    """
    List all asset-initiative relations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    relations = session.exec(
        select(AssetInit).where(AssetInit.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetInit.asset, AssetInit.init)
    ).all()
    return relations


# Registered BEFORE the composite /{asset_id}/{init_id} route so that
# GET /asset/5 matches here instead of 422-ing on the composite parser.
@router.get("/asset/{asset_id}", response_model=List[AssetInit])
def get_by_asset(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(current_active_user),
) -> List[AssetInit]:
    """
    List active initiative relations for the given asset.

    Read access: `LIB/ASSETS` OR a privilege on the asset's own category (same
    rule as `assets.get`) — lets a catalog viewer (COLLABORATOR/REVIEWER) read
    the Related Inits tab without holding `LIB/ASSETS`.

    - **asset_id**: Asset id
    - **skip** / **limit**: pagination
    """
    asset = session.get(Asset, asset_id)
    check_any_privilege(
        session, current_user, "LIB",
        ["ASSETS"] + ([asset.category] if asset and asset.category else []),
    )
    relations = session.exec(
        select(AssetInit)
        .where(AssetInit.asset == asset_id, AssetInit.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetInit.init)
    ).all()
    return relations


# ── Addressing ────────────────────────────────────────────────────────────
# A link is identified by (asset, init, type) — the DDL primary key: the same
# pair may be linked once per relation type. The typed routes address one link
# exactly; the older pair routes act on the pair's SINGLE link and answer 409
# when it holds several (mirrors asset_relations).


def _pair_single(session: Session, asset_id: int, init_id: int) -> AssetInit:
    rows = session.exec(
        select(AssetInit).where(AssetInit.asset == asset_id, AssetInit.init == init_id)
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Asset-initiative relation not found")
    active = [r for r in rows if r.is_active]
    candidates = active or rows
    if len(candidates) > 1:
        raise HTTPException(
            status_code=409,
            detail=(f"Asset '{asset_id}' and initiative '{init_id}' are related by several "
                    f"types; use /api/asset_inits/{asset_id}/{init_id}/{{type}}"))
    return candidates[0]


def _typed(session: Session, asset_id: int, init_id: int, type_: str) -> AssetInit:
    relation = session.get(AssetInit, (asset_id, init_id, type_))
    if not relation:
        raise HTTPException(status_code=404, detail="Asset-initiative relation not found")
    return relation


def _ensure_active(relation: AssetInit) -> AssetInit:
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=(f"Asset-initiative relation {relation.asset} -> {relation.init} "
                    f"({relation.type}) is inactive"))
    return relation


def _apply_update(session: Session, relation: AssetInit, update: AssetInitUpdate,
                  allow_type_change: bool) -> AssetInit:
    data = update.model_dump(exclude_unset=True)
    new_type = data.pop("type", None)
    if new_type is not None and new_type != relation.type:
        if not allow_type_change:
            raise HTTPException(
                status_code=400,
                detail="The relation type is part of the key; remove this relation and add a new one")
        if session.get(AssetInit, (relation.asset, relation.init, new_type)):
            raise HTTPException(
                status_code=409,
                detail=f"This asset and initiative are already related as '{new_type}'")
        relation.type = new_type
    for key, value in data.items():
        setattr(relation, key, value)
    relation.updated_at = datetime.utcnow()
    session.add(relation)
    session.commit()
    session.refresh(relation)
    return relation


def _deactivate(session: Session, relation: AssetInit) -> AssetInit:
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=(f"Asset-initiative relation {relation.asset} -> {relation.init} "
                    f"({relation.type}) is already inactive"))
    relation.is_active = False
    relation.updated_at = datetime.utcnow()
    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info("Asset-initiative relation deactivated: %s -> %s (%s)",
                relation.asset, relation.init, relation.type)
    return relation


@router.get("/{asset_id}/{init_id}/{relation_type}", response_model=AssetInit)
def get_typed(
    asset_id: int, init_id: int, relation_type: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False)),
) -> AssetInit:
    """Get one asset-initiative relation by asset, initiative and type."""
    return _ensure_active(_typed(session, asset_id, init_id, relation_type))


@router.get("/{asset_id}/{init_id}", response_model=AssetInit)
def get(
    asset_id: int, init_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> AssetInit:
    """
    Get the pair's single asset-initiative relation (409 when several types
    exist — use the typed route).

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    """
    return _ensure_active(_pair_single(session, asset_id, init_id))


@router.post("/", response_model=AssetInit, status_code=201)
def create(
    relation: AssetInitCreate, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> AssetInit:
    """
    Create a new asset-initiative relation.

    - **asset**: Asset id (required)
    - **init**: Initiative id (required)
    - **type**: Relation type (required)
    - **rationale**: Optional note on why the asset and initiative are related
    - **is_active**: Active/inactive status (default: True)

    The same pair may be linked once per type: an active identical
    (asset, init, type) link → 409; an inactive one is reactivated with the
    given rationale.

    Write access: `LIB/ASSETS` OR a write privilege on the asset's own category
    (mirrors `get_by_asset`'s read rule) — lets a proposer flush the Propose
    wizard's staged "Related Inits" rows against the just-created asset, then
    `_ensure_manage` still enforces per-asset MANAGE (satisfied here since
    propose auto-grants the creator MANAGE on their new asset).
    """
    asset = session.get(Asset, relation.asset)
    if not asset:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{relation.asset}' does not exist"
        )

    initiative = session.get(Initiative, relation.init)
    if not initiative:
        raise HTTPException(
            status_code=400,
            detail=f"Initiative with id '{relation.init}' does not exist"
        )

    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([asset.category] if asset.category else []),
        can_edit=True,
    )
    _ensure_manage(session, current, relation.asset)

    existing = session.get(AssetInit, (relation.asset, relation.init, relation.type))
    if existing and existing.is_active:
        raise HTTPException(
            status_code=409,
            detail=(f"Asset '{relation.asset}' and initiative '{relation.init}' are already "
                    f"related as '{relation.type}'")
        )
    if existing:
        existing.is_active = True
        existing.rationale = relation.rationale
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info("Asset-initiative relation reactivated: %s -> %s (%s)",
                    relation.asset, relation.init, relation.type)
        return existing

    try:
        db = AssetInit.model_validate(relation)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Asset-initiative relation created: {relation.asset} -> {relation.init} ({relation.type})")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating asset-initiative relation {relation.asset}/{relation.init}: {e}")
        raise HTTPException(
            status_code=409,
            detail=(f"Asset '{relation.asset}' and initiative '{relation.init}' are already "
                    f"related as '{relation.type}'")
        )


@router.put("/{asset_id}/{init_id}/{relation_type}", response_model=AssetInit)
def update_typed(
    asset_id: int, init_id: int, relation_type: str,
    update: AssetInitUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetInit:
    """Update one link's rationale / active flag. The type is part of the key
    and cannot change here (400). Requires MANAGE on the asset."""
    relation = _typed(session, asset_id, init_id, relation_type)
    _ensure_manage(session, current, asset_id)
    return _apply_update(session, relation, update, allow_type_change=False)


@router.put("/{asset_id}/{init_id}", response_model=AssetInit)
def update(
    asset_id: int,
    init_id: int,
    update: AssetInitUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetInit:
    """
    Update the pair's single asset-initiative relation (409 when several types
    exist — use the typed route). Requires MANAGE on the asset.

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    - Only provided fields are updated
    """
    relation = _pair_single(session, asset_id, init_id)
    _ensure_manage(session, current, asset_id)
    return _apply_update(session, relation, update, allow_type_change=True)


@router.delete("/{asset_id}/{init_id}/{relation_type}", response_model=AssetInit, status_code=200)
def delete_typed(
    asset_id: int, init_id: int, relation_type: str,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetInit:
    """Logically delete one link (that type only). Requires MANAGE on the asset."""
    relation = _typed(session, asset_id, init_id, relation_type)
    _ensure_manage(session, current, asset_id)
    return _deactivate(session, relation)


@router.delete("/{asset_id}/{init_id}", response_model=AssetInit, status_code=200)
def delete(
    asset_id: int, init_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetInit:
    """
    Logically delete the pair's single asset-initiative relation (409 when
    several types exist — use the typed route). Requires MANAGE on the asset.

    - **asset_id**: Asset id
    - **init_id**: Initiative id
    """
    relation = _pair_single(session, asset_id, init_id)
    _ensure_manage(session, current, asset_id)
    return _deactivate(session, relation)
