"""List-backed core field validation for dashboards (Dashboard Management).

Same semantics as ``inits/internal/list_validation.py``; the value check itself
is shared (app/internal/list_values.py). Raises ValueError (routes map to 400).
"""
from typing import Iterable

from sqlmodel import Session

from ...internal.list_values import validate_list_value

# List-backed core fields and the list each value must come from.
LIST_FIELDS = {
    "type": "DASHBOARD_TYPE",
    "sources_types": "SOURCE_TYPE",
    "status": "DASHBOARD_STATUS",
}
REQUIRED_FIELDS = ("name", "type", "sources_types", "source_url")


def validate_core_fields(
    session: Session, fields: dict, required: Iterable[str] = (),
) -> None:
    """Check the sent core fields: listed `required` ones must be non-blank, and
    every list-backed one must hold a value of its list."""
    for field in required:
        if field in fields and not (fields[field] or "").strip():
            raise ValueError(f"'{field}' cannot be blank")
    for field, list_code in LIST_FIELDS.items():
        if field in fields:
            validate_list_value(session, list_code, fields[field])
