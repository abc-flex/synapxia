import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    AssetRelation, AssetRelationCreate, AssetRelationUpdate, Asset, RelatedAsset,
)
from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege, check_any_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/asset_relations", tags=["asset_relations"])


def _ensure_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard (HU-LI08): MANAGE grant or superuser required.
    Relations are managed FROM the source asset's detail tab, so writes guard
    on the source only (the target need only exist)."""
    try:
        permissions_service.require_asset_manage(session, user, asset_id)
    except permissions_service.AssetAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))

# NOTE on privilege option: relations are subordinate resources managed from
# the Assets screen, so they gate on (LIB, ASSETS) — the option that's
# actually seeded in db/sql/12-admin-insert.sql. The previous
# "ASSET_RELATIONS" option was never seeded, which 403'd every non-superuser.


@router.get("/", response_model=List[AssetRelation])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetRelation]:
    """
    List all asset relations with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    relations = session.exec(select(AssetRelation).where(AssetRelation.is_active == True)
                             .offset(skip).limit(limit)
                             .order_by(AssetRelation.source, AssetRelation.target)).all()
    return relations


# Registered BEFORE the composite /{source_id}/{target_id} route so that
# GET /source/5 matches here instead of 422-ing on the composite parser.
@router.get("/source/{asset_id}", response_model=List[AssetRelation])
def get_by_source(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetRelation]:
    """
    List active relations where the given asset is the source.

    - **asset_id**: Source asset id
    - **skip** / **limit**: pagination
    """
    relations = session.exec(
        select(AssetRelation)
        .where(AssetRelation.source == asset_id, AssetRelation.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetRelation.target)
    ).all()
    return relations


@router.get("/target/{asset_id}", response_model=List[AssetRelation])
def get_by_target(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetRelation]:
    """
    List active relations where the given asset is the **target** (reverse
    lookup — the counterpart to /source/{asset_id}).

    - **asset_id**: Target asset id
    - **skip** / **limit**: pagination
    """
    relations = session.exec(
        select(AssetRelation)
        .where(AssetRelation.target == asset_id, AssetRelation.is_active == True)
        .offset(skip).limit(limit)
        .order_by(AssetRelation.source)
    ).all()
    return relations


@router.get("/related/{asset_id}", response_model=List[RelatedAsset])
def get_related(
    asset_id: int, skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(current_active_user),
) -> List[RelatedAsset]:
    """
    Resolved related assets in **both directions**, with inactive/missing
    assets excluded. "Outgoing wins" per other asset (a bidirectional pair shows
    as outgoing), but every relation TYPE of the winning direction is listed —
    the same pair may be related once per type. Convenience for the gallery "Related" section: the caller gets the
    target asset's display fields + the relation metadata without an extra
    round-trip per relation.

    Read access: `LIB/ASSETS` OR a privilege on the source asset's own category
    (same rule as `assets.get`) — lets a catalog viewer (COLLABORATOR/REVIEWER)
    read the Related Assets tab without holding `LIB/ASSETS`.

    - **asset_id**: The asset whose relations are resolved
    - **skip** / **limit**: pagination over the de-duplicated result
    """
    asset = session.get(Asset, asset_id)
    check_any_privilege(
        session, current_user, "LIB",
        ["ASSETS"] + ([asset.category] if asset and asset.category else []),
    )
    # Bound each direction fetch by the requested page's upper edge — after
    # de-dup the page can draw entirely from one direction, so skip+limit per
    # side is a safe (and bounded) superset.
    cap = skip + limit
    outgoing = session.exec(
        select(AssetRelation)
        .where(AssetRelation.source == asset_id, AssetRelation.is_active == True)
        .order_by(AssetRelation.target, AssetRelation.type).limit(cap)
    ).all()
    incoming = session.exec(
        select(AssetRelation)
        .where(AssetRelation.target == asset_id, AssetRelation.is_active == True)
        .order_by(AssetRelation.source, AssetRelation.type).limit(cap)
    ).all()

    # "Outgoing wins" per other asset: a bidirectional pair shows as outgoing.
    # Within the winning direction every relation type is kept — the same pair
    # may be related once per type (PK source, target, type).
    outgoing_ids = {r.target for r in outgoing}
    ordered = [(r.target, r.type, "outgoing", r.rationale) for r in outgoing]
    ordered += [
        (r.source, r.type, "incoming", r.rationale)
        for r in incoming if r.source not in outgoing_ids
    ]

    page = ordered[skip:skip + limit]
    if not page:
        return []

    # One batched IN query resolves every related asset — no N+1.
    ids = [oid for (oid, _t, _d, _r) in page]
    assets = {
        a.id: a for a in session.exec(
            select(Asset).where(Asset.id.in_(ids), Asset.is_active == True)
        ).all()
    }

    result: List[RelatedAsset] = []
    for (oid, rtype, direction, rationale) in page:
        a = assets.get(oid)
        if not a:  # inactive or missing target asset — excluded
            continue
        result.append(RelatedAsset(
            id=a.id, name=a.name, description=a.description,
            category=a.category, status=a.status, tags=a.tags,
            relation_type=rtype, direction=direction, rationale=rationale,
        ))
    return result


# ── Addressing ────────────────────────────────────────────────────────────
# A relation is identified by (source, target, type) — the DDL primary key: the
# same pair may be related once per relation type. The typed routes below
# address one link exactly. The older pair routes (`/{source}/{target}`) are
# kept for compatibility and act on the pair's SINGLE link; when the pair holds
# several they answer 409 instead of silently picking one.


def _pair_single(session: Session, source_id: int, target_id: int) -> AssetRelation:
    rows = session.exec(
        select(AssetRelation).where(
            AssetRelation.source == source_id, AssetRelation.target == target_id)
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Asset relation not found")
    active = [r for r in rows if r.is_active]
    candidates = active or rows
    if len(candidates) > 1:
        raise HTTPException(
            status_code=409,
            detail=(f"Assets '{source_id}' and '{target_id}' are related by several types; "
                    f"use /api/asset_relations/{source_id}/{target_id}/{{type}}"))
    return candidates[0]


def _typed(session: Session, source_id: int, target_id: int, type_: str) -> AssetRelation:
    relation = session.get(AssetRelation, (source_id, target_id, type_))
    if not relation:
        raise HTTPException(status_code=404, detail="Asset relation not found")
    return relation


def _apply_update(session: Session, relation: AssetRelation, update: AssetRelationUpdate,
                  allow_type_change: bool) -> AssetRelation:
    data = update.model_dump(exclude_unset=True)
    new_type = data.pop("type", None)
    if new_type is not None and new_type != relation.type:
        if not allow_type_change:
            raise HTTPException(
                status_code=400,
                detail="The relation type is part of the key; remove this relation and add a new one")
        if session.get(AssetRelation, (relation.source, relation.target, new_type)):
            raise HTTPException(
                status_code=409,
                detail=f"These assets are already related as '{new_type}'")
        relation.type = new_type
    for key, value in data.items():
        setattr(relation, key, value)
    relation.updated_at = datetime.utcnow()
    session.add(relation)
    session.commit()
    session.refresh(relation)
    return relation


def _deactivate(session: Session, relation: AssetRelation) -> AssetRelation:
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=(f"Asset relation {relation.source} -> {relation.target} "
                    f"({relation.type}) is already inactive"))
    relation.is_active = False
    relation.updated_at = datetime.utcnow()
    session.add(relation)
    session.commit()
    session.refresh(relation)
    logger.info("Asset relation deactivated: %s -> %s (%s)",
                relation.source, relation.target, relation.type)
    return relation


def _ensure_active(relation: AssetRelation) -> AssetRelation:
    if not relation.is_active:
        raise HTTPException(
            status_code=400,
            detail=(f"Asset relation {relation.source} -> {relation.target} "
                    f"({relation.type}) is inactive"))
    return relation


@router.get("/{source_id}/{target_id}/{relation_type}", response_model=AssetRelation)
def get_typed(
    source_id: int, target_id: int, relation_type: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False)),
) -> AssetRelation:
    """Get one asset relation by source, target and relation type."""
    return _ensure_active(_typed(session, source_id, target_id, relation_type))


@router.get("/{source_id}/{target_id}", response_model=AssetRelation)
def get(
    source_id: int, target_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> AssetRelation:
    """
    Get the relation between two assets when the pair has a single one
    (409 when they are related by several types — use the typed route).

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    """
    return _ensure_active(_pair_single(session, source_id, target_id))


@router.post("/", response_model=AssetRelation, status_code=201)
def create(
    relation: AssetRelationCreate, session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> AssetRelation:
    """
    Create a new asset relation.

    - **source**: Source asset id (required)
    - **target**: Target asset id (required)
    - **type**: Relation type (required)
    - **rationale**: Optional note on why the assets are related
    - **is_active**: Active/inactive status (default: True)

    The same pair may be related once per type: an active identical
    (source, target, type) link → 409; an inactive one is reactivated with the
    given rationale.

    Write access: `LIB/ASSETS` OR a write privilege on the source asset's own
    category (mirrors `get_related`'s read rule) — lets a proposer flush the
    Propose wizard's staged "Related Assets" rows against the just-created
    asset, then `_ensure_manage` still enforces per-asset MANAGE (satisfied
    here since propose auto-grants the creator MANAGE on their new asset).
    """
    source_asset = session.get(Asset, relation.source)
    if not source_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Source asset with id '{relation.source}' does not exist"
        )

    target_asset = session.get(Asset, relation.target)
    if not target_asset:
        raise HTTPException(
            status_code=400,
            detail=f"Target asset with id '{relation.target}' does not exist"
        )

    if relation.source == relation.target:
        raise HTTPException(
            status_code=400,
            detail="Source and target assets cannot be the same"
        )

    check_any_privilege(
        session, current, "LIB",
        ["ASSETS"] + ([source_asset.category] if source_asset.category else []),
        can_edit=True,
    )
    _ensure_manage(session, current, relation.source)

    existing = session.get(AssetRelation, (relation.source, relation.target, relation.type))
    if existing and existing.is_active:
        raise HTTPException(
            status_code=409,
            detail=(f"Assets '{relation.source}' and '{relation.target}' are already "
                    f"related as '{relation.type}'")
        )
    if existing:
        existing.is_active = True
        existing.rationale = relation.rationale
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        logger.info("Asset relation reactivated: %s -> %s (%s)",
                    relation.source, relation.target, relation.type)
        return existing

    try:
        db = AssetRelation.model_validate(relation)
        session.add(db)
        session.commit()
        session.refresh(db)
        logger.info(
            f"Asset relation created: {relation.source} -> {relation.target} ({relation.type})")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(
            f"Integrity error creating asset relation {relation.source}/{relation.target}: {e}")
        raise HTTPException(
            status_code=409,
            detail=(f"Assets '{relation.source}' and '{relation.target}' are already "
                    f"related as '{relation.type}'")
        )


@router.put("/{source_id}/{target_id}/{relation_type}", response_model=AssetRelation)
def update_typed(
    source_id: int, target_id: int, relation_type: str,
    update: AssetRelationUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetRelation:
    """Update one relation's rationale / active flag. The type is part of the
    key and cannot change here (400). Requires MANAGE on the source asset."""
    relation = _typed(session, source_id, target_id, relation_type)
    _ensure_manage(session, current, source_id)
    return _apply_update(session, relation, update, allow_type_change=False)


@router.put("/{source_id}/{target_id}", response_model=AssetRelation)
def update(
    source_id: int,
    target_id: int,
    update: AssetRelationUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetRelation:
    """
    Update the pair's single relation (409 when several types exist — use the
    typed route). Requires MANAGE on the source asset.

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    - Only provided fields are updated
    """
    relation = _pair_single(session, source_id, target_id)
    _ensure_manage(session, current, source_id)
    return _apply_update(session, relation, update, allow_type_change=True)


@router.delete("/{source_id}/{target_id}/{relation_type}", response_model=AssetRelation, status_code=200)
def delete_typed(
    source_id: int, target_id: int, relation_type: str,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True)),
) -> AssetRelation:
    """Logically delete one relation (that type only). Requires MANAGE on the
    source asset."""
    relation = _typed(session, source_id, target_id, relation_type)
    _ensure_manage(session, current, source_id)
    return _deactivate(session, relation)


@router.delete("/{source_id}/{target_id}", response_model=AssetRelation, status_code=200)
def delete(
    source_id: int, target_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> AssetRelation:
    """
    Logically delete the pair's single relation (409 when several types exist
    — use the typed route). Requires MANAGE on the source asset.

    - **source_id**: Source asset id
    - **target_id**: Target asset id
    """
    relation = _pair_single(session, source_id, target_id)
    _ensure_manage(session, current, source_id)
    return _deactivate(session, relation)
