"""Process-status policy (Process Management, spec FR-008).

A process is always created in DRAFT. From then on only these moves exist:

  DRAFT     → REVIEW
  REVIEW    → PUBLISHED | DRAFT   (back to the author)
  PUBLISHED → DEPRECATED
  DEPRECATED → (final)

Everything else is refused (→ 400). Keeping the current status is not a move.
There is no activity row: processes have no activity substrate (spec: no status
history).
"""
from typing import List, Optional, Set, Tuple

from ...internal.status import normalize


class StatusTransitionForbidden(ValueError):
    """A status change Process Management does not allow (→ 400)."""


STATUS_DRAFT = "DRAFT"
STATUS_REVIEW = "REVIEW"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_DEPRECATED = "DEPRECATED"

ALLOWED_TRANSITIONS: Set[Tuple[str, str]] = {
    (STATUS_DRAFT, STATUS_REVIEW),
    (STATUS_REVIEW, STATUS_PUBLISHED),
    (STATUS_REVIEW, STATUS_DRAFT),
    (STATUS_PUBLISHED, STATUS_DEPRECATED),
}

# Display order of targets, following the lifecycle.
_ORDER = [STATUS_REVIEW, STATUS_PUBLISHED, STATUS_DRAFT, STATUS_DEPRECATED]


def allowed_targets(current: Optional[str]) -> List[str]:
    """The statuses a process may move to from ``current`` (may be empty)."""
    code = normalize(current)
    targets = {new for (cur, new) in ALLOWED_TRANSITIONS if cur == code}
    return [s for s in _ORDER if s in targets]


def allowed_statuses_for(current: Optional[str]) -> List[str]:
    """What the status control may offer: the current status, then its moves.
    A single entry means the control is locked."""
    return [normalize(current), *allowed_targets(current)]


def validate_create_status(status: Optional[str]) -> str:
    """A new process always starts in DRAFT; any other requested status → 400."""
    code = normalize(status)
    if code in ("", STATUS_DRAFT):
        return STATUS_DRAFT
    raise StatusTransitionForbidden(
        f"A new process starts as {STATUS_DRAFT}; '{status}' cannot be set on create.")


def validate_transition(current: Optional[str], new: Optional[str]) -> bool:
    """True when the status really changes and the move is allowed; False when
    it is unchanged or blank. Raises StatusTransitionForbidden otherwise."""
    current_code, new_code = normalize(current), normalize(new)
    if not new_code or current_code == new_code:
        return False
    if (current_code, new_code) not in ALLOWED_TRANSITIONS:
        raise StatusTransitionForbidden(
            f"Status transition {current_code} → {new_code} is not allowed. "
            "A process can only move DRAFT → REVIEW, REVIEW → PUBLISHED or back to "
            "DRAFT, and PUBLISHED → DEPRECATED; DEPRECATED is final."
        )
    return True
