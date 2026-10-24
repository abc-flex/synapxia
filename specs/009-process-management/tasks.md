# Tasks: Process Management

**Input**: Design documents from `specs/009-process-management/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/processes-api.md](contracts/processes-api.md), [quickstart.md](quickstart.md)

**Tests**: INCLUDED. Constitution Principle III requires automated tests for new contract, permission and data-rule surfaces (research R15). The UI is verified manually through `quickstart.md`.

**Organization**: tasks are grouped by user story (spec.md US1–US5), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task belongs to (US1…US5)

## Conventions for every task

- **Backend**:
  - Domain `api/app/workflows/` (research R1). Models and services go in `internal/`, routes in `routes/`.
  - Gate every route with `require_privilege("PROC", "PROCESSES", can_edit=…)` from `app/internal/permissions.py`, and get the session from `app.internal.dependencies.get_db_session`.
  - Validate list values with `app.internal.list_values.validate_list_value`.
  - Map service `ValueError` → 400, a missing process → 404, conflicts → 409, as in `api/app/insights/routes/dashboards.py`.
  - Routes return bare models or raise `HTTPException`; the global envelope wraps them.
- **Service functions that write links must NOT commit.** They take the caller's session, so create (US5) can compose them in one transaction. Only the route-level orchestration commits or rolls back.
- **Tests**:
  - SQLite fixtures from `api/tests/conftest.py` (`session`, `client`), with helpers in `api/tests/proc_helpers.py`, modelled on `api/tests/ana_helpers.py`.
  - Run with `docker compose exec -T api uv run pytest -q tests/test_proc_*.py`.
- **UI**:
  - Every string goes in both `ui/src/i18n/en.json` and `es.json`.
  - List values (PROCESS_TYPE, PROCESS_STATUS, PROCESS_RELATION_TYPE, RELATION_TYPE) go through `ui/src/lib/listLang.ts` (`toListOptions`, `fillListSelect`, `listLabelsAttr`), never filtered by language by hand.
  - Svelte islands are mounted manually with `mount()` from their `.astro` shell; Svelte template comments use `<!-- -->`.

---

## Phase 1: Setup (schema, seed, labels)

**Purpose**: the in-place schema and seed changes decided in research R2/R13, plus the menu label.

- [X] T001 Edit `db/sql/71-proc-ddl.sql` in place:
  - `process_assets`: add `type VARCHAR(100) NOT NULL -- references List_items.value where list='RELATION_TYPE'` after `asset`, and change the PK to `(process, asset, type)`.
  - `process_inits`: same change with `init`; PK `(process, init, type)`.
  - Change the comment on `related_processes.type` to `list='PROCESS_RELATION_TYPE'`.
  - After the PROCESS_STATUS list, add the list `PROCESS_RELATION_TYPE` (`lists` row: module `PROC`, type `LIST_OF_VALUES`, a description mentioning BPMN), with `en` and `es` `list_items` exactly as in the data-model.md table (PRECEDES 10 … GOVERNS 70).
- [X] T002 Edit `db/sql/72-proc-insert.sql` in place (research R13):
  - Replace the two `related_processes` INSERT blocks with `PRECEDES` (INBL→OPER, OPER→OUTL, OUTL→MKTS, MKTS→SERV) and `SUPPORTS` (TECH→OPER, PROC→INBL, HRMG→OPER, INFR→SERV). Rewrite each rationale to read in the new direction, and change the block comments to match.
  - Add `type` to the `process_assets` and `process_inits` column lists, with `'RELATED_TO'` on every row.
- [X] T003 [P] Relabel `menu_options.processes` to "Process Management" in `ui/src/i18n/en.json` and "Gestión de Procesos" in `ui/src/i18n/es.json` (research R14).
- [X] T004 (done without wiping the dev volume: fresh init verified on a throwaway postgres:18 container, dev DB patched in place) Recreate the DB with `make rebuild` and run the three psql checks from quickstart.md § Prerequisites step 2: 7 `es` rows, the PRECEDES chain plus SUPPORTS, and all asset links RELATED_TO. Fix T001/T002 until `db` initialises without errors (`make logs-db`).

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: models, shared rules, test helpers and the UI service layer used by every story.

**⚠️ CRITICAL**: no user-story work starts before this phase is complete.

- [X] T005 Write `api/app/workflows/internal/models.py`, replacing the stub docstring-only file. SQLModel classes:
  - Tables:
    - `Process` (`__tablename__ = "processes"`, every column of `db/sql/71-proc-ddl.sql`, `code` PK, `tags` as JSON, as `Asset.tags` is mapped in `api/app/lib/internal/models.py`);
    - `RelatedProcess` (`related_processes`, PK source+target+type);
    - `ProcessAsset` (`process_assets`, PK process+asset+type);
    - `ProcessInit` (`process_inits`, PK process+init+type).
  - Request models: `ProcessCreate` (core fields + optional `status`, `owner`, and optional lists `relations`, `assets`, `inits`); `ProcessUpdate` (all optional, **no `code`**); `RelationItem`, `AssetLinkItem`, `InitLinkItem`; `RelationsReplace`, `AssetsReplace`, `InitsReplace`.
  - Response models: `ProcessRead` (with `parent_name`, `unit_name`, `owner_name`); `ProcessDetail` (+ `allowed_statuses: List[str]`); `ProcessRelationRead`, `ProcessAssetRead`, `ProcessInitRead`; `ProcessFormOptions`.
  - Use field names exactly as in contracts/processes-api.md. Length limits are checked in validators so they answer 400, not 422 (same reason as SpecKit 006).
- [X] T006 [P] Create `api/app/workflows/internal/status_service.py`, modelled on `api/app/insights/internal/status_service.py`:
  - constants `DRAFT/REVIEW/PUBLISHED/DEPRECATED`;
  - `ALLOWED_TRANSITIONS = {(DRAFT,REVIEW),(REVIEW,PUBLISHED),(REVIEW,DRAFT),(PUBLISHED,DEPRECATED)}`;
  - `validate_create_status(status) -> "DRAFT"` (None or DRAFT accepted, otherwise `ValueError`);
  - `validate_transition(current, new)` (same status is OK, otherwise it must be in the set, else `ValueError` naming both statuses);
  - `allowed_statuses_for(current) -> [current, *targets]`.
- [X] T007 [P] Create `api/app/workflows/internal/relation_rules.py`:
  - `PROCESS_RELATION_LIST = "PROCESS_RELATION_TYPE"`, `ASSET_INIT_RELATION_LIST = "RELATION_TYPE"`, `UNDIRECTED = {"INTERACTS_WITH"}`.
  - `RULES = {"SUPPORTS": {"source": ["SUPPORT"], "target": ["PRIMARY"]}, "PRECEDES": {"same_type": True}}`.
  - `check_compatible(rel_type, source_type, target_type)`: raises `ValueError` with a message naming the rule.
  - `pair_key(source, target, rel_type)`: an unordered tuple for UNDIRECTED types, ordered otherwise.
  - `incompatible_links_after_type_change(session, code, new_type) -> list[RelatedProcess]`: active SUPPORTS/PRECEDES rows touching `code`, in either direction, that the new type would break.
  - Pure functions where possible, so they can be unit-tested without a DB.
- [X] T008 [P] Create `api/tests/proc_helpers.py`:
  - `seed_proc_privileges(session, profile, can_edit=True)` (PROC module, PROCESSES option and privilege rows, modelled on `seed_privileges` in `api/tests/ana_helpers.py`);
  - `seed_proc_lists(session)` (PROCESS_TYPE, PROCESS_STATUS, PROCESS_RELATION_TYPE, RELATION_TYPE values);
  - `mk_unit(session, code)`, `mk_user(session, …)`;
  - `mk_process(session, code, type="PRIMARY", parent=None, status="DRAFT", **kw)`;
  - `mk_asset(session, …)`, `mk_initiative(session, …)`;
  - `mk_relation(session, source, target, type, active=True)`;
  - `auth_headers(client, user)` (reuse whatever `ana_helpers.py`/`conftest.py` already use for tokens).
- [X] T009 [P] Add `Process`, `ProcessCreate`, `ProcessUpdate`, `ProcessDetail`, `ProcessRelation`, `ProcessAssetLink`, `ProcessInitLink` and `ProcessFormOptions` interfaces to `ui/src/types/api.ts`, matching contracts/processes-api.md.
- [X] T010 Create `ui/src/lib/processes.ts` with every function listed in contracts/processes-api.md § "UI service layer", built on `apiGet`/`apiPost`/`apiPut`/`apiDelete` from `ui/src/lib/api.ts` (look at `ui/src/lib/dashboards.ts` for the pattern), typed with T009. Depends on T009.

**Checkpoint**: models import cleanly (`docker compose exec -T api uv run python -c "import app.workflows.internal.models"`), and the helpers and types exist.

---

## Phase 3: User Story 1 - Browse and maintain the process inventory (Priority: P1) 🎯 MVP

**Goal**: list, search, filter, create (core fields only), edit core fields with the status lifecycle, remove logically, and offer a read-only mode.

**Independent Test**: spec US1. As ADMINISTRATIVE, create OPER-QA (lands in Draft), find it by search and the type filter, rename it, move it to Review, then remove it.

### Tests for User Story 1 (write first, they must fail)

- [X] T011 [P] [US1] `api/tests/test_proc_processes.py`:
  - **List**: active only, ordered by code, `type`/`status`/`unit`/`q` filters, `skip`/`limit`, `limit > 500` → 422 or capped (match the route), and `parent_name`/`unit_name`/`owner_name` resolved.
  - **Detail**: includes `allowed_statuses`; unknown or inactive → 404.
  - **Create (core only)**: 201 in DRAFT; code uppercased and pattern-checked (400); duplicate → 409, also against an inactive process; invalid type/unit/owner/parent → 400 naming the field; owner defaults to the caller.
  - **Update**: partial; a `code` key is ignored; self-parent and descendant-parent → 400.
  - **Delete**: logical; 409 with active children; 200 once the children are removed.
- [X] T012 [P] [US1] `api/tests/test_proc_status.py`:
  - unit tests of `status_service`;
  - API tests: create with PUBLISHED → 400; every allowed move → 200; Published → Draft, Draft → Published and Deprecated → anything → 400; `allowed_statuses` per status as in data-model.md.
- [X] T013 [P] [US1] `api/tests/test_proc_access.py`:
  - no token → 401 on every `/api/processes` route;
  - a profile without PROC/PROCESSES → 403;
  - a read-only privilege → 200 on GETs and 403 on POST/PUT/DELETE;
  - `form-options.can_edit` is true or false accordingly;
  - superuser → allowed.

### Implementation for User Story 1

- [X] T014 [US1] Create `api/app/workflows/internal/process_service.py`:
  - `normalize_code`.
  - `validate_core(session, data, current=None)`: name and lengths; PROCESS_TYPE via `validate_list_value`; unit active; owner an active user; parent active.
  - `check_parent_cycle(session, code, parent)` per research R7: one `select(Process.code, Process.parent)` query and an upward walk with a step cap.
  - `list_processes(session, skip, limit, type, status, unit, q)` with **batched** name lookups for parent, unit and owner (one query each, no N+1).
  - `get_detail`, `create_process(session, data, caller)` (core only for now; it must not commit, so US5 can extend it), `update_process(session, code, data)` (uses `status_service.validate_transition`; the type-change guard is added in T024), `remove_process(session, code)` (409 condition = any active child).
- [X] T015 [US1] Create `api/app/workflows/routes/processes.py` with `router = APIRouter(prefix="/api/processes", tags=["processes"])`:
  - `GET /` (`limit: int = Query(100, ge=1, le=500)`);
  - `GET /form-options`, declared **before** `/{code}`; returns processes, units, owners, assets, initiatives (active only, names only), `relation_rules = relation_rules.RULES` and `can_edit` via `has_privilege(..., can_edit=True)` or superuser;
  - `GET /{code}`, `POST /` (commit or rollback here), `PUT /{code}`, `DELETE /{code}`.
  - Map `ValueError` → 400, missing → 404, and duplicate/children conflicts → 409 (use a small `ProcessConflict` exception defined in process_service).
- [X] T016 [US1] Register the router in `api/app/main.py`: import `from .workflows.routes import processes as processes_router` next to the insights imports, and `app.include_router(processes_router.router)` in the router block.
- [X] T017 [P] [US1] Add the i18n keys in `ui/src/i18n/en.json` and `es.json`:
  - `process_table.*`: column headers code/name/type/parent/unit/owner/status/tags, filter labels, search placeholder, `new`, empty state.
  - `process_modal.*`: title_new/title_edit, field labels and hints for every core field, code_readonly_hint, status_hint_create/status_hint_locked, save, discard confirm, errors such as duplicate code.
  - `process_detail_modal.*`: tab names core/related_processes/related_assets/related_inits, and save_core.
- [X] T018 [US1] Create `ui/src/pages/proc/processes.astro`, mirroring `ui/src/pages/ana/dashboards.astro` (BaseLayout, breadcrumb, `DataTable`):
  - SSR fetch `getProcesses(0, 500)`.
  - Columns per research R11 (`name` as `title` with description as subtitle; `status` as `status`; `tags` as `tags`).
  - Filter slots: type, status and unit, with options from `toListOptions` and the units from form-options.
  - A *New Process* button and row edit/remove actions.
  - Hide New, edit's save and remove when `getProcessFormOptions().can_edit` is false, and open the dialog in read-only mode instead.
  - Removal uses the shared `CrudModal` confirm and shows the 409 message in a `Toast`.
- [X] T019 [US1] Create `ui/src/components/proc/ProcessDetailModal.astro`, mirroring `ui/src/components/ana/DashboardDetailModal.astro`:
  - The `<dialog>` shell with Core Fields as plain DOM inputs (`FormField`, `inputClass`/`labelClass` from `ui/src/lib/formClasses.ts`): code (read-only in edit), name, description, type, parent (excluding self), unit, owner (default the current user), reference, status, tags, detail.
  - **Status policy**: in create, the select is hidden or locked to DRAFT with a hint; in edit, options come from `allowed_statuses`, and the control is locked when only the current status remains (Deprecated).
  - Save Core Fields (`updateProcess`) with server messages shown inline or in a toast.
  - A discard-changes confirm on close.
  - Re-parent the core section into ProcessDetailTabs' `core` panel after mount (same technique as `AssetDetailModal.astro`).
- [X] T020 [US1] Create `ui/src/components/svelte/ProcessDetailTabs.svelte`:
  - A tab strip with the classes and ARIA of `AssetDetailTabs.svelte` (around lines 1100–1230). For now it renders only the **Core Fields** tab and its empty `core` panel; US2–US4 append their tabs **in this order**: Related processes, Related assets, Related inits.
  - `onTabChange` and `setCoreDirty` props/exports like AssetDetailTabs, and the pending-changes dot.
  - `readonly` prop.
  - Mount it from ProcessDetailModal.astro with `mount()`.

**Checkpoint**: T011–T013 pass; quickstart API rows 1, 2, 4, 5, 7–9, 15 and 17 behave as specified; UI scenarios 1, 5 and 8 work for core fields.

---

## Phase 4: User Story 2 - Relate a process to other processes (Priority: P1)

**Goal**: the Related processes tab (first after Core Fields), with BPMN-oriented types, compatibility rules, undirected Interacts With and an atomic tab save.

**Independent Test**: spec US2. Edit OUTL, see `MKTS Precedes`, add `SERV Interacts With`, *Save related processes*, reopen and see both; SERV shows the link as incoming.

### Tests for User Story 2

- [X] T021 [P] [US2] `api/tests/test_proc_relations.py`:
  - GET returns outgoing rows plus incoming INTERACTS_WITH (`direction`), with `target_*` describing the other process and `target_active` false for a removed target.
  - PUT replace: deactivates missing rows, reactivates an identical inactive row (same `created_at`), inserts new rows, updates a changed rationale.
  - 400 and **nothing changed** (atomic) for: self; unknown or inactive target; a `RELATION_TYPE`-only value (e.g. SIMILAR_TO); a duplicate in the set; an unordered INTERACTS_WITH duplicate against an existing incoming row; SUPPORTS Support→Support, Primary→Primary and Primary→Support; PRECEDES Primary→Support.
  - An incoming INTERACTS_WITH can be removed from the target side.
  - **Type-change guard**: `PUT /api/processes/TECH {type: PRIMARY}` with an active `TECH SUPPORTS OPER` → 400 listing the link; allowed once the link is removed.
  - Unit tests of `relation_rules.check_compatible` and `pair_key`.

### Implementation for User Story 2

- [X] T022 [US2] Create `api/app/workflows/internal/links_service.py` with `list_relations(session, code)` and `replace_relations(session, code, items)`. Steps, without committing:
  1. Validate every item: target active and ≠ code; type via `validate_list_value(session, "PROCESS_RELATION_TYPE", …)`; `check_compatible` using both processes' types; no duplicate `pair_key` in the set.
  2. Load the current active outgoing rows plus incoming INTERACTS_WITH rows.
  3. Diff by `pair_key`: deactivate the rows that are gone; keep an existing incoming row as stored; reactivate an identical inactive row; insert new rows (an INTERACTS_WITH duplicate of an incoming row is a 400); update a changed rationale and `updated_at`.
  4. Return the resulting list.
  Batch-load the target names and types in one query.
- [X] T023 [US2] Create `api/app/workflows/routes/process_links.py` (`prefix="/api/processes"`) with `GET /{code}/relations` (read privilege) and `PUT /{code}/relations` (edit privilege): 404 for an unknown or inactive process, and commit on success or rollback on `ValueError` → 400. Register it in `api/app/main.py` next to T016.
- [X] T024 [US2] Wire the type-change guard into `update_process` in `api/app/workflows/internal/process_service.py`. When `type` changes, call `relation_rules.incompatible_links_after_type_change` and raise `ValueError` listing `SOURCE TYPE TARGET` for each conflicting link.
- [X] T025 [P] [US2] Add the `related_links.*` i18n keys (shared by all three tabs) in `ui/src/i18n/en.json` and `es.json`, copying wording and placeholders from the existing `asset_detail_modal.related_*` keys:
  - target label and placeholder per kind (process/asset/initiative);
  - relation type label;
  - rationale placeholder;
  - add, remove, empty list, inactive-target badge;
  - missing_fields and duplicate messages per kind;
  - incompatible_supports and incompatible_precedes;
  - an incoming badge.
  Also add `process_detail_modal.save_related_processes`, `save_related_assets` and `save_related_inits`.
- [X] T026 [US2] Create `ui/src/components/svelte/RelatedLinksTab.svelte` (research R10). Copy the markup and classes of AssetDetailTabs' Related Assets panel (`ui/src/components/svelte/AssetDetailTabs.svelte` around lines 1315–1372) and its staging logic (around lines 192–203 and 452–482).
  - **Props**: `idPrefix`; `kind` (`"process"|"asset"|"init"`, which selects the i18n messages); `targetOptions: {value,label,meta?}[]`; `typeOptions` (from `toListOptions`); `filterTargets?: (type: string) => (opt) => boolean`; `readonly`.
  - **Exports**: `hydrate(rows)` (rows already shaped as `{target, targetLabel, type, typeLabel, rationale, inactive?, incoming?}`, also seeding the dirty baseline); `staged()` (returns `{target, type, rationale}[]`); `dirty()`; `reset()`; `commitBaseline()`.
  - **Behaviour**: the add row offers target, type and rationale. Validation (missing fields, duplicate by `target:type`) shows the inline messages. The target select is filtered by `filterTargets(type)` when a type is chosen; if the picked target becomes incompatible after a type change, the incompatibility message shows and Add is blocked. List rows show the target, the type label (via `listLabelsAttr` so it relabels on language switch), the rationale, and the inactive and incoming badges. Removal is staged.
- [X] T027 [US2] Add the **Related processes** tab to `ui/src/components/svelte/ProcessDetailTabs.svelte`, directly after Core Fields:
  - Mount `RelatedLinksTab` with `kind="process"`.
  - Targets from `formOptions.processes`, excluding the current code.
  - `typeOptions` from PROCESS_RELATION_TYPE.
  - `filterTargets` built from `formOptions.relation_rules` and the current process type: SUPPORTS → source must be SUPPORT and targets PRIMARY; PRECEDES → targets of the same type.
  - Export `hydrateRelations`, `relationsStaged` and `relationsDirty`, and add the tab dot.
- [X] T028 [US2] In `ui/src/components/proc/ProcessDetailModal.astro`, in edit mode:
  - On open, load `getProcessRelations(code)` and hydrate.
  - When the active tab is `related_processes`, label the footer button *Save related processes* and save with `saveProcessRelations(code, tabs.relationsStaged())`. Show a 400 message inline or in a toast; on success, re-hydrate from the response and clear the dot.
  - Leave the other tabs' pending changes untouched (FR-011, SC-006).

**Checkpoint**: T021 passes; quickstart API rows 10–14 and 16 and UI scenarios 3, 4 and 6 (process tab) pass.

---

## Phase 5: User Story 3 - Relate a process to library assets (Priority: P2)

**Goal**: the Related assets tab, with typed links over `process_assets`.

**Independent Test**: spec US3. Edit OPER-DEVELOP, see its seeded asset links, add an asset with a type and rationale, *Save related assets*, reopen.

- [X] T029 [P] [US3] `api/tests/test_proc_links.py` (assets part):
  - GET shape (`asset_name`, `category`, `asset_active`);
  - PUT replace semantics (deactivate, reactivate, insert, rationale update);
  - same asset with two different types allowed;
  - 400 and atomic for: an inactive or unknown asset; a type outside RELATION_TYPE (e.g. PRECEDES); a duplicate `(asset, type)`;
  - 404 for an unknown process.
- [X] T030 [US3] Add `list_assets(session, code)` and `replace_assets(session, code, items)` to `api/app/workflows/internal/links_service.py`. They follow the same diff algorithm as T022, keyed by `(asset, type)`, with type validated against `RELATION_TYPE`, no commit, and asset names and categories batch-loaded.
- [X] T031 [US3] Add `GET /{code}/assets` and `PUT /{code}/assets` to `api/app/workflows/routes/process_links.py`.
- [X] T032 [US3] Add the **Related assets** tab to `ui/src/components/svelte/ProcessDetailTabs.svelte`, after Related processes: `RelatedLinksTab` with `kind="asset"`, targets from `formOptions.assets` (label `name · category`) and `typeOptions` from RELATION_TYPE; plus the dot and `hydrateAssets`, `assetsStaged` and `assetsDirty`.
- [X] T033 [US3] In `ui/src/components/proc/ProcessDetailModal.astro`: load `getProcessAssets` on open, and add the *Save related assets* footer branch using `saveProcessAssets`, with the same handling as T028.

**Checkpoint**: T029 (assets) passes; UI scenario 4 for the assets tab passes.

---

## Phase 6: User Story 4 - Relate a process to initiatives (Priority: P2)

**Goal**: the Related inits tab, with typed links over `process_inits`.

**Independent Test**: spec US4. Edit TECH-AIPLATF, see its seeded initiative link, add one, *Save related inits*, reopen.

- [X] T034 [P] [US4] Extend `api/tests/test_proc_links.py` with the initiatives part, mirroring T029: `init_name`, `init_active`, an inactive initiative refused, typed uniqueness and atomic failure.
- [X] T035 [US4] Add `list_inits(session, code)` and `replace_inits(session, code, items)` to `api/app/workflows/internal/links_service.py`, keyed by `(init, type)` with type from RELATION_TYPE and no commit.
- [X] T036 [US4] Add `GET /{code}/inits` and `PUT /{code}/inits` to `api/app/workflows/routes/process_links.py`.
- [X] T037 [US4] Add the **Related inits** tab (the last tab) to `ui/src/components/svelte/ProcessDetailTabs.svelte`: `RelatedLinksTab` with `kind="init"`, targets from `formOptions.initiatives` and types from RELATION_TYPE; plus the dot and the hydrate/staged/dirty exports. Confirm the final tab order is Core Fields, Related processes, Related assets, Related inits.
- [X] T038 [US4] In `ui/src/components/proc/ProcessDetailModal.astro`: load `getProcessInits` on open, and add the *Save related inits* footer branch using `saveProcessInits`.

**Checkpoint**: T034 passes; UI scenario 4 for the inits tab passes.

---

## Phase 7: User Story 5 - Create a process with its links in one pass (Priority: P3)

**Goal**: in create mode every tab is staged, and one *Save* writes the process and all its links atomically.

**Independent Test**: spec US5. *New Process*, fill Core Fields, stage one link per Related tab, save once, reopen and see all three.

- [X] T039 [P] [US5] Add create-with-links cases to `api/tests/test_proc_processes.py`:
  - POST with `relations`, `assets` and `inits` → 201 and all links stored;
  - an invalid link in any array (e.g. SIMILAR_TO in relations, an incompatible SUPPORTS, an inactive asset) → 400 with **no process row and no link rows**;
  - a duplicate code with links → 409 and no links.
- [X] T040 [US5] Extend `create_process` in `api/app/workflows/internal/process_service.py`: after inserting the process (flushed, not committed), call `links_service.replace_relations`, `replace_assets` and `replace_inits` on the same session when their arrays are present. The `POST /` route in `api/app/workflows/routes/processes.py` commits once, or rolls everything back on any exception.
- [X] T041 [US5] Create mode in `ui/src/components/proc/ProcessDetailModal.astro` and `ui/src/components/svelte/ProcessDetailTabs.svelte`:
  - All four tabs are enabled and staged.
  - The footer shows a single *Save* on every tab, which validates Core Fields first: on missing required fields, switch to the Core Fields tab and mark the fields with `setFieldInvalid`.
  - Send `createProcess({...core, relations: tabs.relationsStaged(), assets: tabs.assetsStaged(), inits: tabs.initsStaged()})`.
  - In the Related processes tab in create mode, the compatibility filter uses the type selected in Core Fields (re-evaluated when it changes).
  - After success, reload the list (`window.location.reload()`, as Dashboard Management does).

**Checkpoint**: T039 passes; quickstart API rows 3 and 6 and UI scenario 2 pass.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T042 [P] Update `docs/user-stories/07-proc.md`: the API domain reference changes `api/app/proc` → `api/app/workflows`. HU-PR02 type changes to `PROCESS_RELATION_TYPE` (list the 7 values and their BPMN counterparts); HU-PR03 and HU-PR04 PKs gain `type`; add the UI path `ui/src/pages/proc/processes.astro`.
- [X] T043 [P] Update `api/CLAUDE.md` and `api/AGENTS.md`: `workflows` is no longer an empty stub; it is the Processes domain (partial: Process Management shipped; Value Chain and Process Map pending).
- [X] T044 Run the full backend suite with `docker compose exec -T api uv run pytest -q` (baseline 749 passed plus the new suites, 0 failed), then `make test` and `cd ui && bun run build`. `astro check` must add no new errors beyond the known "Svelte file is not a module" pattern, once per new Svelte import.
- [X] T045 Run the quickstart.md API table (rows 1–17) live as an ADMINISTRATIVE user and as COLLABORATOR, then clean up OPER-QA. Record any deviation, and fix it before continuing.
- [ ] T046 (NOT DONE — no browser available in this environment; flagged in CHANGELOG and MEMORY) Run the quickstart.md UI scenarios 1–9 in a browser (en and es, light and dark), including the side-by-side parity check against `/lib/assets` Related Assets (SC-003). If no browser is available, state that explicitly in the CHANGELOG entry and the MEMORY decision row.
- [X] T047 Update `memory/MEMORY.md`:
  - **Decisions log row**: workflows = Processes domain; PROCESS_RELATION_TYPE with BPMN mapping and the SUPPORTS/PRECEDES rules; atomic per-tab replace endpoints; all-or-nothing create; in-place DDL with no migration (provisioned DBs need `make rebuild`); shared `RelatedLinksTab.svelte` (AssetDetailTabs adoption pending).
  - **Feature status row**: Process Management.
  - **"In progress / stubs"**: workflows becomes partial.
  - **Backend tests baseline**: the new count.
  - **P2 blockers**: drop `workflows` from "Stub domains not implemented" if appropriate.
- [X] T048 Add the rollup entry at the top of `memory/CHANGELOG.md`, `## YYYY-MM-DD HH:MM — Process Management (SpecKit 009)` (time from `date '+%Y-%m-%d %H:%M'`). It needs 1–3 bullets, which must name the in-place DDL and the `make rebuild` requirement, plus the files affected.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies. T004 needs T001 and T002.
- **Foundational (Phase 2)**: needs Phase 1 (models mirror the edited DDL). T010 needs T009.
- **US1 (Phase 3)**: needs Phase 2. It is the MVP.
- **US2 (Phase 4)**: needs US1's routes, modal and tabs shell (T015, T019, T020). T026 is the shared component that US3 and US4 reuse.
- **US3 (Phase 5)** and **US4 (Phase 6)**: need US2's T022 (links_service file and diff pattern), T023 (routes file) and T026 (component). After that, US3 and US4 are independent of each other: their backend tasks touch different functions but the same files, so run them sequentially or coordinate the edits.
- **US5 (Phase 7)**: needs US2–US4 (all three replace functions and tabs).
- **Polish (Phase 8)**: needs every story that ships.

### Within each story

Tests first (they must fail), then services, routes, i18n, components, and finally modal wiring.

### Parallel opportunities

- Phase 1: T003 runs in parallel with T001 and T002.
- Phase 2: T006, T007, T008 and T009 run in parallel after T005 (T006 and T007 do not import models). T010 follows T009.
- US1: T011, T012, T013 and T017 run in parallel; T014 → T015 → T016 are sequential; T018–T020 are UI and can proceed alongside the backend once T010 exists.
- US2: T021 and T025 run in parallel; T022 → T023 and T024 are backend; T026 → T027 → T028 are UI.
- US3 and US4 tests (T029, T034) can be written in parallel.
- Polish: T042 and T043 run in parallel.

### Parallel example: User Story 1

```text
Task: "T011 [P] [US1] test_proc_processes.py"
Task: "T012 [P] [US1] test_proc_status.py"
Task: "T013 [P] [US1] test_proc_access.py"
Task: "T017 [P] [US1] process_table/process_modal/process_detail_modal i18n keys"
```

### Parallel example: User Story 2

```text
Task: "T021 [P] [US2] test_proc_relations.py"
Task: "T025 [P] [US2] related_links.* i18n keys"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1, then Phase 2.
2. Phase 3 (US1). Stop and validate the inventory: list, create, edit, lifecycle, removal and access.

### Incremental delivery

1. US1 → the process inventory is usable.
2. US2 → process dependencies (the core of the Value Chain and Process Map data).
3. US3 + US4 → links to assets and initiatives.
4. US5 → one-pass create.
5. Polish → docs, memory, CHANGELOG and the full verification.

## Notes

- [P] = different files, no dependency on unfinished tasks. [USn] = traceability to spec.md.
- Never commit inside `links_service`/`process_service` write helpers; the routes own the transaction.
- Do not touch `AssetDetailTabs.svelte` (research R10: adopting the new component there is a follow-up).
- One CHANGELOG entry for the whole branch (T048); update it rather than appending on later commits.
