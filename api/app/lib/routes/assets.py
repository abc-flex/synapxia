import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, SQLModel
from sqlalchemy import cast, String
from sqlalchemy.exc import IntegrityError

from ..internal.models import (
    Asset, AssetCreate, AssetUpdate, AssetPermission, AssetWithAccessLevels,
    ProposeRequest, ReviewerOption, ReviewRequest, ModifyRequest, VersionRequest,
    AssetVersion, Characterization,
)
from ..internal import propose_service
from ..internal import review_service
from ..internal import modify_service
from ..internal import version_service
from ..internal import permissions_service
from ...taxo.internal.models import Category
from ..internal.dependencies import get_db_session
from ...auth.routes import current_active_user
from ...internal.permissions import require_privilege
from ...admin.internal.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assets", tags=["assets"])


def _ensure_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard (HU-LI08): MANAGE grant or superuser required.
    Layered INSIDE the module-level `require_privilege` RBAC gate."""
    try:
        permissions_service.require_asset_manage(session, user, asset_id)
    except permissions_service.AssetAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/", response_model=List[Asset])
def get_all(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[Asset]:
    """
    List all assets with pagination.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    assets = session.exec(select(Asset).where(Asset.is_active == True)
                          .offset(skip).limit(limit)
                          .order_by(Asset.name)).all()
    return assets


# NOTE: declared before any `/{...}` dynamic route so "with-access" isn't
# captured as a path parameter.
@router.get("/with-access", response_model=List[AssetWithAccessLevels])
def get_all_with_access(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetWithAccessLevels]:
    """
    List the assets THE CALLER CAN ACCESS, with a per-asset access summary.

    Visibility is caller-scoped (HU-LI08): only assets with an active,
    temporally-valid `asset_permissions` grant reaching the current user (via
    USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC) are returned — an asset with no grants
    is hidden. Superusers see every active asset. Access filtering happens
    BEFORE `skip`/`limit`, so pages stay full and stable.

    Each row adds `access_levels` (distinct active access levels granted on the
    asset to anyone), `is_public` (any active permission targeting PUBLIC),
    `permission_scopes` (the scope-types by which the current user is granted
    access; drives the privileges/permisos filter), and `my_access` (the
    caller's effective level, MANAGE beats VIEW — superusers always MANAGE;
    drives the row action gating). The existing `GET /api/assets/` contract is
    unchanged.

    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum number of records to return (default: 100)
    """
    if current.is_superuser:
        access_map: dict = {}
        query = select(Asset).where(Asset.is_active == True)  # noqa: E712
    else:
        access_map = permissions_service.accessible_assets(session, current)
        if not access_map:
            return []
        query = select(Asset).where(
            Asset.is_active == True,  # noqa: E712
            Asset.id.in_(list(access_map)),  # type: ignore[attr-defined]
        )
    assets = session.exec(
        query.order_by(Asset.name).offset(skip).limit(limit)
    ).all()
    asset_ids = [asset.id for asset in assets]

    # Asset-wide summary (who-is-granted-what display fields). Mirrors the old
    # SQL aggregate's semantics exactly: is_active only, no temporal check —
    # only visibility/my_access honor validity windows.
    summary_perms = session.exec(
        select(AssetPermission).where(
            AssetPermission.asset.in_(asset_ids),  # type: ignore[attr-defined]
            AssetPermission.is_active == True,  # noqa: E712
        )
    ).all() if asset_ids else []
    levels_by_asset: dict = {}
    public_assets: set = set()
    for p in summary_perms:
        levels_by_asset.setdefault(p.asset, set()).add(p.access_level)
        if p.target_type == "PUBLIC":
            public_assets.add(p.asset)

    # Per-current-user scope-types granting access, for the assets on this page.
    scopes_by_asset = permissions_service.assets_user_scopes(session, current, asset_ids)

    result: List[AssetWithAccessLevels] = []
    for asset in assets:
        result.append(AssetWithAccessLevels(
            id=asset.id,
            name=asset.name,
            description=asset.description,
            category=asset.category,
            reference=asset.reference,
            status=asset.status,
            tags=asset.tags,
            detail=asset.detail,
            current_version=asset.current_version,
            is_active=asset.is_active,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            access_levels=sorted(levels_by_asset.get(asset.id, set())),
            is_public=asset.id in public_assets,
            permission_scopes=scopes_by_asset.get(asset.id, []),
            my_access=(permissions_service.ACCESS_MANAGE if current.is_superuser
                       else access_map.get(asset.id)),
        ))
    return result


class AssetBasic(SQLModel):
    """Lightweight {value,label} shape for UI dropdowns."""
    value: str
    label: str


# Registered BEFORE /{asset_id} so "select" isn't parsed as an asset id.
@router.get("/select", response_model=List[AssetBasic])
def get_select(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetBasic]:
    """
    Lightweight list of active assets for UI dropdowns: value = id, label = name.
    """
    rows = session.exec(
        select(
            cast(Asset.id, String).label("value"),
            Asset.name.label("label"),
        )
        .where(Asset.is_active == True)
        .order_by(Asset.name)
    ).all()
    return rows


@router.get("/category/{category_code}", response_model=List[Asset])
def get_by_category(
    category_code: str,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[Asset]:
    """
    Obtener todos los assets de una categoría específica.

    - **category_code**: Código de la categoría para filtrar
    """
    # Validar primero si la categoría existe (opcional, pero recomendado por integridad)
    category_exists = session.get(Category, category_code)
    if not category_exists:
        raise HTTPException(
            status_code=404, 
            detail=f"Category with code '{category_code}' does not exist"
        )
    items = session.exec(
        select(Asset)
        .where(Asset.category == category_code)
        .offset(skip)
        .limit(limit)
        .order_by(Asset.name)
    ).all()
    return items


# ---------------------------------------------------------------------------
# Proposal (HU-Propose) — the review-workflow entry point. Registered BEFORE the
# composite `/{asset_id}` route so "reviewers"/"propose" aren't parsed as ids.
# ---------------------------------------------------------------------------


@router.get("/reviewers", response_model=List[ReviewerOption])
def list_reviewers(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[ReviewerOption]:
    """
    Eligible reviewers for a proposal — active users with an administrator or
    REVIEWER profile (or superusers), as ``{value: id, label: name}`` for the
    propose form's dropdown. Lives under LIB so a proposer doesn't need
    ADMIN/USERS access.
    """
    return [
        ReviewerOption(
            value=u.id,
            label=(f"{u.first_name} {u.last_name}".strip() or u.username),
            profile=u.profile,
            is_superuser=bool(u.is_superuser),
        )
        for u in propose_service.list_reviewers(session)
    ]


@router.post("/propose", response_model=Asset, status_code=201)
def propose(
    payload: ProposeRequest, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Propose an asset for review (HU-Propose). Atomically creates the asset
    (PROPOSED), its characterizations (from the category's specs), a PROPOSAL
    action for the current user, a REVIEW assignment for the reviewer, and MANAGE
    permissions for both — generating the reviewer's notification.

    - **name** / **category**: required
    - **reviewer_id**: optional (auto-assigned to the first eligible reviewer —
      administrator, REVIEWER, or superuser)
    - **values**: optional per-feature characterization overrides
    """
    try:
        return propose_service.propose_asset(session, current.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error on propose (proposer=%s)", current.id)
        raise HTTPException(
            status_code=409, detail="Could not propose the asset due to a data conflict")


@router.post("/{asset_id}/review", response_model=Asset)
def review(
    asset_id: int, payload: ReviewRequest, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Record a reviewer's decision on a PROPOSED asset (HU-Review). In one
    transaction: closes the reviewer's REVIEW assignment (REVIEW/FINISHED), sets
    the asset status, and notifies the proposer with the feedback.

    - **decision**: `approve` → PUBLISHED (+ PUBLICATION), `reject` → REJECTED
      (+ REJECTION), `changes` → FEEDBACK (+ MODIFICATION)
    - **feedback**: shown to the proposer (recommended for reject / changes)

    403 if the caller isn't the assigned/eligible reviewer; 409 if the asset is
    no longer awaiting review.
    """
    try:
        return review_service.review_asset(
            session, current, asset_id, payload.decision, payload.feedback)
    except review_service.ReviewForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except review_service.ReviewConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error on review (asset=%s reviewer=%s)", asset_id, current.id)
        raise HTTPException(
            status_code=409, detail="Could not review the asset due to a data conflict")


@router.post("/{asset_id}/resubmit", response_model=Asset)
def resubmit(
    asset_id: int, payload: ModifyRequest, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Resubmit an asset for re-review after a reviewer requested changes (HU-Modify).
    In one transaction: updates the asset's editable fields + its characterizations,
    closes the proposer's MODIFICATION assignment (MODIFICATION/FINISHED), sets the
    asset status back to PROPOSED, and re-arms the original reviewer (REVIEW/ASSIGNED).

    - Editable: `name`, `description`, `reference`, `tags`, `detail`, and per-feature
      characterization `values` (category is fixed).

    403 if the caller isn't the proposer holding the open MODIFICATION assignment;
    409 if the asset is not awaiting modification (status != FEEDBACK).
    """
    try:
        return modify_service.resubmit_asset(session, current, asset_id, payload)
    except modify_service.ModifyForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except modify_service.ModifyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error on resubmit (asset=%s proposer=%s)", asset_id, current.id)
        raise HTTPException(
            status_code=409, detail="Could not resubmit the asset due to a data conflict")


@router.post("/{asset_id}/versions", response_model=Asset)
def create_version(
    asset_id: int, payload: VersionRequest, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Save the edits as a NEW VERSION of the asset (HU-LI09, versioning half).
    In one transaction: bumps `current_version` by the chosen `change_type`
    (major → X+1.0.0 / minor → X.Y+1.0 / patch → X.Y.Z+1), applies the core
    edits, writes the new version's characterization rows under the bumped
    `version_label` (prior versions keep theirs untouched), and logs a
    VERSIONING/FINISHED action.

    - `values` is the FULL desired characterization set (feature → value);
      omit it entirely for a core-only save (current set is copied forward).

    400 for a bad `change_type` or unknown category; 404 for a missing asset;
    409 when the bumped label already exists (e.g. two concurrent saves racing
    from the same version). 403 unless the caller holds MANAGE on the asset
    (non-superusers probing an unknown asset get 403 rather than 404 — no
    grant can exist for it, and existence isn't disclosed).
    """
    _ensure_manage(session, current, asset_id)
    try:
        return version_service.create_version(session, current, asset_id, payload)
    except version_service.VersionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{asset_id}/versions", response_model=List[AssetVersion])
def list_versions(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[AssetVersion]:
    """
    The asset's version history (HU-LI09, read side), newest-first by creation
    date. Each entry: `version_label`, `created_at` (the version's first
    characterization snapshot), `is_current`, and — for bumped versions — the
    `change_type` + `actor` from the VERSIONING action (null for the initial
    1.0.0). A browse-surface read: module read privilege only, no per-asset
    MANAGE guard (same access as viewing the current snapshot).

    - **asset_id**: Unique asset id (404 if it doesn't exist / is inactive)
    """
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")
    return version_service.list_versions(session, asset_id)


@router.get(
    "/{asset_id}/versions/{version_label}/characterizations",
    response_model=List[Characterization],
)
def get_version_characterizations(
    asset_id: int, version_label: str, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> List[Characterization]:
    """
    The characterization snapshot of one specific version of an asset — what the
    Versions tab renders when a version row is expanded. Same browse-surface read
    gate as the version list. Returns `[]` for an unknown label (a valid "no
    rows" answer, not a 404).

    - **asset_id**: Unique asset id (404 if it doesn't exist / is inactive)
    - **version_label**: The semver label, e.g. `1.1.0`
    """
    asset = session.get(Asset, asset_id)
    if not asset or not asset.is_active:
        raise HTTPException(status_code=404, detail="Asset not found")
    return version_service.get_version_characterizations(
        session, asset_id, version_label)


@router.get("/{asset_id}", response_model=Asset)
def get(
    asset_id: int, session: Session = Depends(get_db_session),
    _: User = Depends(require_privilege("LIB", "ASSETS", can_edit=False))
) -> Asset:
    """
    Get an asset by its id.

    - **asset_id**: Unique asset id
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    elif not asset.is_active:
        raise HTTPException(status_code=400, detail=f"Asset with id '{asset_id}' is inactive")
    return asset


@router.post("/", response_model=Asset, status_code=201)
def create(
    asset: AssetCreate, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Create a new asset. The creator is auto-granted a USER/MANAGE permission
    (same as the propose flow) so the asset stays visible and editable to them
    under the caller-scoped repo listing.

    - **name**: Asset name (required)
    - **status**: Asset status (required)
    - **description**: Optional description
    - **category**: Category code (optional)
    - **reference**: Asset reference (optional)
    - **tags**: Asset tags in JSON format (optional)
    - **detail**: Asset detail (optional)
    - **is_active**: Active/inactive status (default: True)
    """
    # Validate that the category exists if provided
    if asset.category:
        category = session.get(Category, asset.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{asset.category}' does not exist"
            )

    try:
        db = Asset.model_validate(asset)
        session.add(db)
        session.flush()  # populate db.id for the grant row (same txn)
        session.add(AssetPermission(
            asset=db.id,
            target_type=permissions_service.SCOPE_USER,
            target_code=str(current.id),
            access_level=permissions_service.ACCESS_MANAGE,
        ))
        session.commit()
        session.refresh(db)
        logger.info(f"Asset created: {db.id}")
        return db
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating asset {asset.name}: {e}")
        raise HTTPException(
            status_code=409,
            detail="Asset could not be created due to a constraint violation"
        )


@router.put("/{asset_id}", response_model=Asset)
def update(
    asset_id: int, update: AssetUpdate, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Update an existing asset. Requires MANAGE on the asset (or superuser).

    - **asset_id**: Unique asset id to update
    - Only provided fields are updated
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    _ensure_manage(session, current, asset_id)

    # Validate that the category exists if provided
    if update.category is not None:
        category = session.get(Category, update.category)
        if not category:
            raise HTTPException(
                status_code=400,
                detail=f"Category with code '{update.category}' does not exist"
            )

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(asset, key, value)

    # Update timestamp
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset updated: {asset_id}")
    return asset


@router.delete("/{asset_id}", response_model=Asset, status_code=200)
def delete(
    asset_id: int, session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("LIB", "ASSETS", can_edit=True))
) -> Asset:
    """
    Delete an asset (logical delete). Requires MANAGE on the asset (or superuser).

    Performs a logical delete by setting is_active=False instead of removing the record.

    - **asset_id**: Unique asset id to delete
    """
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    _ensure_manage(session, current, asset_id)

    # Check if already inactive
    if not asset.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with id '{asset_id}' is already inactive"
        )

    # Logical delete: update is_active to False
    asset.is_active = False
    asset.updated_at = datetime.utcnow()

    session.add(asset)
    session.commit()
    session.refresh(asset)
    logger.info(f"Asset deactivated (logical delete): {asset_id}")
    return asset
