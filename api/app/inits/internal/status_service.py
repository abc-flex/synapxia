"""Initiative-status policy for the Initiative Management surface + its trail.

Initiative Management is the *owner's* surface, not the propose/diagnose
workflow. Only the post-acceptance moves belong to the owner, and each one is
recorded on the ``collaborations`` substrate so it shows up in the initiative's
history (never a new table):

  ACCEPTED    → IN_PROGRESS   KICKOFF
  ACCEPTED    → DELIVERED     DELIVERY
  ACCEPTED    → ARCHIVED      ARCHIVING
  IN_PROGRESS → DELIVERED     DELIVERY
  IN_PROGRESS → ARCHIVED      ARCHIVING
  DELIVERED   → ARCHIVED      ARCHIVING

Every other change from this surface is refused (→ 400): ACTIVATED / FEEDBACK /
ACCEPTED / REJECTED are set by proposing, diagnosing and modifying.

Rows are written HANDLED — self-service events with nothing owed to anybody
(no notice for the proposer, by product decision), mirroring lib's
status_service for DEPRECATION.
"""
import logging
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session

from .models import Collaboration
from ...internal.status import normalize

logger = logging.getLogger(__name__)


class StatusTransitionForbidden(ValueError):
    """A status change this surface does not allow (→ 400)."""


STATUS_ACTIVATED = "ACTIVATED"
STATUS_FEEDBACK = "FEEDBACK"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_REJECTED = "REJECTED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_DELIVERED = "DELIVERED"
STATUS_ARCHIVED = "ARCHIVED"

TYPE_KICKOFF = "KICKOFF"
TYPE_DELIVERY = "DELIVERY"
TYPE_ARCHIVING = "ARCHIVING"
WF_HANDLED = "HANDLED"

# (current, new) → collaboration type logged. Anything absent here is refused.
ALLOWED_TRANSITIONS: Dict[Tuple[str, str], str] = {
    (STATUS_ACCEPTED, STATUS_IN_PROGRESS): TYPE_KICKOFF,
    (STATUS_ACCEPTED, STATUS_DELIVERED): TYPE_DELIVERY,
    (STATUS_ACCEPTED, STATUS_ARCHIVED): TYPE_ARCHIVING,
    (STATUS_IN_PROGRESS, STATUS_DELIVERED): TYPE_DELIVERY,
    (STATUS_IN_PROGRESS, STATUS_ARCHIVED): TYPE_ARCHIVING,
    (STATUS_DELIVERED, STATUS_ARCHIVED): TYPE_ARCHIVING,
}

# Display order of targets, following the lifecycle.
_ORDER = [STATUS_IN_PROGRESS, STATUS_DELIVERED, STATUS_ARCHIVED]


def allowed_targets(current: Optional[str]) -> List[str]:
    """The statuses an owner may move to from ``current`` (may be empty)."""
    code = normalize(current)
    targets = {new for (cur, new) in ALLOWED_TRANSITIONS if cur == code}
    return [s for s in _ORDER if s in targets]


def allowed_statuses_for(current: Optional[str]) -> List[str]:
    """What the status control may offer: the current status, then its moves.
    A single entry means the control is locked."""
    return [normalize(current), *allowed_targets(current)]


def validate_transition(current: Optional[str], new: Optional[str]) -> Optional[str]:
    """Return the collaboration type to log for this status change.

    ``None`` when the status is unchanged or blank (the edit dialog always
    sends the field). Raises StatusTransitionForbidden for any other move.
    """
    current_code, new_code = normalize(current), normalize(new)
    if not new_code or current_code == new_code:
        return None
    collab_type = ALLOWED_TRANSITIONS.get((current_code, new_code))
    if collab_type is None:
        raise StatusTransitionForbidden(
            f"Status transition {current_code} → {new_code} is not allowed. "
            "From Initiative Management an initiative can only move "
            "ACCEPTED → IN_PROGRESS/DELIVERED/ARCHIVED, IN_PROGRESS → "
            "DELIVERED/ARCHIVED or DELIVERED → ARCHIVED; every other status "
            "belongs to the propose/diagnose workflow."
        )
    return collab_type


def log_status_collaboration(
    session: Session, init_id: int, user_id: int, collab_type: str,
) -> Collaboration:
    """Stage the history row for a status change (HANDLED — nothing is owed).

    Added to the session but NOT committed: the caller owns the transaction, so
    the status change and its history entry land together or not at all.
    """
    row = Collaboration(
        init=init_id, user_id=user_id,
        type=collab_type, workflow_status=WF_HANDLED,
    )
    session.add(row)
    logger.info(
        "Initiative status collaboration logged: init=%s user=%s type=%s",
        init_id, user_id, collab_type)
    return row
