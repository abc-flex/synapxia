"""Usage Metrics (HU-AN07, specs/008-usage-metrics).

A read-only view over ``executions`` for managers. One projected, index-backed
range query loads the period (plus the preceding period of equal length) and a
single Python pass builds every figure — medians, local-time buckets and the
run-time team attribution are not portable SQL, and the suites run on SQLite
(research R1).

This module is the single owner of three rules — never re-derive them elsewhere:

- **Run vs attempt** (``OUTCOME_*``, research R5). Success, Failed, Timeout and
  Incomplete (status NULL) are *runs*; Cancelled and Unauthorized are
  *attempts* (abandoned or refused) and never count as usage. Success rate =
  Success ÷ (Success + Failed + Timeout).
- **Scope** (``scope_for``, research R4). Superusers and ``ORG_WIDE_PROFILES``
  see every execution; anyone else only executions of dashboards they hold a
  live MANAGE grant to (the shared per-resource engine).
- **Periods** (``parse_period``, research R3). Local dates in
  ``settings.app_timezone``; buckets are local days, ISO weeks or months.

Nothing returned here identifies a person or an individual execution (FR-015).
"""
from __future__ import annotations

import logging
import statistics
import time as _time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from . import permissions_service
from .models import (
    Dashboard, Execution, UsageBucket, UsageChange, UsageDashboardRow, UsageErrorItem,
    UsageErrors, UsageFigures, UsageFilter, UsageMetrics, UsagePeriod, UsageScope,
    UsageProjectRow, UsageSummary, UsageTeamRow, UsageUnitNode,
)
from ...admin.internal.models import BusinessUnit, User
from ...collab.internal.models import Assignment, Project, Team
from ...core.config import settings
from ...internal.resource_permissions import ACCESS_MANAGE, as_naive_utc
from ...internal.status import normalize

logger = logging.getLogger(__name__)

# Profiles with the organization-wide view (clarification Q1 = C). Deliberately
# NOT app/internal/reviewers.ADMIN_PROFILES: that one includes ADMINISTRATIVE,
# which this feature scopes to the dashboards it manages.
ORG_WIDE_PROFILES = ("ADMINISTRATOR",)

NO_TEAM = "__none__"     # "No team" row / filter value
NO_PROJECT = "__none__"  # "No project" row / filter value
MAX_DAYS = 731  # 24 months (FR-004)
PUBLISHED = "PUBLISHED"

SUCCESS, FAILED, TIMEOUT, INCOMPLETE = "SUCCESS", "FAILED", "TIMEOUT", "INCOMPLETE"
CANCELLED, UNAUTHORIZED = "CANCELLED", "UNAUTHORIZED"
OUTCOME_RUNS = (SUCCESS, FAILED, TIMEOUT, INCOMPLETE)
OUTCOME_ATTEMPTS = (CANCELLED, UNAUTHORIZED)
OUTCOME_KEYS = OUTCOME_RUNS + OUTCOME_ATTEMPTS
RATE_KEYS = (SUCCESS, FAILED, TIMEOUT)


class UsageNotFound(LookupError):
    """A dashboard that does not exist or lies outside the caller's scope (→ 404)."""


# ── Classification (research R5) ────────────────────────────────────────────


def classify(status: Optional[str]) -> Tuple[str, bool]:
    """→ (outcome key, is_run). NULL is Incomplete (a run). An unknown code is a
    run reported under its own key, so it never disappears silently."""
    if status is None or not str(status).strip():
        return INCOMPLETE, True
    key = normalize(status).upper()
    return key, key not in OUTCOME_ATTEMPTS


@dataclass(frozen=True)
class Row:
    dashboard: int
    user: int
    at: datetime          # naive UTC
    outcome: str
    is_run: bool
    duration: Optional[int]


# ── Periods (research R3, R9) ────────────────────────────────────────────────


@dataclass
class Period:
    date_from: date
    date_to: date
    days: int
    prev_from: date
    prev_to: date
    bucket: str
    tz: ZoneInfo
    start: datetime = field(init=False)       # naive UTC, inclusive
    end: datetime = field(init=False)         # naive UTC, exclusive
    prev_start: datetime = field(init=False)

    def __post_init__(self):
        self.start = self.to_utc(self.date_from)
        self.end = self.to_utc(self.date_to + timedelta(days=1))
        self.prev_start = self.to_utc(self.prev_from)

    def to_utc(self, d: date) -> datetime:
        local = datetime.combine(d, time.min, tzinfo=self.tz)
        return local.astimezone(timezone.utc).replace(tzinfo=None)

    def local_date(self, at: datetime) -> date:
        return at.replace(tzinfo=timezone.utc).astimezone(self.tz).date()


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def _parse_date(value: Optional[str], name: str) -> date:
    if not value:
        raise ValueError(f"'{name}' is required (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"'{name}' must be a date (YYYY-MM-DD)")


def parse_period(date_from: Optional[str], date_to: Optional[str],
                 today: Optional[date] = None) -> Period:
    tz = _tz()
    start, end = _parse_date(date_from, "date_from"), _parse_date(date_to, "date_to")
    today = today or datetime.now(tz).date()
    if end < start:
        raise ValueError("'date_to' must not be before 'date_from'")
    if (end - start).days > MAX_DAYS:
        raise ValueError("The period can span at most 24 months")
    if end > today + timedelta(days=1):
        raise ValueError("'date_to' cannot be in the future")
    days = (end - start).days + 1
    bucket = "day" if days <= 31 else "week" if days <= 183 else "month"
    return Period(date_from=start, date_to=end, days=days,
                  prev_from=start - timedelta(days=days),
                  prev_to=start - timedelta(days=1), bucket=bucket, tz=tz)


def _bucket_start(d: date, bucket: str) -> date:
    if bucket == "week":
        return d - timedelta(days=d.weekday())  # ISO week, Monday
    if bucket == "month":
        return d.replace(day=1)
    return d


def _next_bucket(d: date, bucket: str) -> date:
    if bucket == "week":
        return d + timedelta(days=7)
    if bucket == "month":
        return (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return d + timedelta(days=1)


def bucket_ranges(p: Period) -> List[Tuple[date, date]]:
    """Every bucket of the period, oldest first, clipped to the period."""
    out: List[Tuple[date, date]] = []
    natural = _bucket_start(p.date_from, p.bucket)
    while natural <= p.date_to:
        nxt = _next_bucket(natural, p.bucket)
        out.append((max(natural, p.date_from), min(nxt - timedelta(days=1), p.date_to)))
        natural = nxt
    return out


# ── Scope (research R4) ──────────────────────────────────────────────────────


def scope_for(session: Session, user: User) -> Optional[Set[int]]:
    """None = unrestricted; otherwise the dashboard ids the user MANAGEs."""
    if getattr(user, "is_superuser", False) or getattr(user, "profile", None) in ORG_WIDE_PROFILES:
        return None
    levels = permissions_service.accessible_dashboards(session, user)
    return {d for d, level in levels.items() if level == ACCESS_MANAGE}


# ── Loading ──────────────────────────────────────────────────────────────────


def load_rows(session: Session, start: datetime, end: datetime,
              scope: Optional[Set[int]], dashboard: Optional[int] = None) -> List[Row]:
    """One projected range query (no payload, no error text), streamed."""
    if scope is not None and not scope:
        return []
    stmt = select(Execution.dashboard, Execution.user_id, Execution.executed_at,
                  Execution.status, Execution.duration_ms).where(
        Execution.executed_at >= start, Execution.executed_at < end)
    if scope is not None:
        stmt = stmt.where(Execution.dashboard.in_(sorted(scope)))
    if dashboard is not None:
        stmt = stmt.where(Execution.dashboard == dashboard)
    rows: List[Row] = []
    for d, u, at, status, duration in session.exec(stmt.execution_options(yield_per=5000)):
        outcome, is_run = classify(status)
        rows.append(Row(d, u, as_naive_utc(at), outcome, is_run, duration))
    return rows


# ── Figures (research R5, R9) ────────────────────────────────────────────────


def _rate(outcomes: Counter) -> Optional[float]:
    denominator = sum(outcomes[k] for k in RATE_KEYS)
    return round(outcomes[SUCCESS] / denominator, 4) if denominator else None


def figures(rows: Iterable[Row]) -> UsageFigures:
    outcomes: Counter = Counter({k: 0 for k in OUTCOME_KEYS})
    users: Set[int] = set()
    dashboards: Set[int] = set()
    durations: List[int] = []
    runs = attempts = 0
    for r in rows:
        outcomes[r.outcome] += 1
        if r.is_run:
            runs += 1
            users.add(r.user)
            dashboards.add(r.dashboard)
        else:
            attempts += 1
        if r.outcome == SUCCESS and r.duration is not None:
            durations.append(r.duration)
    return UsageFigures(
        runs=runs, attempts=attempts, users=len(users), dashboards=len(dashboards),
        success_rate=_rate(outcomes),
        median_ms=round(statistics.median(durations)) if durations else None,
        avg_ms=round(statistics.fmean(durations)) if durations else None,
        incomplete=outcomes[INCOMPLETE], outcomes=dict(outcomes))


def _ratio(cur: float, prev: float) -> Optional[float]:
    return round((cur - prev) / prev, 4) if prev else None


def _diff(cur, prev):
    if cur is None or prev is None:
        return None
    return round(cur - prev, 4) if isinstance(cur, float) or isinstance(prev, float) else cur - prev


def change(cur: UsageFigures, prev: UsageFigures) -> UsageChange:
    return UsageChange(
        runs=_ratio(cur.runs, prev.runs), attempts=_ratio(cur.attempts, prev.attempts),
        users=_ratio(cur.users, prev.users), dashboards=_ratio(cur.dashboards, prev.dashboards),
        success_rate=_diff(cur.success_rate, prev.success_rate),
        median_ms=_diff(cur.median_ms, prev.median_ms), avg_ms=_diff(cur.avg_ms, prev.avg_ms),
        incomplete=_ratio(cur.incomplete, prev.incomplete))


def timeline(rows: Iterable[Row], p: Period) -> List[UsageBucket]:
    ranges = bucket_ranges(p)
    counts: Dict[date, Counter] = {start: Counter({k: 0 for k in OUTCOME_KEYS})
                                   for start, _ in ranges}
    for r in rows:
        key = max(_bucket_start(p.local_date(r.at), p.bucket), p.date_from)
        if key in counts:
            counts[key][r.outcome] += 1
    return [UsageBucket(start=s.isoformat(), end=e.isoformat(), outcomes=dict(counts[s]))
            for s, e in ranges]


# ── Dashboards table (FR-011) ────────────────────────────────────────────────


def _as_utc(at: Optional[datetime]) -> Optional[datetime]:
    return at.replace(tzinfo=timezone.utc) if at else None


def dashboard_rows(session: Session, rows: Iterable[Row],
                   scope: Optional[Set[int]]) -> List[UsageDashboardRow]:
    per: Dict[int, List[Row]] = defaultdict(list)
    for r in rows:
        per[r.dashboard].append(r)

    dashboards = {d.id: d for d in session.exec(select(Dashboard)).all()}
    used: List[UsageDashboardRow] = []
    for dash_id, items in per.items():
        d = dashboards.get(dash_id)
        f = figures(items)
        runs = [r for r in items if r.is_run]
        used.append(UsageDashboardRow(
            id=dash_id, name=d.name if d else f"#{dash_id}",
            type=normalize(d.type) if d else "", source=normalize(d.sources_types) if d else "",
            status=normalize(d.status) if d else "",
            runs=f.runs, attempts=f.attempts, users=f.users, success_rate=f.success_rate,
            median_ms=f.median_ms,
            last_run_at=_as_utc(max((r.at for r in runs), default=None))))
    used.sort(key=lambda x: (-x.runs, x.name.lower()))

    unused = [
        UsageDashboardRow(id=d.id, name=d.name, type=normalize(d.type),
                          source=normalize(d.sources_types), status=normalize(d.status),
                          unused=True)
        for d in dashboards.values()
        if d.id not in per and d.is_active and normalize(d.status) == PUBLISHED
        and (scope is None or d.id in scope)
    ]
    unused.sort(key=lambda x: x.name.lower())
    return used + unused


# ── Units and teams (research R7, R8) ────────────────────────────────────────


# (team, valid_from, valid_to) of one active assignment, naive UTC.
_Window = Tuple[str, datetime, Optional[datetime]]


class Groups:
    """Organization structure for one request: four constant queries."""

    def __init__(self, session: Session, p: Period):
        self.p = p
        self.now = datetime.utcnow()
        self.units: Dict[str, BusinessUnit] = {
            u.code: u for u in session.exec(select(BusinessUnit)).all()}
        users = session.exec(select(User.id, User.unit, User.is_active)).all()
        self.user_unit: Dict[int, str] = {uid: unit for uid, unit, _ in users}
        self.active_users: Dict[int, str] = {uid: unit for uid, unit, act in users if act}
        self.teams: Dict[str, Team] = {t.code: t for t in session.exec(select(Team)).all()}
        self.assignments: Dict[int, List[_Window]] = defaultdict(list)
        for uid, team, vf, vt in session.exec(
                select(Assignment.user_id, Assignment.team, Assignment.valid_from,
                       Assignment.valid_to).where(
                    Assignment.is_active == True, Assignment.team.is_not(None))):  # noqa: E712
            self.assignments[uid].append((team, as_naive_utc(vf), as_naive_utc(vt)))
        self._current: Dict[int, List[str]] = {}
        # Projects belong to one team; people reach a project through its team.
        self.projects: Dict[str, Project] = {
            pr.code: pr for pr in session.exec(
                select(Project).where(Project.is_active == True)).all()}  # noqa: E712
        self.team_projects: Dict[str, List[Project]] = defaultdict(list)
        for pr in self.projects.values():
            if pr.team:
                self.team_projects[pr.team].append(pr)
        self.children, self.roots = self._tree()

    # unit tree --------------------------------------------------------------

    def _tree(self) -> Tuple[Dict[str, List[str]], List[str]]:
        children: Dict[str, List[str]] = defaultdict(list)
        roots: List[str] = []
        for code, u in self.units.items():
            if u.parent and u.parent in self.units and u.parent != code:
                children[u.parent].append(code)
            else:
                roots.append(code)
        reached: Set[str] = set()

        def reach(start: str) -> None:
            stack = [start]
            while stack:
                code = stack.pop()
                if code in reached:
                    continue
                reached.add(code)
                stack.extend(children.get(code, []))

        for code in roots:
            reach(code)
        # A parent cycle leaves units unreachable: break each cycle at one unit
        # (it becomes a root) and the rest of the cycle hangs below it.
        while set(self.units) - reached:
            code = min(set(self.units) - reached)
            logger.warning("Usage metrics: business unit %s is in a parent cycle", code)
            for kids in children.values():
                if code in kids:
                    kids.remove(code)
            roots.append(code)
            reach(code)
        return children, roots

    def subtree(self, code: str) -> Set[str]:
        out: Set[str] = set()
        stack = [code]
        while stack:
            c = stack.pop()
            if c in out:
                continue
            out.add(c)
            stack.extend(self.children.get(c, []))
        return out

    # teams ------------------------------------------------------------------

    @staticmethod
    def _valid(vf: datetime, vt: Optional[datetime], at: datetime) -> bool:
        return vf <= at and (vt is None or at < vt)

    def teams_for_run(self, user_id: int, at: datetime) -> List[str]:
        """Hybrid rule (clarification): teams valid when the run started; else
        the user's current teams; else "No team"."""
        rows = self.assignments.get(user_id, [])
        then = sorted({t for t, vf, vt in rows if self._valid(vf, vt, at)})
        if then:
            return then
        if user_id not in self._current:
            self._current[user_id] = sorted(
                {t for t, vf, vt in rows if self._valid(vf, vt, self.now)})
        return self._current[user_id] or [NO_TEAM]

    def team_members(self) -> Dict[str, Set[int]]:
        """Active users with an assignment valid during the period or now."""
        p, members = self.p, defaultdict(set)
        for uid, rows in self.assignments.items():
            if uid not in self.active_users:
                continue
            for team, vf, vt in rows:
                overlaps = vf < p.end and (vt is None or vt > p.start)
                if overlaps or self._valid(vf, vt, self.now):
                    members[team].add(uid)
        return members

    # projects ---------------------------------------------------------------

    def projects_for_run(self, user_id: int, at: datetime) -> List[str]:
        """The active projects of every team the run counts in (teams_for_run),
        when the run's local date falls inside the project's dates (open ends
        allowed); else "No project"."""
        day = self.p.local_date(at)
        codes = {
            pr.code
            for team in self.teams_for_run(user_id, at) if team != NO_TEAM
            for pr in self.team_projects.get(team, [])
            if (pr.start_date is None or pr.start_date <= day)
            and (pr.end_date is None or day <= pr.end_date)
        }
        return sorted(codes) or [NO_PROJECT]

    def project_members(self, team_members: Dict[str, Set[int]]) -> Dict[str, Set[int]]:
        """A project's members are its team's members (period or now)."""
        return {code: set(team_members.get(pr.team, set())) if pr.team else set()
                for code, pr in self.projects.items()}

    # filter (FR-005) --------------------------------------------------------

    def row_filter(self, unit: Optional[str], team: Optional[str],
                   project: Optional[str] = None) -> Optional[Callable[[Row], bool]]:
        if sum(1 for v in (unit, team, project) if v) > 1:
            raise ValueError("Filter by one unit, team or project at a time")
        if project:
            if project != NO_PROJECT and project not in self.projects:
                raise ValueError(f"Unknown project '{project}'")
            return lambda r: project in self.projects_for_run(r.user, r.at)
        if unit:
            if unit not in self.units:
                raise ValueError(f"Unknown unit '{unit}'")
            codes = self.subtree(unit)
            return lambda r: self.user_unit.get(r.user) in codes
        if team:
            if team != NO_TEAM and team not in self.teams:
                raise ValueError(f"Unknown team '{team}'")
            return lambda r: team in self.teams_for_run(r.user, r.at)
        return None


def _adoption(users: int, members: int) -> Optional[float]:
    return round(users / members, 4) if members else None


def unit_tree(groups: Groups, rows: List[Row]) -> List[UsageUnitNode]:
    direct_rows: Dict[str, List[Row]] = defaultdict(list)
    for r in rows:
        if r.is_run:
            direct_rows[groups.user_unit.get(r.user)].append(r)
    direct_members = Counter(groups.active_users.values())

    def build(code: str, seen: Set[str]):
        if code in seen:
            return None, [], 0
        seen.add(code)
        own = direct_rows.get(code, [])
        all_rows, members = list(own), direct_members.get(code, 0)
        kids: List[UsageUnitNode] = []
        for child in groups.children.get(code, []):
            node, child_rows, child_members = build(child, seen)
            all_rows.extend(child_rows)
            members += child_members
            if node is not None:
                kids.append(node)
        if members == 0 and not all_rows:
            return None, all_rows, members
        f = figures(all_rows)
        kids.sort(key=lambda n: (-n.runs, n.name.lower()))
        node = UsageUnitNode(
            code=code, name=groups.units[code].name, members=members,
            direct_members=direct_members.get(code, 0), runs=f.runs, users=f.users,
            success_rate=f.success_rate, adoption_rate=_adoption(f.users, members),
            children=kids)
        return node, all_rows, members

    seen: Set[str] = set()
    out = [n for n in (build(code, seen)[0] for code in groups.roots) if n is not None]
    out.sort(key=lambda n: (-n.runs, n.name.lower()))
    return out


def team_rows(groups: Groups, rows: List[Row]) -> List[UsageTeamRow]:
    per: Dict[str, List[Row]] = defaultdict(list)
    for r in rows:
        if r.is_run:
            for t in groups.teams_for_run(r.user, r.at):
                per[t].append(r)
    members = groups.team_members()
    out: List[UsageTeamRow] = []
    for code in sorted(set(per) | set(members) - {NO_TEAM}):
        f = figures(per.get(code, []))
        if code == NO_TEAM:
            out.append(UsageTeamRow(code=NO_TEAM, runs=f.runs, users=f.users,
                                    success_rate=f.success_rate))
            continue
        team = groups.teams.get(code)
        n = len(members.get(code, set()))
        out.append(UsageTeamRow(
            code=code, name=team.name if team else code, members=n, runs=f.runs,
            users=f.users, success_rate=f.success_rate, adoption_rate=_adoption(f.users, n)))
    out.sort(key=lambda t: (t.code == NO_TEAM, -t.runs, (t.name or "").lower()))
    return out


def project_rows(groups: Groups, rows: List[Row]) -> List[UsageProjectRow]:
    per: Dict[str, List[Row]] = defaultdict(list)
    for r in rows:
        if r.is_run:
            for code in groups.projects_for_run(r.user, r.at):
                per[code].append(r)
    members = groups.project_members(groups.team_members())
    out: List[UsageProjectRow] = []
    for code in sorted(set(per) | set(members) - {NO_PROJECT}):
        f = figures(per.get(code, []))
        if code == NO_PROJECT:
            out.append(UsageProjectRow(code=NO_PROJECT, runs=f.runs, users=f.users,
                                       success_rate=f.success_rate))
            continue
        pr = groups.projects.get(code)
        team = groups.teams.get(pr.team) if pr and pr.team else None
        n = len(members.get(code, set()))
        out.append(UsageProjectRow(
            code=code, name=pr.name if pr else code, team=pr.team if pr else None,
            team_name=team.name if team else (pr.team if pr else None), members=n,
            runs=f.runs, users=f.users, success_rate=f.success_rate,
            adoption_rate=_adoption(f.users, n)))
    out.sort(key=lambda x: (x.code == NO_PROJECT, -x.runs, (x.name or "").lower()))
    return out


# ── Entry points ─────────────────────────────────────────────────────────────


def build_metrics(session: Session, user: User, date_from: Optional[str],
                  date_to: Optional[str], unit: Optional[str] = None,
                  team: Optional[str] = None, project: Optional[str] = None) -> UsageMetrics:
    started = _time.perf_counter()
    p = parse_period(date_from, date_to)
    groups = Groups(session, p)
    keep = groups.row_filter(unit or None, team or None, project or None)
    scope = scope_for(session, user)

    rows = load_rows(session, p.prev_start, p.end, scope)
    current = [r for r in rows if r.at >= p.start]
    previous = [r for r in rows if r.at < p.start]
    narrowed_cur = [r for r in current if keep(r)] if keep else current
    narrowed_prev = [r for r in previous if keep(r)] if keep else previous

    cur_f, prev_f = figures(narrowed_cur), figures(narrowed_prev)
    result = UsageMetrics(
        period=UsagePeriod(
            date_from=p.date_from.isoformat(), date_to=p.date_to.isoformat(),
            previous_from=p.prev_from.isoformat(), previous_to=p.prev_to.isoformat(),
            bucket=p.bucket, timezone=settings.app_timezone),
        scope=UsageScope(restricted=scope is not None,
                         dashboards=None if scope is None else len(scope)),
        filter=UsageFilter(unit=unit or None, team=team or None, project=project or None),
        summary=UsageSummary(current=cur_f, previous=prev_f, change=change(cur_f, prev_f)),
        timeline=timeline(narrowed_cur, p),
        dashboards=dashboard_rows(session, narrowed_cur, scope),
        units=unit_tree(groups, current),
        teams=team_rows(groups, current),
        projects=project_rows(groups, current),
    )
    logger.info(
        "Usage metrics: user=%s from=%s to=%s unit=%s team=%s project=%s scope=%s rows=%d "
        "elapsed_ms=%d", user.id, p.date_from, p.date_to, unit, team, project,
        "all" if scope is None else len(scope), len(rows),
        round((_time.perf_counter() - started) * 1000))
    return result


def dashboard_errors(session: Session, user: User, dashboard_id: int,
                     date_from: Optional[str], date_to: Optional[str],
                     unit: Optional[str] = None, team: Optional[str] = None,
                     limit: int = 10, project: Optional[str] = None) -> UsageErrors:
    p = parse_period(date_from, date_to)
    groups = Groups(session, p)
    keep = groups.row_filter(unit or None, team or None, project or None)
    scope = scope_for(session, user)
    if session.get(Dashboard, dashboard_id) is None or (
            scope is not None and dashboard_id not in scope):
        raise UsageNotFound("Dashboard not found")

    stmt = select(Execution.user_id, Execution.executed_at, Execution.status,
                  Execution.error_message).where(
        Execution.dashboard == dashboard_id,
        Execution.executed_at >= p.start, Execution.executed_at < p.end,
        Execution.error_message.is_not(None))
    counts: Counter = Counter()
    statuses: Dict[str, Set[str]] = defaultdict(set)
    for uid, at, status, message in session.exec(stmt):
        message = (message or "").strip()
        if not message:
            continue
        outcome, is_run = classify(status)
        if keep and not keep(Row(dashboard_id, uid, as_naive_utc(at), outcome, is_run, None)):
            continue
        counts[message] += 1
        statuses[message].add(outcome)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return UsageErrors(
        dashboard=dashboard_id, total_with_error=sum(counts.values()),
        items=[UsageErrorItem(message=m, count=c, statuses=sorted(statuses[m]))
               for m, c in ranked[:limit]])
