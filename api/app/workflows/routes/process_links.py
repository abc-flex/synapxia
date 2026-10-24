"""Process links (Process Management — specs/009-process-management, HU-PR02–04).

One GET and one PUT per Related tab. The PUT takes the tab's whole desired set
and applies it in one transaction (workflows/internal/links_service.py), so a
tab is never left half saved.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..internal import links_service, process_service
from ..internal.dependencies import get_db_session
from ..internal.models import (
    AssetsReplace, InitsReplace, Process, ProcessAssetRead, ProcessInitRead,
    ProcessRelationRead, RelationsReplace,
)
from ...admin.internal.models import User
from ...internal.permissions import require_privilege

router = APIRouter(prefix="/api/processes", tags=["processes"])

read_access = require_privilege("PROC", "PROCESSES", can_edit=False)
edit_access = require_privilege("PROC", "PROCESSES", can_edit=True)


def _active_or_404(session: Session, code: str) -> Process:
    try:
        return process_service.get_active(session, code)
    except process_service.ProcessNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _replace(session: Session, action) -> None:
    try:
        action()
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{code}/relations", response_model=List[ProcessRelationRead])
def get_relations(
    code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(read_access),
) -> List[ProcessRelationRead]:
    """Outgoing relations plus undirected (Interacts With) ones where this
    process is the target; `target` is always the other process."""
    process = _active_or_404(session, code)
    return links_service.list_relations(session, process.code)


@router.put("/{code}/relations", response_model=List[ProcessRelationRead])
def put_relations(
    code: str,
    body: RelationsReplace,
    session: Session = Depends(get_db_session),
    _: User = Depends(edit_access),
) -> List[ProcessRelationRead]:
    process = _active_or_404(session, code)
    _replace(session, lambda: links_service.replace_relations(session, process, body.relations))
    return links_service.list_relations(session, process.code)


@router.get("/{code}/assets", response_model=List[ProcessAssetRead])
def get_assets(
    code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(read_access),
) -> List[ProcessAssetRead]:
    process = _active_or_404(session, code)
    return links_service.list_assets(session, process.code)


@router.put("/{code}/assets", response_model=List[ProcessAssetRead])
def put_assets(
    code: str,
    body: AssetsReplace,
    session: Session = Depends(get_db_session),
    _: User = Depends(edit_access),
) -> List[ProcessAssetRead]:
    process = _active_or_404(session, code)
    _replace(session, lambda: links_service.replace_assets(session, process, body.assets))
    return links_service.list_assets(session, process.code)


@router.get("/{code}/inits", response_model=List[ProcessInitRead])
def get_inits(
    code: str,
    session: Session = Depends(get_db_session),
    _: User = Depends(read_access),
) -> List[ProcessInitRead]:
    process = _active_or_404(session, code)
    return links_service.list_inits(session, process.code)


@router.put("/{code}/inits", response_model=List[ProcessInitRead])
def put_inits(
    code: str,
    body: InitsReplace,
    session: Session = Depends(get_db_session),
    _: User = Depends(edit_access),
) -> List[ProcessInitRead]:
    process = _active_or_404(session, code)
    _replace(session, lambda: links_service.replace_inits(session, process, body.inits))
    return links_service.list_inits(session, process.code)
