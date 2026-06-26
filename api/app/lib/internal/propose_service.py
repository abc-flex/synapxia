"""Asset proposal service (HU-Propose) — the entry point of the review workflow.

Per docs/user-stories/lib-status.md, proposing an asset is an all-or-nothing
operation that, in a single transaction, inserts:
  1. the asset (status PROPOSED),
  2. one characterization per feature in the category's specifications,
  3. a PROPOSAL action (FINISHED) for the proposer,
  4. a REVIEW action (ASSIGNED) for a reviewer (an ADMINISTRATIVE user),
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

logger = logging.getLogger(__name__)

# The profile a reviewer must have (db/sql/12-admin-insert.sql).
REVIEWER_PROFILE = "ADMINISTRATIVE"

STATUS_PROPOSED = "PROPOSED"
TYPE_PROPOSAL = "PROPOSAL"
TYPE_REVIEW = "REVIEW"
WF_FINISHED = "FINISHED"
WF_ASSIGNED = "ASSIGNED"
TARGET_USER = "USER"
ACCESS_MANAGE = "MANAGE"


def list_reviewers(session: Session) -> List[User]:
    """Active users eligible to review (ADMINISTRATIVE profile), id order."""
    return session.exec(
        select(User)
        .where(User.profile == REVIEWER_PROFILE, User.is_active == True)  # noqa: E712
        .order_by(User.id)
    ).all()


def resolve_reviewer(session: Session, reviewer_id: Optional[int]) -> User:
    """Resolve the reviewer for a proposal: the requested user (which must be an
    active ADMINISTRATIVE user) or, when none is requested, the first eligible
    one. Raises ValueError if the requested reviewer is invalid or none exist."""
    if reviewer_id is not None:
        user = session.get(User, reviewer_id)
        if not user or not user.is_active:
            raise ValueError(f"Reviewer '{reviewer_id}' not found or inactive.")
        if user.profile != REVIEWER_PROFILE:
            raise ValueError("Reviewer must have the ADMINISTRATIVE profile.")
        return user
    eligible = list_reviewers(session)
    if not eligible:
        raise ValueError("No reviewer with the ADMINISTRATIVE profile is available.")
    return eligible[0]


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
    reviewer = resolve_reviewer(session, data.reviewer_id)
    overrides: Dict[str, str] = data.values or {}

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
            ))

        # 3 + 4. Proposal (finished) + review assignment (assigned).
        session.add(Action(
            asset=asset.id, user_id=proposer_id,
            type=TYPE_PROPOSAL, workflow_status=WF_FINISHED))
        session.add(Action(
            asset=asset.id, user_id=reviewer.id,
            type=TYPE_REVIEW, workflow_status=WF_ASSIGNED))

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
