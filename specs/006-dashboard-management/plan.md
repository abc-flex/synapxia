# Implementation Plan: Dashboard Management

**Branch**: `006-dashboard-management` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-dashboard-management/spec.md`

## Summary

Give analysts a governed inventory of dashboards at `/ana/dashboards`. It is a grant-scoped,
filterable list with a "New Dashboard" action and a three-tab edit dialog (Core Fields,
Parameters, Permissions), and each tab saves only its own slice. New dashboards start in Draft
and the creator receives MANAGE. Status follows a server-enforced lifecycle:
Draft → Published; Published → Archived or Retired; Archived → Published or Retired; Retired is
final. Parameters are declared with a type-checked default, an optional allowed-values list and
an optional binding to one of the dashboard's grants. The value source (grant / list / viewer
input) is derived from those two columns, ready for the future Execute story's parameters window.

Technically this promotes the `insights` stub to a real domain:

- SQLModel mappings over three tables that already exist (`dashboards`, `parameters`,
  `dashboard_permissions`), with no DDL.
- A permission service that **binds** the shared `app/internal/resource_permissions` engine (the
  third binding after `lib` and `inits`).
- A status service, three route modules and 16 additive endpoints (two of them for favorites, added by the 2026-10-02 amendment, R14).
- Spanish seed rows for the analytics lists.
- A UI page, modal and Svelte island modelled on Initiative Management, with the Permissions tab
  extracted into a shared island instead of a third copy.

## Technical Context

**Language/Version**: Python ≥3.14 (API, per `api/pyproject.toml`) · TypeScript / Astro 5 SSR +
Svelte 5 (UI) · PostgreSQL 18 (DB)

**Primary Dependencies**: FastAPI + SQLModel, `uv` · Astro 5, Vite 8, Tailwind, Flowbite,
Svelte 5 via manual `mount()` (never `@astrojs/svelte`), Bun

**Storage**: PostgreSQL 18. The tables already exist in `db/sql/61-ana-ddl.sql`. Seed lists are
edited in place (unreleased product, `make rebuild`). Provisioned DBs get
`provisioned-db.sql`.

**Testing**: `pytest` in `api/tests/` on the SQLite `session`/`client` fixtures, run inside the
API container (`docker compose exec -T api uv run pytest -q`). Baseline is 570 passed, 0 failed.
UI: `bun run build` + `astro check` (baseline), plus a manual click-through (there is no browser
harness).

**Target Platform**: Docker Compose locally; Vercel serverless (Mangum) + Neon

**Project Type**: Web, as a modular monolith with three surfaces (API, UI, DB)

**Performance Goals**: the list and the dialog should feel instant with 500 dashboards (SC-006).
The query count per request stays constant: batched `IN` lookups for scopes and binding labels,
with no N+1.

**Constraints**: additive API only (Principle II). Every list is bounded by `skip`/`limit`
(`limit ≤ 500`). Queries must be portable to SQLite (no Postgres-only aggregates). `FOR UPDATE`
on dashboard PUT.

**Scale/Scope**: tens to hundreds of dashboards, a handful of parameters and grants each.
About 16 endpoints in 3 route modules, 5 small service/validation modules, 1 model file, 1 seed
file, 5 new test modules + helpers, and on the UI side 1 page, 1 modal, 2 islands (one shared),
3 services, types and 2 i18n files.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design. The result is unchanged.*

### I. Modular Monolith Boundaries — ✅ PASS

All new backend code lives in `api/app/insights/` (`internal/` models and services, `routes/`),
the domain the user stories assign to module `ANA` (R1). Permission resolution is **not** copied.
`insights/internal/permissions_service.py` binds the shared engine in `app/internal`
(R2). Since `inits` and `insights` now both need list-value validation, the 10-line
`validate_list_value` moves to `app/internal/list_values.py` and each domain keeps its own field
map (R10). No per-module connection, auth or permission plumbing is introduced.

### II. API-First Contract Stability — ✅ PASS

Every endpoint is new, and no existing route, request key or response key changes. The R10
hoist keeps `inits.internal.list_validation`'s public names, so it is a re-export. All list
endpoints take bounded `skip`/`limit`. See [contracts/dashboards-api.md](contracts/dashboards-api.md).

### III. Risk-Based Testing Discipline — ✅ PASS (with required work)

This feature adds contract, permission and state-transition behaviour, so automated tests are
mandatory. Five new `test_ana_*.py` modules (R13) cover:

- the full transition table, both allowed and refused, with nothing changed on refusal
- MANAGE/VIEW enforcement on every write and per-dashboard read, and no self-escalation
- scoping before pagination
- revoke and re-grant, and the window and duplicate rules
- favorites: personal, idempotent, logical removal, VIEW required (`test_ana_favorites.py`)
- every parameter rule, including binding integrity

The unchanged `test_inits_*` suites guard the refactors. `make test` plus
[quickstart.md](quickstart.md) cover UI behaviour.

### IV. Security and Secret Hygiene — ✅ PASS

There is no change to authentication, secrets or CORS. Authorization is layered: module RBAC
(`ANA/DASHBOARDS`, edit rights for writes) is the outer gate, and per-dashboard MANAGE/VIEW is
the inner one. Superuser bypass and `is_active` semantics are preserved. The status rule,
list-value checks, `source_url` format and binding integrity are all enforced server-side, not
only in the UI. A VIEW holder cannot grant themselves MANAGE. External `source_url` values must
be `https`, and nothing is fetched server-side, so there is no SSRF surface.

### V. Performance and Operability Baselines — ✅ PASS

Managed sessions come from `app/internal/dependencies`. `/with-access` filters before paginating
using one grant query plus one scope query. Parameter listing resolves binding labels in one
batched query. Compose services, ports and Make targets are untouched, and logging stays
structured (`logger.info` on create, revoke and status change).

### Established Domain Patterns

- **Per-resource permissions — ✅ PASS.** `dashboard_permissions` follows the
  `asset_permissions` model exactly: MANAGE/VIEW, `valid_from`/`valid_to`, revoke-not-delete,
  no `is_active`, RBAC outer + `require_dashboard_manage` / `DashboardAccessForbidden` → 403
  inner. It shares the engine (R2, R3).
- **Content versioning — n/a.** Dashboards are not versioned.
- **Contribution / approval workflows — n/a.** Dashboards are created directly, with no
  propose/review loop, and status moves are owner edits. No activity substrate is used, because
  the spec keeps History out of scope (R4).

### Compatibility and Deployment Rules — ⚠️ DEVIATION, justified

The `es` list rows are added to the existing seed file instead of a new ordered migration. See
§ Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-dashboard-management/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0: 14 decisions
├── data-model.md        # Phase 1: entities, state machine, access matrix, seeds
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── dashboards-api.md    # Phase 1: 16 new endpoints + UI service layer
├── checklists/
│   └── requirements.md  # Spec quality checklist
├── provisioned-db.sql   # (implementation) es list rows for existing DBs
├── test-owner.sql       # (implementation) test grants for felipe.cardenas, not seed data
└── tasks.md             # Phase 2: created by /speckit-tasks, NOT by this command
```

### Source code (repository root)

```text
db/sql/
└── 61-ana-ddl.sql              # + es rows for DASHBOARD_TYPE, SOURCE_TYPE, DASHBOARD_STATUS,
                                #   PARAM_TYPE, EXECUTION_STATUS

api/app/internal/
└── list_values.py              # NEW: validate_list_value (hoisted from inits)

api/app/inits/internal/
└── list_validation.py          # REFACTOR: imports validate_list_value from app/internal;
                                #   public names unchanged

api/app/insights/
├── internal/
│   ├── models.py               # Dashboard(+Base/Create/Update/WithAccess), Parameter
│   │                           #   (+Create/Update/Read), DashboardPermission(+Create/Update),
│   │                           #   RevokedDashboardPermission, ListOption
│   ├── permissions_service.py  # NEW: binds resource_permissions to dashboard_permissions
│   ├── status_service.py       # NEW: transition map, validate_create_status,
│   │                           #   validate_transition, allowed_statuses_for
│   ├── list_validation.py      # NEW: LIST_FIELDS / REQUIRED_FIELDS / validate_core_fields
│   ├── source_validation.py    # NEW: validate_source_url(source_type, url)
│   └── parameter_validation.py # NEW: name format, default vs type/list, list exists,
│                               #   binding integrity, value_source()
└── routes/
    ├── dashboards.py           # NEW: /api/dashboards (with-access, parameter-lists, CRUD)
    ├── parameters.py           # NEW: /api/dashboards/{id}/parameters
    └── dashboard_permissions.py  # NEW: /api/dashboard_permissions

api/app/main.py                 # include the three new routers

api/tests/
├── ana_helpers.py              # NEW: fixtures-as-functions (modelled on inits_helpers.py)
├── test_ana_dashboards.py      # NEW
├── test_ana_status.py          # NEW
├── test_ana_permissions.py     # NEW
├── test_ana_parameters.py      # NEW
├── test_ana_parameter_lists.py # NEW
└── test_ana_favorites.py       # NEW (amendment R14)

ui/src/
├── pages/ana/dashboards.astro              # NEW: list page + New Dashboard
├── components/ana/DashboardDetailModal.astro   # NEW: shell, Core Fields, status policy,
│                                               #   create→edit switch, tab-scoped save, discard
├── components/svelte/
│   ├── DashboardDetailTabs.svelte          # NEW: Parameters tab (staged, diff flush) + hosts
│   │                                       #   PermissionsTab
│   ├── PermissionsTab.svelte               # NEW: extracted from InitiativeDetailTabs
│   │                                       #   (props: resourceId, api, i18nPrefix, readonly)
│   └── InitiativeDetailTabs.svelte         # REFACTOR: uses PermissionsTab, behaviour unchanged
├── lib/
│   ├── dashboards.ts                       # NEW
│   ├── dashboard_parameters.ts             # NEW
│   └── dashboard_permissions.ts            # NEW
├── types/api.ts                            # + Dashboard*, DashboardParameter*, DashboardPermission*
└── i18n/{en,es}.json                       # dashboard_table.*, dashboard_modal.*,
                                            #   dashboard_detail_modal.* (params, perms, status)
```

**Structure Decision**: the existing three-surface layout, unchanged. The backend follows the
domain layout of `api/app/inits/` (models + services in `internal/`, one route module per
resource, routers registered in `main.py`). The UI follows Initiative Management's page → `.astro`
modal shell → Svelte island split.

## Phase summary

- **Phase 0 — [research.md](research.md)**: 14 decisions (R1–R13, plus the R14 amendment). There were no unresolved
  unknowns.
- **Phase 1**: [data-model.md](data-model.md), [contracts/dashboards-api.md](contracts/dashboards-api.md),
  [quickstart.md](quickstart.md). `CLAUDE.md`'s SpecKit block now points to this plan.
- **Post-design Constitution re-check**: unchanged, all PASS, with one justified seed deviation.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Spanish list rows edited into the existing `61-ana-ddl.sql` instead of a new ordered migration file | The product is unreleased and every surface rebuilds from seeds (`make rebuild`). The same in-place convention was used on 2026-10-01 for nine other lists and in 004 and 005. Provisioned DBs get `provisioned-db.sql` | A new `63-ana-*.sql` file would split one list's labels across two files for no runtime benefit, and it would diverge from how every other list was localised |
| `PermissionsTab.svelte` extracted from `InitiativeDetailTabs.svelte` as part of this feature (touches a shipped surface) | A third copy of the permissions UI would violate the reuse-over-fork convention. The extraction is the reuse | Copying the tab is simpler today, but it triples the maintenance and lets the three copies drift. **Fallback**: if the extraction changes initiative behaviour, keep a local copy and record it here |
