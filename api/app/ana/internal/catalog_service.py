"""Dashboard Catalog reads (specs/007-dashboard-catalog, HU-AN04 / HU-AN05).

The catalog shows only active PUBLISHED dashboards reached by a live grant of
the caller (superusers: every published one). For a run, each parameter gets an
*effective* source for THIS viewer (research R3):

  context_binding set AND the bound grant is one of the caller's matching
  grants → GRANT (value = the grant's target_code, fixed)
  else list set → LIST (the viewer picks one of the list's values)
  else          → INPUT (the viewer types a value valid for data_type)

A binding the viewer did not come through — or a revoked one — falls back to
LIST/INPUT, exactly as SpecKit 006 defined it.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from sqlalchemy import func, or_
from sqlmodel import Session, select

from . import parameter_validation as pv
from . import permissions_service
from .models import (
    EXEC_SUCCESS, MODE_TAB, MODE_VIEWER, CatalogDashboard, Dashboard, Execution,
    FavoriteDashboard, LastValues, Parameter, RunForm, RunFormOption, RunFormParameter,
)
from .source_validation import SOURCE_INTERNAL_PAGE
from ...admin.internal.models import ListItem, User
from ...internal.status import normalize

PUBLISHED = "PUBLISHED"


@dataclass
class EffectiveParam:
    param: Parameter
    source: str                       # GRANT / LIST / INPUT
    bound_value: Optional[str] = None
    bound_label: Optional[str] = None
    allowed: Optional[Set[str]] = None  # LIST only; None = list unavailable

    @property
    def list_unavailable(self) -> bool:
        return self.source == pv.SOURCE_LIST and not self.allowed


def is_catalog_visible(dashboard: Optional[Dashboard]) -> bool:
    return bool(dashboard) and dashboard.is_active and normalize(dashboard.status) == PUBLISHED


def launch_mode(dashboard: Dashboard) -> str:
    return MODE_VIEWER if normalize(dashboard.sources_types) == SOURCE_INTERNAL_PAGE else MODE_TAB


def active_parameters(session: Session, dashboard_id: int) -> List[Parameter]:
    return list(session.exec(
        select(Parameter)
        .where(Parameter.dashboard == dashboard_id, Parameter.is_active == True)  # noqa: E712
        .order_by(Parameter.name)
    ).all())


def resolve_effective_parameters(
    session: Session, user: User, dashboard_id: int,
) -> List[EffectiveParam]:
    """Each active parameter with its source for this viewer (one query for the
    parameters, one for the caller's grants, one per distinct list)."""
    params = active_parameters(session, dashboard_id)
    if not params:
        return []
    grants = {g.id: g for g in permissions_service.dashboard_matching_grants(
        session, user, dashboard_id)}
    lists: Dict[str, Optional[Set[str]]] = {}
    out: List[EffectiveParam] = []
    for p in params:
        grant = grants.get(p.context_binding) if p.context_binding is not None else None
        if grant is not None:
            out.append(EffectiveParam(
                p, pv.SOURCE_GRANT, bound_value=grant.target_code,
                bound_label=f"{grant.target_type} {grant.target_code}"))
        elif p.list:
            if p.list not in lists:
                lists[p.list] = pv.list_values(session, p.list)
            out.append(EffectiveParam(p, pv.SOURCE_LIST, allowed=lists[p.list]))
        else:
            out.append(EffectiveParam(p, pv.SOURCE_INPUT))
    return out


def favorite_ids(session: Session, user: User, dashboard_ids: List[int]) -> set:
    """The subset of ``dashboard_ids`` the caller has marked as a favorite (one query)."""
    if not dashboard_ids:
        return set()
    return set(session.exec(
        select(FavoriteDashboard.dashboard).where(
            FavoriteDashboard.user_id == user.id,
            FavoriteDashboard.is_active == True,  # noqa: E712
            FavoriteDashboard.dashboard.in_(dashboard_ids),
        )
    ).all())


def _parameter_counts(session: Session, dashboard_ids: List[int]) -> Dict[int, int]:
    if not dashboard_ids:
        return {}
    rows = session.exec(
        select(Parameter.dashboard, func.count())
        .where(Parameter.dashboard.in_(dashboard_ids), Parameter.is_active == True)  # noqa: E712
        .group_by(Parameter.dashboard)
    ).all()
    return {d: n for d, n in rows}


def list_catalog(session: Session, user: User, skip: int, limit: int) -> List[CatalogDashboard]:
    """Published, active dashboards the caller can access, filtered BEFORE
    pagination; scopes, favorites and parameter counts in one query each."""
    query = select(Dashboard).where(
        Dashboard.is_active == True,  # noqa: E712
        # Legacy rows may carry the list sort prefix ("2-PUBLISHED"), see app/internal/status.py.
        or_(Dashboard.status == PUBLISHED, Dashboard.status.like(f"%-{PUBLISHED}")),
    )
    if not user.is_superuser:
        access = permissions_service.accessible_dashboards(session, user)
        if not access:
            return []
        query = query.where(Dashboard.id.in_(list(access)))
    rows = session.exec(
        query.order_by(Dashboard.name, Dashboard.id).offset(skip).limit(limit)
    ).all()
    ids = [r.id for r in rows]
    scopes = permissions_service.dashboards_user_scopes(session, user, ids)
    favorites = favorite_ids(session, user, ids)
    counts = _parameter_counts(session, ids)
    return [
        CatalogDashboard(
            id=r.id, name=r.name, description=r.description, type=r.type,
            sources_types=r.sources_types, tags=r.tags, detail=r.detail,
            created_at=r.created_at, is_favorite=r.id in favorites,
            permission_scopes=scopes.get(r.id, []), parameter_count=counts.get(r.id, 0),
        )
        for r in rows
    ]


def _has_success(session: Session, user: User, dashboard_id: int) -> bool:
    return session.exec(
        select(Execution.id).where(
            Execution.user_id == user.id,
            Execution.dashboard == dashboard_id,
            Execution.status == EXEC_SUCCESS,
        ).limit(1)
    ).first() is not None


def build_run_form(session: Session, user: User, dashboard: Dashboard) -> RunForm:
    effective = resolve_effective_parameters(session, user, dashboard.id)
    codes = sorted({e.param.list for e in effective if e.source == pv.SOURCE_LIST})
    options: Dict[str, List[RunFormOption]] = {}
    if codes:
        items = session.exec(
            select(ListItem)
            .where(ListItem.list.in_(codes), ListItem.is_active == True)  # noqa: E712
            .order_by(ListItem.list, ListItem.sort_order, ListItem.lang)
        ).all()
        for it in items:
            options.setdefault(it.list, []).append(RunFormOption(
                value=it.value, lang=it.lang, label=it.label, sort_order=it.sort_order))

    parameters = []
    for e in effective:
        p = e.param
        item = RunFormParameter(
            name=p.name, label=p.label, data_type=p.data_type, is_required=p.is_required,
            default_value=p.default_value, effective_source=e.source,
        )
        if e.source == pv.SOURCE_GRANT:
            item.bound_value, item.bound_label = e.bound_value, e.bound_label
        elif e.source == pv.SOURCE_LIST:
            item.list = p.list
            item.list_unavailable = e.list_unavailable
            item.options = [] if e.list_unavailable else options.get(p.list, [])
        parameters.append(item)

    return RunForm(
        dashboard=dashboard.id, name=dashboard.name, mode=launch_mode(dashboard),
        has_last_values=_has_success(session, user, dashboard.id), parameters=parameters,
    )


def payload_values(payload) -> Dict[str, str]:
    """``payload.values``, or the payload itself for the legacy flat shape."""
    if not isinstance(payload, dict):
        return {}
    values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    return {k: str(v) for k, v in values.items() if v is not None and not isinstance(v, (dict, list))}


def last_values(session: Session, user: User, dashboard_id: int) -> LastValues:
    """FR-009a: the caller's most recent SUCCESS run, re-checked against the
    current parameter definitions. GRANT values are never taken from it,
    removed parameters are skipped and invalid values are left out (so the
    window keeps the default)."""
    row = session.exec(
        select(Execution).where(
            Execution.user_id == user.id,
            Execution.dashboard == dashboard_id,
            Execution.status == EXEC_SUCCESS,
        ).order_by(Execution.executed_at.desc(), Execution.id.desc()).limit(1)
    ).first()
    if row is None:
        return LastValues()
    stored = payload_values(row.payload)
    values: Dict[str, str] = {}
    for e in resolve_effective_parameters(session, user, dashboard_id):
        name = e.param.name
        if e.source == pv.SOURCE_GRANT or name not in stored or e.list_unavailable:
            continue
        value = stored[name]
        allowed = e.allowed if e.source == pv.SOURCE_LIST else None
        if len(value) <= pv.MAX_VALUE_LENGTH and pv.value_problem(e.param.data_type, value, allowed) is None:
            values[name] = value
    return LastValues(values=values, executed_at=row.executed_at)
