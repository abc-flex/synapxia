"""Reviewer eligibility and assignment, shared by every contribution workflow.

Both the AI Library's asset review (lib/internal/propose_service.py) and the
initiatives' diagnosis (inits/internal/propose_service.py) ask the same
questions — who may review, may the proposer review their own work, and who
gets the assignment when the proposer picks nobody — so the answer lives here
once (Constitution I: no duplicated workflow plumbing per module).
specs/005-explore-initiatives research R2.
"""
from typing import List, Optional

from sqlmodel import Session, select

from ..admin.internal.models import User

# Profiles eligible to review a proposal (db/sql/12-admin-insert.sql). Superusers
# are always eligible too (see list_reviewers / resolve_reviewer). REVIEWER is the
# dedicated reviewer profile; ADMINISTRATOR/ADMINISTRATIVE are the admin profiles.
REVIEWER_PROFILES = ("ADMINISTRATOR", "ADMINISTRATIVE", "REVIEWER")

# The truly "administrative" profiles — exempt from the self-review exclusion
# below (an admin proposing on the org's behalf may still self-assign; a
# REVIEWER or COLLABORATOR proposing their own work may not review it).
ADMIN_PROFILES = ("ADMINISTRATOR", "ADMINISTRATIVE")


def is_eligible(user: User) -> bool:
    """A user can review if active and either an admin/REVIEWER profile or superuser."""
    return bool(user.is_active) and (
        user.profile in REVIEWER_PROFILES or bool(user.is_superuser)
    )


def is_admin(user: User) -> bool:
    """Truly administrative (exempt from the self-review exclusion)."""
    return bool(user.is_superuser) or user.profile in ADMIN_PROFILES


def list_reviewers(session: Session, exclude_user_id: Optional[int] = None) -> List[User]:
    """Active users eligible to review (admin/REVIEWER profile or superuser), id
    order. `exclude_user_id` (the proposer, when they're not themselves an admin/
    superuser — see resolve_reviewer) drops that user from the results so a
    REVIEWER/COLLABORATOR can't be offered themselves as their own reviewer."""
    statement = select(User).where(
        User.is_active == True,  # noqa: E712
        (User.profile.in_(REVIEWER_PROFILES)) | (User.is_superuser == True),  # noqa: E712
    )
    if exclude_user_id is not None:
        statement = statement.where(User.id != exclude_user_id)
    return session.exec(statement.order_by(User.id)).all()


def resolve_reviewer(
    session: Session, reviewer_id: Optional[int], proposer: Optional[User] = None
) -> User:
    """Resolve the reviewer for a proposal: the requested user (which must be an
    active admin/REVIEWER or superuser) or, when none is requested, the first
    eligible one. Raises ValueError if the requested reviewer is invalid or none
    exist.

    A non-admin `proposer` (COLLABORATOR/REVIEWER — see is_admin) may not
    resolve to themselves: an admin proposing on the org's behalf may still
    self-assign, but a REVIEWER/COLLABORATOR reviewing their own proposal
    would defeat the point of the review step.
    """
    exclude_id = proposer.id if proposer and not is_admin(proposer) else None
    if reviewer_id is not None:
        user = session.get(User, reviewer_id)
        if not user or not user.is_active:
            raise ValueError(f"Reviewer '{reviewer_id}' not found or inactive.")
        if not is_eligible(user):
            raise ValueError(
                "Reviewer must be an administrator, a REVIEWER, or a superuser."
            )
        if exclude_id is not None and user.id == exclude_id:
            raise ValueError("You cannot select yourself as the reviewer.")
        return user
    eligible = list_reviewers(session, exclude_user_id=exclude_id)
    if not eligible:
        raise ValueError(
            "No eligible reviewer (administrator, REVIEWER, or superuser) is available."
        )
    return eligible[0]
