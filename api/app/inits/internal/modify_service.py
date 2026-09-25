"""Modify Initiative (HU-IN16) — the proposer's resubmission after a change request.

Mirrors lib's ``modify_service`` over `collaborations` (specs/005 research R9).
One transaction:
  1. applies the sent core fields and upserts the proposer's answers,
  2. records the proposer's MODIFICATION as HANDLED,
  3. returns the initiative to ACTIVATED,
  4. re-arms the reviewer who requested the changes (newest DIAGNOSIS row's
     user) with a new PENDING DIAGNOSIS.
The previous round's reviewer scores are kept until the next diagnosis
overwrites them. The loop is unlimited. Opening the page writes nothing.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .criteria_validation import validate_creator_answers
from .diagnosis_service import has_pending, proposer_id
from .list_validation import REQUIRED_FIELDS, validate_core_fields
from .models import Collaboration, Diagnostic, Initiative, InitiativeResubmitRequest
from ...admin.internal.models import User

logger = logging.getLogger(__name__)

STATUS_FEEDBACK = "FEEDBACK"
STATUS_ACTIVATED = "ACTIVATED"
TYPE_DIAGNOSIS = "DIAGNOSIS"
TYPE_MODIFICATION = "MODIFICATION"
WF_PENDING = "PENDING"
WF_HANDLED = "HANDLED"
EDITABLE_FIELDS = (
    "name", "description", "type", "expected_impact", "priority_level",
    "reference", "tags", "detail",
)


class ModifyForbidden(Exception):
    """Caller is not the proposer or holds no change request (→ 403)."""


class ModifyConflict(Exception):
    """The initiative is not awaiting changes (→ 409)."""


def _last_reviewer(session: Session, init_id: int) -> Optional[int]:
    row = session.exec(
        select(Collaboration).where(
            Collaboration.init == init_id,
            Collaboration.type == TYPE_DIAGNOSIS,
            Collaboration.is_active == True,  # noqa: E712
        ).order_by(Collaboration.created_at.desc(), Collaboration.id.desc())
    ).first()
    return row.user_id if row else None


def resubmit_initiative(
    session: Session, proposer: User, init_id: int, data: InitiativeResubmitRequest,
) -> Initiative:
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise ValueError(f"Initiative {init_id} does not exist or is inactive.")
    if not has_pending(session, init_id, proposer.id, TYPE_MODIFICATION):
        raise ModifyForbidden("There is no change request for you on this initiative.")
    if proposer_id(session, init_id) != proposer.id:
        raise ModifyForbidden("Only the initiative's proposer can resubmit it.")
    if initiative.status != STATUS_FEEDBACK:
        raise ModifyConflict(
            f"Initiative {init_id} is '{initiative.status}', not awaiting changes.")

    updates = data.model_dump(exclude_unset=True, include=set(EDITABLE_FIELDS))
    validate_core_fields(session, updates, required=REQUIRED_FIELDS)
    answers = (
        validate_creator_answers(session, data.answers)
        if data.answers is not None else None
    )
    reviewer_id = _last_reviewer(session, init_id)
    if reviewer_id is None:
        raise ValueError(f"Initiative {init_id} has no reviewer to re-notify.")

    now = datetime.utcnow()
    try:
        for key, value in updates.items():
            setattr(initiative, key, value.strip() if key == "name" else value)
        initiative.status = STATUS_ACTIVATED
        initiative.updated_at = now
        session.add(initiative)

        if answers is not None:
            existing = {
                d.criteria: d for d in session.exec(
                    select(Diagnostic).where(Diagnostic.init == init_id)).all()
            }
            for code, answer in answers.items():
                row = existing.get(code) or Diagnostic(
                    init=init_id, criteria=code, creator_score=answer.score)
                row.creator_score = answer.score
                row.rationale = answer.rationale
                row.updated_at = now
                session.add(row)

        session.add(Collaboration(
            init=init_id, user_id=proposer.id,
            type=TYPE_MODIFICATION, workflow_status=WF_HANDLED))
        session.add(Collaboration(
            init=init_id, user_id=reviewer_id,
            type=TYPE_DIAGNOSIS, workflow_status=WF_PENDING))
        session.commit()
        session.refresh(initiative)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error resubmitting initiative %s", init_id)
        raise

    logger.info("Initiative resubmitted: id=%s proposer=%s reviewer=%s",
                init_id, proposer.id, reviewer_id)
    return initiative
