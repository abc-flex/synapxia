# Tasks: Dashboard Catalog (with Execute and Favorite)

**Input**: Design documents from `/specs/007-dashboard-catalog/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/catalog-api.md](contracts/catalog-api.md),
[quickstart.md](quickstart.md)

**Tests**: REQUIRED. Constitution Principle III makes automated tests mandatory for contract, permission and auth changes; research R12 lists what to cover. Each story writes its backend tests first and confirms they fail before implementing. UI is verified manually through the quickstart.

**Organization**: tasks are grouped by the spec's user stories:

- US1: browse the dashboards shared with me (P1)
- US2: run a dashboard with parameter values (P1)
- US3: every run is recorded (P1)
- US4: favorite a dashboard from the catalog (P2)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4; Setup, Foundational and Polish tasks carry no story label
- Paths are repository-relative: `api/`, `ui/`, `db/`

## Conventions every task follows

- **Backend**: copy the style of `api/app/insights/routes/dashboards.py` and `parameters.py`.
  - Routes wrap guard exceptions in a local `_ensure_*` → `HTTPException(403)`.
  - `ValueError` maps to 400.
  - Module RBAC is `require_privilege("ANA", "CATALOG", can_edit=False)` unless a task says otherwise.
  - Lists take `skip: int = Query(0, ge=0)` and `limit: int = Query(100, ge=1, le=500)`.
  - Business logic lives in `api/app/insights/internal/*_service.py`, never in routes.
  - The actor is always the `current` user from the dependency, never from the body.
- **Tests**: use `api/tests/ana_helpers.py` (`seed_privileges`, `mk_dashboard`, `mk_grant`, `mk_param`, `seed_ana_lists`) and run with `docker compose exec -T api uv run pytest -q <path>`.
- **UI**: copy `ui/src/pages/lib/explore.astro` (SSR gallery) and `ui/src/components/lib/ExploreCard.astro`.
  - Mount Svelte with `mount()` from a bundled `<script>` that imports through `@/`.
  - List values go through `ui/src/lib/listLang.ts`.
  - Form styling comes from `ui/src/lib/formClasses.ts`.
  - Every string goes in both `ui/src/i18n/en.json` and `es.json` under `dashboard_catalog.*`.

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: prepare the files every story touches.

- [X] T001 Create the empty modules with module docstrings referencing `specs/007-dashboard-catalog`: `api/app/insights/internal/catalog_service.py`, `api/app/insights/internal/execution_service.py`, `api/app/insights/routes/catalog.py` (`APIRouter(prefix="/api/dashboards", tags=["dashboard_catalog"])`) and `api/app/insights/routes/executions.py` (`APIRouter(tags=["dashboard_executions"])`, full paths per route).
- [X] T002 Register both routers in `api/app/main.py` under the "Analytics module" block. `catalog` and `executions` MUST be included **before** `dashboards_router`, so `/api/dashboards/catalog` is not captured by `GET /api/dashboards/{dashboard_id}`. Add a comment saying why.
- [X] T003 [P] Add the `dashboard_catalog.*` i18n skeleton (title, subtitle, search placeholder, empty state, execute, detail headings, parameters window, viewer, errors) to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`. Reuse the existing `dashboard_table.perm_filter_*` keys for the privilege options and `gallery.favorites_only` for the favorites pill.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the model, validation and permission helpers shared by US1–US3.

- [X] T004 Map the `executions` table in `api/app/insights/internal/models.py` as `Execution(SQLModel, table=True)`: `id`, `dashboard` (BigInteger FK `dashboards.id`), `user_id` (BigInteger FK `users.id`), `executed_at` (default utcnow), `payload` (`Column("payload", JSON)`), `status` (nullable), `error_message` (nullable), `duration_ms` (nullable int). Add the projections from data-model.md: `CatalogDashboard`, `RunFormOption`, `RunFormParameter`, `RunForm`, `ExecutionStart` (`values: Dict[str, Optional[str]] = {}`), `ExecutionStarted`, `ExecutionFinish` (`status: str`, `error_message: Optional[str]`), `ExecutionCancelled` (`values`, `duration_ms: Optional[int]`), `ExecutionRead`, `LastValues`. Add constants `EXEC_SUCCESS/FAILED/CANCELLED/TIMEOUT/UNAUTHORIZED`, `MODE_VIEWER/TAB` and `SOURCE_DEFAULT = "DEFAULT"`.
- [X] T005 [P] In `api/app/insights/internal/parameter_validation.py`, add `validate_run_value(data_type, value, allowed) -> None` (NUMBER finite decimal, BOOLEAN `true|false`, DATE `YYYY-MM-DD` real date, list membership when `allowed` is not None, max 1 000 chars; raises ValueError with the parameter-agnostic message) and `list_values(session, code) -> Optional[Set[str]]` (None when the list is missing, inactive or not LIST_OF_VALUES; else its values). Make `validate_default` delegate to `validate_run_value` with identical messages. `api/tests/test_ana_parameters.py` must stay green unchanged.
- [X] T006 [P] In `api/app/insights/internal/permissions_service.py`, add `dashboard_matching_grants(session, user, dashboard_id) -> List[DashboardPermission]` (thin wrapper over `rp.matching_grants(session, user, DashboardPermission, _FK, [dashboard_id])`).
- [X] T007 In `api/app/insights/internal/catalog_service.py`, implement `is_catalog_visible(dashboard) -> bool` (`is_active` and `normalize(status) == "PUBLISHED"`). Also implement `resolve_effective_parameters(session, user, dashboard_id) -> List[EffectiveParam]`, where each item holds the parameter row, `effective_source` (GRANT/LIST/INPUT), `bound_value`, `bound_label` and `allowed: Optional[Set[str]]`. Use the R3 rule: GRANT only if `context_binding` ∈ ids of `dashboard_matching_grants` and that grant is not revoked; otherwise LIST if `list` is set, else INPUT. Read only active parameters, ordered by name, with one query for parameters and one for the grants.
- [X] T008 [P] Add the TS types to `ui/src/types/api.ts`: `CatalogDashboard`, `RunFormOption`, `RunFormParameter`, `RunForm`, `ExecutionStarted`, `ExecutionRead`, `LastValues`, `ExecutionStatus` and `EffectiveSource`. Create `ui/src/lib/dashboardExecutions.ts` with `getCatalog(skip, limit)`, `getRunForm(id)`, `startExecution(id, values)`, `finishExecution(execId, status, errorMessage?)`, `recordCancelled(id, values, durationMs)` and `getLastValues(id)` over `lib/api.ts`. Start, finish and cancel must surface `apiErrorDetail()` messages.
- [X] T009 Foundational tests in `api/tests/test_ana_catalog_foundation.py`:
  - `validate_run_value` accepts and rejects each type, the list check and the 1 000-character cap.
  - `validate_default` keeps its messages.
  - `resolve_effective_parameters` covers: bound grant matched → GRANT with `bound_value = target_code`; caller reaching via PUBLIC only → LIST fallback when a list is set, INPUT otherwise; revoked bound grant → fallback; superuser with no matching grant → fallback; inactive parameters excluded.

**Checkpoint**: model and helpers exist; the stories can start.

---

## Phase 3: User Story 1 — Browse the dashboards shared with me (Priority: P1) 🎯 MVP

**Goal**: `/ana/catalog` lists the Published dashboards the user can see, in a card grid, with the privileges filter, search, favorites toggle and a read-only detail.

**Independent Test**: as a collaborator with grants through PUBLIC, USER and TEAM plus a Draft dashboard with a PUBLIC grant, each privilege option shows exactly the matching Published dashboards, the Draft never appears, and search and favorites narrow the grid (quickstart A).

### Tests for User Story 1 (write first, confirm they fail)

- [X] T010 [P] [US1] `api/tests/test_ana_catalog.py` covering `GET /api/dashboards/catalog`:
  - 403 without `ANA/CATALOG`; 200 with read-only `ANA/CATALOG` (`can_edit=False`).
  - Only active PUBLISHED rows; DRAFT, ARCHIVED, RETIRED and inactive rows are hidden even with a PUBLIC grant.
  - Ungranted rows are hidden; a superuser sees every Published row.
  - Visibility is filtered before `skip`/`limit` (a full page even when hidden rows come first by name).
  - `permission_scopes` (e.g. `["PUBLIC","TEAM"]`), `is_favorite`, `parameter_count` (active parameters only).
  - `source_url` is absent from the response.
  - Ordering is by name.

### Implementation for User Story 1

- [X] T011 [US1] In `api/app/insights/internal/catalog_service.py`, implement `list_catalog(session, user, skip, limit) -> List[CatalogDashboard]`:
  - The base query is active and PUBLISHED.
  - Non-superusers are restricted to `permissions_service.accessible_dashboards`, returning `[]` early when empty.
  - Order by name, id, then apply offset/limit.
  - Batch scopes via `dashboards_user_scopes`, favorites via one query over `FavoriteDashboard` (copy `_favorite_ids` from `routes/dashboards.py` into the service and have the route reuse it), and active parameter counts via one grouped `COUNT` over `Parameter`.
- [X] T012 [US1] In `api/app/insights/routes/catalog.py`, add `GET /catalog` → `List[CatalogDashboard]` calling `list_catalog`, with a docstring per contract.
- [X] T013 [P] [US1] Create `ui/src/components/ana/CatalogCard.astro` wrapping `ui/src/components/lib/gallery/GalleryCard.astro`, modelled on `ExploreCard.astro`.
  - Icon chosen by source: a local map `SOURCE_TYPE → icon` (e.g. `POWER_BI`/`TABLEAU`/`QLIK_SENSE` → `chart-bar`, `LOOKER_STUDIO`/`METABASE`/`SUPERSET` → `chart-pie`, `INTERNAL_PAGE` → `document-text`, `CUSTOM_IFRAME` → `code`), each verified to exist in `ui/src/images/icons/`, falling back to `chart-pie`.
  - Type and source chips carry `data-list-labels` via `listLabelsAttr`.
  - `#tag` chips, relative time, the star (`favorite`) and an **Execute** button (`data-action="execute" data-dashboard-id={id}`) in the `actions` slot.
  - `detailModalId="catalog-detail-modal"`; `searchText` and `permissions` come in as props.
- [X] T014 [P] [US1] Create `ui/src/components/ana/CatalogDetailModal.astro`, a read-only `<dialog id="catalog-detail-modal">` opened by the gallery's `data-modal-open` trigger with `data-dashboard-id`.
  - On open, read the clicked card's data (name, description, type/source labels, tags, detail, favorite) from a JSON blob the page embeds (no extra request) and call `getRunForm(id)` for the parameters table (label, data type, required).
  - Render `detail` as markdown exactly the way `ui/src/components/lib/ExploreDetailModal.astro` / `lib/catalogDetail.ts` render asset detail.
  - Footer: the star (dispatches `gallery:card-update` after `setDashboardFavorite`) and an Execute button with the same `data-action="execute"`.
- [X] T015 [US1] Create `ui/src/pages/ana/catalog.astro` mirroring `ui/src/pages/lib/explore.astro`:
  - `BaseLayout`; `getOption("ANA","CATALOG")` for name and icon (fallback `chart-pie`); Breadcrumb with `moduleNameKey="modules.ANA"`.
  - SSR `getCatalog(0, 500)` and `getListItemsbyList` for `DASHBOARD_TYPE` and `SOURCE_TYPE`.
  - `data-search` = name + description + tags + **en and es** labels of type and source (FR-004, R9); `permissions = permission_scopes.join(",")`.
  - `<CardGallery layout="grid" statuses={[]} showFavorites privileges={[PUBLIC, USER, ROLE, TEAM, UNIT, PROJECT]}>` with `dashboard_table.perm_filter_*` keys in that order, and the empty state `dashboard_catalog.empty`.
  - One `CatalogCard` per row, then `CatalogDetailModal` and the JSON blob.
  - Bundled script: `initCardGallery({ galleryId, idAttr: "dashboardId", services: { toggleFavorite: (id,on) => setDashboardFavorite(Number(id), on) } })`.
- [X] T016 [US1] Confirm in `ui/src/lib/catalogGallery.ts` that card-body clicks ignore clicks on `button`/`a` descendants, so Execute and the star do not open the detail. If they don't, add an exclusion for `[data-action]` targets that leaves existing galleries unchanged.

**Checkpoint**: US1 passes its tests and quickstart A.

---

## Phase 4: User Story 2 — Run a dashboard with parameter values (Priority: P1)

**Goal**: Execute opens a parameters window built per viewer, validates, starts the run on the server and opens the dashboard: Internal Page in a viewer, external in a new tab. "Use my last values" fills from the last successful run.

**Independent Test**: on dashboard 2 as adriana (role TL), the window shows Role = TL read-only and defaults prefilled; an empty required field blocks the run; a valid run opens the Power BI URL with the values and writes one execution row (quickstart C, D.1–D.2, E.2).

### Tests for User Story 2 (write first, confirm they fail)

- [X] T017 [P] [US2] `api/tests/test_ana_run_form.py` covering `GET /api/dashboards/{id}/run-form`:
  - 404 missing or inactive; 403 with no grant; 403 when not PUBLISHED; 403 without `ANA/CATALOG`.
  - `mode` VIEWER for INTERNAL_PAGE, TAB otherwise.
  - GRANT row carries `bound_value` and `bound_label`; fallback rows carry LIST/INPUT.
  - LIST `options` include every language (`lang` field) and `list_unavailable` is true for an empty or inactive list.
  - `has_last_values` is false until a SUCCESS row exists, and ignores other users' and other statuses' rows.
- [X] T018 [P] [US2] `api/tests/test_ana_executions.py`, start path (`POST /api/dashboards/{id}/executions`):
  - 201 with an in-progress row (status NULL) and `user_id` = the session user (a `user_id` in the body is ignored).
  - `launch_url` keeps the existing query string, urlencodes values and appends `embed=1` only for INTERNAL_PAGE.
  - A GRANT value is forced to `target_code` and a submitted one is ignored.
  - Missing values take their defaults.
  - Payload `values` / `sources` with DEFAULT vs INPUT/LIST/GRANT, and `mode`.
  - Unknown names are dropped.
- [X] T019 [P] [US2] `api/tests/test_ana_last_values.py` covering `GET /api/dashboards/{id}/executions/last-values`:
  - Picks the caller's newest SUCCESS only (ignores FAILED/CANCELLED/NULL and other users).
  - Excludes GRANT-effective names, removed or inactive parameters, and values that no longer validate (e.g. a list value deleted).
  - Tolerates a legacy flat payload.
  - Returns `{values:{}, executed_at:null}` with no history.
  - Same 403/404 rules as `run-form`.

### Implementation for User Story 2

- [X] T020 [US2] In `api/app/insights/internal/catalog_service.py`, implement `build_run_form(session, user, dashboard) -> RunForm`:
  - Use `resolve_effective_parameters`.
  - For LIST, load all `ListItem` rows of every LIST code in one query (value, lang, label, sort_order), with `list_unavailable` when `list_values` is None or empty.
  - `has_last_values` comes from an EXISTS over `Execution` for (user, dashboard, SUCCESS).
- [X] T021 [US2] In `api/app/insights/internal/execution_service.py`, implement:
  - `ExecutionUnauthorized` and `ExecutionInvalid(ValueError)`.
  - `check_runnable(session, user, dashboard)`, which raises Unauthorized when the dashboard is inactive, not PUBLISHED or has no live grant (superuser passes).
  - `resolve_values(session, user, dashboard_id, submitted) -> (values, sources)`, which applies GRANT, then defaults, then `validate_run_value`, the required check and the `list_unavailable` + required → "cannot be run" check. Sources use DEFAULT when the value equals `default_value`.
  - `build_launch_url(dashboard, values) -> (url, mode)` with `urllib.parse` (merge `parse_qsl` of the existing query, `urlencode`, `embed=1` for INTERNAL_PAGE).
  - `start_execution(session, user, dashboard_id, submitted) -> ExecutionStarted`, which inserts exactly one row in every outcome. On Unauthorized: status UNAUTHORIZED, `error_message`, a sanitised payload (`{values}` restricted to active names, truncated), commit, then re-raise. On invalid values: status FAILED likewise. On success: status None and payload `{values, sources, mode}`.
  - Log each outcome with `logger.info` (dashboard, user, status).
- [X] T022 [US2] In `api/app/insights/internal/catalog_service.py`, implement `last_values(session, user, dashboard_id) -> LastValues`: the newest SUCCESS row of (user, dashboard) ordered by `executed_at desc, id desc` limit 1; `payload.values`, or the payload itself when it is a flat legacy dict; then filter by `resolve_effective_parameters` (drop GRANT and unknown names) and `validate_run_value` (drop invalid values).
- [X] T023 [US2] Routes:
  - In `api/app/insights/routes/catalog.py`: `GET /{dashboard_id}/run-form` (404 missing or inactive, `_ensure_runnable` → 403 via `check_runnable` without recording).
  - In `api/app/insights/routes/executions.py`: `POST /api/dashboards/{dashboard_id}/executions` (201; `ExecutionUnauthorized` → 403, `ExecutionInvalid` → 400, both after the row is committed) and `GET /api/dashboards/{dashboard_id}/executions/last-values`.
- [X] T024 [US2] In `ui/src/layouts/BaseLayout.astro`, add the embed mode. When `Astro.url.searchParams.get("embed") === "1"`, render only the main slot (no `SideBar`, no `Header`), keeping `<head>`, theme and i18n scripts. Default rendering is unchanged.
- [X] T025 [US2] Create `ui/src/components/svelte/DashboardRun.svelte`. Its parameters window is a `<dialog>`; mount it from `catalog.astro`'s bundled script with `mount(DashboardRun, { target })`.
  - A delegated document listener on `[data-action="execute"]` reads `data-dashboard-id` and the name.
  - It calls `getRunForm` and skips the window when no parameter needs input (all GRANT or none), running directly (US2-9).
  - Fields by effective source:
    - LIST → `<select>` from `toListOptions(options, currentLang())`, re-read under `langTick`, with a "— choose —" placeholder when not required or no default.
    - INPUT: STRING text, NUMBER `type=number step=any`, DATE `type=date`, BOOLEAN select (not set / yes / no; not set only when optional).
    - GRANT → read-only text showing `bound_value`.
  - Prefill defaults and mark required fields.
  - The "Use my last values" button shows only when `has_last_values`; it calls `getLastValues` and fills only the returned names.
  - Client validation mirrors R7 with inline errors via `setFieldInvalid` from `ui/src/lib/formClasses.ts`.
  - The Execute button is disabled while a start is in flight (FR-014).
- [X] T026 [US2] Add the launch behaviour to `DashboardRun.svelte`, without timeout or cancel handling yet (those come in US3).
  - TAB:
    1. In the click handler, synchronously `const tab = window.open("", "_blank")`.
    2. `await startExecution`.
    3. On success with a tab: `tab.opener = null; tab.location.href = launch_url`, then `finishExecution(id, "SUCCESS")`.
    4. On a start error: close the tab and show the server message.
  - VIEWER: open a second `<dialog>` (the viewer) with the dashboard name, the values used (label: value), an "open full page" link (`launch_url` without `embed=1`) and an `<iframe src=launch_url>`; on iframe `load` call `finishExecution(id, "SUCCESS")`.
  - A 400 start response shows the error inline in the window.

**Checkpoint**: US2 passes its tests and quickstart C, D.1–D.2, E.2.

---

## Phase 5: User Story 3 — Every run is recorded (Priority: P1)

**Goal**: every attempt ends in exactly one record with the right status: finish-once with owner check, cancelled windows, 30 s timeout, viewer closed early, popup blocked, unauthorized.

**Independent Test**: a successful run, a server-rejected value, a run on a dashboard archived mid-window, a closed window, a closed viewer and a timed-out viewer each leave exactly one row with the expected status, values and duration (quickstart D.3–D.4, E.1, E.3, F).

### Tests for User Story 3 (write first, confirm they fail)

- [X] T027 [P] [US3] Extend `api/tests/test_ana_executions.py`:
  - **Start refusals**: no grant → 403 + one UNAUTHORIZED row; ARCHIVED → 403 + UNAUTHORIZED; each invalid value kind and a missing required value → 400 + one FAILED row with the message; required LIST with an empty list → 400 FAILED; 403 without `ANA/CATALOG` writes **no** row.
  - **Finish** (`POST /api/executions/{id}/finish`): owner only → 403 for others; a second finish → 409; an invalid status → 400; `duration_ms` is computed by the server (≥ 0); `error_message` truncated to 1 000 characters.
  - **Cancelled** (`POST …/executions/cancelled`): a CANCELLED row with sanitised values and `duration_ms` clamped (negative → 0, huge → 86 400 000); no grant → 403 + UNAUTHORIZED row.
  - No update or delete route exists for executions.

### Implementation for User Story 3

- [X] T028 [US3] In `api/app/insights/internal/execution_service.py`, implement `finish_execution(session, user, execution_id, status, error_message) -> ExecutionRead` and `record_cancelled(session, user, dashboard_id, values, duration_ms) -> ExecutionRead`.
  - `finish_execution`: 404 via `LookupError`, 403 via `ExecutionForbidden` when `user_id != user.id`, 409 via `ExecutionConflict` when the status is already set, ValueError for a status outside SUCCESS/FAILED/TIMEOUT/CANCELLED. It sets `duration_ms` from `utcnow() - as_naive_utc(executed_at)` and selects with `with_for_update()` so concurrent finishes can't both win.
  - `record_cancelled`: `check_runnable` (→ UNAUTHORIZED row + raise), else a CANCELLED row with `{values}` sanitised and the duration clamped.
- [X] T029 [US3] In `api/app/insights/routes/executions.py`, add `POST /api/executions/{execution_id}/finish` (mapping 404/403/409/400) and `POST /api/dashboards/{dashboard_id}/executions/cancelled` (201; 403 after the row is committed). Gate both on `require_privilege("ANA","CATALOG", can_edit=False)`.
- [X] T030 [US3] Complete outcome reporting in `ui/src/components/svelte/DashboardRun.svelte`:
  - Closing the parameters window (Cancel button, Esc or backdrop) without Execute → `recordCancelled(id, currentValues, elapsedMs)`, best effort and silent on error.
  - VIEWER:
    - A 30 s timer started at iframe creation → on expiry, `finishExecution(id,"TIMEOUT","Did not load within 30 s")` and a "did not respond" message that keeps the full-page link.
    - Closing the viewer before `load` → `finishExecution(id,"CANCELLED")`.
    - A `load` after the timeout → ignore the 409.
    - Iframe `error` → FAILED.
  - TAB with a null `tab` (popup blocked) → `startExecution` still runs, then `finishExecution(id,"FAILED","Popup blocked")` and an inline message with a manual "open" link (`target=_blank rel=noopener`).
  - A start 403 (UNAUTHORIZED) → close the window and show the server message as an error toast.
  - Guard every finish call so it fires at most once per execution.
- [X] T031 [US3] Rewrite the six seed `executions` payloads in `db/sql/62-ana-insert.sql` to `{"values": {...}, "sources": {...}, "mode": "TAB"}`. All seed dashboards are external; use sources DEFAULT for values equal to the parameter defaults and INPUT otherwise. Keep ids, users, statuses and durations.

**Checkpoint**: US3 passes its tests and quickstart D.3–D.4, E.1, E.3, F.

---

## Phase 6: User Story 4 — Favorite a dashboard from the catalog (Priority: P2)

**Goal**: catalog users with read-only `ANA/CATALOG` can star and unstar, sharing favorites with Dashboard Management.

**Independent Test**: as adriana (CATALOG only), starring dashboard 3 works and shows under "★ My favorites"; unstarring with the toggle on removes it without a reload; felipe sees catalog favorites in `/ana/dashboards` (quickstart B).

### Tests for User Story 4 (write first, confirm they fail)

- [X] T032 [P] [US4] Extend `api/tests/test_ana_favorites.py`:
  - A profile holding only `ANA/CATALOG` read can `PUT` and `DELETE /api/dashboards/{id}/favorite` (200).
  - It still gets 403 without a live grant.
  - A profile with neither `DASHBOARDS` nor `CATALOG` gets 403.
  - The existing `DASHBOARDS` tests pass unchanged.
  - A favorite set through these endpoints shows `is_favorite: true` in `GET /api/dashboards/catalog`.

### Implementation for User Story 4

- [X] T033 [US4] In `api/app/insights/routes/dashboards.py`, change `add_favorite` and `remove_favorite` to depend on `current_active_user` and call `check_any_privilege(session, current, "ANA", ["DASHBOARDS", "CATALOG"], can_edit=False)` (import from `app/internal/permissions`). Update both docstrings. `_set_favorite` (VIEW check) is unchanged.
- [X] T034 [US4] Verify the star wiring end-to-end in `ui/src/pages/ana/catalog.astro` and `ui/src/components/ana/CatalogDetailModal.astro`: the card star goes through `initCardGallery` services; the detail star calls `setDashboardFavorite` and dispatches `gallery:card-update` `{galleryId, id, favorite}` so the card and the active favorites filter update without a reload (US4-2).

**Checkpoint**: US4 passes its tests and quickstart B.

---

## Phase 7: Polish & cross-cutting concerns

- [X] T035 [P] Complete and proofread every `dashboard_catalog.*` key in `ui/src/i18n/en.json` and `es.json`. Check that no hard-coded strings remain in `catalog.astro`, `CatalogCard.astro`, `CatalogDetailModal.astro` or `DashboardRun.svelte`, and that list values relabel on a language switch.
- [X] T036 [P] Responsive pass at about 390 px for the grid, the detail, the parameters window and the viewer (no horizontal scroll, FR-023). The viewer iframe fills the dialog body.
- [X] T037 Run the full backend suite (`docker compose exec -T api uv run pytest -q`, expect the 670 baseline plus the new tests, 0 failed), `cd ui && bun run build`, `bunx astro check` (no new errors beyond the existing baseline), and `make test`.
- [ ] T038 Run [quickstart.md](quickstart.md) sections A–F after loading [test-catalog.sql](test-catalog.sql), as adriana.velez, santiago.marin, felipe.cardenas and admin. Record anything not click-tested.
- [X] T039 [P] Update `docs/user-stories/06-ana.md`: HU-AN04, HU-AN05 and HU-AN06 statuses with links to `specs/007-dashboard-catalog`.
- [X] T040 Update `memory/MEMORY.md`:
  - Feature-status row "Dashboard Catalog".
  - `insights` stub row: pending is now only Usage Metrics.
  - Decisions-log entry covering the catalog endpoints gated on CATALOG, the widened favorites gate, the two-step record finished once, the payload shape, the `embed=1` mode and the blank-tab-first popup strategy.
  - Updated test baseline.
- [X] T041 Add the single rollup entry for this branch at the top of `memory/CHANGELOG.md` (`## YYYY-MM-DD HH:MM — …`, from `date '+%Y-%m-%d %H:%M'`), listing the files affected.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1; blocks every story. T007 needs T004–T006, and T009 tests T005–T007.
- **US1 (Phase 3)**: needs Phase 2.
- **US2 (Phase 4)**: needs Phase 2. Its UI (T025–T026) mounts on the catalog page, so it needs T015 from US1.
- **US3 (Phase 5)**: needs US2's start path (T021, T023) and the UI island (T026).
- **US4 (Phase 6)**: backend (T032–T033) needs only Phase 2 and can run in parallel with US1–US3. UI verification (T034) needs T014–T015.
- **Polish (Phase 7)**: after the desired stories.

### Story dependency graph

```text
Setup → Foundational ─┬─► US1 (catalog) ──► US2 (execute) ──► US3 (recording)
                      └─► US4 backend ─────────────(UI check after US1)
```

### Within each story

Tests first (confirm they fail), then services, then routes, then UI. Each backend change needs its suite green before the UI task that uses it.

## Parallel Examples

### Phase 2

```text
T005 parameter_validation.py   ║  T006 permissions_service.py   ║  T008 ui types + lib/dashboardExecutions.ts
```

### User Story 1

```text
T010 test_ana_catalog.py   ║  T013 CatalogCard.astro   ║  T014 CatalogDetailModal.astro
```

### User Story 2

```text
T017 test_ana_run_form.py  ║  T018 test_ana_executions.py (start)  ║  T019 test_ana_last_values.py  ║  T024 BaseLayout embed mode
```

### Across stories

```text
US4 backend (T032 → T033) can run alongside US1/US2 work; it touches only dashboards.py and test_ana_favorites.py.
```

## Implementation Strategy

### MVP first (User Story 1 only)

Phases 1–3 deliver a browsable catalog: visibility, the six privilege options, search over type/source in both languages, and the detail. Stop and validate with quickstart A.

### Incremental delivery

1. **US1**: the catalog (MVP).
2. **US2**: running with parameters. Successful runs are already recorded.
3. **US3**: complete traceability (refusals, cancellations, timeouts, popup blocks).
4. **US4**: favorites for catalog-only profiles. Its backend can land at any point after Phase 2.

US2 and US3 are both P1 and ship together. They are split so the happy path can be demonstrated before every failure outcome is wired.

---

## Implementation notes (2026-10-05)

- **Status**: 40 of 41 tasks done. **T038 stays open**: the quickstart's browser walkthrough (sections A–F) was not click-tested, because this environment has no Playwright. The parameters window, the viewer's load/timeout/close handling and the popup-blocked path need a manual pass after loading `test-catalog.sql`.
- **What was verified**:
  - **Tests**: the full backend suite passes (715/0, 45 of them new).
  - **Build**: `bun run build` is clean, and `astro check` adds only the known "Svelte file is not a module" error for the new island.
  - **Live API smoke as `admin`**: catalog, run-form, a FAILED 400, start → finish → 409 on a repeat, last values and cancel. The three smoke rows were deleted afterwards.
  - **SSR**: `/ana/catalog` renders the grid, the six privilege options, Execute buttons and bilingual search text; `/support?embed=1` renders without the sidebar or header.
- **Deviations from the task text**:
  - T005: `validate_run_value` takes the parameter `label` as its first argument, so messages name the field (`'Top' must be a number`). `value_problem` is the shared core.
  - T013/T014: the card opens the detail through `editModalId`, because `detailModalId` would also render `GalleryCard`'s discussion button. The detail renders `detail` as preformatted text: the repo has no markdown renderer, and the asset detail view does not render markdown either.
  - T016: the gallery did not skip unhandled card buttons, so it gained an opt-in `data-gallery-passthrough` attribute. Existing galleries are unchanged.
  - Extra: submitted values accept any JSON scalar, converted to text (`true` becomes `"true"`), so a number sent by an API client gets a clear 400 or a run, never a bare 422. External dashboards with no parameters pre-open their tab in the click (`data-mode` / `data-param-count` on the Execute button) so popup blockers let it through.
