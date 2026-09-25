"""Shared reviewer eligibility (app/internal/reviewers.py).

The rule was moved out of lib's propose_service so the initiatives' diagnosis
workflow uses the same one (specs/005-explore-initiatives R2). The lib suites
guard the re-exports; these tests pin the rule itself.
"""
import pytest

from app.internal import reviewers
from app.lib.internal import propose_service
from tests.inits_helpers import mk_user_row


def _seed(session):
    mk_user_row(session, 1, "admin_like", profile="ADMINISTRATOR")
    mk_user_row(session, 2, "clerk", profile="ADMINISTRATIVE")
    mk_user_row(session, 3, "rev", profile="REVIEWER")
    mk_user_row(session, 4, "collab", profile="COLLABORATOR")
    mk_user_row(session, 5, "root", profile="COLLABORATOR", is_superuser=True)
    mk_user_row(session, 6, "gone", profile="REVIEWER", is_active=False)


def test_list_reviewers_eligible_profiles_and_superusers_only(session):
    _seed(session)
    assert [u.id for u in reviewers.list_reviewers(session)] == [1, 2, 3, 5]


def test_list_reviewers_excludes_requested_user(session):
    _seed(session)
    assert 3 not in [u.id for u in reviewers.list_reviewers(session, exclude_user_id=3)]


def test_non_admin_proposer_cannot_self_select(session):
    _seed(session)
    proposer = session.get(reviewers.User, 3)  # REVIEWER, not admin
    with pytest.raises(ValueError, match="yourself"):
        reviewers.resolve_reviewer(session, 3, proposer=proposer)


def test_admin_proposer_may_self_select(session):
    _seed(session)
    proposer = session.get(reviewers.User, 2)  # ADMINISTRATIVE
    assert reviewers.resolve_reviewer(session, 2, proposer=proposer).id == 2


def test_ineligible_or_inactive_reviewer_refused(session):
    _seed(session)
    with pytest.raises(ValueError):
        reviewers.resolve_reviewer(session, 4)  # COLLABORATOR
    with pytest.raises(ValueError):
        reviewers.resolve_reviewer(session, 6)  # inactive
    with pytest.raises(ValueError):
        reviewers.resolve_reviewer(session, 999)  # missing


def test_auto_assign_lowest_eligible_minus_non_admin_proposer(session):
    mk_user_row(session, 3, "rev", profile="REVIEWER")
    mk_user_row(session, 7, "rev2", profile="REVIEWER")
    proposer = session.get(reviewers.User, 3)
    assert reviewers.resolve_reviewer(session, None, proposer=proposer).id == 7
    assert reviewers.resolve_reviewer(session, None).id == 3


def test_no_eligible_reviewer_raises(session):
    mk_user_row(session, 4, "collab", profile="COLLABORATOR")
    with pytest.raises(ValueError, match="No eligible reviewer"):
        reviewers.resolve_reviewer(session, None)


def test_lib_reexports_are_the_shared_functions():
    assert propose_service.resolve_reviewer is reviewers.resolve_reviewer
    assert propose_service.list_reviewers is reviewers.list_reviewers
    assert propose_service.is_admin is reviewers.is_admin
    assert propose_service._is_eligible is reviewers.is_eligible
