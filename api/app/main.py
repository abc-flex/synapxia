import json
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from starlette.datastructures import MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from .internal.responses import (
    build_meta,
    error_envelope,
    should_wrap,
    success_envelope,
)
from .auth import routes as auth_routes

from .admin.routes import health as admin_health_router
from .admin.routes import profiles as profiles_router
from .admin.routes import modules as modules_router
from .admin.routes import lists as lists_router
from .admin.routes import list_items as list_items_router
from .admin.routes import business_units as business_units_router
from .admin.routes import users as users_router
from .admin.routes import options as options_router
from .admin.routes import privileges as privileges_router

from .taxo.routes import categories as categories_router
from .taxo.routes import features as features_router
from .taxo.routes import specifications as specifications_router

from .lib.routes import assets as assets_router
from .lib.routes import characterizations as characterizations_router
from .lib.routes import favorites as favorites_router
from .lib.routes import actions as actions_router
from .lib.routes import asset_relations as asset_relations_router
from .lib.routes import asset_permissions as asset_permissions_router

from .collab.routes import teams as teams_router
from .collab.routes import assignments as assignments_router
from .collab.routes import projects as projects_router
from .collab.routes import dimensions as dimensions_router
from .collab.routes import metrics as metrics_router
from .collab.routes import roles as roles_router

from .inits.routes import criterias as criterias_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SynapxIA API",
    version="1.0.0",
    description="API for AI adoption management - System for Insight, Adoption, Practice & eXpansion through Intelligent Agents",
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User authentication endpoints (login, register, profile)",
        },
        {
            "name": "health",
            "description": "Health check endpoints",
        },
        {
            "name": "profiles",
            "description": "Profile management operations",
        },
        {
            "name": "modules",
            "description": "Module management operations",
        },
        {
            "name": "lists",
            "description": "List management operations",
        },
        {
            "name": "list_items",
            "description": "List item management operations",
        },
        {
            "name": "units",
            "description": "Unit management operations",
        },
        {
            "name": "users",
            "description": "User management operations",
        },
        {
            "name": "options",
            "description": "Option management operations",
        },
        {
            "name": "privileges",
            "description": "Privilege management operations",
        },
        {
            "name": "categories",
            "description": "Category management operations",
        },
        {
            "name": "features",
            "description": "Feature management operations",
        },
        {
            "name": "specifications",
            "description": "Specification management operations",
        },
        {
            "name": "assets",
            "description": "Asset management operations",
        },
        {
            "name": "characterizations",
            "description": "Characterization management operations",
        },
        {
            "name": "favorites",
            "description": "Favorite management operations",
        },
        {
            "name": "actions",
            "description": "Action management operations",
        },
        {
            "name": "asset_relations",
            "description": "Asset relation management operations",
        },
        {
            "name": "asset_permissions",
            "description": "Asset permission management operations",
        },
        {
            "name": "teams",
            "description": "Team management operations",
        },
        {
            "name": "roles",
            "description": "Role management operations",
        },
        {
            "name": "assignments",
            "description": "Assignment management operations",
        },
        {
            "name": "projects",
            "description": "Project management operations",
        },
        {
            "name": "dimensions",
            "description": "Dimension management operations",
        },
        {
            "name": "metrics",
            "description": "Metric management operations",
        },
        {
            "name": "criterias",
            "description": "Initiative evaluation criteria management operations",
        },
    ],
)

# ────────────────────────────────────────────────────────────────────────
# ForwardedHostMiddleware — uvicorn's --proxy-headers sets scheme + client
# from X-Forwarded-Proto / X-Forwarded-For, but NOT the request's Host.
# Without this, FastAPI's trailing-slash redirects build the Location
# header from the internal container hostname (`http://synapxia-api:80/...`)
# — unreachable from the browser → "Failed to fetch".
#
# This rewrites the Host header from X-Forwarded-Host (set by the Vite
# proxy via `xfwd: true` in dev and automatically by Vercel rewrites in
# prod) so all generated URLs use the public origin. Only applied for
# HTTP scope; trusted IPs gating is handled upstream by uvicorn's
# `--forwarded-allow-ips`.
# ────────────────────────────────────────────────────────────────────────
class ForwardedHostMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        forwarded_host = headers.get(b"x-forwarded-host")
        if forwarded_host:
            # Replace the Host header in scope so request.url.netloc picks
            # it up. List of (bytes, bytes) per ASGI spec.
            new_headers = []
            for k, v in scope["headers"]:
                if k == b"host":
                    new_headers.append((b"host", forwarded_host))
                else:
                    new_headers.append((k, v))
            scope = {**scope, "headers": new_headers}

        await self.app(scope, receive, send)


# Configure CORS
# allow_origins=["*"] + allow_credentials=True is invalid per the CORS spec —
# browsers reject it. When no specific origins are configured we fall back to
# wildcard WITHOUT credentials (safe for public endpoints). When explicit
# origins are provided we enable credentials so the JWT Bearer header works.
_raw_origins = os.getenv("CORS_ORIGINS", "").strip()
if _raw_origins and _raw_origins != "*":
    cors_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Apply ForwardedHostMiddleware AFTER CORS so CORS sees the rewritten
# Host (origin checks may rely on it). add_middleware wraps in reverse
# call order: this becomes the outermost middleware, hitting requests
# before CORS does.
app.add_middleware(ForwardedHostMiddleware)


# ────────────────────────────────────────────────────────────────────────
# Response envelope — every successful JSON response under /api/ (except
# /api/auth/*) is wrapped as {data, error: null, meta}; errors are wrapped
# as {data: null, error: {code, message, details}, meta} by the handlers
# below. One predictable shape for the UI (ui/src/lib/api.ts unwraps it).
# Auth (fastapi-users) + /health + / + docs keep their native shapes —
# see app/internal/responses.py:should_wrap. No per-endpoint edits needed.
# ────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def wrap_success_envelope(request: Request, call_next):
    response = await call_next(request)
    if not should_wrap(request.url.path):
        return response
    # Errors are enveloped by the exception handlers; only wrap 2xx JSON here.
    if not (200 <= response.status_code < 300):
        return response
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response  # e.g. 204 No Content, file/stream responses

    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    if not body:
        return response
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        # Unexpected non-JSON-parseable body — pass through untouched.
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )

    # Idempotency guard: don't double-wrap an already-enveloped body.
    if isinstance(payload, dict) and {"data", "error", "meta"} <= payload.keys():
        envelope = payload
    else:
        envelope = success_envelope(payload, build_meta(request.query_params, payload))

    data_bytes = json.dumps(envelope, default=str).encode("utf-8")
    # Preserve upstream headers (CORS, etc.); fix the length/type for the new body.
    headers = MutableHeaders(raw=list(response.raw_headers))
    headers["content-length"] = str(len(data_bytes))
    headers["content-type"] = "application/json"
    return Response(content=data_bytes, status_code=response.status_code, headers=dict(headers))


@app.exception_handler(StarletteHTTPException)
async def http_exception_envelope(request: Request, exc: StarletteHTTPException):
    if should_wrap(request.url.path):
        return JSONResponse(
            error_envelope(exc.status_code, exc.detail),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_envelope(request: Request, exc: RequestValidationError):
    if should_wrap(request.url.path):
        return JSONResponse(
            error_envelope(422, "Validation error", jsonable_encoder(exc.errors())),
            status_code=422,
        )
    return await request_validation_exception_handler(request, exc)


# Include routers
# Authentication module (must be first)
app.include_router(auth_routes.router)

# Administration module
app.include_router(admin_health_router.router)
app.include_router(profiles_router.router)
app.include_router(modules_router.router)
app.include_router(lists_router.router)
app.include_router(list_items_router.router)
app.include_router(business_units_router.router)
app.include_router(users_router.router)
app.include_router(options_router.router)
app.include_router(privileges_router.router)

# Taxonomy module
app.include_router(categories_router.router)
app.include_router(features_router.router)
app.include_router(specifications_router.router)

# Asset Library module
app.include_router(assets_router.router)
app.include_router(characterizations_router.router)
app.include_router(favorites_router.router)
app.include_router(actions_router.router)
app.include_router(asset_relations_router.router)
app.include_router(asset_permissions_router.router)

# Collaboration module
app.include_router(teams_router.router)
app.include_router(roles_router.router)
app.include_router(assignments_router.router)
app.include_router(projects_router.router)
app.include_router(dimensions_router.router)
app.include_router(metrics_router.router)

# GenAI Initiatives module
app.include_router(criterias_router.router)

# TODO: Add routers for other modules when implemented
# - genai (Generative AI)
# - insights (GenAI Insights)
# - workflows (Processes)


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("SynapxIA API starting up...")
    logger.info(f"Environment: {os.getenv('APP_ENV', 'development')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("SynapxIA API shutting down...")


# Tag → module grouping for the root endpoint inventory.
TAG_TO_MODULE: dict[str, str] = {
    "authentication": "auth",
    "profiles": "admin",
    "modules": "admin",
    "lists": "admin",
    "list_items": "admin",
    "business_units": "admin",
    "users": "admin",
    "options": "admin",
    "privileges": "admin",
    "categories": "taxo",
    "features": "taxo",
    "specifications": "taxo",
    "assets": "lib",
    "characterizations": "lib",
    "favorites": "lib",
    "actions": "lib",
    "asset_relations": "lib",
    "asset_permissions": "lib",
    "teams": "collab",
    "roles": "collab",
    "assignments": "collab",
    "projects": "collab",
    "dimensions": "collab",
    "metrics": "collab",
    "criterias": "inits",
}


@app.get("/", tags=["health"])
def read_root() -> dict:
    """
    API root endpoint.

    Returns metadata about the API plus a live inventory of every registered route,
    grouped by module → tag. Built by introspecting ``app.routes`` so it stays in sync
    as routers are added.
    """
    modules: dict[str, dict[str, list[dict]]] = {}
    meta: dict[str, list[dict]] = {"health": [], "system": []}

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        methods = sorted(m for m in (route.methods or set()) if m != "HEAD")
        operation = {
            "path": route.path,
            "methods": methods,
            "summary": route.summary or route.name,
        }

        tag = (route.tags or [None])[0]
        module = TAG_TO_MODULE.get(tag) if tag else None

        if route.path == "/":
            meta["system"].append(operation)
        elif tag == "health" or route.path == "/health":
            meta["health"].append(operation)
        elif module:
            modules.setdefault(module, {}).setdefault(tag, []).append(operation)
        else:
            modules.setdefault("other", {}).setdefault(tag or "untagged", []).append(operation)

    for tag_map in modules.values():
        for ops in tag_map.values():
            ops.sort(key=lambda op: (op["path"], op["methods"]))

    return {
        "name": "SynapxIA API",
        "description": "System for Insight, Adoption, Practice & eXpansion through Intelligent Agents",
        "version": app.version,
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "health": "/health",
        "modules": modules,
        "meta_endpoints": meta,
    }
