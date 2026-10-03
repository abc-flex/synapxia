"""Dashboard parameters (Dashboard Management → Parameters tab, HU-AN02).

Nested under ``/api/dashboards/{dashboard_id}/parameters`` and keyed by the
parameter name (part of the primary key, so never renamed). Reads need VIEW on
the dashboard, writes MANAGE. Removal is logical; re-adding a removed name
restores it. Each parameter's value source (GRANT / LIST / INPUT) is derived
from its binding and list — see insights/internal/parameter_validation.py.
"""
import logging
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from ..internal import parameter_validation as pv
from ..internal import permissions_service
from ..internal.dependencies import get_db_session
from ..internal.models import (
    Dashboard, DashboardPermission, Parameter, ParameterCreate, ParameterRead, ParameterUpdate,
)
from ...admin.internal.models import User
from ...internal.permissions import require_privilege

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboards", tags=["dashboard_parameters"])

MUTABLE = ("label", "data_type", "default_value", "is_required", "list", "context_binding")


def _guard(check, session: Session, user: User, dashboard_id: int) -> None:
    dashboard = session.get(Dashboard, dashboard_id)
    if not dashboard or not dashboard.is_active:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    try:
        check(session, user, dashboard_id)
    except permissions_service.DashboardAccessForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


def _binding_labels(session: Session, params: List[Parameter]) -> Dict[int, str]:
    """`"<TARGET_TYPE> <target_code>"` per bound grant id — one batched query."""
    ids = sorted({p.context_binding for p in params if p.context_binding is not None})
    if not ids:
        return {}
    grants = session.exec(select(DashboardPermission).where(DashboardPermission.id.in_(ids))).all()
    return {g.id: f"{g.target_type} {g.target_code}" for g in grants}


def _read(param: Parameter, labels: Dict[int, str]) -> ParameterRead:
    return ParameterRead(
        **param.model_dump(),
        value_source=pv.value_source(param),
        binding_label=labels.get(param.context_binding) if param.context_binding is not None else None,
    )


def _active_param(session: Session, dashboard_id: int, name: str) -> Parameter:
    param = session.get(Parameter, (dashboard_id, name))
    if not param or not param.is_active:
        raise HTTPException(status_code=404, detail=f"Parameter '{name}' not found")
    return param


def _normalise(fields: dict) -> dict:
    """Trim text; an empty optional value means "none"."""
    out = dict(fields)
    if "label" in out and out["label"] is not None:
        out["label"] = out["label"].strip()
    for key in ("default_value", "list"):
        if key in out and isinstance(out[key], str):
            out[key] = out[key].strip() or None
    return out


@router.get("/{dashboard_id}/parameters", response_model=List[ParameterRead])
def get_parameters(
    dashboard_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=False)),
) -> List[ParameterRead]:
    """Active parameters of a dashboard, in declaration order. Requires VIEW."""
    _guard(permissions_service.require_dashboard_view, session, current, dashboard_id)
    params = session.exec(
        select(Parameter)
        .where(Parameter.dashboard == dashboard_id, Parameter.is_active == True)  # noqa: E712
        .order_by(Parameter.created_at, Parameter.name)
        .offset(skip).limit(limit)
    ).all()
    labels = _binding_labels(session, params)
    return [_read(p, labels) for p in params]


@router.post("/{dashboard_id}/parameters", response_model=ParameterRead, status_code=201)
def create_parameter(
    dashboard_id: int,
    payload: ParameterCreate,
    response: Response,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> ParameterRead:
    """
    Declare a parameter. Requires MANAGE. An active parameter with the same
    name → 409; a removed one is restored with the new values (200).
    """
    _guard(permissions_service.require_dashboard_manage, session, current, dashboard_id)
    fields = _normalise(payload.model_dump())
    try:
        name = pv.validate_name(fields.pop("name"))
        pv.validate_parameter(session, dashboard_id, fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    existing = session.get(Parameter, (dashboard_id, name))
    if existing and existing.is_active:
        raise HTTPException(status_code=409, detail=f"Parameter '{name}' already exists")
    if existing:
        for key in MUTABLE:
            setattr(existing, key, fields.get(key))
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        param = existing
        response.status_code = 200
    else:
        param = Parameter(dashboard=dashboard_id, name=name, **{k: fields.get(k) for k in MUTABLE})
        if param.is_required is None:
            param.is_required = False
    session.add(param)
    session.commit()
    session.refresh(param)
    logger.info("Dashboard parameter saved: dashboard=%s name=%s by user=%s",
                dashboard_id, name, current.id)
    return _read(param, _binding_labels(session, [param]))


@router.put("/{dashboard_id}/parameters/{name}", response_model=ParameterRead)
def update_parameter(
    dashboard_id: int,
    name: str,
    payload: ParameterUpdate,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> ParameterRead:
    """
    Update a parameter's label, type, required flag, default, list or binding
    (send `null` to clear an optional one). The name cannot change. The result
    is validated as a whole — e.g. a new data type re-checks the stored default.
    """
    _guard(permissions_service.require_dashboard_manage, session, current, dashboard_id)
    param = _active_param(session, dashboard_id, name)
    changes = _normalise(payload.model_dump(exclude_unset=True))
    if changes.get("is_required") is None:
        changes.pop("is_required", None)
    merged = {key: changes.get(key, getattr(param, key)) for key in MUTABLE}
    try:
        pv.validate_parameter(session, dashboard_id, merged)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    for key, value in changes.items():
        setattr(param, key, value)
    param.updated_at = datetime.utcnow()
    session.add(param)
    session.commit()
    session.refresh(param)
    return _read(param, _binding_labels(session, [param]))


@router.delete("/{dashboard_id}/parameters/{name}", response_model=ParameterRead)
def delete_parameter(
    dashboard_id: int,
    name: str,
    session: Session = Depends(get_db_session),
    current: User = Depends(require_privilege("ANA", "DASHBOARDS", can_edit=True)),
) -> ParameterRead:
    """Logically remove a parameter. Requires MANAGE."""
    _guard(permissions_service.require_dashboard_manage, session, current, dashboard_id)
    param = _active_param(session, dashboard_id, name)
    param.is_active = False
    param.updated_at = datetime.utcnow()
    session.add(param)
    session.commit()
    session.refresh(param)
    logger.info("Dashboard parameter removed: dashboard=%s name=%s by user=%s",
                dashboard_id, name, current.id)
    return _read(param, _binding_labels(session, [param]))
