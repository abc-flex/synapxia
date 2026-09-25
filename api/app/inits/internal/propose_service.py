"""Initiative proposal (HU-IN05) — the entry point of the diagnosis workflow.

Proposing an initiative is all-or-nothing (spec FR-021, research R3). One
transaction inserts:
  1. the initiative (status ACTIVATED),
  2. one diagnostics row per active criterion (the proposer's `creator_score`
     and rationale),
  3. the staged initiative ↔ asset links (asset_inits),
  4. an ACTIVATION collaboration (HANDLED) for the proposer,
  5. a DIAGNOSIS collaboration (PENDING) for the reviewer,
  6. USER/MANAGE init_permissions for the proposer and the reviewer.

Unlike the asset wizard — which saves its related links with separate calls
after the proposal — the links travel inside this transaction, so a failure can
never leave a proposal without them. Every check runs before the first write.
"""
import logging
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from .criteria_validation import validate_creator_answers
from .list_validation import REQUIRED_FIELDS, validate_core_fields, validate_list_value
from .models import (
    Collaboration, Diagnostic, InitPermission, Initiative, InitiativeProposeRequest,
    ProposeAssetLink,
)
from ...admin.internal.models import User
from ...internal.reviewers import resolve_reviewer
from ...lib.internal import permissions_service as asset_permissions
from ...lib.internal.models import Asset, AssetInit

logger = logging.getLogger(__name__)

STATUS_ACTIVATED = "ACTIVATED"
TYPE_ACTIVATION = "ACTIVATION"
TYPE_DIAGNOSIS = "DIAGNOSIS"
WF_HANDLED = "HANDLED"
WF_PENDING = "PENDING"
TARGET_USER = "USER"
ACCESS_MANAGE = "MANAGE"


def _validate_assets(session: Session, user: User, links: List[ProposeAssetLink]) -> None:
    """Each linked asset must be active and visible to the proposer; each
    relation type must exist; the same (asset, type) may appear once."""
    seen = set()
    for link in links:
        key = (link.asset, link.type)
        if key in seen:
            raise ValueError(
                f"Asset {link.asset} is linked more than once with type '{link.type}'.")
        seen.add(key)
        validate_list_value(session, "RELATION_TYPE", link.type)
        asset = session.get(Asset, link.asset)
        if not asset or not asset.is_active:
            raise ValueError(f"Asset {link.asset} does not exist or is inactive.")
        if not getattr(user, "is_superuser", False) and asset_permissions.user_asset_access(
                session, user, link.asset) is None:
            # Same message as a missing asset: a proposal must not reveal assets
            # the proposer cannot see.
            raise ValueError(f"Asset {link.asset} does not exist or is inactive.")


def propose_initiative(
    session: Session, proposer: User, data: InitiativeProposeRequest,
) -> Initiative:
    """Create an initiative proposal and its diagnosis-workflow records atomically.

    Raises ValueError on any validation problem (→ 400, nothing written) and
    re-raises IntegrityError after rollback (→ 409).
    """
    fields = data.model_dump(include={
        "name", "description", "type", "expected_impact", "priority_level",
        "reference", "tags", "detail"})
    validate_core_fields(session, fields, required=REQUIRED_FIELDS)
    answers = validate_creator_answers(session, data.answers)
    reviewer = resolve_reviewer(session, data.reviewer_id, proposer=proposer)
    _validate_assets(session, proposer, data.assets)

    try:
        initiative = Initiative(
            **{**fields, "name": fields["name"].strip()},
            status=STATUS_ACTIVATED,
        )
        session.add(initiative)
        session.flush()  # populate initiative.id for the dependent rows

        for code, answer in answers.items():
            session.add(Diagnostic(
                init=initiative.id, criteria=code,
                creator_score=answer.score, rationale=answer.rationale))

        for link in data.assets:
            session.add(AssetInit(
                asset=link.asset, init=initiative.id, type=link.type,
                rationale=(link.rationale or "").strip() or None))

        session.add(Collaboration(
            init=initiative.id, user_id=proposer.id,
            type=TYPE_ACTIVATION, workflow_status=WF_HANDLED))
        session.add(Collaboration(
            init=initiative.id, user_id=reviewer.id,
            type=TYPE_DIAGNOSIS, workflow_status=WF_PENDING))

        # MANAGE for proposer + reviewer (one row when an admin self-reviews).
        for target_id in {proposer.id, reviewer.id}:
            session.add(InitPermission(
                init=initiative.id, target_type=TARGET_USER,
                target_code=str(target_id), access_level=ACCESS_MANAGE))

        session.commit()
        session.refresh(initiative)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error proposing initiative (proposer=%s)", proposer.id)
        raise

    logger.info(
        "Initiative proposed: id=%s proposer=%s reviewer=%s answers=%d assets=%d",
        initiative.id, proposer.id, reviewer.id, len(answers), len(data.assets))
    return initiative
