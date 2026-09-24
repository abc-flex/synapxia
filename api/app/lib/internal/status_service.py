"""Direct asset-status policy (Asset Management surface) + its history trail.

Asset Management (`/lib/assets`) is the *manager's* surface, not the review
workflow. Only two status moves are legitimate there, and both are recorded on
the ``actions`` substrate so they show up in the asset's history like every
other transition (never a new table — see actions_service):

  1. **Creation** — a manager-created asset is born PUBLISHED (it never went
     through propose → review, so no other status could be honest), logged as
     PUBLICATION/HANDLED.
  2. **Deprecation** — a PUBLISHED asset may be retired, logged as
     DEPRECATION/HANDLED.

Every other status change from this surface is refused (→ 400). The review
workflow's own transitions (PROPOSED/FEEDBACK/REJECTED → …) stay exclusively
with propose_service/review_service/modify_service, which write their own
actions and deliberately do NOT route through here.

Both rows are written HANDLED — self-service events with nothing owed to
anybody, matching version_service's VERSIONING/HANDLED. PUBLICATION is a
notification type, so a PENDING row here would raise a request the actor would
then have to acknowledge to themselves.
"""
import logging
from typing import Optional

from sqlmodel import Session

from .models import Action
from ...internal.status import normalize  # noqa: F401  (re-exported: status_service.normalize)

logger = logging.getLogger(__name__)


class StatusTransitionForbidden(ValueError):
    """A status change this surface does not allow (→ 400)."""


STATUS_PUBLISHED = "PUBLISHED"
STATUS_DEPRECATED = "DEPRECATED"

TYPE_PUBLICATION = "PUBLICATION"
TYPE_DEPRECATION = "DEPRECATION"
WF_HANDLED = "HANDLED"

# The only status a directly-created asset may carry, and the action it logs.
CREATE_STATUS = STATUS_PUBLISHED
CREATE_ACTION = TYPE_PUBLICATION

# (current, new) → action type logged. Anything absent here is refused.
ALLOWED_TRANSITIONS = {
    (STATUS_PUBLISHED, STATUS_DEPRECATED): TYPE_DEPRECATION,
}

def validate_create_status(status: Optional[str]) -> str:
    """Return the action type to log for a direct create, or raise.

    A manager-created asset must be PUBLISHED: the review statuses (PROPOSED /
    FEEDBACK / REJECTED) describe a proposal moving through review, and this
    surface creates no proposal.
    """
    if normalize(status) != CREATE_STATUS:
        raise StatusTransitionForbidden(
            f"A new asset must be created with status '{CREATE_STATUS}'. "
            "Use the propose flow to submit an asset for review."
        )
    return CREATE_ACTION


def validate_transition(current: Optional[str], new: Optional[str]) -> Optional[str]:
    """Return the action type to log for this status change.

    ``None`` when the status is unchanged (the common case — the edit modal
    always sends the field, changed or not). Raises StatusTransitionForbidden
    for any move other than PUBLISHED → DEPRECATED.
    """
    current_code, new_code = normalize(current), normalize(new)
    if not new_code or current_code == new_code:
        return None
    action_type = ALLOWED_TRANSITIONS.get((current_code, new_code))
    if action_type is None:
        raise StatusTransitionForbidden(
            f"Status cannot change from '{current_code}' to '{new_code}'. "
            f"Only '{STATUS_PUBLISHED}' → '{STATUS_DEPRECATED}' is allowed here; "
            "every other transition belongs to the review workflow."
        )
    return action_type


def log_status_action(
    session: Session,
    asset_id: int,
    user_id: int,
    action_type: str,
    note: Optional[str] = None,
) -> Action:
    """Stage the history row for a status change (HANDLED — nothing is owed).

    Added to the session but NOT committed: the caller owns the transaction, so
    the status change and its history entry land together or not at all.
    """
    row = Action(
        asset=asset_id, user_id=user_id,
        type=action_type, workflow_status=WF_HANDLED, content=note,
    )
    session.add(row)
    logger.info(
        "Asset status action logged: asset=%s user=%s type=%s",
        asset_id, user_id, action_type)
    return row
