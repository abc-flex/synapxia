"""Diagnosis of the Initiative (HU-IN15) — the reviewer's decision.

Mirrors lib's ``review_service`` over `collaborations` (specs/005 research R8).
One transaction:
  1. writes the reviewer's score per criterion (`diagnostics.reviewer_score`;
     the proposer's `rationale` is left untouched),
  2. sets `initiatives.score` = Σ reviewer scores and the new status
     (ACCEPTED / REJECTED / FEEDBACK),
  3. records the reviewer's DIAGNOSIS as HANDLED,
  4. notifies the proposer with a PENDING ACCEPTANCE / REJECTION / MODIFICATION
     carrying the feedback in `content`.
Opening the diagnosis page writes nothing — viewing is not deciding.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .criteria_validation import validate_reviewer_answers
from .models import Collaboration, Diagnostic, Initiative, InitiativeDiagnoseRequest
from ...admin.internal.models import User
from ...internal.reviewers import is_eligible

logger = logging.getLogger(__name__)

STATUS_ACTIVATED = "ACTIVATED"
TYPE_ACTIVATION = "ACTIVATION"
TYPE_DIAGNOSIS = "DIAGNOSIS"
WF_PENDING = "PENDING"
WF_HANDLED = "HANDLED"

# decision → (new initiative status, collaboration type sent to the proposer)
DECISIONS = {
    "accept": ("ACCEPTED", "ACCEPTANCE"),
    "reject": ("REJECTED", "REJECTION"),
    "changes": ("FEEDBACK", "MODIFICATION"),
}
FEEDBACK_REQUIRED = ("reject", "changes")


class DiagnosisForbidden(Exception):
    """Caller is not an eligible reviewer, or holds no diagnosis assignment (→ 403)."""


class DiagnosisConflict(Exception):
    """The initiative is no longer awaiting a diagnosis (→ 409)."""


def proposer_id(session: Session, init_id: int) -> Optional[int]:
    """Author of the initiative's earliest ACTIVATION row."""
    row = session.exec(
        select(Collaboration).where(
            Collaboration.init == init_id,
            Collaboration.type == TYPE_ACTIVATION,
            Collaboration.is_active == True,  # noqa: E712
        ).order_by(Collaboration.created_at.asc(), Collaboration.id.asc())
    ).first()
    return row.user_id if row else None


def has_pending(session: Session, init_id: int, user_id: int, type_: str) -> bool:
    """Whether the user holds an active PENDING row of `type_` on the initiative
    (the assignment). The status precondition guards against double decisions."""
    return session.exec(
        select(Collaboration.id).where(
            Collaboration.init == init_id,
            Collaboration.user_id == user_id,
            Collaboration.type == type_,
            Collaboration.workflow_status == WF_PENDING,
            Collaboration.is_active == True,  # noqa: E712
        )
    ).first() is not None


def diagnose_initiative(
    session: Session, reviewer: User, init_id: int, data: InitiativeDiagnoseRequest,
) -> Initiative:
    decision = (data.decision or "").strip().lower()
    if decision not in DECISIONS:
        raise ValueError("Decision must be one of: accept, reject, changes.")
    initiative = session.get(Initiative, init_id)
    if not initiative or not initiative.is_active:
        raise ValueError(f"Initiative {init_id} does not exist or is inactive.")
    if not is_eligible(reviewer):
        raise DiagnosisForbidden("Only an eligible reviewer can diagnose an initiative.")
    if not has_pending(session, init_id, reviewer.id, TYPE_DIAGNOSIS):
        raise DiagnosisForbidden("You are not the assigned reviewer of this initiative.")
    if initiative.status != STATUS_ACTIVATED:
        raise DiagnosisConflict(
            f"Initiative {init_id} is '{initiative.status}', not awaiting a diagnosis.")
    answers = validate_reviewer_answers(session, data.answers)
    feedback = (data.feedback or "").strip() or None
    if decision in FEEDBACK_REQUIRED and not feedback:
        raise ValueError("Feedback is required to reject or request changes.")
    proposer = proposer_id(session, init_id)
    if proposer is None:
        raise ValueError(f"Initiative {init_id} has no proposer to notify.")

    new_status, proposer_type = DECISIONS[decision]
    now = datetime.utcnow()
    try:
        existing = {
            d.criteria: d for d in session.exec(
                select(Diagnostic).where(Diagnostic.init == init_id)).all()
        }
        for code, score in answers.items():
            row = existing.get(code)
            if row is None:
                # Should exist from the proposal; a criterion added later has no
                # proposer answer yet — record the reviewer's alone.
                row = Diagnostic(init=init_id, criteria=code, creator_score=score)
            row.reviewer_score = score
            row.updated_at = now
            session.add(row)

        initiative.score = sum(answers.values()) if answers else None
        initiative.status = new_status
        initiative.updated_at = now
        session.add(initiative)

        session.add(Collaboration(
            init=init_id, user_id=reviewer.id,
            type=TYPE_DIAGNOSIS, workflow_status=WF_HANDLED))
        session.add(Collaboration(
            init=init_id, user_id=proposer,
            type=proposer_type, workflow_status=WF_PENDING, content=feedback))
        session.commit()
        session.refresh(initiative)
    except IntegrityError:
        session.rollback()
        logger.error("Integrity error diagnosing initiative %s", init_id)
        raise

    logger.info("Initiative diagnosed: id=%s reviewer=%s decision=%s score=%s",
                init_id, reviewer.id, decision, initiative.score)
    return initiative
