"""Asset proposal service (HU-Propose) — the entry point of the review workflow.

Per docs/user-stories/lib-status.md, proposing an asset is an all-or-nothing
operation that, in a single transaction, inserts:
  1. the asset (status PROPOSED),
  2. one characterization per feature in the category's specifications,
  3. a PROPOSAL action (HANDLED) for the proposer,
  4. a REVIEW action (PENDING) for a reviewer (an administrative or REVIEWER user),
  5. MANAGE asset_permissions for the proposer and the reviewer.

Step 4 is the action the notifications menu (HU-LI11) surfaces to the reviewer —
this service is what finally makes those notifications appear. No new table:
every row goes into an existing table (assets / characterizations / actions /
asset_permissions).
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Asset, Characterization, Action, AssetPermission, ProposeRequest
from ...taxo.internal.models import Specification, Category
from ...admin.internal.models import User
# Reviewer eligibility is shared with the initiatives' diagnosis workflow, so it
# lives in app/internal/reviewers.py (specs/005-explore-initiatives R2). The names
# are re-exported here so existing imports keep working unchanged.
from ...internal.reviewers import (  # noqa: F401
    ADMIN_PROFILES, REVIEWER_PROFILES, is_admin, is_eligible, list_reviewers,
    resolve_reviewer,
)
_is_eligible = is_eligible  # historical private name, still imported by review_service

logger = logging.getLogger(__name__)

STATUS_PROPOSED = "PROPOSED"
TYPE_PROPOSAL = "PROPOSAL"
TYPE_REVIEW = "REVIEW"
WF_HANDLED = "HANDLED"
WF_PENDING = "PENDING"
TARGET_USER = "USER"
ACCESS_MANAGE = "MANAGE"


def propose_asset(session: Session, proposer_id: int, data: ProposeRequest) -> Asset:
    """Create an asset proposal and its review-workflow records atomically.

    Returns the created (PROPOSED) asset. Raises ValueError on validation
    problems (→ 400) and re-raises IntegrityError after rollback (→ 409).
    """
    if not (data.name or "").strip():
        raise ValueError("Asset name must not be empty.")
    if not data.category or not session.get(Category, data.category):
        raise ValueError(f"Category '{data.category}' does not exist.")

    # Resolve the reviewer before any write so a bad reviewer fails cleanly.
    proposer = session.get(User, proposer_id)
    reviewer = resolve_reviewer(session, data.reviewer_id, proposer=proposer)
    overrides: Dict[str, str] = data.values or {}
    detail_overrides: Dict[str, str] = data.details or {}

    try:
        asset = Asset(
            name=data.name,
            description=data.description,
            category=data.category,
            reference=data.reference,
            tags=data.tags,
            detail=data.detail,
            status=STATUS_PROPOSED,
        )
        session.add(asset)
        session.flush()  # populate asset.id for the dependent rows (no commit yet)

        # 2. One characterization per active spec feature of the category.
        specs = session.exec(
            select(Specification).where(
                Specification.category == data.category,
                Specification.is_active == True,  # noqa: E712
            )
        ).all()
        for spec in specs:
            session.add(Characterization(
                asset=asset.id,
                feature=spec.feature,
                value=overrides.get(spec.feature, spec.default_value),
                detail=(detail_overrides.get(spec.feature) or "").strip() or None,
            ))

        # 3 + 4. Proposal (finished) + review assignment (assigned).
        session.add(Action(
            asset=asset.id, user_id=proposer_id,
            type=TYPE_PROPOSAL, workflow_status=WF_HANDLED))
        session.add(Action(
            asset=asset.id, user_id=reviewer.id,
            type=TYPE_REVIEW, workflow_status=WF_PENDING))

        # 5. MANAGE permission for proposer + reviewer (deduped if they coincide).
        for target_id in {proposer_id, reviewer.id}:
            session.add(AssetPermission(
                asset=asset.id, target_type=TARGET_USER,
                target_code=str(target_id), access_level=ACCESS_MANAGE))

        session.commit()
        session.refresh(asset)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error proposing asset (proposer=%s)", proposer_id)
        raise

    logger.info(
        "Asset proposed: id=%s proposer=%s reviewer=%s specs=%d",
        asset.id, proposer_id, reviewer.id, len(specs))
    return asset
