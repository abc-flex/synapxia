# CLAUDE.md — API

**Read the root [`AGENTS.md`](../AGENTS.md) first** for the full conventions and the
binding Constitution rules. This file covers what is specific to the backend.

## Stack

Python ≥3.12, FastAPI + SQLModel + SQLAlchemy, `fastapi-users` (JWT + bcrypt),
managed by **`uv`**. Served at port 8000 (→ container 80). Entry point: `app/main.py`.

## Structure (modular monolith)

```
api/app/
  internal/        # shared: DB session/engine, auth, common deps — reuse, don't duplicate
  {domain}/
    routes/        # FastAPI routers (endpoints)
    internal/      # data access for the domain
```

Domains: `admin, auth, collab, taxo, genai, inits, insights, workflows`.
New features go inside their owning domain — never add cross-domain plumbing per module.

## Commands

```bash
make logs-api          # tail API logs
make exec-api          # bash into the API container
make test              # hits /api/health among other checks
uv sync                # install/lock deps (inside api/)
uv run fastapi dev     # run locally (as the container does)
```

API docs: http://localhost:8000/docs · ReDoc http://localhost:8000/redoc.

## Rules that bite here

- **Contract stability:** don't remove/rename existing endpoints or request/response
  keys; incompatible changes need a versioned route + UI adaptation plan.
- **Pagination:** list endpoints take bounded `skip` / `limit`.
- **Logical delete:** set `is_active=False`; keep the row.
- **Status codes:** 409 unique conflict · 400 validation · 403 auth · 404 missing.
- **DB access:** use managed sessions from `app/internal`; no unbounded or N+1 queries.
- **Auth:** JWT Bearer + bcrypt only, never plaintext; preserve `is_active` /
  `is_superuser`. See [`AUTH.md`](AUTH.md).
- **Testing:** auth/contract/migration/permission changes REQUIRE automated tests.
