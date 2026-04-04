# Tasks: Collab Dimensions CRUD with Metrics Master-Detail

**Feature Branch**: `002-collab-dimensions-metrics`  
**Input**: Design documents from `specs/002-collab-dimensions-metrics/`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contract**: [contracts/dimensions.md](contracts/dimensions.md) | **Data Model**: [data-model.md](data-model.md)

**Tests**: Risk class = **low** (UI-only additions consuming already-complete, stable backend APIs). Required: run `make test` to confirm no regressions; manual browser smoke test per quickstart.md. No automated integration tests required for this risk class.

**Organization**: Tasks grouped by user story. Each story is independently implementable and testable. US1 and US2 are both P1 on the same page — implement sequentially within dimensions.astro. US6–US8 are all on metrics.astro.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story (US1–US8 from spec.md)
- Exact file paths are included in every task description

---

## Phase 1: Setup (Environment Verification)

**Purpose**: Confirm branch and dev environment are ready before any changes.

- [X] T001 Confirm branch `002-collab-dimensions-metrics` is checked out; run `make up` and verify API health at `http://localhost:8000/api/health` returns 200; verify `/api/dimensions` and `/api/metrics` endpoints respond with JWT token

**Checkpoint**: Services running — ready to begin foundational work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared TypeScript types, UI service lib files, and i18n keys that ALL user stories depend on. No page work begins until this phase is complete.

**⚠ CRITICAL**: US1–US8 all require T002–T006 to be complete before implementation.

- [X] T002 [P] Add `Dimension`, `DimensionCreate`, `DimensionUpdate`, `Metric`, `MetricCreate`, and `MetricUpdate` TypeScript interfaces to `ui/src/types/api.ts` — append the six interfaces defined in `data-model.md` section "UI Type Interfaces" without modifying any existing entries
- [X] T003 [P] Create `ui/src/lib/dimensions.ts` with five CRUD service functions: `getDimensions(skip, limit)`, `getDimension(code)`, `createDimension(data)`, `updateDimension(code, data)`, `deleteDimension(code)` — mirror `ui/src/lib/lists.ts` structure; import `Dimension`, `DimensionCreate`, `DimensionUpdate` from `../types/api`; use `encodeURIComponent(code)` for path parameters
- [X] T004 [P] Create `ui/src/lib/metrics.ts` with five CRUD service functions: `getMetrics(skip, limit)`, `getMetric(id)`, `createMetric(data)`, `updateMetric(id, data)`, `deleteMetric(id)` — mirror `ui/src/lib/assignments.ts` structure; import `Metric`, `MetricCreate`, `MetricUpdate` from `../types/api`; use numeric `id` in path parameters (not encoded)
- [X] T005 [P] Add `dimension_modal` section to `ui/src/i18n/en.json` with keys: `one_title`, `many_title`, `code`, `name`, `description`, `scale`, `unit`, `add_new`, `edit`, `delete`, `delete_confirmation`, `empty_message`; and add `metric_modal` section with keys: `one_title`, `many_title`, `dimension`, `assignment`, `value`, `observation`, `measured_at`, `add_new`, `edit`, `delete`, `delete_confirmation`, `empty_message`, `filter_title`; also add `"metrics": "Metrics"` under `menu_options` — follow the `role_modal` and `privilege_modal` sections as structural reference
- [X] T006 [P] Add the same `dimension_modal` and `metric_modal` sections with Spanish translations to `ui/src/i18n/es.json` using the identical key structure added in T005 — follow the `role_modal` and `privilege_modal` sections in `es.json` as reference

**Checkpoint**: Foundation ready — US1 through US8 can begin (in priority order)

---

## Phase 3: User Story 1 — List Dimensions (Priority: P1) 🎯 MVP

**Goal**: Users can navigate to the Dimensions page and see all active dimensions in a table ordered by name.

**Independent Test**: Navigate to `http://localhost:4321/collab/dimensions`; verify the table renders with columns code, name, scale, unit; records are ordered by name ascending.

- [X] T007 [US1] Create `ui/src/pages/collab/dimensions.astro` mirroring `ui/src/pages/admin/roles.astro` structure: import `BaseLayout`, `Breadcrumb`, `DataTable`, `CrudModal`, `Toast`; fetch active dimensions via `getDimensions()` from `dimensions.ts`; fetch active lists via `getLists()` from `lists.ts` (for scale select options); fetch list items for `DIMENSIONS_UNIT` via `getListItemsbyList("DIMENSIONS_UNIT")` from `list_items.ts` (for unit select options); map response to data rows with fields: `id=item.code`, `code`, `name`, `description`, `scale`, `unit`, `is_active`, `created_at`, `updated_at`; define table columns: `code` (`dimension_modal.code`), `name` (`dimension_modal.name`), `scale` (`dimension_modal.scale`), `unit` (`dimension_modal.unit`); add `Breadcrumb` with `moduleName="Collaboration"`, `pageName="Dimensions"`, i18n keys `moduleNameKey="modules.COLLAB"`, `pageNameKey="menu_options.dimensions"`, `pageTitleKey="menu_options.dimensions"`
- [X] T008 [US1] Verify the **Collaboration → Dimensions** navigation entry exists in `ui/src/lib/navigation.ts` pointing to `/collab/dimensions`; add it if missing using i18n key `menu_options.dimensions` following the same nav item structure as the existing teams or assignments entries

**Checkpoint**: US1 functional — dimensions list page renders with correct columns and ordering

---

## Phase 4: User Story 2 — Create a New Dimension (Priority: P1)

**Goal**: Users can open a create modal, fill in code and name (plus optional scale/unit), submit, and see the new dimension in the table with a success toast.

**Independent Test**: Click `+ Dimension`, fill code=`TEST-DIM`, name=`Test Dimension`, submit and verify the dimension appears. Then attempt code=`TEST-DIM` again and verify a conflict error toast appears.

- [X] T009 [US2] Add create `CrudModal` to `dimensions.astro` (`modalId="dimension-create-modal"`) with form fields: `code` (text, required, `pk: false`), `name` (text, required), `description` (textarea, optional), `scale` (select from `lists` array as options, optional), `unit` (select from `DIMENSIONS_UNIT` list items as options, optional) — pass `fields={dimensionFields}` and `entityName="Dimension"`; add matching `fieldKeys` and `data-rows` / `data-keys` hidden div following the pattern in `roles.astro`
- [X] T010 [US2] Add `<script type="module">` to `dimensions.astro` that imports `initCrudPage` from `/scripts/crudClient.js` and `createDimension`, `updateDimension`, `deleteDimension` from `/api/dimensions` (dynamic import pattern); call `initCrudPage` with the CRUD functions, `"dimension-create-modal"`, `"dimension-edit-modal"`, `"dimension-delete-modal"` — mirror the client script in `roles.astro` exactly, substituting dimension functions

**Checkpoint**: US1 + US2 functional — list and create both work with toast feedback

---

## Phase 5: User Story 3 — Edit an Existing Dimension (Priority: P2)

**Goal**: Users can click edit on a dimension row and update name, description, scale, or unit in a pre-populated modal.

**Independent Test**: Click the edit icon on an existing dimension row; verify code field is read-only (`pk: true` in edit fields); change the name; submit and verify the updated name appears in the table row.

- [X] T011 [US3] Add edit `CrudModal` to `dimensions.astro` (`modalId="dimension-edit-modal"`) using the same `dimensionFields` array but with `code` field marked `pk: true` (read-only); the `initCrudPage` script from T010 already wires the edit handler to call `updateDimension(code, changedFields)` — verify the edit modal opens pre-populated and that partial updates (only changed fields) are sent

**Checkpoint**: US1 + US2 + US3 functional — full create/read/update cycle works

---

## Phase 6: User Story 4 — Delete a Dimension (Priority: P2)

**Goal**: Users can click delete on a dimension row, confirm the action, and have the dimension disappear from the active list.

**Independent Test**: Click the delete icon on a dimension row; verify the confirmation modal shows the dimension name; confirm and verify the row disappears from the table with a success toast.

- [X] T012 [US4] Add delete `CrudModal` to `dimensions.astro` (`modalId="dimension-delete-modal"`) with the same `dimensionFields` and `entityName="Dimension"`; the `initCrudPage` script from T010 wires the delete handler to call `deleteDimension(code)` — verify the confirmation text uses `dimension_modal.delete_confirmation` and that the row is removed from the table on success

**Checkpoint**: Full Dimensions CRUD complete — US1, US2, US3, US4 all functional

---

## Phase 7: User Story 5 — Navigate to Metrics from a Dimension (Priority: P2)

**Goal**: Users can click a detail action on a dimension row and navigate to the Metrics page with that dimension's filter pre-applied.

**Independent Test**: Click the detail action on a `TEST-DIM` row and verify the browser navigates to `/collab/metrics?dimension=TEST-DIM`; verify the metrics page filter is pre-selected to `TEST-DIM`.

- [X] T013 [US5] Add `detailPage="/collab/metrics"` prop to the `DataTable` component in `dimensions.astro` so each row gets a detail navigation link to `/collab/metrics?dimension={code}` — follow the same pattern used in `ui/src/pages/collab/teams.astro` for the assignments detail link

**Checkpoint**: US5 functional — detail navigation from Dimensions to Metrics works

---

## Phase 8: User Story 6 — List and Filter Metrics by Dimension (Priority: P2)

**Goal**: Users can view all active metrics in a table, filter by dimension via a dropdown, and arrive with the filter pre-applied when navigating from the Dimensions page.

**Independent Test**: Navigate to `http://localhost:4321/collab/metrics`; verify the table shows active metrics with columns dimension, assignment, value, measured_at ordered by measured_at desc; select a dimension from the filter and verify only that dimension's metrics appear; navigate to `/collab/metrics?dimension=TEST-DIM` and verify the filter is pre-selected.

- [X] T014 [US6] Create `ui/src/pages/collab/metrics.astro` mirroring `ui/src/pages/admin/privileges.astro` structure: import `BaseLayout`, `Breadcrumb`, `DataTable`, `CrudModal`, `Toast`; fetch active metrics via `getMetrics()` from `metrics.ts`; fetch active dimensions via `getDimensions()` from `dimensions.ts` (for filter options and create form select); fetch active assignments via `getAssignments()` from `assignments.ts` (for create form select); map response to data rows with fields: `id=item.id`, `dimension`, `assignment`, `value`, `observation`, `measured_at`, `is_active`, `created_at`, `updated_at`; define table columns: `dimension` (`metric_modal.dimension`), `assignment` (`metric_modal.assignment`), `value` (`metric_modal.value`), `measured_at` (`metric_modal.measured_at`); add `Breadcrumb` with `moduleName="Collaboration"`, `pageName="Metrics"`, i18n keys `moduleNameKey="modules.COLLAB"`, `pageNameKey="menu_options.metrics"`, `pageTitleKey="menu_options.metrics"`
- [X] T015 [US6] Add `columnFilter="dimension"` and `filterOptions={dimensions}` props to the `DataTable` in `metrics.astro` (dimensions array with `code` as value and `name` as label) to enable client-side dimension filter dropdown with placeholder from `metric_modal.filter_title`
- [X] T016 [US6] Read `Astro.url.searchParams.get("dimension")` in `metrics.astro` at server-render time and emit the value as a `data-initial-value` attribute on the dimension filter `<select>` element so the filter is pre-selected on page load from URL param; add `masterPage="/collab/dimensions"` prop to the `DataTable` (or equivalent back-link pattern) to render the back navigation link to the Dimensions page
- [X] T017 [US6] Verify the **Collaboration → Metrics** navigation entry exists in `ui/src/lib/navigation.ts` pointing to `/collab/metrics`; add it if missing using i18n key `menu_options.metrics` following the same nav item structure as existing collab entries

**Checkpoint**: US6 functional — metrics list, dimension filter, URL pre-filter, and back-link all work

---

## Phase 9: User Story 7 — Create a New Metric Record (Priority: P2)

**Goal**: Users can open a create modal, select a dimension and assignment, enter a value, and see the new metric in the table with a success toast.

**Independent Test**: Click `+ Metric`, select a dimension, select an assignment, enter value=`85`, submit and verify the metric appears in the table. Navigate from `/collab/metrics?dimension=TEST-DIM` and open create; verify the dimension field is pre-filled.

- [X] T018 [US7] Add create `CrudModal` to `metrics.astro` (`modalId="metric-create-modal"`) with form fields: `dimension` (select from active dimensions array as options, required), `assignment` (select from active assignments array as options, required), `value` (text, required), `observation` (textarea, optional), `measured_at` (text/datetime, optional) — pass `fields={metricFields}` and `entityName="Metric"`; add matching `fieldKeys` and `data-rows` / `data-keys` hidden div following the pattern in `privileges.astro`
- [X] T019 [US7] Add `<script type="module">` to `metrics.astro` that imports `initCrudPage` from `/scripts/crudClient.js` and `createMetric`, `updateMetric`, `deleteMetric` from the metric lib; call `initCrudPage` with the CRUD functions and modal IDs `"metric-create-modal"`, `"metric-edit-modal"`, `"metric-delete-modal"`; if a `dimension` query param is present in the URL, pre-fill the dimension select field in the create modal on open — mirror the client script pattern from `privileges.astro`

**Checkpoint**: US6 + US7 functional — metrics list, filter, and create all work

---

## Phase 10: User Story 8 — Edit and Delete Metric Records (Priority: P3)

**Goal**: Users can edit the value, observation, or measured_at of a metric, or deactivate it with a confirmation prompt.

**Independent Test**: Click the edit icon on a metric row; verify `dimension` and `assignment` fields are read-only; change value to `90`; submit and verify the table row updates. Click delete on another metric row, confirm, and verify it disappears from the active list.

- [X] T020 [US8] Add edit `CrudModal` to `metrics.astro` (`modalId="metric-edit-modal"`) using `metricFields` with `id` marked `pk: true` (read-only) and `dimension` / `assignment` also read-only; the `initCrudPage` script from T019 wires the edit handler to call `updateMetric(id, changedFields)` — verify partial update (only `value`, `observation`, `measured_at`) is sent
- [X] T021 [US8] Add delete `CrudModal` to `metrics.astro` (`modalId="metric-delete-modal"`) with `entityName="Metric"`; the `initCrudPage` script from T019 wires the delete handler to call `deleteMetric(id)`; verify the confirmation text uses `metric_modal.delete_confirmation` and the row is removed from the table on success

**Checkpoint**: All eight user stories complete and independently testable

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Smoke testing, edge case validation, and completeness verification across all stories.

- [ ] T022 Run `make test` to confirm the API health check and existing backend tests still pass after the UI additions (no backend changes in this feature — should be green)
- [ ] T023 [P] Manual smoke test — Dimensions page per `specs/002-collab-dimensions-metrics/quickstart.md`: verify list loads ordered by name; create succeeds with toast; conflict on duplicate code shows error toast; edit updates fields with code read-only; delete removes from active list; detail link navigates to metrics page with filter pre-applied
- [ ] T024 [P] Manual smoke test — Metrics page per `specs/002-collab-dimensions-metrics/quickstart.md`: verify list loads ordered by measured_at desc; dimension filter works; URL `?dimension=CODE` pre-selects filter; create metric with dimension + assignment + value succeeds; edit updates value; delete removes from active list; back link navigates to dimensions page

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational complete
- **US2 (Phase 4)**: Depends on Foundational + US1 page created (same file)
- **US3 (Phase 5)**: Depends on Foundational + US1 page created (same file)
- **US4 (Phase 6)**: Depends on Foundational + US1 page created (same file)
- **US5 (Phase 7)**: Depends on Foundational + US1 page created (same file, adds detailPage)
- **US6 (Phase 8)**: Depends on Foundational complete; independent of US1–US5 (different file)
- **US7 (Phase 9)**: Depends on Foundational + US6 page created (same file)
- **US8 (Phase 10)**: Depends on Foundational + US6 page created (same file)
- **Polish (Final Phase)**: All desired stories complete

### User Story Dependencies

| Story | Priority | Depends On | File |
|-------|----------|-----------|------|
| US1 — List Dimensions | P1 | Foundational only | `dimensions.astro` (new) |
| US2 — Create Dimension | P1 | Foundational + US1 page created | `dimensions.astro` (same) |
| US3 — Edit Dimension | P2 | Foundational + US1 page created | `dimensions.astro` (same) |
| US4 — Delete Dimension | P2 | Foundational + US1 page created | `dimensions.astro` (same) |
| US5 — Detail Link to Metrics | P2 | Foundational + US1 page created | `dimensions.astro` (same) |
| US6 — List + Filter Metrics | P2 | Foundational only | `metrics.astro` (new) |
| US7 — Create Metric | P2 | Foundational + US6 page created | `metrics.astro` (same) |
| US8 — Edit + Delete Metrics | P3 | Foundational + US6 page created | `metrics.astro` (same) |

### Within Each Story

- Foundational types/lib files before page shells
- Page shell (fetch + table) before modal components
- Modal component declaration before event handler script
- All three modals (create/edit/delete) wired in the single `initCrudPage` call

### Parallel Execution Examples

#### Phase 2 — All Foundational Tasks in Parallel (5 tasks, 5 different files)

```
T002  ui/src/types/api.ts            (TypeScript interfaces)
T003  ui/src/lib/dimensions.ts       (dimensions service)
T004  ui/src/lib/metrics.ts          (metrics service)
T005  ui/src/i18n/en.json            (English i18n)
T006  ui/src/i18n/es.json            (Spanish i18n)
```

All five can proceed simultaneously — zero file conflicts.

#### After Foundation: Dimensions and Metrics pages in parallel across two developers

```
Developer A: T007 → T008 → T009 → T010 → T011 → T012 → T013   (dimensions.astro)
Developer B: T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021  (metrics.astro)
```

Both page chains target different files — no conflicts.

#### Within each page: sequential (all tasks modify the same file)

```
dimensions.astro:  T007 → T008 → T009 → T010 → T011 → T012 → T013
metrics.astro:     T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — Dimensions List)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — **do not skip, blocks everything**
3. Complete Phase 3: US1 (T007–T008) — dimensions list page
4. **STOP and VALIDATE**: navigate to `/collab/dimensions`, verify table renders
5. Deploy/demo if ready — this is a usable read-only dimensions catalog

### Incremental Delivery

1. **P1 Dimensions** → Phase 1 + Phase 2 + Phase 3 + Phase 4 → List + Create → Demo
2. **Full Dimensions CRUD** → Phase 5 + Phase 6 + Phase 7 → Edit + Delete + Master-Detail Link → Demo
3. **Metrics List** → Phase 8 → Metrics page with filter + URL pre-select → Demo
4. **Full Metrics CRUD** → Phase 9 → Create Metric → Demo
5. **Complete Feature** → Phase 10 → Edit + Delete Metrics → Full Feature Delivered
6. **Done** → Final Phase polish + smoke test

### Files Changed (7 total)

| File | Action | Blocks |
|------|--------|--------|
| `ui/src/types/api.ts` | Modify (append 6 interfaces) | All UI stories |
| `ui/src/lib/dimensions.ts` | Create | Dimensions page stories |
| `ui/src/lib/metrics.ts` | Create | Metrics page stories |
| `ui/src/i18n/en.json` | Modify (add 2 sections + 1 key) | All UI stories |
| `ui/src/i18n/es.json` | Modify (add 2 sections + 1 key) | All UI stories |
| `ui/src/pages/collab/dimensions.astro` | Create | US1–US5 |
| `ui/src/pages/collab/metrics.astro` | Create | US6–US8 |

No backend files are modified — all backend routes and models are already complete.

---

## Notes

- `[P]` tasks = different files, no shared-file dependencies — can run simultaneously
- `[Story]` label maps task to user story for traceability
- Backend auth and router registration require **no changes** — dimensions and metrics routes are already registered
- No database migration required — `dimensions` and `metrics` tables exist with all columns
- `DIMENSIONS_UNIT` list items are assumed seeded; verify via `GET /api/list_items/?list=DIMENSIONS_UNIT` before wiring the unit select
- The `value` field in the Metrics create form is a free-text input (not a select) per research.md RQ-5 decision — dynamic select per dimension scale is a future enhancement
- The assignment select in the Metrics form uses `getAssignments()` — the display label should show both `user_id` and `team` for readability; format as `{assignment.team} / {assignment.user_id}` or similar
- `make test` runs the API health smoke test only — no individual endpoint tests required for this UI-only risk class
- Commit after each phase checkpoint before moving to the next phase
