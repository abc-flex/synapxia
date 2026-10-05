"""Dashboard Catalog foundation: run-value validation and effective parameter
sources (specs/007-dashboard-catalog R3/R7)."""
import pytest

from app.insights.internal import catalog_service, parameter_validation as pv
from tests.catalog_helpers import (
    PAST, mk_dashboard, mk_grant, mk_list_def, mk_param, seed_ana_lists, superuser, viewer,
)


@pytest.mark.parametrize("data_type,value", [
    ("NUMBER", "1.5"), ("NUMBER", "-3"), ("BOOLEAN", "true"), ("BOOLEAN", "false"),
    ("DATE", "2026-02-28"), ("STRING", "anything"),
])
def test_validate_run_value_accepts(data_type, value):
    pv.validate_run_value("P", data_type, value, None)


@pytest.mark.parametrize("data_type,value,fragment", [
    ("NUMBER", "abc", "must be a number"), ("NUMBER", "NaN", "must be a number"),
    ("BOOLEAN", "yes", "'true' or 'false'"), ("DATE", "2026-02-30", "must be a date"),
    ("DATE", "28/02/2026", "must be a date"),
])
def test_validate_run_value_rejects(data_type, value, fragment):
    with pytest.raises(ValueError, match=fragment):
        pv.validate_run_value("P", data_type, value, None)


def test_validate_run_value_list_and_length():
    pv.validate_run_value("P", "STRING", "DAY", {"DAY", "WEEK"})
    with pytest.raises(ValueError, match="one of its list"):
        pv.validate_run_value("P", "STRING", "YEAR", {"DAY", "WEEK"})
    with pytest.raises(ValueError, match="at most 1000"):
        pv.validate_run_value("P", "STRING", "x" * 1001, None)


def test_validate_default_messages_unchanged():
    with pytest.raises(ValueError, match="Default 'x' is not a number"):
        pv.validate_default("NUMBER", "x", None)
    with pytest.raises(ValueError, match="A Boolean default must be 'true' or 'false'"):
        pv.validate_default("BOOLEAN", "x", None)
    with pytest.raises(ValueError, match="is not one of the list's values"):
        pv.validate_default("STRING", "x", {"a"})


def _sources(session, u, dash_id):
    return {e.param.name: e for e in catalog_service.resolve_effective_parameters(session, u, dash_id)}


def test_effective_sources(session):
    seed_ana_lists(session)
    d = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    unit_grant = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    other_grant = mk_grant(session, d.id, "UNIT", "OPS", access_level="VIEW")
    mk_param(session, d.id, "unit", context_binding=unit_grant.id)
    mk_param(session, d.id, "other", context_binding=other_grant.id, list="GRANULARITY")
    mk_param(session, d.id, "other_free", context_binding=other_grant.id)
    mk_param(session, d.id, "gran", list="GRANULARITY")
    mk_param(session, d.id, "free")
    mk_param(session, d.id, "gone", is_active=False)

    eff = _sources(session, viewer(unit="ENG"), d.id)
    assert set(eff) == {"unit", "other", "other_free", "gran", "free"}
    assert eff["unit"].source == "GRANT" and eff["unit"].bound_value == "ENG"
    assert eff["unit"].bound_label == "UNIT ENG"
    # Reached only through PUBLIC / UNIT ENG, not UNIT OPS → fallbacks.
    assert eff["other"].source == "LIST" and eff["other"].allowed == {"DAY", "WEEK", "MONTH"}
    assert eff["other_free"].source == "INPUT"
    assert eff["gran"].source == "LIST"
    assert eff["free"].source == "INPUT"


def test_revoked_binding_and_superuser_fall_back(session):
    seed_ana_lists(session)
    d = mk_dashboard(session, status="PUBLISHED")
    mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    revoked = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW", valid_to=PAST)
    mk_param(session, d.id, "unit", context_binding=revoked.id)
    assert _sources(session, viewer(unit="ENG"), d.id)["unit"].source == "INPUT"

    live = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    mk_param(session, d.id, "unit2", context_binding=live.id)
    # A superuser in another unit does not come through the bound grant.
    su = superuser()
    su.unit = "OPS"
    assert _sources(session, su, d.id)["unit2"].source == "INPUT"


def test_unavailable_list(session):
    seed_ana_lists(session)
    mk_list_def(session, "EMPTY", name="Empty")
    d = mk_dashboard(session, status="PUBLISHED")
    mk_param(session, d.id, "e", list="EMPTY")
    eff = _sources(session, viewer(), d.id)["e"]
    assert eff.source == "LIST" and eff.list_unavailable
