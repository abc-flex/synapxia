"""Process inventory rules (Process Management, HU-PR01).

Owns core-field validation, the acyclic parent hierarchy, the status lifecycle
hook, the type-change guard and the all-or-nothing create. Nothing here
commits: the routes own the transaction, so a create and its links (US5) land
together or not at all.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlmodel import Session, or_, select

from . import links_service, relation_rules, status_service
from .models import Process, ProcessCreate, ProcessDetail, ProcessRead, ProcessUpdate
from ...admin.internal.models import BusinessUnit, User
from ...internal.list_values import validate_list_value

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,49}$")
NAME_MAX = 100
DESCRIPTION_MAX = 500


class ProcessNotFound(LookupError):
    """Unknown or removed process (→ 404)."""


class ProcessConflict(ValueError):
    """Duplicate code, or removal blocked by active children (→ 409)."""


def full_name(user: User) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username


def normalize_code(code: Optional[str]) -> str:
    code = (code or "").strip().upper()
    if not CODE_RE.match(code):
        raise ValueError(
            "The code must be 1–50 characters: letters A–Z, digits, '_' or '-', "
            "starting with a letter or digit.")
    return code


def get_active(session: Session, code: str) -> Process:
    process = session.get(Process, (code or "").strip().upper())
    if not process or not process.is_active:
        raise ProcessNotFound(f"Process '{code}' not found")
    return process


# ── Validation ───────────────────────────────────────────────────────────────


def _validate_text(values: Dict[str, Any], creating: bool) -> None:
    if creating or "name" in values:
        name = (values.get("name") or "").strip()
        if not name:
            raise ValueError("The name is required.")
        if len(name) > NAME_MAX:
            raise ValueError(f"The name can have at most {NAME_MAX} characters.")
        values["name"] = name
    if values.get("description") is not None:
        if len(values["description"]) > DESCRIPTION_MAX:
            raise ValueError(f"The description can have at most {DESCRIPTION_MAX} characters.")
    if values.get("tags") is not None:
        tags = [str(t).strip() for t in values["tags"]]
        if any(not t for t in tags):
            raise ValueError("Tags cannot be blank.")
        values["tags"] = tags


def _validate_refs(session: Session, values: Dict[str, Any], creating: bool) -> None:
    if creating or "type" in values:
        if not (values.get("type") or "").strip():
            raise ValueError("The type is required.")
        validate_list_value(session, "PROCESS_TYPE", values["type"])
    if values.get("unit") is not None:
        unit = session.get(BusinessUnit, values["unit"])
        if not unit or not unit.is_active:
            raise ValueError(f"Business unit '{values['unit']}' does not exist or is inactive.")
    if "owner" in values:
        owner = session.get(User, values["owner"]) if values["owner"] is not None else None
        if not owner or not owner.is_active:
            raise ValueError("The owner must be an active user.")
    if values.get("parent") is not None:
        values["parent"] = values["parent"].strip().upper()
        parent = session.get(Process, values["parent"])
        if not parent or not parent.is_active:
            raise ValueError(f"Parent process '{values['parent']}' does not exist or was removed.")


def check_parent_cycle(session: Session, code: str, parent: Optional[str]) -> None:
    """ValueError when making ``parent`` the parent of ``code`` closes a loop.
    One projected query, then an upward walk capped at the row count."""
    if parent is None:
        return
    if parent == code:
        raise ValueError("A process cannot be its own parent.")
    parents = dict(session.exec(select(Process.code, Process.parent)).all())
    node, steps = parent, 0
    while node is not None and steps <= len(parents):
        if node == code:
            raise ValueError(
                f"'{parent}' is a sub-process of '{code}'; a process cannot be nested under "
                "its own descendant.")
        node = parents.get(node)
        steps += 1


# ── Reads ────────────────────────────────────────────────────────────────────


def _project(rows: List[Process], session: Session) -> List[ProcessRead]:
    """Resolve parent / unit / owner names with one query each (no N+1)."""
    parent_codes = {r.parent for r in rows if r.parent}
    unit_codes = {r.unit for r in rows if r.unit}
    owner_ids = {r.owner for r in rows}
    parents = {
        p.code: p.name
        for p in session.exec(select(Process).where(Process.code.in_(list(parent_codes)))).all()
    } if parent_codes else {}
    units = {
        u.code: u.name
        for u in session.exec(select(BusinessUnit).where(BusinessUnit.code.in_(list(unit_codes)))).all()
    } if unit_codes else {}
    owners = {
        u.id: full_name(u)
        for u in session.exec(select(User).where(User.id.in_(list(owner_ids)))).all()
    } if owner_ids else {}
    return [
        ProcessRead(
            **r.model_dump(exclude={"is_active"}),
            parent_name=parents.get(r.parent), unit_name=units.get(r.unit),
            owner_name=owners.get(r.owner),
        )
        for r in rows
    ]


def list_processes(
    session: Session, skip: int, limit: int, type: Optional[str] = None,
    status: Optional[str] = None, unit: Optional[str] = None, q: Optional[str] = None,
) -> List[ProcessRead]:
    query = select(Process).where(Process.is_active == True)  # noqa: E712
    if type:
        query = query.where(Process.type == type)
    if status:
        query = query.where(Process.status == status)
    if unit:
        query = query.where(Process.unit == unit)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(or_(
            Process.code.ilike(like), Process.name.ilike(like), Process.description.ilike(like)))
    rows = session.exec(query.order_by(Process.code).offset(skip).limit(limit)).all()
    return _project(list(rows), session)


def detail(session: Session, process: Process) -> ProcessDetail:
    read = _project([process], session)[0]
    return ProcessDetail(
        **read.model_dump(), allowed_statuses=status_service.allowed_statuses_for(process.status))


# ── Writes (no commit) ───────────────────────────────────────────────────────


def create_process(session: Session, data: ProcessCreate, caller: User) -> Process:
    """The process plus every staged link, inside the caller's transaction."""
    code = normalize_code(data.code)
    if session.get(Process, code) is not None:
        raise ProcessConflict(f"The code '{code}' is already in use.")
    status = status_service.validate_create_status(data.status)
    values = data.model_dump(exclude={"code", "status", "relations", "assets", "inits"})
    if values.get("owner") is None:
        values["owner"] = caller.id
    _validate_text(values, creating=True)
    _validate_refs(session, values, creating=True)
    check_parent_cycle(session, code, values.get("parent"))

    process = Process(code=code, status=status, **values)
    session.add(process)
    session.flush()
    if data.relations:
        links_service.replace_relations(session, process, data.relations)
    if data.assets:
        links_service.replace_assets(session, process, data.assets)
    if data.inits:
        links_service.replace_inits(session, process, data.inits)
    return process


def update_process(session: Session, process: Process, data: ProcessUpdate) -> Process:
    values = data.model_dump(exclude_unset=True)
    values.pop("code", None)
    if "status" in values:
        if values["status"] is None:
            values.pop("status")
        else:
            status_service.validate_transition(process.status, values["status"])
            values["status"] = values["status"].strip().upper()
    _validate_text(values, creating=False)
    _validate_refs(session, values, creating=False)
    if "parent" in values:
        check_parent_cycle(session, process.code, values["parent"])
    if "type" in values and values["type"] != process.type:
        broken = relation_rules.incompatible_links_after_type_change(
            session, process.code, values["type"])
        if broken:
            listed = ", ".join(f"{r.source} {r.type} {r.target}" for r in broken)
            raise ValueError(
                f"Changing the type to {values['type']} would break these links: {listed}. "
                "Remove or change them first.")
    for field, value in values.items():
        setattr(process, field, value)
    process.updated_at = datetime.utcnow()
    session.add(process)
    session.flush()
    return process


def remove_process(session: Session, process: Process) -> Process:
    child = session.exec(
        select(Process.code).where(Process.parent == process.code, Process.is_active == True)  # noqa: E712
    ).first()
    if child:
        raise ProcessConflict(
            f"'{process.code}' still has active sub-processes (e.g. '{child}'); move or "
            "remove them first.")
    process.is_active = False
    process.updated_at = datetime.utcnow()
    session.add(process)
    session.flush()
    return process
