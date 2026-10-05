# Implementation Plan: Dashboard Catalog (with Execute and Favorite)

**Branch**: `007-dashboard-catalog` | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-dashboard-catalog/spec.md`

## Summary

This plan builds HU-AN04 Dashboard Catalog, HU-AN05 Execute and the catalog side of HU-AN06 Favorite in the `insights` domain (module `ANA`). Every table already exists, so there is no DDL.

- **Catalog page.** `/ana/catalog` is a card gallery. It reuses the Explore pages' `CardGallery` + `initCardGallery`: SSR fetch, a privileges filter with six options (Public by default, no "all"), search and a "★ My favorites" toggle. It is fed by a new `GET /api/dashboards/catalog` gated on `ANA/CATALOG`. That endpoint returns Published dashboards only, filters by grant before paginating, and adds `permission_scopes` and `is_favorite` to each row.
- **Execute.** A Svelte island renders a parameters window from `GET /api/dashboards/{id}/run-form`. The server has already resolved each parameter's *effective* source for this viewer: a grant-bound value applies only when the viewer came through the bound grant, otherwise it falls back to the list or to free input. The window prefills defaults and offers "use my last values", derived from the payload of the viewer's last Success execution. It validates inline before running.
- **Recording.** Each run is recorded in two steps.
  1. `POST …/executions` validates (access, then values) and always writes one row: `UNAUTHORIZED` + 403, `FAILED` + 400, or status NULL + 201 with a server-built `launch_url`.
  2. `POST /api/executions/{id}/finish` sets the outcome **once**. External sources open in a new tab (SUCCESS, or FAILED when the popup is blocked). Internal pages open in a same-origin viewer with an iframe in `embed=1` mode (SUCCESS on load, TIMEOUT after 30 s, CANCELLED if the viewer is closed before the page loads).

  A parameters window closed without running records `CANCELLED` through its own endpoint.
- **Favorites.** The existing favorite endpoints keep their contract. Only their module gate widens to `DASHBOARDS` or `CATALOG`.

## Technical Context

**Language/Version**: Python ≥ 3.14 (API, `uv`), TypeScript + Astro 5 SSR / Svelte 5 (UI, Bun)

**Primary Dependencies**: FastAPI + SQLModel (API); Astro 5, Vite 8, Tailwind + Flowbite, Svelte 5 via manual `mount()` (UI)

**Storage**: PostgreSQL 18. Tables `dashboards`, `parameters`, `dashboard_permissions`, `favorite_dashboards` and `executions` all exist in `db/sql/61-ana-ddl.sql`. The only seed change is the payload shape of the six `executions` rows (`62-ana-insert.sql`)

**Testing**: pytest in the API container (`docker compose exec -T api uv run pytest -q`, baseline 670 passed / 0 failed); `bun run build` + `astro check` (existing baseline); manual quickstart for UI

**Target Platform**: Docker Compose locally; Vercel (UI static/SSR + API serverless via Mangum) + Neon

**Project Type**: Web application, modular monolith (API / UI / DB)

**Performance Goals**: Catalog filtering < 1 s for ≤ 200 dashboards (client-side filtering, SC-007); catalog, run-form and start each take a bounded, constant number of queries (no N+1)

**Constraints**: Serverless API means no long-lived connections and no background jobs. That is why the outcome is reported by the client and why rows that stay "in progress" are left as NULL. Internal Page timeout is 30 s. Values are at most 1 000 characters

**Scale/Scope**: Dozens to a few hundred dashboards, executions in the low thousands; 6 new endpoints and 1 widened gate; 1 page, 2 Astro components, 1 Svelte island, 1 service module, a small additive `BaseLayout` embed mode

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design: still passes.*

| Principle | How the design complies | Status |
|-----------|------------------------|--------|
| **I. Modular monolith boundaries** | All backend code lives in `api/app/insights` (`routes/catalog.py`, `routes/executions.py`, `internal/catalog_service.py`, `internal/execution_service.py`). Grant matching reuses `app/internal/resource_permissions.py` (`matching_grants`, `user_scopes_for`) through the existing `insights/internal/permissions_service.py`, and run-value validation extends the existing `parameter_validation.py`. Module gates use `app/internal/permissions` (`require_privilege`, `check_any_privilege`). Favorites reuse the existing endpoints. Nothing is duplicated per module. | ✅ |
| **II. API-first contract stability** | Six new endpoints. No endpoint or key is removed or renamed. The favorite endpoints keep their request and response shape and only widen *who* may call them (additive). The list endpoint keeps bounded `skip`/`limit` (`limit ≤ 500`). The UI unwraps the envelope centrally in `lib/api.ts`. | ✅ |
| **III. Risk-based testing** | New contracts, a permission change (favorites gate), auth on execution records and value validation are all high risk, so each gets pytest suites (research R12). The UI is verified manually through the quickstart. `make test` must pass. | ✅ |
| **IV. Security & secret hygiene** | JWT stays unchanged. The actor always comes from the session, never the body. Grant-bound values are computed by the server and submitted ones are ignored. The client never receives `source_url` in the list and never builds the launch address. Only the owner can finish an execution, and only once. Values and error messages are capped. External tabs open with `noopener`. No secrets involved. `is_active` / `is_superuser` semantics are preserved. | ✅ |
| **V. Performance & operability** | Managed sessions come from `app/internal`. Visibility is filtered in SQL before pagination. Scopes, favorites and parameter counts use one batched query each. Last values is one `LIMIT 1` query. Execution starts, finishes and refusals are logged with structured fields. All services still run via Compose and Make. | ✅ |
| **Established pattern: per-resource permissions** | Uses the `dashboard_permissions` binding of the shared engine (MANAGE/VIEW, `valid_from`/`valid_to`, revoke-not-delete). Module RBAC (`ANA/CATALOG`) stays the outer gate, and `require_dashboard_view`-style checks are the inner gate (403). The grant-binding rule reads the same matching grants. | ✅ referenced |
| **Established pattern: contribution workflow** | Not applicable. Executions are telemetry, not a multi-party approval flow, so they use their own pre-existing `executions` table (seeded `EXECUTION_STATUS`) rather than `actions`. This is not a deviation: the pattern covers propose/review flows only. | n/a |
| **Established pattern: content versioning** | Not applicable. | n/a |

## Project Structure

### Documentation (this feature)

```text
specs/007-dashboard-catalog/
├── spec.md              # Feature spec (clarified)
├── plan.md              # This file
├── research.md          # Phase 0 — decisions R1–R12
├── data-model.md        # Phase 1 — Execution mapping, payload, effective sources
├── quickstart.md        # Phase 1 — automated + manual validation
├── contracts/
│   └── catalog-api.md   # Phase 1 — endpoint contracts
├── test-catalog.sql     # Test data for the quickstart (NOT seed data)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
api/app/insights/
├── internal/
│   ├── models.py                 # + Execution (table), CatalogDashboard, RunForm(+Parameter),
│   │                             #   ExecutionStart/Started/Finish/Cancelled/Read, LastValues
│   ├── catalog_service.py        # NEW: catalog list, effective sources, run-form, last values
│   ├── execution_service.py      # NEW: start (UNAUTHORIZED/FAILED/in-progress), launch_url,
│   │                             #   payload, finish-once, cancelled
│   ├── parameter_validation.py   # + validate_run_value (validate_default delegates to it)
│   └── permissions_service.py    # + dashboard_matching_grants (thin wrapper over the engine)
└── routes/
    ├── catalog.py                # NEW: GET /api/dashboards/catalog, /{id}/run-form
    ├── executions.py             # NEW: POST /{id}/executions, /{id}/executions/cancelled,
    │                             #   GET /{id}/executions/last-values, POST /api/executions/{id}/finish
    └── dashboards.py             # favorite PUT/DELETE gate → DASHBOARDS or CATALOG
api/app/main.py                   # include catalog + executions routers (catalog before dashboards
                                  #   so /catalog isn't captured by /{dashboard_id})
api/tests/
├── test_ana_catalog.py           # NEW: visibility, scopes, favorites gate, run-form, last values
└── test_ana_executions.py        # NEW: start/finish/cancel, launch_url, payload, guards

db/sql/62-ana-insert.sql          # executions payloads → {values, sources, mode} shape

ui/src/
├── pages/ana/catalog.astro                    # NEW: SSR fetch + CardGallery + initCardGallery
├── components/ana/CatalogCard.astro           # NEW: GalleryCard wrapper (source icon, chips, star, Execute)
├── components/ana/CatalogDetailModal.astro    # NEW: read-only detail (description, detail, parameters)
├── components/svelte/DashboardRun.svelte      # NEW: parameters window + viewer + outcome reporting
├── lib/dashboardExecutions.ts                 # NEW: catalog/run-form/executions services
├── types/api.ts                               # + CatalogDashboard, RunForm, RunFormParameter, Execution*, LastValues
├── layouts/BaseLayout.astro                   # + embed=1 mode (no SideBar/Header), additive
└── i18n/{en,es}.json                          # + dashboard_catalog.* keys
```

**Structure Decision**: This keeps the repo's existing web-app layout (`api/` + `ui/` + `db/`). The backend goes inside the owning `insights` domain; the UI follows the Explore pages (SSR page + shared gallery) and the Svelte-island convention for the dynamic window.

## Phase summary

- **Phase 0, [research.md](research.md)**: no open unknowns. Key decisions:
  - catalog-specific endpoints gated on `ANA/CATALOG` (R1);
  - a widened favorites gate (R2);
  - grant binding through `matching_grants` (R3);
  - the two-step record, finished once (R4);
  - the payload shape `{values, sources, mode}` (R5);
  - last values computed on the server (R6);
  - shared value validation (R7);
  - a server-built `launch_url`, the same-origin `embed=1` viewer, and opening a blank tab first to dodge popup blockers (R8);
  - the SSR gallery with bilingual type and source search text (R9);
  - UI reuse (R10).
- **Phase 1**: [data-model.md](data-model.md), [contracts/catalog-api.md](contracts/catalog-api.md), [quickstart.md](quickstart.md), [test-catalog.sql](test-catalog.sql). The agent context (`CLAUDE.md` SPECKIT block) now points to this plan.

## Complexity Tracking

| Choice | Why needed | Simpler alternative rejected because |
|--------|-----------|-------------------------------------|
| Two-step execution record (status NULL → final, set once) | The outcome (tab opened, popup blocked, iframe loaded, timeout, viewer closed) is only known in the browser, while Unauthorized and invalid values must be recorded by the server regardless of the client | Client-only recording lets a client skip the record. Recording SUCCESS at start needs an edit when the popup is blocked. The once-only finish keeps the record append-only in practice |
| Separate catalog read endpoints instead of reusing Management's | Consumers hold `ANA/CATALOG`, not `ANA/DASHBOARDS`, and must only see Published dashboards | Branching the Management endpoints on the caller's privilege mixes two visibility rules in one route |
| No index on `executions` yet | Last values runs a `LIMIT 1` query per window open at low volume | An index now would be DDL for a hypothetical load; HU-AN07 will add the indexes its aggregates need |
| `BaseLayout` embed mode | Internal pages must fit the viewer without a nested sidebar and header | A separate layout per internal page would fork the shell |
