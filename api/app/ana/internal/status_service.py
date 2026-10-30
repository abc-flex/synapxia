"""Dashboard-status policy (Dashboard Management, spec US2 / FR-012).

A dashboard is always created in DRAFT. From then on only these moves exist:

  DRAFT     → PUBLISHED
  PUBLISHED → ARCHIVED | RETIRED
  ARCHIVED  → PUBLISHED | RETIRED
  RETIRED   → (final)

Everything else is refused (→ 400), including any move back to DRAFT. An
unknown current value (legacy data) offers no move at all, so its control is
locked. Unlike the assets/initiatives policies there is no activity row: the
analytics domain has no activity substrate and History is out of scope.
"""
from typing import List, Optional, Set, Tuple

from ...internal.status import normalize


class StatusTransitionForbidden(ValueError):
    """A status change Dashboard Management does not allow (→ 400)."""


STATUS_DRAFT = "DRAFT"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_ARCHIVED = "ARCHIVED"
STATUS_RETIRED = "RETIRED"

ALLOWED_TRANSITIONS: Set[Tuple[str, str]] = {
    (STATUS_DRAFT, STATUS_PUBLISHED),
    (STATUS_PUBLISHED, STATUS_ARCHIVED),
    (STATUS_PUBLISHED, STATUS_RETIRED),
    (STATUS_ARCHIVED, STATUS_PUBLISHED),
    (STATUS_ARCHIVED, STATUS_RETIRED),
}

# Display order of targets, following the lifecycle.
_ORDER = [STATUS_PUBLISHED, STATUS_ARCHIVED, STATUS_RETIRED]


def allowed_targets(current: Optional[str]) -> List[str]:
    """The statuses a dashboard may move to from ``current`` (may be empty)."""
    code = normalize(current)
    targets = {new for (cur, new) in ALLOWED_TRANSITIONS if cur == code}
    return [s for s in _ORDER if s in targets]


def allowed_statuses_for(current: Optional[str]) -> List[str]:
    """What the status control may offer: the current status, then its moves.
    A single entry means the control is locked."""
    return [normalize(current), *allowed_targets(current)]


def validate_create_status(status: Optional[str]) -> str:
    """A new dashboard always starts in DRAFT; any other requested status → 400."""
    code = normalize(status)
    if code in ("", STATUS_DRAFT):
        return STATUS_DRAFT
    raise StatusTransitionForbidden(
        f"A new dashboard starts as {STATUS_DRAFT}; '{status}' cannot be set on create.")


def validate_transition(current: Optional[str], new: Optional[str]) -> bool:
    """True when the status really changes and the move is allowed; False when
    it is unchanged or blank. Raises StatusTransitionForbidden otherwise."""
    current_code, new_code = normalize(current), normalize(new)
    if not new_code or current_code == new_code:
        return False
    if (current_code, new_code) not in ALLOWED_TRANSITIONS:
        raise StatusTransitionForbidden(
            f"Status transition {current_code} → {new_code} is not allowed. "
            "A dashboard can only move DRAFT → PUBLISHED, PUBLISHED → "
            "ARCHIVED/RETIRED or ARCHIVED → PUBLISHED/RETIRED; RETIRED is final."
        )
    return True
