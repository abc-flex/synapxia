# Implementation Plan: Process Management

**Branch**: `009-process-management` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-process-management/spec.md`

## Summary

This plan delivers HU-PR01–04. It adds a Process Management page (`/proc/processes`) with a list of processes and a create/edit dialog whose tabs are **Core Fields → Related processes → Related assets → Related inits**. The three Related tabs reproduce Asset Management's Related tabs through one new shared Svelte component.

The backend promotes the `workflows` stub domain to the Processes domain. It adds:
- a server-enforced status lifecycle (DRAFT → REVIEW → PUBLISHED → DEPRECATED, plus REVIEW → DRAFT; create always DRAFT);
- an acyclic parent hierarchy;
- a dedicated, BPMN-oriented `PROCESS_RELATION_TYPE` list with two compatibility rules (SUPPORTS: Support → Primary; PRECEDES: same type);
- one atomic "replace the set" endpoint per Related tab, plus an all-or-nothing create.

`process_assets` and `process_inits` gain a relation type in their primary key. That change is made **in place** in the existing SQL files, at the user's request (pre-production, no migration).

## Technical Context

**Language/Version**: Python ≥3.14 in the API container (`api/pyproject.toml`); TypeScript in Astro 5 / Svelte 5

**Primary Dependencies**: FastAPI + SQLModel, fastapi-users (JWT); Astro 5 SSR + Vite 8 + Tailwind + Flowbite; Svelte 5 islands mounted manually with `mount()`

**Storage**: PostgreSQL 18; tables in `db/sql/71-proc-ddl.sql` (edited in place), seed in `72-proc-insert.sql`

**Testing**: pytest on SQLite fixtures (`docker compose exec -T api uv run pytest -q`; baseline 749 passed); `make test`; manual UI pass through `quickstart.md`

**Target Platform**: Docker Compose locally; Vercel (API serverless via Mangum, UI) + Neon in deployment

**Project Type**: web application (modular monolith: API + UI + DB)

**Performance Goals**: list and dialog load in under 2 s for the seeded inventory (about 45 processes) (SC-005); a tab save is one request

**Constraints**:
- No N+1 queries: list names are resolved with batched lookups, and the parent check is one projected query.
- `limit` is capped at 500.
- No new dependency.
- No access to LIB, INITS or ADMIN privileges is needed for the dialog's pickers.

**Scale/Scope**: tens to low hundreds of processes; 4 tables (2 changed), 1 new list; 12 endpoints; 1 page, 1 modal shell, 2 Svelte components

## Constitution Check

*GATE: must pass before Phase 0 research; re-checked after Phase 1 design.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Modular monolith** | All backend code sits in the existing stub domain `api/app/workflows`, whose models already say "Processes module" (R1): models and services in `internal/`, routes in `routes/`, routers registered in `main.py`. It reuses `app/internal` (`require_privilege`, `get_db_session`, `list_values.validate_list_value`). There is no copied permission, session or list-validation plumbing. | ✅ |
| **II. API-first contract stability** | Only additive routes under `/api/processes`. No existing key is renamed or removed. The list keeps `skip`/`limit` (max 500). UI types and services are added in `types/api.ts` and `lib/processes.ts`. | ✅ |
| **III. Risk-based testing** | New contract, permission and data-rule surfaces get five pytest suites (R15). UI parity and staging are verified manually through `quickstart.md`, which is acceptable for UI-only behaviour. | ✅ |
| **IV. Security & secrets** | JWT plus `require_privilege("PROC","PROCESSES", can_edit)` on every route. Superuser and `is_active` semantics are unchanged. `form-options` returns names only. No secrets. | ✅ |
| **V. Performance & operability** | Managed sessions; batched name lookups; the parent walk uses one query; each tab save is one transaction; the services still boot with `make up` and pass `make test`. | ✅ |
| **Pattern: per-resource permissions** | Not applicable: access is by module privilege only (spec assumption, R9). No grant table is introduced. | ✅ N/A |
| **Pattern: content versioning** | Not applicable: processes are not versioned. | ✅ N/A |
| **Pattern: contribution workflow** | Not applicable: the status lifecycle is a single-actor edit validated by a status service, with no propose/review hand-off and no `actions` rows (spec: no status history). | ✅ N/A |
| **Compatibility rule: DB evolution additive and migration-driven** | **Deviation**: the two link tables change their primary keys in place, with no migration (R2). See Complexity Tracking. | ⚠️ Justified |

**Post-design re-check (after Phase 1)**: the data model, contracts and structure keep every row above. The only deviation is still the in-place schema edit, which is justified below. **Gate passes.**

## Project Structure

### Documentation (this feature)

```text
specs/009-process-management/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified)
├── research.md          # Phase 0: decisions R1–R15
├── data-model.md        # Phase 1: entities, lifecycle, rules, seed changes, access matrix
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── processes-api.md # Phase 1: 12 endpoints + UI service layer
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2: created by /speckit-tasks, NOT by this command
```

### Source code (repository root)

```text
db/sql/
├── 71-proc-ddl.sql             # EDIT IN PLACE: process_assets/process_inits + type, PK with type;
│                               #   PROCESS_RELATION_TYPE list (en/es); comment on related_processes.type
└── 72-proc-insert.sql          # EDIT IN PLACE: related_processes → PRECEDES/SUPPORTS;
                                #   type = RELATED_TO on process_assets/process_inits

api/app/workflows/
├── internal/
│   ├── models.py               # Process (+Create/Update/Read/Detail), RelatedProcess,
│   │                           #   ProcessAsset, ProcessInit, link item/read models, FormOptions
│   ├── status_service.py       # NEW: TRANSITIONS, validate_create_status, validate_transition,
│   │                           #   allowed_statuses_for
│   ├── relation_rules.py       # NEW: self / duplicate / unordered INTERACTS_WITH / compatibility /
│   │                           #   type-change guard; RULES published to form-options
│   ├── process_service.py      # NEW: core validation (code, lists, parent cycle, unit, owner),
│   │                           #   create-with-links transaction, update, logical remove
│   └── links_service.py        # NEW: replace_relations / replace_assets / replace_inits
│                               #   (one transaction, deactivate / reactivate / insert / update)
└── routes/
    ├── processes.py            # NEW: /api/processes (list, form-options, detail, create, update, delete)
    └── process_links.py        # NEW: /api/processes/{code}/{relations,assets,inits} GET + PUT

api/app/main.py                 # include the two new routers

api/tests/
├── proc_helpers.py             # NEW
├── test_proc_processes.py      # NEW
├── test_proc_status.py         # NEW
├── test_proc_relations.py      # NEW
├── test_proc_links.py          # NEW
└── test_proc_access.py         # NEW

ui/src/
├── pages/proc/processes.astro              # NEW: DataTable list + filters + New Process
├── components/proc/ProcessDetailModal.astro  # NEW: shell, Core Fields, status policy,
│                                             #   create (one save) vs edit (per-tab save), discard
├── components/svelte/
│   ├── ProcessDetailTabs.svelte            # NEW: tab strip (Core Fields re-parented + 3 Related tabs),
│   │                                       #   dots, hydrate/staged/reset per tab
│   └── RelatedLinksTab.svelte              # NEW: shared Related tab, markup taken from
│                                           #   AssetDetailTabs' Related Assets (R10)
├── lib/processes.ts                        # NEW
├── types/api.ts                            # + Process* types
└── i18n/{en,es}.json                       # process_table.*, process_modal.*, process_detail_modal.*,
                                            #   related_links.*; menu_options.processes relabelled

docs/user-stories/07-proc.md                # API domain reference → api/app/workflows
```

**Structure Decision**: the existing three-surface layout, unchanged. The backend follows the domain layout of `api/app/ana/` (models and services in `internal/`, one route module per resource). The UI follows Dashboard Management's page → `.astro` modal shell → Svelte island split, with the Related tabs as a reusable component, in the way `PermissionsTab.svelte` was extracted.

## Phase summary

- **Phase 0, [research.md](research.md)**: 15 decisions; no unresolved unknowns. The key ones:
  - R1: `workflows` domain.
  - R2: in-place DDL.
  - R3: per-tab atomic replace.
  - R4: all-or-nothing create.
  - R6: relation rules as data.
  - R8: a PROC-gated form-options endpoint.
  - R10: a shared `RelatedLinksTab`.
- **Phase 1**:
  - [data-model.md](data-model.md): lifecycle, link rules, seed rewrite, access matrix.
  - [contracts/processes-api.md](contracts/processes-api.md): 12 endpoints.
  - [quickstart.md](quickstart.md): 17 API checks and 9 UI checks.
  - The agent context (`CLAUDE.md`) now points to this plan.
- **Phase 2**: `/speckit-tasks`.

## Follow-ups (out of scope)

- Switch `AssetDetailTabs.svelte`'s Related Assets and Related Inits tabs to `RelatedLinksTab.svelte` (R10).
- Value Chain (HU-PR05) and Process Map (HU-PR06) render `PROCESS_RELATION_TYPE` with the BPMN counterparts in data-model.md.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| In-place change of `process_assets`/`process_inits` primary keys and seed, with no ordered migration and no `provisioned-db.sql` (Compatibility rule: "Database evolution MUST be additive and migration-driven") | The user's explicit decision: the product has not reached production, and no environment holds process data that must be preserved. The same approach shipped in SpecKit 003 (seed-only, no migration). | A migration script would preserve data nobody has yet. Rollback: revert `71-proc-ddl.sql` and `72-proc-insert.sql`, then `make rebuild`. Any provisioned DB (local or Neon) must be recreated or patched by hand; the quickstart and CHANGELOG entry will say so. |
