# Implementation Plan: Initiative Management

**Branch**: `004-initiative-management` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-initiative-management/spec.md`

## Summary

Give initiative owners the equivalent of Asset Management for initiatives: a permission-scoped,
filterable list at `/inits/initiatives` (no create), and a tabbed edit dialog — Core Fields,
Diagnosis Questions, Related Assets, Permissions, Discussion, History — where each editable tab
saves only its own slice. The only status moves an owner can make are
Accepted → In Progress / Delivered / Archived, In Progress → Delivered / Archived and
Delivered → Archived; each writes a `KICKOFF` / `DELIVERY` / `ARCHIVING` row to
`collaborations` (as `HANDLED`, no notice) in the same transaction, and the server refuses every
other move.

Technically the `inits` domain goes from read-only to a real domain: four new SQLModel mappings
over tables that already exist (`collaborations`, `init_permissions`, `diagnostics`,
`favorite_inits`), an `inits` status service, an `inits` permission service built on a
per-resource permission engine **extracted** from `lib` into `api/app/internal` (so both domains
share one implementation), 13 new additive endpoints, seed-only list/data changes (no DDL, no
migration), and a UI page + modal + Svelte island derived from the asset ones, with `Foro.svelte`
and `history.ts` parameterised by data source instead of forked.

## Technical Context

**Language/Version**: Python ≥3.14 (API, per `api/pyproject.toml`) · TypeScript / Astro 5 SSR +
Svelte 5 (UI) · PostgreSQL 18 (DB)

**Primary Dependencies**: FastAPI + SQLModel, `uv` · Astro 5, Vite 8, Tailwind, Flowbite,
Svelte 5 via manual `mount()` (never `@astrojs/svelte`), Bun

**Storage**: PostgreSQL 18; existing tables in `db/sql/51-inits-ddl.sql`; seeds edited in place
(unreleased product, `make rebuild`)

**Testing**: `pytest` in `api/tests/` on the SQLite `session`/`client` fixtures, run inside the
API container (`docker compose exec -T api uv run pytest -q`); baseline 8 pre-existing failures.
UI: `bun run build` + `astro check` (138-error baseline); manual click-through (no browser
harness).

**Target Platform**: Docker Compose locally; Vercel serverless (Mangum) + Neon

**Project Type**: Web — modular monolith, three surfaces (API, UI, DB)

**Performance Goals**: list + dialog open feel instant for an internal portfolio (SC-001/SC-006);
constant query count per request — batched `IN` lookups, no N+1

**Constraints**: additive API only (Principle II); every list bounded by `skip`/`limit`
(`limit ≤ 500`); queries portable to SQLite (no Postgres-only aggregates — the
`/with-access` precedent); `FOR UPDATE` used where supported, harmless on SQLite

**Scale/Scope**: tens of initiatives and users. ~13 endpoints across 4 route modules; 3 new + 1
refactored service module; 4 new models; 2 seed files; ~6 new test modules; 1 page, 1 modal,
1 island, 2 parameterised readers, 3 service files, types, 2 i18n files.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design — result unchanged.*

### I. Modular Monolith Boundaries — ✅ PASS

All new code lives in `api/app/inits/` (`internal/` models + services, `routes/`). The one piece
both domains need — the per-resource permission engine — is **moved** to
`api/app/internal/resource_permissions.py`, the shared layer the principle reserves for
cross-domain plumbing; `lib/internal/permissions_service.py` becomes a thin wrapper keeping its
public API (R3). The status normalizer moves to `api/app/internal/status.py` (R2). The init-side
asset-link routes live in `inits` and import `lib`'s `AssetInit` model — the same direction of
dependency `lib/routes/asset_inits.py` already has with `Initiative` (R7). No per-module copy of
connection, auth, permission or transition plumbing is introduced.

### II. API-First Contract Stability — ✅ PASS

Every endpoint is new; the three existing `GET /api/initiatives/*` routes and all `lib` routes are
untouched (the permission extraction preserves `lib`'s function signatures and HTTP behaviour).
All list endpoints take bounded `skip`/`limit`. See
[contracts/initiatives-api.md](contracts/initiatives-api.md).

### III. Risk-Based Testing Discipline — ✅ PASS (with required work)

This feature adds contract, permission and status-transition behaviour, so automated tests are
mandatory: six new `test_inits_*.py` modules (R12) covering the full transition table (allowed
and refused, collaboration written or not), MANAGE/VIEW enforcement on every write and per-init
read, scoping-before-pagination, revoke/re-grant, link restore/409, diagnostics labels and
fallbacks, history/discussion shape. The permission-engine extraction is guarded by the existing
`lib` suites passing unchanged. `make test` plus [quickstart.md](quickstart.md) for UI behaviour.

### IV. Security and Secret Hygiene — ✅ PASS

No change to authentication, secrets or CORS. Layered authorization per the pattern: module RBAC
(`INITS/INITIATIVES`, edit for writes) outer; per-initiative MANAGE/VIEW inner; superuser bypass
and `is_active` semantics preserved. Per-init **reads** also require VIEW (stricter than the
asset side's permission reads, R8). The status rule and list-value validation are enforced
server-side, not only by the disabled `<select>`. VIEW holders cannot self-escalate via
`init_permissions`. An owner cannot link an asset they cannot see.

### V. Performance and Operability Baselines — ✅ PASS

Managed sessions from `app/internal/dependencies`. `/with-access` filters before paginating with
one grant query + one favorites query; diagnostics is three queries; history batches actor
lookups — no N+1. Compose services, ports and Make targets untouched.

### Established Domain Patterns

- **Per-resource permissions — ✅ PASS.** `init_permissions` follows the `asset_permissions`
  model exactly (MANAGE/VIEW, `valid_from`/`valid_to`, revoke-not-delete, no `is_active`,
  RBAC outer + `require_init_manage` / `InitAccessForbidden` → 403 inner), and shares its engine.
- **Content versioning — n/a.** Initiatives are not versioned.
- **Contribution / approval workflows — ⚠️ DEVIATION, justified.** Activity is recorded on
  `collaborations`, not the generic `actions` substrate. See § Complexity Tracking.

### Compatibility and Deployment Rules — ⚠️ DEVIATION, justified

Seed files are edited in place (status realignment, new list rows) rather than through a new
ordered migration. See § Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-initiative-management/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0 — 12 decisions
├── data-model.md        # Phase 1 — models, state machine, seed changes
├── quickstart.md        # Phase 1 — validation scenarios
├── contracts/
│   └── initiatives-api.md   # Phase 1 — 13 new endpoints
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — created by /speckit-tasks, NOT by this command
```

### Source code (repository root)

```text
db/sql/
├── 51-inits-ddl.sql            # + COLLAB_TYPE/KICKOFF; + es rows for 5 inits lists
└── 52-inits-insert.sql         # realign initiative statuses + types; + init_permissions grants

api/app/internal/
├── resource_permissions.py     # NEW — engine extracted from lib (scopes, validity, matching,
│                               #   effective levels, not-revoked clause), model-parameterised
└── status.py                   # NEW — shared normalize()

api/app/lib/internal/
└── permissions_service.py      # REFACTOR — thin wrappers over resource_permissions; public
                                #   API and behaviour unchanged

api/app/inits/
├── internal/
│   ├── models.py               # + InitiativeUpdate, InitiativeWithAccess, Collaboration,
│   │                           #   InitPermission(+Create/Update), Diagnostic, DiagnosticRow,
│   │                           #   FavoriteInit, InitiativeAsset, InitHistoryEntry/DiscussionItem
│   ├── status_service.py       # NEW — transition map, validate_transition, allowed_targets,
│   │                           #   log_status_collaboration
│   ├── permissions_service.py  # NEW — accessible_inits, user_init_access,
│   │                           #   require_init_manage/view, InitAccessForbidden
│   ├── collaborations_service.py  # NEW — get_initiative_history, list_discussion
│   └── diagnostics_service.py  # NEW — per-criterion rows with resolved labels
└── routes/
    ├── initiatives.py          # + /with-access, PUT, DELETE, /{id}/diagnostics
    ├── initiative_assets.py    # NEW — /api/initiatives/{id}/assets GET/POST/DELETE
    ├── init_permissions.py     # NEW — /api/init_permissions
    └── collaborations.py       # NEW — /api/collaborations/{history,discussion}/init/{id}

api/app/main.py                 # include the three new routers

api/tests/
├── test_inits_status.py        # NEW
├── test_inits_access.py        # NEW
├── test_inits_permissions.py   # NEW
├── test_inits_initiative_assets.py  # NEW
├── test_inits_diagnostics.py   # NEW
└── test_inits_collaborations.py     # NEW

ui/src/
├── pages/inits/initiatives.astro           # NEW — list page (no create)
├── components/inits/InitiativeDetailModal.astro   # NEW — shell, core fields, status policy,
│                                                  #   tab-scoped save, discard dialog
├── components/svelte/
│   ├── InitiativeDetailTabs.svelte         # NEW — 6 tabs, diagnosis view, related assets,
│   │                                       #   permissions (diff flush)
│   └── Foro.svelte                         # + optional `api` and `idAttr` props (defaults =
│                                           #   today's asset behaviour)
├── lib/
│   ├── initiatives.ts          # + getInitiativesWithAccess, updateInitiative,
│   │                           #   deleteInitiative, getInitiativeDiagnostics,
│   │                           #   get/add/removeInitiativeAsset
│   ├── init_permissions.ts     # NEW
│   ├── collaborations.ts       # NEW — history + discussion fetchers
│   └── history.ts              # + optional `fetcher` and `idAttr` in mountHistory config
├── types/api.ts                # + InitiativeWithAccess, InitiativeUpdate, DiagnosticRow,
│                               #   InitiativeAsset, InitPermission(+Create/Update)
└── i18n/{en,es}.json           # initiative_modal.*, initiative_table.*,
                                #   initiative_detail_modal.*, history.action.<COLLAB_TYPE>…
```

**Structure Decision**: the existing three-surface layout, unchanged. Backend follows the
domain `internal/` (logic) + `routes/` (HTTP) split, with the single genuinely cross-domain
mechanism promoted to `api/app/internal`. Frontend follows the established split: framework-free
services in `ui/src/lib/`, manually-mounted islands in `ui/src/components/svelte/`, page shells
in `ui/src/pages/{module}/`.

## Implementation Sequencing

1. **Foundation (blocks everything)**: seed changes → models → `resource_permissions`
   extraction with `lib` suites green → `inits` permission + status services.
2. **US1 (P1)**: `/with-access` + tests → list page, i18n. Independently shippable (read-only).
3. **US2 (P1)**: PUT (core, no status yet) / DELETE, diagnostics, init-assets, init-permissions,
   history/discussion endpoints + tests → modal + island; Foro/history parameterisation.
4. **US3 (P2)**: status transitions in PUT + tests → `applyStatusPolicy` from `allowed_statuses`,
   hints, History labels for KICKOFF/DELIVERY/ARCHIVING.
5. **Close-out**: quickstart pass as a non-superuser, `memory/CHANGELOG.md` entry,
   `memory/MEMORY.md` (inits no longer read-only; engine moved to `app/internal`; decisions),
   `docs/user-stories/states-and-types.md` initiative transition table and `COLLAB_TYPE` row.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Workflow activity on `collaborations` instead of the Constitution-named `actions` substrate | User requirement (FR-029); `actions.asset` is a NOT NULL FK to `assets`, so initiative rows cannot live there. `collaborations` pre-exists with the same `type` + `workflow_status` shape and seed data — it is the `inits` instance of the substrate, not a bespoke per-workflow table. The pattern's rules are kept: one substrate per domain, enum extended first (`KICKOFF`), one service per transition, single transaction. | Nullable `actions.asset` + `actions.init`: widens every `lib` query and migrates shipped data; contradicts the user's explicit choice. |
| Seed files edited in place (no ordered migration) | Product unreleased; `make rebuild` is the upgrade path; seed statuses are invalid today and must be corrected at the source. Same exception as the 2026-09-16 notifications redesign. Provisioned DBs get one-off statements listed in the PR / quickstart. | A new `53-inits-*.sql` patch file: leaves the invalid values in the canonical seed and fragments it for a product with no production data. |
| UI modal/island derived by copy rather than a shared generic component | `AssetDetailTabs.svelte` is ~40 % characteristics machinery with asset-bound services and payloads; generalising it risks a shipped surface for one extra consumer. The genuinely generic readers (Foro, history) are parameterised, not copied. | A generic `EntityDetailTabs` with injected services: larger change to a shipped component; revisit when Explore Initiatives adds a third consumer. |
