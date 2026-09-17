# Implementation Plan: Asset Notification Scheme Redesign

**Branch**: `003-asset-notifications-redesign` | **Date**: 2026-09-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-asset-notifications-redesign/spec.md`

## Summary

Collapse the asset workflow lifecycle from three states to two (`PENDING` / `HANDLED`,
labelled "Pendiente" / "Atendido"), turn the header bell into a strict feed of what awaits the
caller, turn "My Asset Requests" into the complete durable record of everything the caller has
taken part in, and make both self-refreshing.

The three-state model is the root defect: the middle state records only that a user *looked*
at an item, mixing read state with work state. That conflation forces the `DISMISSIBLE_TYPES`
special case in `actions_service.py` and makes the bell and the requests page render identical
rows, which is the duplication the user reported. Removing the middle state removes both.

Technically this is: a seed-only enum rewrite across `lib` and `inits` (no DDL, no migration —
the product is unreleased), a new derived read model that groups the caller's workflow rows by
asset instead of by `(asset, type)`, one new endpoint plus three removals and one rename, and a
shared client store that refreshes on focus, on `pageshow`, on a 60 s visibility-gated timer,
and on same-tab mutation events.

## Technical Context

**Language/Version**: Python ≥3.12 (API) · TypeScript / Astro 5 SSR + Svelte 5 (UI) ·
PostgreSQL 18 (DB)

**Primary Dependencies**: FastAPI + SQLModel, managed by `uv` · Astro 5, Vite 8, Tailwind,
Flowbite, Svelte 5 via manual `mount()` (never `@astrojs/svelte` — its island codegen is
broken at the pinned 9.0.0), Bun

**Storage**: PostgreSQL 18; schema and seed data as ordered SQL files in `db/sql/`, executed
only on a fresh volume

**Testing**: `pytest` in `api/tests/` — run on a **Python 3.12** virtualenv, not the
container's default 3.14, which cannot import the backend (pydantic `eval_type_backport`
`AssertionError`). Smoke via `make test`. `bun run build` / `astro check` for the UI. No
browser-automation harness exists in this repo.

**Target Platform**: Docker Compose for local parity; Vercel serverless via Mangum + Neon for
deployment

**Project Type**: Web — modular monolith with three surfaces (API, UI, DB)

**Performance Goals**: a session converges on current state within 90 s while visible
(SC-005); zero requests while hidden (SC-008); every list endpoint bounded by `skip`/`limit`

**Constraints**: no long-lived connections — the serverless target rules out SSE and
websockets, so refresh is polling-based (research R10). Unreleased product: seeds are edited
in place and `make rebuild` is the only upgrade path. Queries must stay portable to SQLite,
which the test suite runs on.

**Scale/Scope**: internal tool, tens of users. Blast radius measured before planning —
5 API service modules, 1 route module, 3 seed files, 6 test files (79 references to the
removed state names, 45 of them in `test_lib_notifications.py`), 4 Svelte islands, 2 Astro
pages, 2 i18n files.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design.*

### I. Modular Monolith Boundaries — ✅ PASS

All backend work stays inside `api/app/lib/` (`internal/actions_service.py`,
`internal/{propose,review,modify,version}_service.py`, `routes/actions.py`). The seed change
touches `inits` data but adds no `inits` code. No new shared plumbing is introduced: the
participation read model lives in `actions_service`, which already owns every query over the
`actions` substrate.

### II. API-First Contract Stability — ⚠️ **VIOLATION — justified below**

Removes `POST /api/actions/notifications/{id}/notified`, `GET /api/actions/reviews`,
`GET /api/actions/modifications`; renames `.../dismiss` to `.../acknowledge`; changes
`GET /api/actions/notifications` from a bare array to `{ items, total }` and drops its
`unread` key. Bounded pagination is preserved and extended — the new `participations`
endpoint takes `skip`/`limit`. See § Complexity Tracking.

### III. Risk-Based Testing Discipline — ✅ PASS (with required work)

This is a contract change, so automated tests are mandatory, not optional. The plan requires
updating all six affected test files and adding coverage for: the two-state transitions,
participation grouping (INV-1, one row per asset), the `SELF`/`OTHER` derivation across all
seven worked cases in [data-model.md](data-model.md), the acknowledge guard's `400` on
actionable types, and the pagination bound. `make test` plus the manual pass in
[quickstart.md](quickstart.md) cover the UI behaviour no harness can assert.

### IV. Security and Secret Hygiene — ✅ PASS

No change to authentication, secrets, CORS, or `is_active` / `is_superuser` semantics. The new
endpoint is inherently self-scoped (`Action.user_id == caller`) and uses `current_active_user`
without a module privilege gate — following the 2026-09-09 precedent where self-scoping
`actions` endpoints dropped the never-seeded `LIB/ACTIONS` privilege that rejected every
non-superuser. The acknowledge endpoint keeps its per-action ownership check. No endpoint
widens who may act on an asset.

### V. Performance and Operability Baselines — ✅ PASS

Three statements per request regardless of row count, using the batched `IN` pattern
`_list_open_actions` already uses — no N+1 (research R8). Grouping happens in Python rather
than in a Postgres-only aggregate, keeping the query SQLite-testable; the `/api/assets/with-access`
rewrite is the in-repo precedent for why that matters. `skip`/`limit` bound every list.
Sessions stop polling when hidden. Compose service contracts, ports and Make targets are
untouched.

### Established Domain Patterns — ✅ PASS (contribution/approval workflow)

The Constitution requires any propose → review → publish flow to build on the generic
`actions` substrate and to **extend the existing `ACTION_TYPE` / `WORKFLOW_STATUS` enums
first**, never to create a bespoke table. This feature does exactly that: it modifies
`WORKFLOW_STATUS` in place and adds no table. Each state transition stays owned by one service
module inside a single transaction (`review_service`, `modify_service`, and the acknowledge
path in `actions_service`). The per-resource permission and same-row versioning patterns are
not touched by this feature.

### Compatibility and Deployment Rules — ⚠️ **DEVIATION — justified below**

"Database evolution MUST be additive and migration-driven through `db/sql` with ordered
scripts; destructive changes require explicit rollback instructions." This plan edits existing
seed files in place and deletes rows from them. See § Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-asset-notifications-redesign/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — 14 decisions with rationale
├── data-model.md        # Phase 1 — enum change + derived Participation model
├── quickstart.md        # Phase 1 — validation scenarios
├── contracts/
│   └── actions.md       # Phase 1 — API contract deltas
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — created by /speckit-tasks, NOT by this command
```

### Source code (repository root)

```text
db/sql/
├── 41-lib-ddl.sql             # WORKFLOW_STATUS list_items: 3 values → 2
├── 42-lib-insert.sql          # actions seed: rename values, delete NOTIFIED rows
└── 52-inits-insert.sql        # collaborations seed: same value rewrite

api/app/lib/
├── internal/
│   ├── actions_service.py     # state constants, _WORKFLOW_SUMMARIES, participation
│   │                          #   read model; remove mark_notified, DISMISSIBLE_TYPES,
│   │                          #   NotificationNotDismissible, list_review_requests,
│   │                          #   list_pending_modifications, the `unread` field
│   ├── propose_service.py     # WF_* constants
│   ├── review_service.py      # WF_* constants
│   ├── modify_service.py      # WF_* constants
│   ├── version_service.py     # WF_* constants
│   └── models.py              # NotificationItem → participation response models
└── routes/
    └── actions.py             # + /participations · notifications narrowed
                               # · /notified removed · /dismiss → /acknowledge
                               # · /reviews and /modifications removed

ui/src/
├── lib/
│   ├── notifications.ts       # drop markNotified/getReviewRequests/
│   │                          #   getPendingModifications; add getParticipations,
│   │                          #   acknowledgeNotification
│   └── notificationsStore.ts  # NEW — shared list + subscribe/refresh/start/stop,
│                              #   visibility gating, pageshow, notifications:changed
├── components/svelte/
│   ├── NotificationBell.svelte    # subscribe to store; pending-only; "view all" link;
│   │                              #   remove dismiss control and unread styling
│   ├── MyAssetRequests.svelte     # NEW — two views, awaited-party column,
│   │                              #   inline acknowledge
│   ├── ReviewAction.svelte        # remove markNotified; navigate to the page on success
│   ├── ModifyAction.svelte        # remove markNotified; navigate to the page on success
│   └── ShowAction.svelte          # remove markNotified; Dismiss → Acknowledge
├── pages/lib/
│   ├── my_asset_requests.astro    # SSR table → island shell
│   └── modifications.astro        # DELETED (already unreferenced)
├── types/api.ts               # Participation types; drop `unread`
└── i18n/{en,es}.json          # status_seen → status_handled; awaited-party,
                               #   acknowledge, tab and empty-state strings

api/tests/                     # test_lib_notifications (rewrite), test_lib_review,
                               #   test_lib_modify, test_lib_propose, test_lib_history,
                               #   test_lib_versioning
```

**Structure Decision**: The repo's existing three-surface layout is used unchanged. Backend
work is confined to the `lib` domain's `internal/` (logic) and `routes/` (HTTP) split per
Principle I. Frontend work follows the established division where `ui/src/lib/` holds
framework-free services and `ui/src/components/svelte/` holds manually-mounted islands — the
same split `lib/foro.ts` / `Foro.svelte` settled on.

## Implementation Sequencing

The user stories are independently testable, but one ordering constraint is a correctness
requirement rather than a preference:

> **US1 must ship before US2.** `/lib/modifications` is already unreferenced from every menu,
> so the notification bell is today the *only* route to a `MODIFICATION` assignment. Narrowing
> the bell before the unified page covers that type would strand a proposer who opened their
> modify screen and navigated away — and because the state is persisted, redeploying would not
> recover it.

US3 (refresh) is genuinely independent and can be built and demonstrated against the current
lists. US4 (vocabulary) is the seed-and-labels pass; it lands last because every backend slice
depends on the constants it defines, so it is scheduled first *in the code* but verified last
*as a user-visible outcome*.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| **Principle II** — removing `POST /notifications/{id}/notified` and dropping the `unread` response key | FR-002 and FR-003 forbid recording or exposing that a user has viewed an item. The endpoint exists only to write that state; `unread` exists only to read it. Keeping either would preserve the read/work conflation the feature removes. | Deprecating them in place and leaving them unused was considered. Rejected: a live endpoint that writes a state no longer in the enum is a trap for the next contributor, and `unread` would have to be filled with a constant, which is worse than absent. The product is unreleased and the bundled UI is the sole consumer, adapted in the same PR — the same justification accepted for the 2026-06-27 response-envelope change. |
| **Principle II** — removing `GET /actions/reviews` and `GET /actions/modifications` | FR-027 requires retiring surfaces made redundant by the unified page. Each returns a single-type slice of what `participations` returns whole. | Keeping them as thin wrappers was considered. Rejected: they are precisely the partial duplicate lists this feature exists to eliminate, and leaving them invites a future page to re-create the split. Both have exactly one caller each, deleted in the same PR. |
| **Principle II** — renaming `.../dismiss` to `.../acknowledge` | Under the new model "dismiss" denotes what FR-017 forbids: removing an item from view without resolving it. Acknowledging *is* resolving, for informational types. | Keeping the old path was the lower-diff option and genuinely tempting. Rejected because the endpoint would stay named after the behaviour being eliminated, and the guard it carries (informational types only) would read as arbitrary rather than as the natural consequence of what acknowledgement means. |
| **Compatibility rules** — editing `db/sql` seeds in place, including deleting rows, with no migration script | The product is unreleased (user's explicit instruction). Seed files execute only on a fresh volume, so an in-place edit *is* the pre-release convention, and `make rebuild` is the rollback. | An additive migration under `db/sql/manual/` was planned and then dropped at the user's direction. Rejected because it would produce a script that no database ever runs: there is no deployed instance holding the old vocabulary. The obligation this waives — rollback instructions — is met by `make rebuild` being the documented and only path, stated in [quickstart.md](quickstart.md). |

**Post-Phase-1 re-check**: the design added no further violations. The new `participations`
endpoint is additive and bounded; the client store introduces no server state; no table, column
or index is created.

## Phase 2 scope note

`/speckit-tasks` generates `tasks.md`. Two items must not be lost in that translation, because
neither is visible from the requirement list alone:

1. **The CHANGELOG entry.** `AGENTS.md` requires one rollup entry in `memory/CHANGELOG.md` per
   PR, and `MEMORY.md`'s decisions log needs the two-state decision recorded — plus the
   "Known blockers" P1 row updated, since the endpoints named there are changing.
2. **The seed/rebuild dependency.** Any task that verifies behaviour against a running stack
   depends on `make rebuild` having run after the seed edits. Verifying against a stale volume
   produces a confusing all-empty failure mode rather than an obvious one.
