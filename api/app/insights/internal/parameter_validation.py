"""Parameter validation for dashboards (Dashboard Management, HU-AN02).

A parameter's value source is derived, never stored:

  context_binding set → GRANT  (value = the bound grant's recipient)
  else list set       → LIST   (the viewer picks one of the list's values)
  else                → INPUT  (the viewer types a value valid for data_type)

A grant-bound parameter may also carry a list, used as the fallback for viewers
who reach the dashboard through another grant. Everything raises ValueError
(routes map it to 400).
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional, Set

from sqlmodel import Session, select

from . import permissions_service
from .models import DashboardPermission
from ...admin.internal.models import List as ListModel, ListItem
from ...internal.list_values import validate_list_value
from ...internal.resource_permissions import SCOPE_PUBLIC

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIST_OF_VALUES = "LIST_OF_VALUES"

SOURCE_GRANT = "GRANT"
SOURCE_LIST = "LIST"
SOURCE_INPUT = "INPUT"


def value_source(param) -> str:
    if param.context_binding is not None:
        return SOURCE_GRANT
    if param.list:
        return SOURCE_LIST
    return SOURCE_INPUT


def validate_name(name: Optional[str]) -> str:
    value = (name or "").strip()
    if not NAME_RE.match(value) or len(value) > 100:
        raise ValueError(
            "A parameter name must use lowercase letters, digits and _, start with a "
            "letter and be at most 100 characters (e.g. date_from)")
    return value


MAX_VALUE_LENGTH = 1000


def value_problem(data_type: str, value: str, allowed: Optional[Set[str]]) -> Optional[str]:
    """Why ``value`` is not valid for a parameter — "list", "number", "boolean"
    or "date" — or None when it is. The one definition of a valid parameter
    value, shared by defaults (Management) and run values (Execute)."""
    if allowed is not None:
        return None if value in allowed else "list"
    if data_type == "NUMBER":
        try:
            if not Decimal(value).is_finite():
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return "number"
    elif data_type == "BOOLEAN":
        if value not in ("true", "false"):
            return "boolean"
    elif data_type == "DATE":
        try:
            if not DATE_RE.match(value):
                raise ValueError
            date.fromisoformat(value)
        except ValueError:
            return "date"
    return None


def validate_default(data_type: str, default: Optional[str], allowed: Optional[Set[str]]) -> None:
    if default is None or default == "":
        return
    problem = value_problem(data_type, default, allowed)
    if problem == "list":
        raise ValueError(f"Default '{default}' is not one of the list's values")
    if problem == "number":
        raise ValueError(f"Default '{default}' is not a number")
    if problem == "boolean":
        raise ValueError("A Boolean default must be 'true' or 'false'")
    if problem == "date":
        raise ValueError(f"Default '{default}' is not a date (YYYY-MM-DD)")


def validate_run_value(label: str, data_type: str, value: str, allowed: Optional[Set[str]]) -> None:
    """A value submitted to run a dashboard (specs/007-dashboard-catalog R7)."""
    if len(value) > MAX_VALUE_LENGTH:
        raise ValueError(f"'{label}' must be at most {MAX_VALUE_LENGTH} characters")
    problem = value_problem(data_type, value, allowed)
    if problem == "list":
        raise ValueError(f"'{label}' must be one of its list's values")
    if problem == "number":
        raise ValueError(f"'{label}' must be a number")
    if problem == "boolean":
        raise ValueError(f"'{label}' must be 'true' or 'false'")
    if problem == "date":
        raise ValueError(f"'{label}' must be a date (YYYY-MM-DD)")


def list_values(session: Session, code: str) -> Optional[Set[str]]:
    """The values of an active LIST_OF_VALUES list, or None when the list is
    missing, inactive or of another type (non-raising twin of validate_list)."""
    try:
        return validate_list(session, code)
    except ValueError:
        return None


def validate_list(session: Session, code: str) -> Set[str]:
    """The list must be an active LIST_OF_VALUES list; returns its values."""
    row = session.get(ListModel, code)
    if not row or not row.is_active or row.type != LIST_OF_VALUES:
        raise ValueError(f"'{code}' is not an active list of values")
    return set(session.exec(select(ListItem.value).where(ListItem.list == code)).all())


def validate_binding(session: Session, dashboard_id: int, permission_id: int) -> DashboardPermission:
    """A binding must be a live, non-PUBLIC grant of the same dashboard."""
    grant = session.get(DashboardPermission, permission_id)
    if (
        not grant
        or grant.dashboard != dashboard_id
        or permissions_service.is_revoked(grant)
        or grant.target_type == SCOPE_PUBLIC
    ):
        raise ValueError(
            "context_binding must be a live grant of this dashboard to a user, role, "
            "project, team or unit")
    return grant


def validate_parameter(session: Session, dashboard_id: int, fields: dict) -> None:
    """Check a parameter's final (merged) state as a whole."""
    label = (fields.get("label") or "").strip()
    if not label:
        raise ValueError("'label' cannot be blank")
    if len(label) > 100:
        raise ValueError("'label' must be at most 100 characters")
    data_type = fields.get("data_type")
    if not data_type:
        raise ValueError("'data_type' is required")
    validate_list_value(session, "PARAM_TYPE", data_type)
    allowed = validate_list(session, fields["list"]) if fields.get("list") else None
    if fields.get("context_binding") is not None:
        validate_binding(session, dashboard_id, fields["context_binding"])
    validate_default(data_type, fields.get("default_value"), allowed)
