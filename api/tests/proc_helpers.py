"""Shared fixtures-as-functions for the Process Management test modules
(specs/009-process-management). Same style as ana_helpers.py; the generic
helpers come from inits_helpers.py rather than being copied."""
from app.admin.internal.models import BusinessUnit, Privilege
from app.inits.internal.models import Initiative
from app.lib.internal.models import Asset
from app.workflows.internal.models import Process, ProcessAsset, ProcessInit, RelatedProcess
from tests.inits_helpers import (  # noqa: F401 — re-exported for the test modules
    data, mk_init, mk_list, mk_user_row, override, superuser, user,
)

OWNER_PROFILE = "ADMINISTRATIVE"
BASE = "/api/processes"


def seed_privileges(session, profile=OWNER_PROFILE, can_edit=True):
    session.add(Privilege(
        profile=profile, module="PROC", option="PROCESSES",
        can_edit=can_edit, is_active=True))
    session.commit()


def seed_view_privileges(session, profile="COLLABORATOR", options=("VALUE_CHAIN", "MAP"),
                         can_edit=False):
    """The landscape views' options (specs/010-process-landscape-views)."""
    for option in options:
        session.add(Privilege(profile=profile, module="PROC", option=option,
                              can_edit=can_edit, is_active=True))
    session.commit()


def seed_proc_lists(session):
    mk_list(session, "PROCESS_TYPE", [("PRIMARY", "Primary"), ("SUPPORT", "Support")])
    mk_list(session, "PROCESS_STATUS", [
        ("DRAFT", "Draft"), ("REVIEW", "Review"),
        ("PUBLISHED", "Published"), ("DEPRECATED", "Deprecated")])
    mk_list(session, "PROCESS_RELATION_TYPE", [
        ("PRECEDES", "Precedes"), ("TRIGGERS", "Triggers"), ("CALLS", "Calls"),
        ("FEEDS_INTO", "Feeds Into"), ("INTERACTS_WITH", "Interacts With"),
        ("SUPPORTS", "Supports"), ("GOVERNS", "Governs")])
    mk_list(session, "RELATION_TYPE", [
        ("DEPENDS_ON", "Depends On"), ("RELATED_TO", "Related To"),
        ("SIMILAR_TO", "Similar To"), ("USED_BY", "Used By")])


def mk_unit(session, code="ENG", name=None, active=True):
    row = BusinessUnit(code=code, name=name or code, is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_process(session, code, type="PRIMARY", parent=None, status="DRAFT",
               owner=1, name=None, active=True, **kw):
    row = Process(code=code, name=name or code, type=type, parent=parent,
                  status=status, owner=owner, is_active=active, **kw)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def mk_asset(session, id=None, name="Asset", category="PROMPTS", active=True):
    row = Asset(id=id, name=name, category=category, status="PUBLISHED", is_active=active)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def mk_relation(session, source, target, type="PRECEDES", rationale=None, active=True):
    row = RelatedProcess(source=source, target=target, type=type,
                         rationale=rationale, is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_asset_link(session, process, asset, type="RELATED_TO", active=True):
    row = ProcessAsset(process=process, asset=asset, type=type, is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_init_link(session, process, init, type="RELATED_TO", active=True):
    row = ProcessInit(process=process, init=init, type=type, is_active=active)
    session.add(row)
    session.commit()
    return row


def setup(session, can_edit=True, uid=1):
    """Privileges, lists, a unit and an owner row; the caller is overridden."""
    seed_privileges(session, can_edit=can_edit)
    seed_proc_lists(session)
    mk_unit(session, "ENG", "Engineering")
    mk_user_row(session, uid)
    override(user(uid))


def initiative(session, id, name="Init", active=True):
    row = mk_init(session, id=id, name=name, is_active=active)
    assert isinstance(row, Initiative)
    return row
