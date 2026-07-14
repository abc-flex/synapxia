"""Asset review service (HU-Review) — the reviewer's decision step of the workflow.

Per docs/user-stories/lib-status.md ("HU-Review"), when the assigned reviewer
approves / rejects / requests changes on a PROPOSED asset, one transaction:
  1. closes the reviewer's assignment — inserts a REVIEW action (FINISHED),
  2. sets the asset status → PUBLISHED / REJECTED / FEEDBACK respectively,
  3. notifies the proposer — inserts a new action for the proposer of type
     PUBLICATION / REJECTION / MODIFICATION (ASSIGNED), carrying the reviewer's
     feedback in ``content`` (Show Action renders it).

Every workflow transition is a NEW ``actions`` row (never an update), matching
propose_service. No new table.
"""
import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Asset, Action
from .propose_service import _is_eligible
from ...admin.internal.models import User

logger = logging.getLogger(__name__)


class ReviewForbidden(Exception):
    """Reviewer is not eligible or not the assignee (→ 403)."""


class ReviewConflict(Exception):
    """Asset is not awaiting review — already decided (→ 409)."""


STATUS_PROPOSED = "PROPOSED"
TYPE_REVIEW = "REVIEW"
TYPE_PROPOSAL = "PROPOSAL"
WF_ASSIGNED = "ASSIGNED"
WF_NOTIFIED = "NOTIFIED"
WF_FINISHED = "FINISHED"

# decision → (new asset status, action type raised for the proposer)
DECISIONS = {
    "approve": ("PUBLISHED", "PUBLICATION"),
    "reject": ("REJECTED", "REJECTION"),
    "changes": ("FEEDBACK", "MODIFICATION"),
}


def review_asset(
    session: Session,
    reviewer: User,
    asset_id: int,
    decision: str,
    feedback: Optional[str] = None,
) -> Asset:
    """Record a reviewer's decision on a PROPOSED asset, atomically.

    Returns the updated asset. Raises ValueError for validation / authorization
    problems; the route maps them to 400/403/409. Re-raises IntegrityError after
    rollback (→ 409).
    """
    if decision not in DECISIONS:
        raise ValueError(
            "decision must be one of: approve, reject, changes."
        )
    new_status, proposer_type = DECISIONS[decision]

    asset = session.get(Asset, asset_id)
    if not asset or asset.is_active is False:
        raise ValueError(f"Asset '{asset_id}' not found.")

    # Only an eligible reviewer who holds the open REVIEW assignment may decide.
    if not _is_eligible(reviewer):
        raise ReviewForbidden(
            "Only an administrator, a REVIEWER, or a superuser can review assets."
        )
    assignment = session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.user_id == reviewer.id,
            Action.type == TYPE_REVIEW,
            Action.workflow_status.in_((WF_ASSIGNED, WF_NOTIFIED)),  # type: ignore[attr-defined]
            Action.is_active == True,  # noqa: E712
        )
    ).first()
    if not assignment:
        raise ReviewForbidden(
            "You are not the assigned reviewer for this asset."
        )

    # The asset must still be awaiting review (guards against double-submit).
    if asset.status != STATUS_PROPOSED:
        raise ReviewConflict(
            f"Asset '{asset_id}' is not awaiting review (status={asset.status})."
        )

    # The proposer is the author of the asset's PROPOSAL action.
    proposal = session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.type == TYPE_PROPOSAL,
        ).order_by(Action.id)
    ).first()
    if not proposal:
        raise ValueError(f"Asset '{asset_id}' has no proposal to review.")
    proposer_id = proposal.user_id

    note = (feedback or "").strip() or None

    try:
        # 1. Close the reviewer's assignment.
        session.add(Action(
            asset=asset_id, user_id=reviewer.id,
            type=TYPE_REVIEW, workflow_status=WF_FINISHED))
        # 2. Flip the asset status.
        asset.status = new_status
        session.add(asset)
        # 3. Notify the proposer with the outcome + feedback.
        session.add(Action(
            asset=asset_id, user_id=proposer_id,
            type=proposer_type, workflow_status=WF_ASSIGNED, content=note))
        session.commit()
        session.refresh(asset)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error reviewing asset %s (reviewer=%s)", asset_id, reviewer.id)
        raise

    logger.info(
        "Asset reviewed: id=%s reviewer=%s decision=%s status=%s proposer=%s",
        asset_id, reviewer.id, decision, new_status, proposer_id,
    )
    return asset
