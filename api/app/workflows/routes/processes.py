"""Processes (Process Management — specs/009-process-management, HU-PR01).

The process inventory. A new process lands in DRAFT and its status then follows
workflows/internal/status_service.py; creating one may carry its Related links,
written in the same transaction. Access is the PROC/PROCESSES privilege only:
read for GETs, edit for writes.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..internal import process_service, relation_rules
from ..internal.dependencies import get_db_session
from ..internal.models import (
    AssetOption, InitOption, OwnerOption, Process, ProcessCreate, ProcessDetail,
    ProcessFormOptions, ProcessOption, ProcessRead, ProcessUpdate, UnitOption,
)
from ...admin.internal.models import BusinessUnit, User
from ...inits.internal.models import Initiative
from ...internal.permissions import has_privilege, require_privilege
from ...lib.internal.models import Asset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/processes", tags=["processes"])

read_access = require_privilege("PROC", "PROCESSES", can_edit=False)
edit_access = require_privilege("PROC", "PROCESSES", can_edit=True)


def _active_or_404(session: Session, code: str) -> Process:
    try:
        return process_service.get_active(session, code)
    except process_service.ProcessNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _write(session: Session, action):
    """Run a write, commit once, and map service errors to HTTP codes."""
    try:
        result = action()
        session.commit()
        return result
    except process_service.ProcessConflict as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="The process conflicts with an existing one.")


@router.get("/", response_model=List[ProcessRead])
def get_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    type: Optional[str] = None,
    status: Optional[str] = None,
    unit: Optional[str] = None,
    q: Optional[str] = None,
    session: Session = Depends(get_db_session),
    _: User = Depends(read_access),
) -> List[ProcessRead]:
    """Active processes ordered by code, with parent / unit / owner names."""
    return process_service.list_processes(session, skip, limit, type, status, unit, q)


# Static path first, so it is not captured by `/{code}`.


@router.get("/form-options", response_model=ProcessFormOptions)
def get_form_options(
    session: Session = Depends(get_db_session),
    current: User = Depends(read_access),
) -> ProcessFormOptions:
    """
    Everything the process dialog needs in one call: active processes, units,
    owners, assets and initiatives (names only), the relation compatibility
    rules, and whether the caller may edit. Its own endpoint so Process
    Management never depends on ADMIN/LIB/INITS privileges.
    """
    active = lambda model: model.is_active == True  # noqa: E712,E731
    processes = session.exec(select(Process).where(active(Process)).order_by(Process.code)).all()
    units = session.exec(
        select(BusinessUnit).where(active(BusinessUnit)).order_by(BusinessUnit.name)).all()
    owners = session.exec(
        select(User).where(active(User)).order_by(User.first_name, User.last_name)).all()
    assets = session.exec(select(Asset).where(active(Asset)).order_by(Asset.name)).all()
    inits = session.exec(
        select(Initiative).where(active(Initiative)).order_by(Initiative.name)).all()
    return ProcessFormOptions(
        can_edit=has_privilege(session, current, "PROC", "PROCESSES", can_edit=True),
        processes=[ProcessOption(code=p.code, name=p.name, type=p.type) for p in processes],
        units=[UnitOption(code=u.code, name=u.name) for u in units],
        owners=[OwnerOption(id=u.id, name=process_service.full_name(u)) for u in owners],
        assets=[AssetOption(id=a.id, name=a.name, category=a.category) for a in assets],
        initiatives=[InitOption(id=i.id, name=i.name) for i in inits],
        relation_rules=relation_rules.RULES,
    )


@router.get("/{code}", response_model=ProcessDetail)
def get(
    code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(read_access),
) -> ProcessDetail:
    """One process plus `allowed_statuses` (current status first, then its moves)."""
    return process_service.detail(session, _active_or_404(session, code))


@router.post("/", response_model=ProcessDetail, status_code=201)
def create(
    body: ProcessCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(edit_access),
) -> ProcessDetail:
    """
    Create a process in DRAFT, optionally with its `relations`, `assets` and
    `inits`. All-or-nothing: any invalid field or link writes nothing.
    """
    process = _write(session, lambda: process_service.create_process(session, body, current))
    session.refresh(process)
    logger.info("process created", extra={"code": process.code, "user": current.id})
    return process_service.detail(session, process)


@router.put("/{code}", response_model=ProcessDetail)
def update(
    code: str,
    body: ProcessUpdate,
    session: Session = Depends(get_db_session),
    _: User = Depends(edit_access),
) -> ProcessDetail:
    """Core fields only (partial). The code is immutable; links are untouched."""
    process = _active_or_404(session, code)
    process = _write(session, lambda: process_service.update_process(session, process, body))
    session.refresh(process)
    return process_service.detail(session, process)


@router.delete("/{code}", response_model=ProcessRead)
def delete(
    code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(edit_access),
) -> ProcessRead:
    """Logical removal; 409 while the process has active sub-processes."""
    process = _active_or_404(session, code)
    process = _write(session, lambda: process_service.remove_process(session, process))
    session.refresh(process)
    return process_service._project([process], session)[0]
