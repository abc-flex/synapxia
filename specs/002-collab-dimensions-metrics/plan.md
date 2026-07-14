# Implementation Plan: Collab Dimensions CRUD with Metrics Master-Detail

**Branch**: `002-collab-dimensions-metrics` | **Date**: 2026-04-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-collab-dimensions-metrics/spec.md`

## Summary

Add two UI pages to the Collaboration module — **Dimensions** (master) and **Metrics** (detail) — that expose full CRUD operations using the existing FastAPI backend endpoints (`/api/dimensions` and `/api/metrics`). The Dimensions page mirrors the Roles pattern from the admin module; the Metrics page mirrors the Privileges pattern, filtered by dimension. Both pages use the established Astro + CrudModal + DataTable + Toast UI stack. No backend changes are required; all backend routes and models are already implemented.

## Technical Context

**Language/Version**: Python 3.12 (backend, `uv`-managed) · TypeScript / Astro 4 (frontend, Bun)  
**Primary Dependencies**: FastAPI + SQLModel (backend) · Astro + Tailwind CSS + Bun (frontend)  
**Storage**: PostgreSQL — `dimensions` and `metrics` tables exist; no migration needed  
**Testing**: pytest (backend smoke) · manual browser validation (UI)  
**Target Platform**: Linux container (Docker Compose) · modern browser (Astro SSR + client script)  
**Project Type**: Full-stack web application (modular monolith API + Astro SSR UI)  
**Performance Goals**: Page load <3 s; CRUD feedback <2 s (toast confirmation)  
**Constraints**: Pagination default limit=100; no new env vars; backward-compatible API  
**Scale/Scope**: ~200 dimension records, ~1 000 metric records worst case; 2 new UI pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I - Modular boundaries**: All backend code already lives in `api/app/collab/routes/` and `api/app/collab/internal/`. UI lib files go to `ui/src/lib/`, UI pages to `ui/src/pages/collab/`. Centralized `api/app/internal/dependencies.py` is reused via the collab re-export. No cross-domain duplication.
- [x] **Principle II - Contract stability**: Backend API contracts for `/api/dimensions` and `/api/metrics` already exist and are complete. No existing endpoints are modified. New UI lib files and types are purely additive. UI types extension in `api.ts` adds new interfaces without touching existing ones.
- [x] **Principle III - Testing discipline**: Risk is **low** (UI-only additions consuming stable existing API). Manual browser validation is acceptable per constitution for UI-only changes. Backend is already tested. No auth or migration changes are present.
- [x] **Principle IV - Security hygiene**: Both `/api/dimensions` and `/api/metrics` are already protected by JWT Bearer middleware. The `can_edit` privilege for `COLLAB/DIMENSIONS` already exists in the DB seed data. No new secrets, CORS rules, or access control changes are introduced.
- [x] **Principle V - Operability/performance**: Both API endpoints use managed sessions from centralized dependencies. List endpoints include `skip`/`limit` pagination. No unbounded queries. Docker Compose and `make` targets are unaffected.

**Constitution gate: PASS — no violations.**

## Project Structure

### Documentation (this feature)

```text
specs/002-collab-dimensions-metrics/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── dimensions.md    # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
api/
└── app/
    └── collab/
        ├── internal/
        │   └── models.py          ✅ exists — Dimension, DimensionCreate, DimensionUpdate,
        │                                       Metric, MetricCreate, MetricUpdate
        └── routes/
            ├── dimensions.py      ✅ exists — GET/POST/PUT/DELETE /api/dimensions
            └── metrics.py         ✅ exists — GET/POST/PUT/DELETE /api/metrics

ui/
└── src/
    ├── lib/
    │   ├── dimensions.ts          ❌ create — getDimensions, getDimension,
    │   │                                       createDimension, updateDimension, deleteDimension
    │   └── metrics.ts             ❌ create — getMetrics, getMetric,
    │                                           createMetric, updateMetric, deleteMetric
    ├── types/
    │   └── api.ts                 ❌ extend — add Dimension, DimensionCreate, DimensionUpdate,
    │                                           Metric, MetricCreate, MetricUpdate interfaces
    ├── pages/
    │   └── collab/
    │       ├── dimensions.astro   ❌ create — master page (CRUD table + detail link)
    │       └── metrics.astro      ❌ create — detail page (CRUD table + dimension filter)
    └── i18n/
        ├── en.json                ❌ extend — add "metrics" key and dimension/metric modal keys
        └── es.json                ❌ extend — same keys in Spanish
```

**Structure Decision**: Web application (Option 2 pattern). Backend code is complete; all new files are in the UI layer. The collab module directory already exists; this feature adds two lib files, two page files, and extends shared types and i18n.
