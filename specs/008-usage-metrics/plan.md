# Implementation Plan: Usage Metrics

**Branch**: `008-usage-metrics` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-usage-metrics/spec.md`

## Summary

HU-AN07 Usage Metrics adds a read-only manager page, `/ana/usage`, to the `insights` domain (module `ANA`). It aggregates the `executions` records that the Dashboard Catalog (SpecKit 007) writes.

- **API.** There are two endpoints, gated on `ANA/USAGE`:
  - `GET /api/usage/metrics` returns one aggregate document: headline with previous-period change, timeline buckets, dashboards table (with unused rows), unit tree and team rows.
  - `GET /api/usage/dashboards/{id}/errors` returns the top error messages for one dashboard, loaded lazily.
- **Aggregation.** A new `usage_service` loads the period's executions with one projected query, then aggregates them in a single Python pass. This keeps medians, local-time buckets and hybrid team attribution portable, so the tests can run on SQLite (research R1).
- **Scope.** A superuser or an Administrator sees everything. Anyone else sees only dashboards they hold MANAGE on, resolved through the shared permission engine.
- **Definitions** follow the clarifications:
  - runs exclude Cancelled and Unauthorized;
  - success rate = Success ÷ (Success + Failed + Timeout);
  - units roll up as a tree;
  - teams are those valid at run time, falling back to the current teams.
- **UI.** A thin SSR page mounts a Svelte island. It has period presets and a custom range, headline tiles, an SVG stacked chart, the dashboards table, unit and team adoption tabs, and CSV and `.xlsx` export built in the browser.
- **Database.** The only DB change is two additive indexes on `executions`. Synthetic development data ships as hand-run scripts.

## Technical Context

**Language/Version**: Python ≥ 3.14 (API, `uv`), TypeScript + Astro 5 SSR / Svelte 5 (UI, Bun)

**Primary Dependencies**: FastAPI + SQLModel, `zoneinfo` from the standard library (API); Astro 5, Vite 8, Tailwind + Flowbite, Svelte 5 via manual `mount()` (UI). **No new dependencies**: the chart is hand-built SVG and the `.xlsx` writer is a small in-repo module.

**Storage**: PostgreSQL 18.
- Read-only over `executions`, `dashboards`, `dashboard_permissions`, `users`, `business_units`, `assignments`, `teams` and `list_items`.
- DDL: two indexes on `executions`, in `db/sql/61-ana-ddl.sql` plus [provisioned-db.sql](provisioned-db.sql).
- Development data: [synthetic-usage.sql](synthetic-usage.sql) and [synthetic-usage-remove.sql](synthetic-usage-remove.sql).

**Testing**: pytest in the API container (`docker compose exec -T api uv run pytest -q`, baseline 715 passed / 0 failed; suites on SQLite); `bun run build` + `astro check` (existing baseline); manual [quickstart](quickstart.md) for UI and the scope check

**Target Platform**: Docker Compose locally; Vercel (UI SSR + API serverless via Mangum) + Neon

**Project Type**: Web application, modular monolith (API / UI / DB)

**Performance Goals**: The metrics document in under 3 s for a period with up to 100 000 executions (SC-003). One projected query per request, plus a constant number of small lookups for users, units, assignments, teams, dashboards and scope. No N+1.

**Constraints**:
- The API is serverless, so there are no background jobs or materialized summaries.
- Periods are capped at 24 months.
- Organization time zone `APP_TIMEZONE` (default `America/Bogota`).
- Aggregates only: no execution row, `user_id` or payload ever leaves the API (FR-015).

**Scale/Scope**:
- Volume: up to about 100 000 executions per period; tens of dashboards; fewer than 100 units; tens of teams.
- API: 2 endpoints, 1 service module, 1 routes module, 1 setting.
- UI: 1 page and 1 Svelte island with 3 sub-components; 2 small libs (export helpers, `.xlsx` writer); 1 service module; i18n keys in en and es.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design: still passes.*

| Principle | How the design complies | Status |
|-----------|------------------------|--------|
| **I. Modular monolith boundaries** | All backend code lives in `api/app/insights` (`routes/usage.py`, `internal/usage_service.py`, response models in `internal/models.py`). The MANAGE scope reuses `insights/internal/permissions_service.accessible_dashboards`, which is the binding of the shared `app/internal/resource_permissions` engine. The module gate uses `app/internal/permissions.require_privilege`. Other domains' tables (`users`, `business_units`, `assignments`, `teams`) are read through their existing SQLModel classes; no plumbing is duplicated. The CSV escaping is extracted from `advancedTable.ts` into a shared `lib/` helper rather than copied. | ✅ |
| **II. API-first contract stability** | The two endpoints are new, and nothing is removed or renamed. `metrics` is an aggregate document bounded by entities, not a list of records. The one list-like endpoint (errors) takes a bounded `limit` (1–50). The UI unwraps the envelope centrally. | ✅ |
| **III. Risk-based testing** | New contracts plus a permission rule (Administrator vs MANAGE scope) are high risk. pytest suites cover access and scope, run classification and rates, buckets and time zone, the unit tree, hybrid teams, the comparison, the errors endpoint, validation and the no-leak rule (research R14). The UI is checked manually through the quickstart. `make test` must pass. | ✅ |
| **IV. Security & secret hygiene** | JWT and RBAC are unchanged. Scope is enforced on the server for every section and for the errors endpoint (404 outside scope, without revealing existence). No personal-level data is exposed: aggregates only, with no user ids or payloads. Read-only. No secrets. `is_active` / `is_superuser` semantics are preserved: inactive users don't count as members, and superusers keep the bypass. | ✅ |
| **V. Performance & operability** | Managed sessions come from `app/internal`. One projected, index-backed range query is streamed with `yield_per`. Each lookup is a single batched query. Each request logs structured fields: the period, scope size, row count and elapsed ms. Compose and Make are unchanged. | ✅ |
| **Established pattern: per-resource permissions** | The `dashboard_permissions` binding of the shared engine defines the MANAGE scope (MANAGE beats VIEW, validity window, revoke-not-delete). Module RBAC (`ANA/USAGE`) stays the outer gate. | ✅ referenced |
| **Established pattern: contribution workflow / content versioning** | Not applicable: this is a read-only analytics view over telemetry. | n/a |

## Project Structure

### Documentation (this feature)

```text
specs/008-usage-metrics/
├── spec.md                     # Feature spec (clarified)
├── plan.md                     # This file
├── research.md                 # Phase 0: decisions R1–R14
├── data-model.md               # Phase 1: sources, derived concepts, validation
├── quickstart.md               # Phase 1: automated + manual + performance validation
├── contracts/
│   └── usage-api.md            # Phase 1: endpoint contracts
├── provisioned-db.sql          # Indexes for already-provisioned DBs (one-off)
├── synthetic-usage.sql         # Development data (NOT seed data): executions only, deterministic
├── synthetic-usage-remove.sql  # Deletes the executions marked "synthetic"
├── checklists/
│   └── requirements.md         # Spec quality checklist
└── tasks.md                    # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
api/app/core/config.py                 # + APP_TIMEZONE (default "America/Bogota")
api/app/insights/
├── internal/
│   ├── models.py                      # + Usage* response models (Summary, Bucket, DashboardRow,
│   │                                  #   UnitNode, TeamRow, Metrics, ErrorItem, Errors)
│   └── usage_service.py               # NEW: period/bucket math, scope_for, classification,
│                                      #   one-pass aggregation, unit tree, hybrid teams, errors
└── routes/
    └── usage.py                       # NEW: GET /api/usage/metrics, GET /api/usage/dashboards/{id}/errors
api/app/main.py                        # include the usage router
api/tests/
├── usage_helpers.py                   # NEW: builders (units tree, users, assignments, executions)
├── test_ana_usage_access.py           # NEW: gate, Administrator vs MANAGE scope, 404 errors, no-leak
├── test_ana_usage_metrics.py          # NEW: classification, rates, medians, buckets/TZ, comparison
├── test_ana_usage_dashboards.py       # NEW: dashboard rows, unused rows, errors endpoint
└── test_ana_usage_groups.py           # NEW: unit roll-up, hybrid teams, filters, adoption

db/sql/61-ana-ddl.sql                  # + 2 indexes on executions

ui/src/
├── pages/ana/usage.astro              # NEW: SSR shell (BaseLayout, breadcrumb, option name/icon, mount point)
├── components/svelte/
│   ├── UsageMetrics.svelte            # NEW: island root: period, filter chip, tiles, sections, fetch
│   ├── UsageTimeline.svelte           # NEW: SVG stacked bars + legend + tooltip (light/dark)
│   ├── UsageDashboardsTable.svelte    # NEW: sortable/searchable table, unused toggle, lazy errors, export
│   └── UsageAdoption.svelte           # NEW: unit tree / team tabs, adoption, row → filter, export
├── lib/
│   ├── usageMetrics.ts                # NEW: getUsageMetrics / getDashboardErrors services
│   ├── tableExport.ts                 # NEW: shared toCSV (extracted from advancedTable.ts) + download
│   └── xlsx.ts                        # NEW: minimal single-sheet .xlsx writer (STORE zip + CRC-32)
├── components/table/advancedTable.ts  # toCSV now imported from lib/tableExport.ts (same output)
├── types/api.ts                       # + UsageMetrics, UsageSummary, UsageBucket, UsageDashboardRow,
│                                      #   UsageUnitNode, UsageTeamRow, UsageErrors
└── i18n/{en,es}.json                  # + usage_metrics.* keys

specs/008-usage-metrics/synthetic-usage.sql   # + optional `scale` psql variable (SC-003 benchmark)
```

**Structure Decision**: This keeps the repo's web-app layout (`api/` + `ui/` + `db/`). The backend sits in the owning `insights` domain. The UI follows the Svelte-island convention for an interactive page whose data changes with the period, because an SSR snapshot would be stale by construction (the same reasoning as My Asset Requests, 2026-09-16).

## Phase summary

**Phase 0, [research.md](research.md).** No open unknowns. Decisions:

| # | Decision |
|---|----------|
| R1 | One projected query aggregated in Python, portable and testable on SQLite |
| R2 | Two indexes on `executions` |
| R3 | `APP_TIMEZONE` for local periods and buckets |
| R4 | Administrator/superuser sees all; anyone else is limited to the MANAGE scope via the shared engine |
| R5 | Classification table for runs vs attempts, rate and durations |
| R6 | One metrics document plus a lazy errors endpoint |
| R7 | Unit roll-up tree |
| R8 | Hybrid team attribution |
| R9 | Previous-period comparison |
| R10 | Hand-built SVG chart, no ECharts |
| R11 | CSV with BOM plus an in-repo `.xlsx` writer |
| R12 | SSR shell plus Svelte island |
| R13 | Synthetic data scripts with a `scale` variable |
| R14 | Test matrix |

**Phase 1.** [data-model.md](data-model.md), [contracts/usage-api.md](contracts/usage-api.md), [quickstart.md](quickstart.md) and [provisioned-db.sql](provisioned-db.sql). The agent context (`CLAUDE.md` SPECKIT block) now points to this plan.

## Complexity Tracking

| Choice | Why needed | Simpler alternative rejected because |
|--------|-----------|-------------------------------------|
| Aggregation in Python over a projected row stream | Medians, local-time buckets and run-time team attribution are not portable SQL, and the suites run on SQLite | Postgres-only SQL would leave the core figures untestable in CI (Constitution III). Within the 24-month cap and about 100 000 rows the cost stays within SC-003; a benchmark is in the quickstart, with a documented fallback (research R1) |
| In-repo `.xlsx` writer (~120 lines) | The clarification asked for an Excel export, and the repo has no spreadsheet library | SheetJS adds about 400 KB and licensing churn. An HTML or SpreadsheetML file renamed `.xls` triggers Excel's format warning |
| Hand-built SVG chart instead of reusing ECharts | One stacked bar chart, themed light and dark, inside a Svelte island | ECharts is a 1 MB global CDN script, harder to theme and outside the `mount()` convention |
| `ORG_WIDE_PROFILES = ("ADMINISTRATOR",)` as the organization-wide rule | Clarification Q1 = C fixes the rule per profile | A new privilege option would be seed and privilege churn for a fixed rule. `reviewers.ADMIN_PROFILES` is not reused because it also contains ADMINISTRATIVE, which must be scoped here |
