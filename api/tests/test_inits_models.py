"""Smoke test: the inits models added by Initiative Management map onto tables
SQLModel can create and round-trip (T010)."""
from datetime import datetime

from sqlmodel import select

from app.inits.internal.models import (
    Collaboration, Criteria, Diagnostic, FavoriteInit, InitPermission, Initiative,
)
from tests.inits_helpers import mk_user_row


def test_new_inits_models_round_trip(session):
    mk_user_row(session, 1)
    session.add_all([
        Initiative(id=1, name="I", expected_impact="OTHER",
                   priority_level="LOW", status="ACCEPTED"),
        Criteria(code="C1", name="Crit"),
    ])
    session.commit()

    session.add_all([
        Collaboration(init=1, user_id=1, type="KICKOFF", workflow_status="HANDLED"),
        InitPermission(init=1, target_type="USER", target_code="1",
                       access_level="MANAGE", valid_from=datetime.utcnow()),
        Diagnostic(init=1, criteria="C1", creator_score=2),
        FavoriteInit(user_id=1, init=1),
    ])
    session.commit()

    assert session.get(Diagnostic, (1, "C1")).creator_score == 2
    assert session.get(FavoriteInit, (1, 1)).is_active is True
    assert session.exec(select(Collaboration)).one().type == "KICKOFF"
    assert session.exec(select(InitPermission)).one().access_level == "MANAGE"
