"""Asset versioning service (HU-LI09, versioning half — deprecation is separate).

Saving an edit to an existing asset from the repo creates a NEW VERSION instead
of silently mutating history. The version lives on the same asset row
(``assets.current_version``); the characterizations are snapshotted per version
via ``characterizations.version_label`` — part of the table's primary key
``(asset, version_label, feature)`` — so every prior version keeps its full
characterization set untouched. In one transaction this service:
  1. bumps the semver label by the caller-chosen ``change_type``
     (major → X+1.0.0, minor → X.Y+1.0, patch → X.Y.Z+1),
  2. applies the core-field edits to the asset row,
  3. writes the new version's characterization rows at the new label
     (copying the current set forward when the request carries no ``values``),
  4. logs a VERSIONING/FINISHED action (a NEW ``actions`` row, never an
     update — matching propose/review/modify_service; the history timeline
     already localizes it as "created a new version").

Concurrent saves racing from the same label collide on the 3-column PK and the
loser gets a 409 via IntegrityError.
"""
import logging
import re
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Action, Asset, AssetVersion, Characterization, VersionRequest
from ...admin.internal.models import User
from ...taxo.internal.models import Category

logger = logging.getLogger(__name__)


class VersionConflict(Exception):
    """Version snapshot collided with an existing label (→ 409)."""


TYPE_VERSIONING = "VERSIONING"
WF_FINISHED = "FINISHED"

CHANGE_TYPES = ("major", "minor", "patch")
DEFAULT_LABEL = "1.0.0"

# Asset columns a version save may edit. `category` is included because the
# repo's edit modal already lets the user change it (unlike the review-loop's
# resubmit, which locks it).
EDITABLE_FIELDS = (
    "name", "description", "category", "reference", "status", "tags", "detail")

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump_label(label: Optional[str], change_type: str) -> str:
    """Return the next semver label for ``change_type``.

    A missing/malformed ``label`` is treated as the ``1.0.0`` base so legacy
    rows (NULL ``current_version``) version cleanly.
    """
    if change_type not in CHANGE_TYPES:
        raise ValueError(
            f"change_type must be one of {', '.join(CHANGE_TYPES)}.")
    match = _SEMVER.match((label or "").strip())
    major, minor, patch = (
        (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if match else (1, 0, 0)
    )
    if change_type == "major":
        return f"{major + 1}.0.0"
    if change_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def create_version(
    session: Session,
    user: User,
    asset_id: int,
    data: VersionRequest,
) -> Asset:
    """Apply the edits and save them as a new version of the asset, atomically.

    Returns the updated asset. Raises ``ValueError`` (400; "not found" → 404
    in the route) for a missing/inactive asset, bad ``change_type`` or unknown
    ``category``, and ``VersionConflict`` (409) when the new label already
    exists (e.g. two concurrent saves).
    """
    asset = session.get(Asset, asset_id)
    if not asset or asset.is_active is False:
        raise ValueError(f"Asset '{asset_id}' not found.")

    old_label = (asset.current_version or "").strip() or DEFAULT_LABEL
    new_label = bump_label(old_label, data.change_type)

    updates = data.model_dump(exclude_unset=True, exclude={"change_type", "values"})
    if updates.get("category"):
        if not session.get(Category, updates["category"]):
            raise ValueError(f"Category '{updates['category']}' does not exist.")

    # The current version's characterization set — the snapshot source.
    current_chars = session.exec(
        select(Characterization).where(
            Characterization.asset == asset_id,
            Characterization.version_label == old_label,
            Characterization.is_active == True,  # noqa: E712
        )
    ).all()
    by_feature = {c.feature: c for c in current_chars}

    now = datetime.utcnow()
    try:
        # 1. Core-field edits on the asset row.
        for key in EDITABLE_FIELDS:
            if key in updates:
                setattr(asset, key, updates[key])
        # 2. The new version's characterization rows. ``values`` is the FULL
        #    desired set (blank/omitted feature = not carried = delete); when
        #    absent (core-only save) the current set is copied unchanged.
        if data.values is None:
            snapshot = {
                feature: (char.value, char.detail)
                for feature, char in by_feature.items()
            }
        else:
            snapshot = {}
            for feature, value in data.values.items():
                if value is None or not str(value).strip():
                    continue
                old = by_feature.get(feature)
                snapshot[feature] = (value, old.detail if old else None)
        for feature, (value, detail) in snapshot.items():
            session.add(Characterization(
                asset=asset_id, feature=feature, version_label=new_label,
                value=value, detail=detail))
        # 3. Flip the asset to the new version.
        asset.current_version = new_label
        asset.updated_at = now
        session.add(asset)
        # 4. Log the versioning event (self-service — straight to FINISHED,
        #    no reviewer assignment, per docs/user-stories/states-and-types.md).
        session.add(Action(
            asset=asset_id, user_id=user.id,
            type=TYPE_VERSIONING, workflow_status=WF_FINISHED,
            content=new_label,
            detail=f"{old_label} -> {new_label} ({data.change_type})"))
        session.commit()
        session.refresh(asset)
    except IntegrityError as exc:
        session.rollback()
        logger.error(
            "Integrity error versioning asset %s (%s -> %s): %s",
            asset_id, old_label, new_label, exc)
        raise VersionConflict(
            f"Version '{new_label}' already exists for asset '{asset_id}'."
        ) from exc

    logger.info(
        "Asset versioned: id=%s %s -> %s (%s) by user=%s",
        asset_id, old_label, new_label, data.change_type, user.id,
    )
    return asset


# Parses the change type out of a VERSIONING action's `detail`, which
# create_version writes as "<old> -> <new> (<change_type>)".
_DETAIL_CHANGE_TYPE = re.compile(r"\(([^)]+)\)\s*$")


def list_versions(session: Session, asset_id: int) -> List[AssetVersion]:
    """The asset's version history, newest-first by creation date (read side).

    The label + its date come from a DISTINCT/GROUP BY over the asset's active
    characterizations (``MIN(created_at)`` per ``version_label``); each row is
    then enriched from the matching VERSIONING action (``content == label``) for
    the change type + actor — the initial ``1.0.0`` has no versioning action, so
    those stay ``None``. Returns ``[]`` for a missing asset (the route 404s).
    """
    asset = session.get(Asset, asset_id)
    if not asset or asset.is_active is False:
        return []

    # DISTINCT query: one row per version_label with its first-seen timestamp.
    rows = session.exec(
        select(
            Characterization.version_label,
            func.min(Characterization.created_at),
        )
        .where(
            Characterization.asset == asset_id,
            Characterization.is_active == True,  # noqa: E712
        )
        .group_by(Characterization.version_label)
    ).all()

    # Enrich from the VERSIONING actions (one per bump; keyed by new label in
    # `content`). Resolve actor usernames in one batched lookup — no N+1.
    actions = session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.type == TYPE_VERSIONING,
            Action.is_active == True,  # noqa: E712
        )
    ).all()
    user_ids = {a.user_id for a in actions if a.user_id is not None}
    names: dict = {}
    if user_ids:
        for u in session.exec(select(User).where(User.id.in_(user_ids))).all():
            names[u.id] = u.username
    meta_by_label: dict = {}
    for a in actions:
        if not a.content:
            continue
        m = _DETAIL_CHANGE_TYPE.search(a.detail or "")
        meta_by_label[a.content] = (
            m.group(1) if m else None,
            names.get(a.user_id),
        )

    current = (asset.current_version or DEFAULT_LABEL)
    out: List[AssetVersion] = []
    for label, created_at in rows:
        change_type, actor = meta_by_label.get(label, (None, None))
        out.append(AssetVersion(
            version_label=label,
            created_at=created_at,
            is_current=(label == current),
            change_type=change_type,
            actor=actor,
        ))
    # Newest first by the version's creation date (the user's "based on the
    # version date"); ties broken by label so the order is deterministic.
    out.sort(key=lambda v: (v.created_at, v.version_label), reverse=True)
    return out


def get_version_characterizations(
    session: Session, asset_id: int, version_label: str,
) -> List[Characterization]:
    """The active characterization rows for one specific version of an asset —
    the snapshot the UI renders when a version row is expanded. Empty list for
    an unknown label (a valid "no rows" answer)."""
    return session.exec(
        select(Characterization).where(
            Characterization.asset == asset_id,
            Characterization.version_label == version_label,
            Characterization.is_active == True,  # noqa: E712
        )
    ).all()
