# Tasks: Collab Projects CRUD with Team Filter

**Feature Branch**: `001-collab-projects`  
**Input**: Design documents from `specs/001-collab-projects/`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Contract**: [contracts/projects.md](contracts/projects.md)

**Tests**: Risk class = **medium** (one backend behavioral change + new UI page). Required: run `make test` after backend change; manual smoke test per quickstart.md. No automated integration tests required for this risk class.

**Organization**: Tasks grouped by user story. Each story is independently implementable and testable. US1 and US2 are both P1 — implement sequentially or in parallel on the same page.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story (US1–US5 from spec.md)
- Exact file paths are included in every task description

---

## Phase 1: Setup (Environment Verification)

**Purpose**: Confirm branch and dev environment are ready before any changes.

- [X] T001 Confirm branch `001-collab-projects` is checked out; run `make up` and verify API health check at `http://localhost:8000/api/health` returns 200

**Checkpoint**: Services running — ready to begin foundational work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend extension and UI infrastructure that ALL user stories depend on. No user story work begins until this phase is complete.

**⚠ CRITICAL**: US1–US5 all require T002–T006 to be complete before implementation.

- [X] T002 [P] Extend `list_projects()` in `api/app/collab/routes/projects.py`: add `is_active=True` filter (always applied), optional `team: Optional[str] = None` query param (filtered when provided), and `order_by(Project.team, Project.name)` — replace the current query entirely per the target implementation in `contracts/projects.md`
- [X] T003 [P] Add `Project`, `ProjectCreate`, and `ProjectUpdate` TypeScript interfaces to `ui/src/types/api.ts` — append the three interfaces defined in `data-model.md` section "TypeScript Interfaces" without modifying existing entries
- [X] T004 [P] Create `ui/src/lib/projects.ts` with five CRUD service functions: `getProjects(team?, skip, limit)`, `getProject(code)`, `createProject(data)`, `updateProject(code, data)`, `deleteProject(code)` — mirror `ui/src/lib/teams.ts` structure, import types from `../types/api`
- [X] T005 [P] Add `project_modal` section to `ui/src/i18n/en.json` with keys: `add_new`, `edit`, `delete`, `one_title`, `many_title`, `empty_message`, `delete_confirmation`, `filter_title`, `code`, `name`, `description`, `team`, `status`, `repo_url`, `start_date`, `end_date` — follow the `team_modal` section as structural reference
- [X] T006 [P] Add `project_modal` section with Spanish translations to `ui/src/i18n/es.json` using the same key structure added in T005 — follow the `team_modal` section in `es.json` as reference

**Checkpoint**: Foundation ready — US1 through US5 can begin (in priority order or parallel if staffed)

---

## Phase 3: User Story 1 — List and Filter Projects by Team (Priority: P1) 🎯 MVP

**Goal**: Users can navigate to the Projects page and see all active projects in a table, filter by team, and have the filter pre-applied when arriving from a team link.

**Independent Test**: Navigate to `http://localhost:4321/collab/projects`, verify the table loads with active projects ordered by team then name; select a team from the dropdown and verify only that team's projects appear; select blank option and verify all projects return.

- [X] T007 [US1] Create `ui/src/pages/collab/projects.astro` mirroring `ui/src/pages/admin/options.astro` structure: fetch active projects via `getProjects()` from `projects.ts`, fetch active teams via `getTeams()` from `teams.ts`, render `DataTable` with columns: `code`, `name`, `team`, `status`, `start_date`, `end_date` and i18n item key `project`
- [X] T008 [US1] Add `columnFilter="team"` and `filterOptions={teams}` props to the `DataTable` in `projects.astro` (teams array with `code` and `name` fields) to enable the client-side team filter dropdown with placeholder from `project_modal.filter_title`
- [X] T009 [US1] Read `Astro.url.searchParams.get("team")` in `projects.astro` at server-render time and emit the value as a `data-initial-value` attribute on the team filter `<select>` element so the filter is pre-selected on page load from URL param
- [X] T010 [US1] Verify the **Collaboration → Projects** navigation entry exists in `ui/src/lib/navigation.ts` pointing to `/collab/projects`; add it if missing using i18n key `menu_options.projects` following the same nav item structure as the existing teams or assignments entries

**Checkpoint**: US1 fully functional — projects list, team filter, and URL pre-filter all work independently

---

## Phase 4: User Story 2 — Create a New Project (Priority: P1)

**Goal**: Users can open a create modal, fill in project details, submit, and see the new project appear in the table with a success toast — or see an error toast on duplicate code.

**Independent Test**: Click `+ Project`, fill code=`TEST-001`, name=`Test Project`, status=`PLANNED`, submit and verify the project appears in the table. Then attempt to create again with the same code and verify a 409 conflict error toast appears.

- [X] T011 [US2] Add create `CrudModal` to `projects.astro` with form fields: `code` (text, required), `name` (text, required), `description` (textarea, optional), `team` (select from `getTeams()`, optional), `status` (select from `getListItemsbyList("PROJECT_STATUS")`, required), `repo_url` (text, optional), `start_date` (text/date, optional), `end_date` (text/date, optional); fetch `PROJECT_STATUS` list items at server-render time and pass as options array
- [X] T012 [US2] Wire the `crud-submit` create event handler in `projects.astro` to call `createProject(data)` from `projects.ts`; on success refresh the table and show a success toast; on 409 conflict show an explicit conflict error toast (project code already exists); on other errors show a generic error toast

**Checkpoint**: US1 + US2 both functional — users can list, filter, and create projects

---

## Phase 5: User Story 3 — Edit an Existing Project (Priority: P2)

**Goal**: Users can click edit on any project row, modify fields in a pre-populated modal, submit, and see updates reflected immediately in the table.

**Independent Test**: Click the edit icon on an existing project, change the name and status, submit, and verify the table row reflects the updated values and a success toast appears.

- [X] T013 [US3] Add edit `CrudModal` to `projects.astro` pre-populated with the selected project's current field values; set `code` field as read-only (`pk=true`); wire the `crud-submit` edit event handler to call `updateProject(code, changedFields)` from `projects.ts` using `exclude_unset` equivalent (send only modified fields); show success or error toast on completion

**Checkpoint**: US1 + US2 + US3 functional — full create/read/update cycle works

---

## Phase 6: User Story 4 — Delete a Project (Priority: P2)

**Goal**: Users can click delete on a project row, confirm the action in a modal, and have the project disappear from the active list with a success toast.

**Independent Test**: Click the delete icon on a project row, verify the confirmation modal shows the project name, confirm deletion, and verify the project no longer appears in the table and a success toast is shown.

- [X] T014 [US4] Add delete `CrudModal` to `projects.astro` showing the project name in the confirmation body text (`project_modal.delete_confirmation`); wire the `crud-submit` delete event handler to call `deleteProject(code)` from `projects.ts` (sets `is_active=False` server-side); on success remove the row from the table and show a success toast; on error show an error toast

**Checkpoint**: Full CRUD cycle complete — US1, US2, US3, US4 all functional

---

## Phase 7: User Story 5 — Navigate to Projects from Teams (Priority: P3)

**Goal**: Users on the Teams page can click a project/detail action on a team row and land on the Projects page with the team filter pre-applied.

**Independent Test**: Navigate to `http://localhost:4321/collab/teams`, click the projects action on a team row, and verify the browser navigates to `/collab/projects?team={team_code}` with only that team's projects shown and the filter dropdown pre-selected.

- [X] T015 [P] [US5] Add a projects detail action to `ui/src/pages/collab/teams.astro` that generates a link to `/collab/projects?team={team.code}` for each team row — follow the same master-detail pattern used by the existing assignments link (`detailPage` prop or equivalent; refer to `ui/src/pages/collab/assignments.astro` for the back-link pattern if used)

**Checkpoint**: All five user stories complete and independently testable

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Validation, edge case confirmation, and smoke testing across all stories.

- [ ] T016 Run `make test` to confirm the API health check passes after the `list_projects()` backend modification in `api/app/collab/routes/projects.py`
- [ ] T017 [P] Verify the 409 conflict response on duplicate project code via `curl -X POST http://localhost:8000/api/projects/ -H "Authorization: Bearer <token>" -d '{"code":"TEST-001","name":"Dup","status":"PLANNED"}'` (run twice); confirm second call returns HTTP 409
- [ ] T018 Manual smoke test per `specs/001-collab-projects/quickstart.md`: verify list loads ordered by team then name; filter by team works; filter clearance restores full list; create succeeds and shows toast; edit updates values; delete removes from active list; clicking a team on the teams page navigates to projects filtered by that team

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational complete
- **US2 (Phase 4)**: Depends on Foundational complete; US1 must exist (same page)
- **US3 (Phase 5)**: Depends on Foundational complete; US1 must exist (same page)
- **US4 (Phase 6)**: Depends on Foundational complete; US1 must exist (same page)
- **US5 (Phase 7)**: Depends on Foundational complete; independent of US2–US4 (different file)
- **Polish (Final Phase)**: All desired stories complete

### User Story Dependencies

| Story | Depends On | File |
|-------|-----------|------|
| US1 — List + Filter | Foundational only | `projects.astro` (new) |
| US2 — Create | Foundational + US1 page created | `projects.astro` (same) |
| US3 — Edit | Foundational + US1 page created | `projects.astro` (same) |
| US4 — Delete | Foundational + US1 page created | `projects.astro` (same) |
| US5 — Teams Link | Foundational only | `teams.astro` (independent) |

### Within Each Story

- Fetch data (getTeams, getListItems) at server-render level before modal rendering
- Modal component declaration before event handler wiring
- Event handlers after modal declarations

---

## Parallel Execution Examples

### Phase 2 — All Foundational Tasks in Parallel (5 tasks, 5 different files)

```
T002  api/app/collab/routes/projects.py  (backend endpoint)
T003  ui/src/types/api.ts                (TypeScript types)
T004  ui/src/lib/projects.ts             (service layer)
T005  ui/src/i18n/en.json               (English i18n)
T006  ui/src/i18n/es.json               (Spanish i18n)
```

All five can proceed simultaneously — zero file conflicts.

### Phase 3 + Phase 7 — US1 and US5 in parallel once Foundation is done

```
Developer A: T007 → T008 → T009 → T010  (projects.astro page)
Developer B: T015                        (teams.astro link — independent file)
```

### After US1 page exists: US2, US3, US4 sequentially in one file

```
T011 → T012  (create modal + handler in projects.astro)
T013         (edit modal + handler in projects.astro)
T014         (delete modal + handler in projects.astro)
```

These target the same file and must run sequentially to avoid conflicts.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — **do not skip, blocks everything**
3. Complete Phase 3: US1 (T007–T010) — list page with team filter
4. **STOP and VALIDATE**: navigate to `/collab/projects`, verify list and filter work
5. Deploy/demo if ready — this is a fully usable read-only view

### Incremental Delivery

1. **P1 Complete** → Phase 1 + Phase 2 + Phase 3 (list) + Phase 4 (create) → Demo
2. **P2 Complete** → Phase 5 (edit) + Phase 6 (delete) → Full CRUD Demo
3. **P3 Complete** → Phase 7 (teams link) → Full Feature Delivered
4. **Done** → Final Phase polish + smoke test

### Files Changed (6 total)

| File | Action | Blocks |
|------|--------|--------|
| `api/app/collab/routes/projects.py` | Modify | US1 list endpoint |
| `ui/src/types/api.ts` | Modify (append) | All UI stories |
| `ui/src/lib/projects.ts` | Create | All UI stories |
| `ui/src/pages/collab/projects.astro` | Create | US1–US4 |
| `ui/src/pages/collab/teams.astro` | Modify | US5 |
| `ui/src/i18n/en.json` + `es.json` | Modify | All UI stories |

---

## Notes

- `[P]` tasks = different files, no shared-file dependencies
- `[Story]` label maps task to user story for traceability
- Backend auth and router registration require **no changes** — already covered
- No database migration required — `projects` table exists with all columns
- `PROJECT_STATUS` list items are already seeded in the DB — no data migration needed
- `make test` runs the API health smoke test only — not individual endpoint tests
- Commit after each phase checkpoint before moving to next phase
- The `exclude_unset=True` (exclude_unset) pattern for PATCH-style updates is already established in the backend `update_project()` — no backend change required for PUT
