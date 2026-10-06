"""Helpers for the Usage Metrics test modules (specs/008-usage-metrics)."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.admin.internal.models import BusinessUnit, User
from app.collab.internal.models import Assignment, Project, Role, Team
from app.core.config import settings
from tests.ana_helpers import (  # noqa: F401 — re-exported
    PAST, data, mk_dashboard, mk_grant, override, seed_ana_lists, seed_privileges,
    superuser, user,
)
from tests.catalog_helpers import mk_execution

URL = "/api/usage/metrics"
TZ = ZoneInfo(settings.app_timezone)


def today() -> date:
    return datetime.now(TZ).date()


def admin(id=50):
    """An ADMINISTRATOR (organization-wide view, no superuser bypass)."""
    return user(id=id, profile="ADMINISTRATOR")


def analyst(id=1, unit="ENG"):
    """An ADMINISTRATIVE manager (view limited to dashboards they MANAGE)."""
    return user(id=id, unit=unit, profile="ADMINISTRATIVE")


def seed_usage(session):
    """ANA/USAGE (read) for ADMINISTRATOR and ADMINISTRATIVE, plus the ANA lists."""
    seed_privileges(session, profile="ADMINISTRATOR", options=("USAGE",), can_edit=False)
    seed_privileges(session, profile="ADMINISTRATIVE", options=("USAGE",), can_edit=False)
    seed_ana_lists(session)


def mk_unit(session, code, parent=None, name=None, active=True):
    row = BusinessUnit(code=code, name=name or code.title(), parent=parent, is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_user(session, id, unit="ENG", profile="COLLABORATOR", active=True, is_superuser=False):
    row = User(id=id, username=f"u{id}", email=f"u{id}@x.co", password_hash="x",
               first_name="F", last_name="L", profile=profile, unit=unit,
               is_active=active, is_superuser=is_superuser)
    session.add(row)
    session.commit()
    return row


def mk_team(session, code, name=None, active=True):
    row = Team(code=code, name=name or code.title(), is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_project(session, code, team, name=None, start=None, end=None, active=True):
    row = Project(code=code, name=name or code.title(), team=team, status="ACTIVE",
                  start_date=start, end_date=end, is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_assignment(session, user_id, team, valid_from, valid_to=None, active=True, role="DEV"):
    if session.get(Role, role) is None:
        session.add(Role(code=role, name=role))
        session.commit()
    row = Assignment(team=team, user_id=user_id, role=role, valid_from=valid_from,
                     valid_to=valid_to, is_active=active)
    session.add(row)
    session.commit()
    return row


def utc(local: datetime) -> datetime:
    """A naive local (APP_TIMEZONE) datetime → naive UTC, as stored."""
    return local.replace(tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None)


def at(d: date, hour=10, minute=0) -> datetime:
    """Naive UTC instant of local `d` at hour:minute."""
    return utc(datetime.combine(d, time(hour, minute)))


def run(session, dashboard, user_id=1, status="SUCCESS", when=None, duration_ms=None,
        error=None):
    """One execution at `when` (naive UTC; default: today 10:00 local)."""
    row = mk_execution(session, dashboard, user_id=user_id, status=status,
                       executed_at=when or at(today()))
    row.duration_ms = duration_ms
    row.error_message = error
    session.add(row)
    session.commit()
    return row


def period(days=30, end=None):
    """Query string for the `days`-long period ending `end` (default today)."""
    end = end or today()
    start = end - timedelta(days=days - 1)
    return f"date_from={start.isoformat()}&date_to={end.isoformat()}"
