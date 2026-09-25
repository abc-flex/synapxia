# Implementation Plan: Explore Initiatives, Propose Initiative & Initiative Notifications

**Branch**: `005-explore-initiatives` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-explore-initiatives/spec.md`

## Summary

This feature gives the `inits` domain the whole contribution loop the AI Library already has:

- **Explore Initiatives** (`/inits/explore`): a grant-scoped gallery of Accepted, In Progress and Delivered initiatives. It has the same favorites toggle and six-option privilege filter as Explore Category, votes, a discussion count, and "+ Propose". Initiatives are shown as full-width rows rather than the dense asset grid, and a card opens a read-only Initiative Detail.
- **Propose Initiative** (`/inits/propose`): a Core Fields → Diagnosis Questions → Related Assets wizard, with the asset reviewer rule. "Request diagnosis" writes everything in one transaction.
- **Diagnosis**, **Modify** and **Acknowledgment** pages close the loop.
- **The bell splits** into Assets and Initiatives tabs.
- **My Initiative Requests** sits directly below My Asset Requests in the Account Menu.

Technically:

- **No DDL.** Two seed edits: collaborators and reviewers get edit access on `INITS/EXPLORE`, and an obsolete `DELIVERY/PENDING` row is removed.
- **Four new inits services** mirror the lib `propose` / `review` / `modify` / `actions` services over `collaborations`.
- **Reviewer eligibility** is extracted from `lib` into `api/app/internal/reviewers.py` (shared, public names preserved).
- **14 additive endpoints.**
- **UI.** Six new pages and five new components. Shared pieces are parameterised rather than forked: `CardGallery` layout, `initCardGallery` services, a `DiagnosisTable` extracted from the 004 island, `AckDialog`, and the notifications store.

## Technical Context

**Language/Version**: Python ≥3.14 (API, per `api/pyproject.toml`) · TypeScript / Astro 5 SSR + Svelte 5 (UI) · PostgreSQL 18 (DB)

**Primary Dependencies**: FastAPI + SQLModel, `uv` · Astro 5, Vite 8, Tailwind, Flowbite, Svelte 5 via manual `mount()` (never `@astrojs/svelte`), Bun

**Storage**: PostgreSQL 18. The tables already exist (`db/sql/51-inits-ddl.sql`) and are mapped by spec 004. Seeds are edited in place (unreleased product, `make rebuild`).

**Testing**: `pytest` in `api/tests/` on the SQLite `session`/`client` fixtures and `inits_helpers.py`, run as `docker compose exec -T api uv run pytest -q`, with a baseline of 8 pre-existing failures. UI: `bun run build` + `astro check` (unchanged baseline), plus a manual click-through as seeded non-superusers (no browser harness).

**Target Platform**: Docker Compose locally; Vercel serverless (Mangum) + Neon. No long-lived connections, so notifications stay poll-based (60 s, visibility-gated).

**Project Type**: Web — modular monolith, three surfaces (API, UI, DB)

**Performance Goals**: gallery and bell feel instant for an internal portfolio (tens of initiatives). Constant query count per request (grouped `IN` lookups, no N+1). A new diagnosis request is visible to the reviewer within one 60 s poll (SC-003).

**Constraints**:
- Additive API only (Principle II).
- Lists bounded by `skip`/`limit` (Explore `limit ≤ 500`, requests `≤ 200`, feed `≤ 50`).
- Queries portable to SQLite (no Postgres-only aggregates).
- Every workflow transition is one transaction, with the actor taken from the session.

**Scale/Scope**:
- API: 13 endpoints across 2 route modules; 4 new inits services + 1 shared `internal` module; about 10 new schemas; 2 seed edits; 7 new test modules.
- UI: 6 pages, 5 new components, 4 parameterised shared pieces, 2 service files extended, types, and 2 i18n files.

## Constitution Check

*GATE: evaluated before Phase 0 and re-checked after Phase 1 design — result unchanged.*

### I. Modular Monolith Boundaries — ✅ PASS

- **Where the code lives.** All new behaviour is in `api/app/inits/` (`internal/` services + schemas, `routes/`).
- **Shared plumbing.** The one mechanism both domains need, reviewer eligibility and auto-assignment, is **moved** to `api/app/internal/reviewers.py`. `lib/internal/propose_service.py` re-exports it unchanged (R2), following the spec 004 `resource_permissions` precedent.
- **Existing shared modules used.** Permission checks go through the shared engine via `inits/internal/permissions_service.py`. Asset visibility for linking goes through `lib`'s existing `permissions_service` — the same direction of dependency that `initiative_assets.py` already has.
- **Nothing duplicated.** No connection, auth, permission or transition plumbing is copied.

### II. API-First Contract Stability — ✅ PASS

- All 13 endpoints are new.
- `GET /api/initiatives/{id}`, `/with-access` and every `lib` route keep their gating and shapes.
- The reviewer extraction keeps `lib`'s function names, signatures and HTTP behaviour.
- `GET /api/collaborations/{id}` adds an embedded `initiative`, so core fields never require widening an existing route.
- Every list is bounded.
- See [contracts/initiatives-workflow-api.md](contracts/initiatives-workflow-api.md).

### III. Risk-Based Testing Discipline — ✅ PASS (with required work)

Contract, permission and workflow-transition changes make automated tests mandatory. Seven new modules (R16) cover:
- **Propose:** all-or-nothing, every 400 path, self-review, auto-assign, grant dedup.
- **Diagnosis:** each decision, guard order 403/409/400, score = Σ reviewer scores.
- **Modify:** reviewer re-armed, proposer-only, FEEDBACK-only, unlimited rounds.
- **Requests / notifications:** SELF/OTHER/HANDLED derivation including the owed-before-status rule, one row per initiative, the feed as a strict subset, acknowledge idempotency and 404/400, and DELIVERY/KICKOFF rows ignored.
- **Votes:** toggle, switch, clear, one active per user, actor from the session.
- **Explore:** the status filter, scoping before pagination, counts, favorites.
- **Reviewers:** a module test.

The lib workflow suites pass unchanged, which guards the extraction. UI behaviour is covered by [quickstart.md](quickstart.md) plus `make test`.

### IV. Security and Secret Hygiene — ✅ PASS

- No change to authentication, secrets or CORS.
- **Layered authorization:** `INITS` RBAC is the outer gate (edit for propose, votes and discussion), and per-initiative VIEW is the inner check. The workflow routes additionally require holding the PENDING thread, plus reviewer eligibility or proposer identity, re-checked server-side.
- **Actors come from the session.** No endpoint accepts a `user_id`. The asset vote API does; the initiative one deliberately does not (FR-053).
- **Link safety.** A proposer cannot link an asset they cannot see.
- **Semantics preserved.** Superuser bypass and `is_active` semantics are unchanged. The seed privilege change (R4) is scoped to one option for two profiles and mirrors their existing asset-side rights.

### V. Performance and Operability Baselines — ✅ PASS

- Managed sessions come from `app/internal/dependencies`.
- `/explore` uses a constant set of grouped queries.
- Requests and notifications use one threads query plus one batched initiatives query, as in `lib`.
- The store's parallel refresh keeps the last-known state per domain on failure.
- Compose services, ports and Make targets are untouched.

### Established Domain Patterns

- **Per-resource permissions — ✅ PASS.** Propose grants USER/MANAGE through `init_permissions` (open `valid_to`), exactly like the asset propose grants. All reads and writes use the shared engine; no new permission table.
- **Content versioning — n/a.** Initiatives are not versioned.
- **Contribution / approval workflows — ⚠️ DEVIATION, justified (same as spec 004).** The workflow runs on `collaborations`, not `actions`. The pattern's rules are kept: an existing substrate with `type` + `workflow_status`, the enum already holding every type, one service per transition, and a single transaction per transition. See § Complexity Tracking.

### Compatibility and Deployment Rules — ⚠️ DEVIATION, justified

Two seed files are edited in place rather than through a new ordered script. Provisioned DBs get the two one-off statements in quickstart § Provisioned databases. See § Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-explore-initiatives/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified 2026-09-24)
├── research.md          # Phase 0 — 16 decisions
├── data-model.md        # Phase 1 — threads, status machine, schemas, derivation, seed changes
├── quickstart.md        # Phase 1 — validation scenarios
├── contracts/
│   ├── initiatives-workflow-api.md   # 13 new endpoints
│   └── ui-surfaces.md                # routes, pages, components, i18n
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — created by /speckit-tasks, NOT by this command
```

### Source code (repository root)

```text
db/sql/
├── 12-admin-insert.sql         # COLLABORATOR/REVIEWER INITS.EXPLORE can_edit → TRUE
└── 52-inits-insert.sql         # delete collaboration id 8 (DELIVERY/PENDING)

api/app/internal/
└── reviewers.py                # NEW — REVIEWER_PROFILES, ADMIN_PROFILES, is_eligible,
                                #   is_admin, list_reviewers, resolve_reviewer (moved from lib)

api/app/lib/internal/
└── propose_service.py          # REFACTOR — re-export the moved names; behaviour unchanged

api/app/inits/
├── internal/
│   ├── models.py               # + DiagnosisAnswer, InitiativeProposeRequest,
│   │                           #   InitiativeDiagnoseRequest, InitiativeResubmitRequest,
│   │                           #   LinkableAsset, InitVoteTally, InitiativeExploreItem,
│   │                           #   InitiativeRequest, InitNotificationItem/Feed,
│   │                           #   CollaborationDetail
│   ├── criteria_validation.py  # NEW — active criteria + scale values; validate answers
│   ├── propose_service.py      # NEW — propose_initiative (single transaction)
│   ├── diagnosis_service.py    # NEW — DECISIONS, diagnose_initiative, score
│   ├── modify_service.py       # NEW — resubmit_initiative
│   ├── requests_service.py     # NEW — threads, participations, notifications, acknowledge
│   ├── votes_service.py        # NEW — get/set/clear vote, tallies (single + grouped)
│   └── explore_service.py      # NEW — explore listing + grouped counts
└── routes/
    ├── initiatives.py          # + /explore, /reviewers, /linkable-assets, /propose,
    │                           #   /{id}/diagnose, /{id}/resubmit (declared before /{init_id})
    └── collaborations.py       # + /votes/init/{id} GET/PUT/DELETE, /requests,
                                #   /notifications, /notifications/{id}/acknowledge, /{id}

api/tests/
├── inits_helpers.py            # + mk_collab, seed_criteria_with_scale, mk_asset helpers
├── test_internal_reviewers.py  # NEW
├── test_inits_propose.py       # NEW
├── test_inits_diagnosis.py     # NEW
├── test_inits_modify.py        # NEW
├── test_inits_requests.py      # NEW
├── test_inits_votes.py         # NEW
└── test_inits_explore.py       # NEW

ui/src/
├── pages/inits/
│   ├── explore.astro                     # NEW
│   ├── propose.astro                     # NEW
│   ├── diagnose.astro                    # NEW
│   ├── modify.astro                      # NEW
│   ├── show-collab.astro                 # NEW
│   └── my_initiative_requests.astro      # NEW
├── pages/lib/propose.astro               # adopt shared AckDialog (behaviour unchanged)
├── components/inits/
│   ├── InitiativeCard.astro              # NEW — full-width row card
│   └── InitiativeExploreModal.astro      # NEW — dialog shell for InitiativeDetailView
├── components/lib/gallery/CardGallery.astro   # + layout?: "grid" | "list" (default grid)
├── components/ui/AckDialog.astro         # NEW — extracted blocking dialog
├── components/svelte/
│   ├── DiagnosisTable.svelte             # NEW — extracted; modes view/propose/review/modify
│   ├── InitiativeDetailView.svelte       # NEW — read-only detail (5 tabs)
│   ├── InitiativeDiagnose.svelte         # NEW
│   ├── InitiativeModify.svelte           # NEW
│   ├── InitiativeOutcome.svelte          # NEW (show-collab)
│   ├── MyInitiativeRequests.svelte       # NEW
│   ├── InitiativeDetailTabs.svelte       # use DiagnosisTable mode="view" (rendering unchanged)
│   └── NotificationBell.svelte           # split into Assets / Initiatives tabs
├── components/core/header/
│   ├── Header.astro                      # + My Initiative Requests work item
│   └── AccountMenu.astro                 # + icon entry
├── lib/
│   ├── catalogGallery.ts                 # + optional services / idAttr (defaults = assets)
│   ├── ackDialog.ts                      # NEW — showAckDialog()
│   ├── initiatives.ts                    # + getInitiativesExplore, getInitiativeReviewers,
│   │                                     #   getLinkableAssets, proposeInitiative,
│   │                                     #   diagnoseInitiative, resubmitInitiative
│   ├── collaborations.ts                 # + votes, getCollaboration, getInitiativeRequests,
│   │                                     #   getInitiativeNotifications, acknowledgeCollaboration
│   └── notificationsStore.ts             # + initFeed / initPending / initHandled, allSettled
├── types/api.ts                          # + the schemas in data-model.md
└── i18n/{en,es}.json                     # namespaces listed in contracts/ui-surfaces.md

docs/user-stories/
├── 05-inits.md                 # HU-IN05 Related Assets step; HU-IN13 without DELIVERY
└── states-and-types.md         # tab matrix: Propose → Related Assets "Add relation"
```

**Structure Decision**: the existing three-surface layout is kept.
- **Backend.** It follows the domain `internal/` (logic) + `routes/` (HTTP) split, and promotes the single cross-domain rule (reviewer eligibility) to `api/app/internal`.
- **Frontend.** Framework-free services live in `ui/src/lib/`, manually-mounted islands in `ui/src/components/svelte/`, and page shells in `ui/src/pages/inits/`.
- **Parameterise, don't fork.** Shared components gain opt-in props whose defaults preserve today's behaviour.

## Implementation Sequencing

1. **Foundation (blocks everything).** The two seed edits, then the `reviewers.py` extraction (lib suites green), then the new schemas, then `criteria_validation.py`, then the `inits_helpers` additions.
2. **US1 + US2 (P1) — Propose.** `/reviewers`, `/linkable-assets`, `/propose` + tests; then `AckDialog` extraction, `DiagnosisTable` extraction (004 island adopts `view`), and the `/inits/propose` page with i18n. Independently shippable: proposals are recorded and visible in Initiative Management.
3. **US3 (P1) — Explore.** `votes_service`, `explore_service`, then `/explore` and the vote routes + tests. Then `CardGallery` layout, `initCardGallery` services, `InitiativeCard`, `InitiativeDetailView` + modal, and the `/inits/explore` page.
4. **US4 + US5 (P2) — Notifications and requests.** `requests_service`, then `/requests`, `/notifications`, acknowledge and `/{id}` + tests. Then store extension, bell split, `MyInitiativeRequests` page and the Account Menu item.
5. **US6 + US7 (P2) — Diagnose and modify.** Services + routes + tests, then the two pages.
6. **US8 (P3) — Acknowledgment.** Outcome page (the endpoint comes from step 4).
7. **Close-out.**
   - A quickstart pass as `adriana.velez` / `santiago.marin`.
   - The lib regression suites.
   - The `memory/CHANGELOG.md` rollup entry.
   - `memory/MEMORY.md`: inits workflow shipped; reviewer rule moved to `app/internal`; the stale "My Asset Requests is profile-gated" note fixed; the P2 stub row updated.
   - The two `docs/user-stories` files.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Workflow on `collaborations` instead of the Constitution-named `actions` substrate | This is the user's explicit choice (spec input). Also, `actions.asset` is a NOT NULL FK to `assets`. `collaborations` is the inits instance of the same substrate (`type` + `workflow_status`) and already holds every type. The same exception was recorded in spec 004. | Nullable `actions.asset` + `actions.init` widens every `lib` query and migrates shipped data, contradicting the user's choice. |
| Workflow services ported per domain rather than a generic model-parameterised engine | The lib services are small. Their guards differ by domain: characterizations vs diagnostics, `current_version` vs score, PUBLICATION vs ACCEPTANCE. A generic engine would rewrite shipped, tested `lib` code for one extra consumer. The genuinely shared rule, reviewer eligibility, **is** extracted (R2). | A generic threads/transition engine: high blast radius on the shipped asset workflow. Revisit if a third workflow domain appears. |
| Seed files edited in place (no ordered migration) | The product is unreleased; `make rebuild` is the upgrade path. The privilege flip and the obsolete-row removal belong in the canonical seed. The same exception applied to the 2026-09-16 redesign and spec 004. Provisioned DBs get one-off statements (quickstart). | A new `53-inits-*.sql` patch leaves the canonical seed inconsistent with the intended RBAC, for a product with no production data. |
| Propose persists links inside the proposal transaction, unlike the asset wizard's flush-after calls | FR-021 / SC-002 require all-or-nothing, which the asset pattern cannot give. | Mirroring the asset pattern violates the spec. |
