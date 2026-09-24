"""Initiative ↔ asset links seen from the initiative (Related Assets tab).

Backed by lib's ``asset_inits`` table (``AssetInit``) — the same records the
asset side's "Related Inits" tab shows. Authority here is the INITIATIVE's
MANAGE (the page's owner), not the asset's; the asset-side routes keep their own
asset-MANAGE guard. A link is identified by (asset, initiative, type) — the same
asset may be linked once per relation type; re-adding a removed identical link
restores it instead of duplicating it.
"""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ..internal.models import Initiative, InitiativeAsset, InitiativeAssetCreate
from ...admin.internal.models import ListItem, User
from ...auth.routes import current_active_user
from ...internal.permissions import check_any_privilege, require_privilege
from ...lib.internal import permissions_service as asset_permissions
from ...lib.internal.models import Asset, AssetInit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/initiatives", tags=["initiative-assets"])


def _active_initiative(session: Session, init_id: int) -> Initiative:
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise HTTPException(status_code=404, detail="Initiative not found")
    return initiative


def _guard(check, session: Session, user: User, init_id: int) -> None:
    try:
        check(session, user, init_id)
    except permissions_service.InitAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _project(link: AssetInit, asset: Asset | None) -> InitiativeAsset:
    return InitiativeAsset(
        asset=link.asset,
        asset_name=asset.name if asset else None,
        category=asset.category if asset else None,
        asset_status=asset.status if asset else None,
        type=link.type,
        rationale=link.rationale,
        created_at=link.created_at,
    )


@router.get("/{init_id}/assets", response_model=List[InitiativeAsset])
def get_assets(
    init_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> List[InitiativeAsset]:
    """Active asset links of an initiative, newest first. Assets the caller
    cannot open are still listed by name so no link is invisible."""
    check_any_privilege(session, current, "INITS", ["INITIATIVES", "EXPLORE"])
    _active_initiative(session, init_id)
    _guard(permissions_service.require_init_view, session, current, init_id)
    rows = session.exec(
        select(AssetInit, Asset)
        .join(Asset, Asset.id == AssetInit.asset, isouter=True)
        .where(AssetInit.init == init_id, AssetInit.is_active == True)  # noqa: E712
        .order_by(AssetInit.created_at.desc())
        .offset(skip).limit(limit)
    ).all()
    return [_project(link, asset) for link, asset in rows]


@router.post("/{init_id}/assets", response_model=InitiativeAsset, status_code=201)
def add_asset(
    init_id: int,
    payload: InitiativeAssetCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitiativeAsset:
    """Link an asset to the initiative. Requires MANAGE on the initiative and
    that the caller can see the asset."""
    _active_initiative(session, init_id)
    _guard(permissions_service.require_init_manage, session, current, init_id)

    asset = session.get(Asset, payload.asset)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=400, detail=f"Asset with id '{payload.asset}' does not exist")
    if not current.is_superuser and asset_permissions.user_asset_access(
            session, current, payload.asset) is None:
        raise HTTPException(status_code=403, detail="You do not have access to this asset")
    known = session.exec(
        select(ListItem.value).where(
            ListItem.list == "RELATION_TYPE", ListItem.value == payload.type)
    ).first()
    if known is None:
        raise HTTPException(status_code=400, detail=f"'{payload.type}' is not a valid RELATION_TYPE value")

    link = session.get(AssetInit, (payload.asset, init_id, payload.type))
    if link and link.is_active:
        raise HTTPException(
            status_code=409,
            detail=f"This asset is already related to the initiative as '{payload.type}'")
    if link:
        link.is_active = True
        link.rationale = payload.rationale
        link.updated_at = datetime.utcnow()
    else:
        link = AssetInit(asset=payload.asset, init=init_id,
                         type=payload.type, rationale=payload.rationale)
    session.add(link)
    session.commit()
    session.refresh(link)
    logger.info("Initiative asset linked: init=%s asset=%s type=%s",
                init_id, payload.asset, payload.type)
    return _project(link, asset)


@router.delete("/{init_id}/assets/{asset_id}/{relation_type}", response_model=InitiativeAsset)
def remove_asset(
    init_id: int,
    asset_id: int,
    relation_type: str,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("INITS", "INITIATIVES", can_edit=True)),
) -> InitiativeAsset:
    """Logically remove one asset link (that relation type only). Requires
    MANAGE on the initiative."""
    _active_initiative(session, init_id)
    _guard(permissions_service.require_init_manage, session, current, init_id)
    link = session.get(AssetInit, (asset_id, init_id, relation_type))
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if not link.is_active:
        raise HTTPException(status_code=400, detail="Link is already removed")
    link.is_active = False
    link.updated_at = datetime.utcnow()
    session.add(link)
    session.commit()
    session.refresh(link)
    return _project(link, session.get(Asset, asset_id))
