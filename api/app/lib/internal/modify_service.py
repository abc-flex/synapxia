"""Asset modify/resubmit service (HU-Modify) — the proposer's step after a
reviewer requested changes.

Per docs/user-stories/lib-status.md ("HU-Modify") + 04-lib.md (HU-LI14), when the
reviewer picks "request changes" the asset goes to FEEDBACK and the proposer gets
a MODIFICATION/ASSIGNED action carrying the feedback in ``content``. This service
is the resubmit: the proposer edits the asset + its characterizations and sends it
back for re-review. In one transaction it:
  1. updates the asset's editable fields + its characterizations,
  2. closes the proposer's assignment — inserts a MODIFICATION/FINISHED action,
  3. sets the asset status back to PROPOSED (so HU-Review can accept it again —
     ``review_service`` guards ``status == "PROPOSED"``; there is no dedicated
     "resubmitted" status in the ASSET_STATUS enum),
  4. re-arms the loop — inserts a fresh REVIEW/ASSIGNED action for the original
     reviewer (the one chosen at propose time).

Every workflow transition is a NEW ``actions`` row (never an update), matching
propose_service / review_service. No new table.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .models import Action, Asset, Characterization, ModifyRequest
from . import actions_service
from ...admin.internal.models import User

logger = logging.getLogger(__name__)


class ModifyForbidden(Exception):
    """Caller is not the proposer holding the open MODIFICATION assignment (→ 403)."""


class ModifyConflict(Exception):
    """Asset is not awaiting modification — not in FEEDBACK (→ 409)."""


STATUS_FEEDBACK = "FEEDBACK"
STATUS_PROPOSED = "PROPOSED"
TYPE_REVIEW = "REVIEW"
TYPE_PROPOSAL = "PROPOSAL"
TYPE_MODIFICATION = "MODIFICATION"
WF_ASSIGNED = "ASSIGNED"
WF_NOTIFIED = "NOTIFIED"
WF_FINISHED = "FINISHED"

# Asset columns the proposer may edit on resubmit (category is intentionally
# excluded — it drives the spec/characterization set).
EDITABLE_FIELDS = ("name", "description", "reference", "tags", "detail")


def resubmit_asset(
    session: Session,
    proposer: User,
    asset_id: int,
    data: ModifyRequest,
) -> Asset:
    """Apply the proposer's edits and resubmit the asset for re-review, atomically.

    Returns the updated asset. Raises ``ModifyForbidden`` (403) if the caller
    isn't the proposer with an open MODIFICATION assignment, ``ModifyConflict``
    (409) if the asset isn't awaiting modification, or ``ValueError`` (400) for
    missing asset / no reviewer to re-notify. Re-raises IntegrityError after
    rollback (→ 409).
    """
    asset = session.get(Asset, asset_id)
    if not asset or asset.is_active is False:
        raise ValueError(f"Asset '{asset_id}' not found.")

    # The caller must hold the open MODIFICATION assignment for this asset — this
    # is the "is this the proposer being asked to modify?" gate (mirrors the
    # reviewer-assignment check in review_service).
    assignment = session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.user_id == proposer.id,
            Action.type == TYPE_MODIFICATION,
            Action.workflow_status.in_((WF_ASSIGNED, WF_NOTIFIED)),  # type: ignore[attr-defined]
            Action.is_active == True,  # noqa: E712
        )
    ).first()
    if not assignment:
        raise ModifyForbidden(
            "You are not the proposer assigned to modify this asset."
        )

    # Belt-and-suspenders: confirm the caller authored the original proposal.
    proposal = session.exec(
        select(Action).where(
            Action.asset == asset_id,
            Action.type == TYPE_PROPOSAL,
        ).order_by(Action.id)
    ).first()
    if not proposal or proposal.user_id != proposer.id:
        raise ModifyForbidden(
            "Only the original proposer can modify this asset."
        )

    # The asset must still be awaiting modification (guards against double-submit).
    if asset.status != STATUS_FEEDBACK:
        raise ModifyConflict(
            f"Asset '{asset_id}' is not awaiting modification (status={asset.status})."
        )

    # Re-notify the same reviewer who handled the previous cycle. All REVIEW
    # actions for the asset carry the same reviewer id; take the newest.
    review_actions = actions_service.list_actions_for_asset(
        session, asset_id, type=TYPE_REVIEW)
    if not review_actions:
        raise ValueError(f"Asset '{asset_id}' has no reviewer to re-notify.")
    reviewer_id = review_actions[0].user_id

    now = datetime.utcnow()
    updates = data.model_dump(exclude_unset=True, exclude={"values"})

    try:
        # 1. Update the asset's editable fields.
        changed = False
        for key in EDITABLE_FIELDS:
            if key in updates:
                setattr(asset, key, updates[key])
                changed = True
        # 2. Update characterizations in place (create any missing row).
        for feature, value in (data.values or {}).items():
            char = session.exec(
                select(Characterization).where(
                    Characterization.asset == asset_id,
                    Characterization.feature == feature,
                )
            ).first()
            if char:
                char.value = value
                char.updated_at = now
                session.add(char)
            else:
                session.add(Characterization(
                    asset=asset_id, feature=feature, value=value))
        # 3. Close the proposer's MODIFICATION assignment.
        session.add(Action(
            asset=asset_id, user_id=proposer.id,
            type=TYPE_MODIFICATION, workflow_status=WF_FINISHED))
        # 4. Send the asset back into review.
        asset.status = STATUS_PROPOSED
        if changed:
            asset.updated_at = now
        session.add(asset)
        # 5. Re-arm the reviewer's assignment.
        session.add(Action(
            asset=asset_id, user_id=reviewer_id,
            type=TYPE_REVIEW, workflow_status=WF_ASSIGNED))
        session.commit()
        session.refresh(asset)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error resubmitting asset %s (proposer=%s)", asset_id, proposer.id)
        raise

    logger.info(
        "Asset resubmitted: id=%s proposer=%s reviewer=%s status=%s",
        asset_id, proposer.id, reviewer_id, STATUS_PROPOSED,
    )
    return asset
