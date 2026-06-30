"""Standardized API response envelope (success + error).

Every JSON response under ``/api/`` — EXCEPT ``/api/auth/*`` — is wrapped by the
middleware + exception handlers in ``app/main.py`` into one predictable shape so
the UI (``ui/src/lib/api.ts``) can consume a single format:

    success → {"data": <payload>, "error": null, "meta": {...}}
    error   → {"data": null, "error": {"code", "message", "details"}, "meta": {}}

Intentionally left in their NATIVE shapes (not wrapped):
  - ``/api/auth/*``  — the fastapi-users contract + the bespoke fetches in
    ``ui/src/lib/auth.ts`` read raw ``{access_token}`` / ``UserRead`` / ``{detail}``.
  - ``/health``, ``/`` (root inventory), ``/docs``, ``/openapi.json`` — meta/health
    surfaces consumed by tooling, not the data layer.

This keeps the refactor central: the wrapping lives here + in ``main.py``; no
per-endpoint edits.
"""
from typing import Any, Optional

from pydantic import BaseModel

API_PREFIX = "/api/"
AUTH_PREFIX = "/api/auth/"


def should_wrap(path: str) -> bool:
    """True for the data/CRUD endpoints that get the envelope.

    Everything under ``/api/`` except the auth subtree. ``/health``, ``/`` and
    the docs/openapi surfaces fall outside ``/api/`` and are never wrapped.
    """
    return path.startswith(API_PREFIX) and not path.startswith(AUTH_PREFIX)


class ErrorBody(BaseModel):
    """The ``error`` member of the envelope (null on success)."""

    code: int
    message: str
    details: Optional[Any] = None


class ResponseMeta(BaseModel):
    """The ``meta`` member — pagination echo for list endpoints (no COUNT query)."""

    skip: Optional[int] = None
    limit: Optional[int] = None
    count: Optional[int] = None


def success_envelope(data: Any, meta: Optional[dict] = None) -> dict:
    return {"data": data, "error": None, "meta": meta or {}}


def error_envelope(code: int, message: Any, details: Any = None) -> dict:
    return {
        "data": None,
        "error": {"code": code, "message": message, "details": details},
        "meta": {},
    }


def build_meta(query_params, payload: Any) -> dict:
    """Echo ``skip``/``limit`` from the request and ``count`` for list payloads.

    Deliberately does NOT compute a grand ``total`` — that would require a COUNT
    query in every list endpoint (a separate, larger change). See the PR notes.
    """
    meta: dict = {}
    for key in ("skip", "limit"):
        raw = query_params.get(key)
        if raw is not None:
            try:
                meta[key] = int(raw)
            except (TypeError, ValueError):
                pass
    if isinstance(payload, list):
        meta["count"] = len(payload)
    return meta
