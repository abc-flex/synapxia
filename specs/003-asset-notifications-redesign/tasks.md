---

description: "Task list for Asset Notification Scheme Redesign"
---

# Tasks: Asset Notification Scheme Redesign

**Input**: Design documents from `/specs/003-asset-notifications-redesign/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/actions.md](contracts/actions.md),
[quickstart.md](quickstart.md)

**Tests**: REQUIRED, not optional. Constitution Principle III mandates automated tests for
backend contract and permission changes; this feature is a contract change. Test tasks are
listed first within each story and must fail before the implementation tasks land.

**Organization**: Tasks are grouped by user story. One deviation from full independence is a
correctness requirement, not a preference — see Dependencies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

Three surfaces per [plan.md](plan.md) § Project Structure: `api/app/lib/` (backend),
`ui/src/` (frontend), `db/sql/` (schema and seeds). Paths below are repository-relative.

---

## Phase 1: Setup

**Purpose**: A working test loop and a recorded baseline before anything changes.

- [X] T001 ~~Create the API test virtualenv on Python 3.12 at `api/.venv`~~ — **premise was stale.** Run the suite inside the container instead: `docker compose exec -T api uv run pytest -q`. The container's Python 3.14 venv imports the backend fine; the pydantic `eval_type_backport` `AssertionError` recorded in `memory/MEMORY.md` (2026-07-02) no longer reproduces, and `api/pyproject.toml` now declares `requires-python = ">=3.14"`, so a 3.12 venv would contradict the project's own pin. A stale Linux `api/.venv` leaked to the host through the bind mount and was deleted (untracked build output; `docker-compose.yml:77` shields the container's own venv with an anonymous volume).
- [X] T002 Baseline recorded: **8 failed, 231 passed**. All 8 are pre-existing and live in `api/tests/test_auth.py` (3), `test_health.py` (1) and `test_users.py` (4) — none of which this feature touches. Any failure outside those three files is new and must be accounted for.
- [X] T003 [P] Stack verified green: `make test` passes API health, DB readiness and the admin user.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two-state model at the data and constant level. Every user story's backend
reads these constants, so nothing else can start until this is complete.

**⚠️ CRITICAL**: Blocks US1, US2, US3 and US4.

**Note on scope**: this phase also renames the state **labels** in i18n. That work belongs to
US4 conceptually, but a label missing while the backend already emits the new value is a
visible defect on day one, so it lands here. US4's own phase covers the surface-by-surface
consistency sweep.

### Seeds

- [X] T004 Rewrite the `WORKFLOW_STATUS` list in `db/sql/41-lib-ddl.sql` (lines ~197-199): `ASSIGNED`→`PENDING` (label "Pending", sort 10), `FINISHED`→`HANDLED` (label "Handled", sort 20); delete the `NOTIFIED` row entirely.
- [X] T005 Rewrite the `actions` seed block in `db/sql/42-lib-insert.sql` (from line ~458): `'ASSIGNED'`→`'PENDING'` (20 rows), `'FINISHED'`→`'HANDLED'` (30 rows — 10 more than PENDING, because each of the 10 assets carries a `PROPOSAL` row that is born terminal), and **deleted** all 20 `'NOTIFIED'` rows. Do **not** renumber ids — gaps are safe because the block ends with `setval(pg_get_serial_sequence('actions','id'), MAX(id))`, and renumbering would require rewriting the `parent` references on rows 8/56/77/89.
- [X] T006 [P] Apply the same three rewrites to the `collaborations` seed block in `db/sql/52-inits-insert.sql` (from line ~113). Seed-only: no `inits` application code reads these values.

### Service constants

- [X] T007 In `api/app/lib/internal/actions_service.py`, replace `WORKFLOW_ASSIGNED`/`WORKFLOW_NOTIFIED`/`WORKFLOW_FINISHED` with `WORKFLOW_PENDING`/`WORKFLOW_HANDLED`, collapse `NOTIFICATION_OPEN_STATUSES` to the single pending value, and delete `mark_notified`, `DISMISSIBLE_TYPES` and `NotificationNotDismissible` (the latter two are superseded by the acknowledge guard in T024).
- [X] T008 [P] Update `WF_ASSIGNED`/`WF_FINISHED` to the new constants in `api/app/lib/internal/propose_service.py` (lines ~41-42, and the `PROPOSAL`/`REVIEW` inserts at ~154-157).
- [X] T009 [P] Update the `WF_*` constants and inserts in `api/app/lib/internal/review_service.py`.
- [X] T010 [P] Update the `WF_*` constants and inserts in `api/app/lib/internal/modify_service.py` (lines ~47-49, ~82, ~151, ~160).
- [X] T011 [P] Update the `VERSIONING` insert's status literal in `api/app/lib/internal/version_service.py`.
- [X] T012 In `api/app/lib/internal/actions_service.py`, rewrite `_WORKFLOW_SUMMARIES` (lines ~334-348): delete all six `*_NOTIFIED` entries and rekey `ASSIGNED`→`PENDING`, `FINISHED`→`HANDLED`. A leftover `NOTIFIED` key would silently fall through to the generic summary.

### Labels

- [X] T013 [P] Rename the workflow state labels in `ui/src/i18n/en.json` (`workflow_status` block, lines ~922-924) to `PENDING`: "Pending" / `HANDLED`: "Handled"; delete the `NOTIFIED` key.
- [X] T014 [P] Same in `ui/src/i18n/es.json`: `PENDING`: "Pendiente" / `HANDLED`: "Atendido"; delete `NOTIFIED`.

### Verification

- [X] T015 Run `make rebuild`, then the SQL checks from [quickstart.md](quickstart.md) § "Verifying the data model changed": `list_items` for `WORKFLOW_STATUS` returns exactly two rows, and both `actions` and `collaborations` return zero rows for the old three values.
- [X] T016 Update the existing constant references in `api/tests/test_lib_propose.py`, `test_lib_review.py`, `test_lib_modify.py`, `test_lib_versioning.py` and `test_lib_history.py` so the suite imports and collects again. Behavioural rewrites come with their stories; this task only unblocks collection.

**Checkpoint**: the database and every write path speak two states. User story work can begin.

---

## Phase 3: User Story 1 - Find all my asset work in one place (Priority: P1) 🎯 MVP

**Goal**: One page listing every asset the caller has taken part in — requests directed at
them plus assets they proposed — split into in-motion and closed views, one entry per asset,
each stating whose turn it is.

**Independent Test**: As `adriana.velez`, propose an asset and confirm it appears once in
Pending marked as awaiting *another person*; as `santiago.marin`, confirm the same asset
appears once marked as awaiting *you* with a route to the review; after approval and
acknowledgement, confirm Adriana still sees exactly **one** row for it, now in Handled.

### Tests for User Story 1 ⚠️

> Write these first and confirm they fail.

- [X] T017 [P] [US1] Contract test for `GET /api/actions/requests` — response shape per [contracts/actions.md](contracts/actions.md), `state` filter, and the `skip`/`limit` bound — in `api/tests/test_lib_participations.py`.
- [X] T018 [P] [US1] Test invariant INV-1 (one entry per `(user, asset)`) in `api/tests/test_lib_participations.py`: a user who proposed an asset *and* received its publication notice gets exactly one row, not two.
- [X] T019 [P] [US1] Test the `awaited_party` / `state` derivation across all seven worked cases in [data-model.md](data-model.md) § "Worked cases", in `api/tests/test_lib_participations.py`. Include the ordering case explicitly: a `PUBLISHED` asset with an unacknowledged notice must read `PENDING`/`SELF`, not `HANDLED`.
- [X] T020 [P] [US1] Test the acknowledge guard in `api/tests/test_lib_notifications.py`: `400` on a `REVIEW` or `MODIFICATION` action (and the assignment still pending afterwards), `403` for a non-recipient, `404` for an unknown id, `200` plus a `HANDLED` row for `PUBLICATION`/`REJECTION`.

### Backend for User Story 1

- [X] T021 [US1] Add the `Participation` response model (fields per [data-model.md](data-model.md) § 4) to `api/app/lib/internal/models.py`.
- [X] T022 [US1] Implement `list_participations(session, user_id, state, skip, limit)` in `api/app/lib/internal/actions_service.py`: collapse the caller's `PROPOSAL`/`REVIEW`/`MODIFICATION`/`PUBLICATION`/`REJECTION` rows per `(asset, type)`, group by asset, apply the derivation rules, sort newest-change first, then paginate. Use the three-statement batched pattern from research R8 — no per-row asset or user fetch.
- [X] T023 [US1] Add `GET /api/actions/requests` to `api/app/lib/routes/actions.py`, gated on `current_active_user` only (self-scoping, per the 2026-09-09 precedent), with `state`/`skip`/`limit` query params.
- [X] T024 [US1] Rename `dismiss_notification` to `acknowledge_notification` in `api/app/lib/internal/actions_service.py`, keeping the informational-types-only guard (now raising a plain `ValueError`→400 rather than the deleted `NotificationNotDismissible`), and rename the route to `POST /api/actions/notifications/{id}/acknowledge` in `api/app/lib/routes/actions.py`.
- [X] T025 [US1] Delete `list_review_requests` and `list_pending_modifications` from `api/app/lib/internal/actions_service.py` and their routes `GET /api/actions/reviews` and `GET /api/actions/modifications` from `api/app/lib/routes/actions.py` — both are strict subsets of `participations` (FR-027).

### Frontend for User Story 1

- [X] T026 [P] [US1] Add the `Participation` interface to `ui/src/types/api.ts` and remove `unread` from the notification item type.
- [X] T027 [US1] In `ui/src/lib/notifications.ts`, add `getParticipations(state, skip, limit)` and `acknowledgeNotification(id)`; delete `getReviewRequests`, `getPendingModifications` and `dismissNotification`; update the module docstring, which currently documents the removed endpoints.
- [X] T028 [US1] Create `ui/src/components/svelte/MyAssetRequests.svelte`: two switchable views, columns for asset / kind / state / whose turn / last change, an inline acknowledge control on unacknowledged outcomes (FR-010b), a route to the action screen when `awaited_party` is `SELF`, per-view empty states, and paged loading of the closed view (FR-012).
- [X] T029 [US1] Convert `ui/src/pages/lib/my_asset_requests.astro` from its server-rendered table to a shell that manually `mount()`s `MyAssetRequests.svelte` — an SSR snapshot is stale by construction (research R13). Keep the existing `BaseLayout` and `Breadcrumb`.
- [X] T030 [P] [US1] Delete `ui/src/pages/lib/modifications.astro` and its `modifications.*` i18n block from `ui/src/i18n/en.json` and `es.json`. It is already unreferenced from every menu and link.
- [X] T031 [P] [US1] Add the new i18n keys to `ui/src/i18n/en.json` and `es.json` under `my_asset_requests`: tab labels (Pending/Handled — Pendientes/Atendidas), awaited-party values (You / Someone else — Tú / Otra persona), the acknowledge action, the kind-of-involvement labels, and both empty states. Replace `status_seen` with `status_handled`.
- [X] T032 [US1] Walk Scenario 1 in [quickstart.md](quickstart.md) as `adriana.velez` and `santiago.marin` — not as `admin`, whose superuser bypass hides this domain's permission defects. **Verified end-to-end against the live API** as those two accounts (propose → one row awaiting OTHER for the proposer / SELF for the reviewer → approve → still ONE row, pending on the proposer → acknowledge → moves to Handled). Test asset cleaned up. The browser click-through of the tabs and the acknowledge button is still outstanding.

**Checkpoint**: the page is complete and durable. Every request kind now has a home, which is
the precondition for narrowing the bell.

---

## Phase 4: User Story 2 - Be alerted without a second list to scan (Priority: P1)

**Goal**: The header indicator reflects only what awaits the caller, caps what it shows, and
hands off to the full page. No control clears an unresolved item.

**⚠️ Depends on US1** — see Dependencies for why this is a correctness constraint.

**Independent Test**: As `adriana.velez` immediately after proposing, the bell is empty (the
asset awaits the reviewer, not her) while the page shows it. As `santiago.marin`, the review
appears in the bell with no dismiss control, and the panel links to the page.

### Tests for User Story 2 ⚠️

- [X] T033 [P] [US2] Test that `GET /api/actions/notifications` returns only entries awaiting the caller — a user who proposed an asset awaiting someone else's review gets an empty feed — in `api/tests/test_lib_notifications.py`.
- [X] T034 [P] [US2] Test the `{ items, total }` response shape, that `limit` bounds `items` while `total` counts everything pending, and that `unread` is absent, in `api/tests/test_lib_notifications.py`.
- [X] T035 [P] [US2] Test that `POST /api/actions/notifications/{id}/notified`, `GET /api/actions/reviews` and `GET /api/actions/modifications` all return `404` in `api/tests/test_lib_notifications.py`.
- [X] T036 [P] [US2] Test invariant INV-2 in `api/tests/test_lib_notifications.py`: every id in the feed also appears in `participations` with `awaited_party == "SELF"`.

### Backend for User Story 2

- [X] T037 [US2] Narrow `list_notifications` in `api/app/lib/internal/actions_service.py` to threads that are `PENDING` and awaiting the caller, returning items plus a total; drop the `unread` and `workflow_status` fields from the projection. Derive it from the same pass as `list_participations` rather than duplicating the grouping logic.
- [X] T038 [US2] Update `GET /api/actions/notifications` in `api/app/lib/routes/actions.py` for the `{ items, total }` model and the `limit` param, and delete the `POST /api/actions/notifications/{id}/notified` route.

### Frontend for User Story 2

- [X] T039 [US2] Delete `markNotified` from `ui/src/lib/notifications.ts` and update `getNotifications` for the `{ items, total }` shape.
- [X] T040 [P] [US2] Remove the `markNotified` call and its import from `ui/src/components/svelte/ReviewAction.svelte` (line ~142).
- [X] T041 [P] [US2] Remove the `markNotified` call and its import from `ui/src/components/svelte/ModifyAction.svelte` (line ~200).
- [X] T042 [US2] In `ui/src/components/svelte/ShowAction.svelte`, remove the `markNotified` call (line ~113) and relabel the Dismiss control to Acknowledge, pointing it at `acknowledgeNotification`.
- [X] T043 [US2] Rework `ui/src/components/svelte/NotificationBell.svelte`: render only the pending feed, show at most five entries with an indication when `total` exceeds them, add the "view all" route to `/lib/my_asset_requests`, and delete the dismiss button, the `unread` bold styling and the `onDismiss` handler.
- [X] T044 [US2] Walk Scenario 2 in [quickstart.md](quickstart.md), including the invariant check that the bell never contains anything the page does not. **Verified against the live API**: after proposing, the proposer's feed is empty while their page shows the asset; the reviewer's feed has exactly the one entry. Panel capping and the "view all" link are code-verified only — not click-tested.

**Checkpoint**: the duplication that motivated the feature is gone — the indicator is a strict
subset of the page.

---

## Phase 5: User Story 3 - Never act on a stale list (Priority: P1)

**Goal**: The indicator and the page reflect current state without a manual reload, converge
on out-of-session changes within 90 s while visible, and go quiet when hidden.

**Independent Test**: Resolve a request in one session and confirm that session updates with
no reload; leave a second user's tab visible and untouched and confirm it converges within
90 s; background the tab and confirm no further requests.

### Tests for User Story 3 ⚠️

- [ ] T045 [P] [US3] Unit-test the store's failure behaviour (FR-023) in `ui/src/lib/notificationsStore.ts`'s own test or via a documented manual check: a rejected refresh leaves the previous list intact and never publishes an empty list. This is the behaviour today's bell gets wrong with its `catch { items = [] }`. — **BLOCKED, cannot be automated here.** This repo has no UI test runner (no vitest, no Playwright). The behaviour is implemented (`refresh()` keeps the previous state on a rejected fetch and never publishes an empty list) but only a manual check per Scenario 3.5 can confirm it.

### Implementation for User Story 3

- [X] T046 [US3] Create `ui/src/lib/notificationsStore.ts` as a framework-free module (research R12): holds the feed and the participation list, exposes `subscribe()`, `refresh()`, `start()` and `stop()`, swallows refresh failures without clearing state, and de-duplicates concurrent refreshes.
- [X] T047 [US3] Wire the refresh triggers inside the store: initial start, `visibilitychange`→visible, `pageshow` (including `event.persisted`, which is the bfcache case), a 60 s timer that runs only while the document is visible, and a `notifications:changed` window event.
- [X] T048 [US3] Subscribe `ui/src/components/svelte/NotificationBell.svelte` to the store in place of its one-shot `onMount` `load()`, starting the store on mount and stopping it on destroy.
- [X] T049 [US3] Subscribe `ui/src/components/svelte/MyAssetRequests.svelte` to the store so the page and the indicator can never disagree, preserving the selected view and any in-progress input across a refresh (FR-024).
- [X] T050 [US3] Dispatch `notifications:changed` after every mutation that changes the caller's pending set — acknowledge in `MyAssetRequests.svelte` and `ShowAction.svelte`, decide in `ReviewAction.svelte`, resubmit in `ModifyAction.svelte`.
- [X] T051 [P] [US3] Replace `goHome()`'s `window.history.back()` with an explicit navigation to `/lib/my_asset_requests` in `ui/src/components/svelte/ReviewAction.svelte` (line ~64) — this both avoids the bfcache path and returns the user to their own list with the item visibly resolved.
- [X] T052 [P] [US3] Same replacement in `ui/src/components/svelte/ModifyAction.svelte` (line ~72).
- [ ] T053 [US3] Walk Scenario 3 in [quickstart.md](quickstart.md), all six checks — same-session, back-navigation, cross-user, hidden-tab silence, API-down resilience, and non-disruption of typed input. — **BLOCKED: needs a real browser.** bfcache restore, hidden-tab silence and the two-browser cross-user convergence cannot be exercised from here.

**Checkpoint**: the reported staleness defect is closed on all three of its causes.

---

## Phase 6: User Story 4 - One vocabulary everywhere (Priority: P2)

**Goal**: Only two state labels appear anywhere in the product, in both languages, and no
surface records or shows that someone merely looked at an item.

**Independent Test**: Sweep the activity timeline, the workflow-stage badge, the requests page
and Admin → Lists; confirm only Pending/Handled — Pendiente/Atendido appear, in both
languages.

- [X] T054 [US4] Delete the six orphaned `*_NOTIFIED` keys from the `history.workflow` blocks in `ui/src/i18n/en.json` and `es.json` (lines ~897-910) and rekey the `*_ASSIGNED`/`*_FINISHED` entries to the new state names, matching the `_WORKFLOW_SUMMARIES` rewrite from T012.
- [X] T055 [P] [US4] Verify the workflow-stage badge fed by `get_workflow_stage` renders the new labels, including on the log-only types (`PROPOSAL`, `VERSIONING`, `DEPRECATION`), which now read as Handled by design (research R5).
- [X] T056 [P] [US4] Sweep `ui/src/i18n/en.json` and `es.json` for any remaining `ASSIGNED`/`NOTIFIED`/`FINISHED` string and confirm EN/ES parity on every key this feature added or changed.
- [X] T057 [US4] Update `docs/user-stories/states-and-types.md` — the canonical state reference — including the lifecycle line (~16) and both state tables (~22, ~98).
- [X] T058 [P] [US4] Update the remaining state references in `docs/user-stories/lib-status.md` (13), `docs/user-stories/04-lib.md` (17), `docs/user-stories/05-inits.md` (19) and `docs/user-stories/inits-status.md` (14).
- [ ] T059 [US4] Walk Scenario 4 in [quickstart.md](quickstart.md) in both languages. — **BLOCKED: needs a real browser** to confirm the rendered labels in both languages.

**Checkpoint**: all four stories complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T060 Add the single rollup entry to `memory/CHANGELOG.md` per `AGENTS.md` (format `## YYYY-MM-DD HH:MM — Title`, newest at top; run `date '+%Y-%m-%d %H:%M'` for the timestamp). One entry for the whole PR — update it on later commits to this branch rather than appending another.
- [X] T061 Update `memory/MEMORY.md`: add the two-state decision to the decisions log, revise the **P1 "Known blockers" row** (it names `/api/actions/notifications`, `/reviews`, `/modifications` and the `LIB/ACTIONS` history — `/reviews` and `/modifications` no longer exist), and update the "Review Requests / My Modifications" and notification rows in Feature status.
- [X] T062 Update the `api/CLAUDE.md` and `ui/CLAUDE.md` sections that describe the notification endpoints and the LIB page inventory, so the per-surface guides do not keep documenting removed routes and the deleted `modifications` page.
- [X] T063 Run the full backend suite from `api/` with `uv run pytest` and compare against the T002 baseline — every new failure must be accounted for.
- [X] T064 [P] Run `cd ui && bun run build` and confirm no new diagnostics versus the pre-existing baseline.
- [X] T065 [P] Run `make test` and confirm API health, DB readiness and the admin user all pass.
- [X] T066 Walk Scenario 5 in [quickstart.md](quickstart.md) — the retired surfaces: `/lib/modifications` gone, the three removed endpoints `404`, and acknowledge on a `REVIEW` returning `400` with the review still pending afterwards. **Verified**: `/lib/modifications` deleted; acknowledge on a REVIEW returns 400 with the review still pending. Correction to the task as written — the three removed endpoints return **422**, not 404: the generic `/api/actions/{id}` route catches the path and cannot parse "reviews" as an integer. They are gone from the OpenAPI surface either way (asserted in `test_retired_routes_are_gone`).
- [ ] T067 Re-read [plan.md](plan.md) § Complexity Tracking and confirm the PR description states the two Constitution deviations (Principle II removals/rename; in-place seed edits without a migration) with their justifications, as the governance rules require. — **Outstanding until the PR is opened.** Nothing is committed yet; the two deviations are written up in `plan.md` § Complexity Tracking, ready to paste.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup. **Blocks every user story** — all four read the
  state constants it defines.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on Foundational **and on US1** (see below).
- **US3 (Phase 5)**: depends on Foundational. Independent of US1/US2 in principle, but T049
  targets the component US1 creates, so in practice schedule it after US1.
- **US4 (Phase 6)**: depends on Foundational.
- **Polish (Phase 7)**: depends on all desired stories.

### The one non-obvious dependency

**US2 must not ship before US1.** `/lib/modifications` is already unreferenced from every menu
and link, so the notification bell is today the **only** route to a `MODIFICATION` assignment.
Narrowing the bell (T043) before the unified page covers that type would strand a proposer who
opened their modify screen and navigated away. Because the state is persisted in `actions`,
redeploying would not recover it — the work would have to be reassigned by hand. This is a
correctness constraint, not a sequencing preference.

### Within each story

- Tests before implementation, and confirmed failing first.
- Backend models → services → routes → frontend types → services → components → pages.
- The manual quickstart walk closes each story.

### Parallel Opportunities

- T008–T011 (four service-constant files) are fully parallel.
- T013/T014 (the two i18n files) are parallel with each other and with the service work.
- T017–T020 (US1 tests) are parallel; T033–T036 (US2 tests) are parallel.
- T040/T041 (removing `markNotified` from two islands) are parallel; T051/T052 likewise.
- T055/T056/T058 (US4 sweeps) are parallel.
- Once Foundational completes, US4's documentation tasks (T057, T058) can proceed alongside
  US1 — they touch no shared file.

**Not parallel despite appearances**: T005 and T006 both edit seed files but T005 is the
larger, riskier rewrite; T007 and T012 both edit `actions_service.py`; T037 depends on T022
because it reuses the same grouping pass rather than duplicating it.

---

## Parallel Example: Foundational service constants

```bash
# After T007 defines the new constants, these four are independent files:
Task: "Update WF_* constants in api/app/lib/internal/propose_service.py"
Task: "Update WF_* constants in api/app/lib/internal/review_service.py"
Task: "Update WF_* constants in api/app/lib/internal/modify_service.py"
Task: "Update the VERSIONING status literal in api/app/lib/internal/version_service.py"
```

## Parallel Example: User Story 1 tests

```bash
Task: "Contract test for GET /api/actions/requests in api/tests/test_lib_participations.py"
Task: "Test INV-1 one entry per (user, asset) in api/tests/test_lib_participations.py"
Task: "Test awaited_party/state derivation, 7 cases, in api/tests/test_lib_participations.py"
Task: "Test the acknowledge guard in api/tests/test_lib_notifications.py"
```

---

## Implementation Strategy

### MVP (Setup + Foundational + US1)

1. Phase 1 — test loop and baseline.
2. Phase 2 — two-state model, `make rebuild`, SQL verification.
3. Phase 3 — the complete requests page.
4. **STOP and VALIDATE**: Scenario 1 from [quickstart.md](quickstart.md).

At this point the duplication is not yet gone — the bell still mirrors the page — but nothing
is lost and the durable record exists. This is a safe stopping point; the next one is not
reached until US2 completes.

### Incremental Delivery

1. MVP as above.
2. **US2** → the bell becomes a strict subset. This is the increment that closes the original
   complaint. Do not start it before US1 is validated.
3. **US3** → staleness closed on all three causes.
4. **US4** → vocabulary sweep across history, badges and docs.
5. **Polish** → memory files, docs, full verification.

### Parallel Team Strategy

After Foundational: one developer takes US1 then US2 (they are sequential by the constraint
above); a second can take US3's store and refresh wiring against the existing bell, rebasing
onto US1's component when it lands; a third can take US4's documentation and i18n sweep
immediately, since it shares no file with the others.

---

## Notes

- Every task that verifies behaviour against a running stack depends on `make rebuild` having
  run after T004–T006. Verifying against a stale volume fails as "everything is empty", which
  reads like a code bug rather than a missing rebuild.
- Run every manual scenario as `santiago.marin` (REVIEWER) and `adriana.velez` (COLLABORATOR),
  never as `admin` — the superuser bypass is exactly what hid this domain's permission defects
  before.
- Commit per task or per logical group; keep the single `CHANGELOG.md` entry updated rather
  than appending a second one.
