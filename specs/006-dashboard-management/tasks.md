# Tasks: Dashboard Management

**Input**: Design documents from `/specs/006-dashboard-management/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/dashboards-api.md](contracts/dashboards-api.md),
[quickstart.md](quickstart.md)

**Tests**: REQUIRED. Constitution Principle III makes automated tests mandatory for contract,
permission and state-transition changes, and plan.md R13 lists the modules. Each story writes its
tests first and confirms they fail before implementing.

**Organization**: tasks are grouped by the spec's user stories:

- US1: register and maintain dashboards (P1)
- US2: status lifecycle (P1)
- US3: parameters (P2)
- US4: permissions (P2)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4; Setup, Foundational and Polish tasks carry no story label
- Paths are repository-relative: `api/`, `ui/` and `db/` are the three surfaces

## Conventions every task follows

- **Backend**: copy the matching `api/app/inits/` file's style.
  - Routes wrap guard exceptions in a local `_ensure_manage`/`_ensure_view` → `HTTPException(403)`.
  - `ValueError` maps to 400 and `IntegrityError` to 409.
  - Module RBAC is `require_privilege("ANA", "DASHBOARDS", can_edit=…)`.
  - Lists take `skip: int = Query(0, ge=0)` and `limit: int = Query(100, ge=1, le=500)`.
- **UI**: copy `ui/src/pages/inits/initiatives.astro`, `ui/src/components/inits/InitiativeDetailModal.astro`
  and `ui/src/components/svelte/InitiativeDetailTabs.svelte`.
  - Svelte is mounted with `mount()` from a bundled `<script>` that imports through `@/`.
  - List values render through `ui/src/lib/listLang.ts`.
  - Every string goes in both `ui/src/i18n/en.json` and `es.json`.
- **Tests**: run inside the container with `docker compose exec -T api uv run pytest -q <path>`.

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: seeds and test scaffolding that every story uses.

- [X] T001 [P] Add Spanish `list_items` rows (`lang='es'`, same `value` and `sort_order` as the `en` rows) to `db/sql/61-ana-ddl.sql`, right after each list's `en` INSERT:
  - DASHBOARD_TYPE: Tablero, Informe, Cuadro de mando, Vista de KPI, Vista analítica.
  - SOURCE_TYPE: Página interna, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Iframe personalizado.
  - DASHBOARD_STATUS: Borrador, Publicado, Archivado, Retirado.
  - PARAM_TYPE: Texto, Número, Booleano, Fecha.
  - EXECUTION_STATUS: Exitosa, Fallida, Cancelada, Tiempo agotado, No autorizada.
- [X] T002 [P] Create `specs/006-dashboard-management/provisioned-db.sql` for already-provisioned DBs (local + Neon). It holds the same `es` INSERTs as T001, each guarded with `WHERE NOT EXISTS (SELECT 1 FROM list_items WHERE list=… AND lang='es' AND value=…)` so it is safe to rerun. Add a header comment explaining when to run it.
- [X] T003 [P] Create `specs/006-dashboard-management/test-owner.sql` (test data, NOT seed). Make sure `felipe.cardenas` (ADMINISTRATIVE) has `dashboard_permissions` rows: USER/<his id>/MANAGE on dashboard 1 and USER/<his id>/VIEW on dashboard 2, with nothing on dashboard 3. Resolve his id with a subquery on `users.username`. Include a matching cleanup block that revokes those grants (`UPDATE … SET valid_to = NOW()`).
- [X] T004 [P] Create `api/tests/ana_helpers.py`, modelled on `api/tests/inits_helpers.py`. Reuse its `user`, `superuser`, `override`, `mk_user_row`, `data` and `mk_list` (import them from `inits_helpers` rather than copying). Add these helpers:
  - `seed_privileges(session, profile, options=("DASHBOARDS",), can_edit=True)` for module `ANA`.
  - `seed_ana_lists(session)`: DASHBOARD_TYPE, SOURCE_TYPE, DASHBOARD_STATUS, PARAM_TYPE, TARGET_TYPE and ACCESS_LEVEL values, plus a `LIST_OF_VALUES` list `GRANULARITY` with DAY/WEEK/MONTH and a non-LoV list.
  - `mk_dashboard(session, id=None, name="Dash", status="DRAFT", type="DASHBOARD", sources_types="POWER_BI", source_url="https://x.example/d", **kw)`.
  - `mk_grant(session, dashboard, target_type="USER", target_code="1", access_level="MANAGE", valid_from=None, valid_to=None)`.
  - `mk_param(session, dashboard, name, label=None, data_type="STRING", **kw)`.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: models, the permission binding, shared validation, status rules and router wiring.
Every story needs these.

**⚠️ No story work starts until this phase is complete.**

- [X] T005 Hoist list-value validation into the shared layer. Create `api/app/internal/list_values.py` with `validate_list_value(session, list_code, value)`, moved verbatim from `api/app/inits/internal/list_validation.py`. Change that inits module to `from ...internal.list_values import validate_list_value` and keep re-exporting the name, so `LIST_FIELDS`, `REQUIRED_FIELDS`, `validate_list_value` and `validate_core_fields` stay importable from it unchanged. Run `docker compose exec -T api uv run pytest -q tests/test_inits_*.py`; it must pass unchanged.
- [X] T006 Write `api/app/insights/internal/models.py`, replacing the stub comment. Follow [data-model.md](data-model.md) and the `api/app/inits/internal/models.py` style (`Column(..., BigInteger, ForeignKey(...))` for bigint FKs, `tags` as `sa_column=Column("tags", JSON)`).
  - `DashboardBase`, `Dashboard(table="dashboards")`, `DashboardCreate` (name, description, type, sources_types, source_url, tags, detail, plus an optional `status` that is only accepted if it is DRAFT), `DashboardUpdate` (all optional, incl. `status`), and `DashboardWithAccess(DashboardBase)` with `id`, `my_access`, `allowed_statuses: List[str]` and `permission_scopes: List[str]`.
  - `Parameter(table="parameters")` with composite PK `dashboard` + `name`, `context_binding` as BigInteger FK to `dashboard_permissions.id`, and `list` as String(50) FK to `lists.code`. Also `ParameterCreate`, `ParameterUpdate` (no `name`), and `ParameterRead` (all columns + `value_source: str` + `binding_label: Optional[str]`).
  - `DashboardPermission(table="dashboard_permissions")` with no `is_active`, plus `DashboardPermissionCreate`, `DashboardPermissionUpdate` (`access_level`, `valid_from`, `valid_to`) and `RevokedDashboardPermission` (all columns + `bound_parameters: List[str]`).
  - `ListOption(value: str, label: str)`.
- [X] T007 [P] Create `api/app/insights/internal/permissions_service.py`, a twin of `api/app/inits/internal/permissions_service.py` bound to `DashboardPermission` with `_FK = "dashboard"`. It exposes `DashboardAccessForbidden`, `not_revoked_clause`, `is_revoked`, `dashboards_user_access`, `dashboards_user_scopes`, `accessible_dashboards`, `user_dashboard_access` (superuser → MANAGE), `require_dashboard_manage` and `require_dashboard_view`, and re-exports `ACCESS_MANAGE`/`ACCESS_VIEW`.
- [X] T008 [P] Create `api/app/insights/internal/status_service.py`, mirroring `api/app/inits/internal/status_service.py` without the collaboration logging.
  - Define `StatusTransitionForbidden(ValueError)` and constants DRAFT/PUBLISHED/ARCHIVED/RETIRED.
  - `ALLOWED_TRANSITIONS` is a set of pairs: (DRAFT,PUBLISHED), (PUBLISHED,ARCHIVED), (PUBLISHED,RETIRED), (ARCHIVED,PUBLISHED), (ARCHIVED,RETIRED).
  - `_ORDER = [PUBLISHED, ARCHIVED, RETIRED]`.
  - `allowed_targets(current)` and `allowed_statuses_for(current)` return `[normalize(current), *targets]`.
  - `validate_create_status(status)`: None/blank/DRAFT → "DRAFT", anything else raises.
  - `validate_transition(current, new)`: returns True when the status changes, False when unchanged or blank, and raises a message listing the allowed moves when the move is disallowed.
  - Use `app/internal/status.normalize`.
- [X] T009 [P] Create `api/app/insights/internal/list_validation.py` with `LIST_FIELDS = {"type": "DASHBOARD_TYPE", "sources_types": "SOURCE_TYPE", "status": "DASHBOARD_STATUS"}`, `REQUIRED_FIELDS = ("name", "type", "sources_types", "source_url")`, and a `validate_core_fields(session, fields, required=())` that has the same semantics as the inits one and uses `app/internal/list_values.validate_list_value`.
- [X] T010 Create the grants read route in `api/app/insights/routes/dashboard_permissions.py` (router prefix `/api/dashboard_permissions`, tag `dashboard_permissions`). Include only `GET /dashboard/{dashboard_id}`: it returns 404 if the dashboard is missing, requires VIEW (`_guard`), returns grants that are not revoked ordered by id with bounded `skip`/`limit`, and is gated on `ANA/DASHBOARDS` read. US3's binding picker needs this; writes are added in US4.
- [X] T011 Create empty-but-valid route modules `api/app/insights/routes/dashboards.py` (prefix `/api/dashboards`, tag `dashboards`) and `api/app/insights/routes/parameters.py` (prefix `/api/dashboards`, tag `dashboard_parameters`), each with a module docstring. Register all three insights routers in `api/app/main.py`: add imports next to the `inits` block (`from .insights.routes import dashboards as dashboards_router`, etc.) and `app.include_router(...)` calls in the matching section. Confirm `/docs` loads.
- [X] T012 [P] Add the UI types to `ui/src/types/api.ts`, mirroring the backend models: `Dashboard`, `DashboardCreate`, `DashboardUpdate`, `DashboardWithAccess`, `DashboardParameter` (incl. `value_source: "GRANT" | "LIST" | "INPUT"` and `binding_label`), `DashboardParameterCreate`, `DashboardParameterUpdate`, `DashboardPermission`, `DashboardPermissionCreate`, `DashboardPermissionUpdate`, `RevokedDashboardPermission` and `ListOption`.
- [X] T013 [P] Create `ui/src/lib/dashboard_permissions.ts` with `getDashboardPermissions(dashboardId, skip=0, limit=500)`, wrapping `lib/api.ts` the way `ui/src/lib/init_permissions.ts` does. US4 adds the write functions.
- [X] T014 [P] Add a test module `api/tests/test_ana_foundation.py`:
  - `status_service` unit tests: `allowed_statuses_for` for each status and for an unknown value (single entry), `validate_create_status`, and `validate_transition` over the full 4×4 matrix.
  - `permissions_service` tests: a PUBLIC VIEW grant, a TEAM grant through an active assignment, MANAGE beating VIEW, an expired grant ignored, a future-dated grant not in effect, and superuser → MANAGE.
  - `GET /api/dashboard_permissions/dashboard/{id}` tests: 401 without a token, 403 without RBAC, 403 without a grant, 200 with VIEW, and revoked grants excluded while future-dated ones are included.

**Checkpoint**: run `pytest -q tests/test_ana_foundation.py tests/test_inits_*.py`; all pass. The routers are registered.

---

## Phase 3: User Story 1 — Register and maintain dashboards (Priority: P1) 🎯 MVP

**Goal**: a grant-scoped, filterable list at `/ana/dashboards` with New Dashboard, and an edit
dialog whose Core Fields tab creates, edits and removes dashboards (FR-001–FR-011).

**Independent test**: quickstart scenarios 1, 2 and 7. Felipe sees dashboards 1 and 2, with 2
read-only. A created dashboard is Draft, its creator holds MANAGE, and it shows in the list.

### Tests for User Story 1 (write first, confirm they fail)

- [X] T015 [P] [US1] Write `api/tests/test_ana_dashboards.py`, using `ana_helpers`.
  - **POST**:
    - 201 with status DRAFT and a USER/MANAGE grant for the caller, created in the same transaction.
    - A `status` other than DRAFT → 400.
    - A blank name/type/sources_types/source_url → 400.
    - A type or source outside its list → 400.
    - POWER_BI with `http://…` or a relative path → 400.
    - INTERNAL_PAGE with `/ana/usage` → 201, and with `https://…` or `//evil` → 400.
    - Without the edit privilege → 403.
  - **GET /with-access**:
    - Only granted dashboards appear, the filter is applied before `skip`/`limit` (seed 3 granted among 6 and page with `limit=2`), and inactive dashboards are excluded.
    - Superusers see all, with `my_access = MANAGE`.
    - `my_access` reflects MANAGE beating VIEW, and `permission_scopes` lists the scope types.
  - **GET /{id}**: VIEW → 200, no grant → 403, missing or inactive → 404.
  - **PUT /{id}**:
    - Only sent keys are applied and `updated_at` is set.
    - VIEW → 403.
    - `source_url` is re-validated when `sources_types` changes.
  - **DELETE /{id}**: MANAGE → 200 with `is_active=false`, after which the dashboard is gone from `/with-access`; VIEW → 403.

### Implementation for User Story 1

- [X] T016 [P] [US1] Create `api/app/insights/internal/source_validation.py` with `validate_source_url(source_type, url)` (raises `ValueError`).
  - INTERNAL_PAGE: starts with `/`, not `//`, no `:` before the first `/`, at most 2048 characters.
  - Every other source: `urllib.parse.urlsplit` with scheme `https` and a non-empty netloc, at most 2048 characters.
  - Normalise the source code through `app/internal/status.normalize`.
- [X] T017 [US1] Implement the dashboard routes in `api/app/insights/routes/dashboards.py`, per [contracts](contracts/dashboards-api.md#dashboards--apiappinsightsroutesdashboardspy). Declare `/with-access` before `/{dashboard_id}`.
  - Add a `_with_access(d, access, scopes)` builder that fills `allowed_statuses` from `status_service.allowed_statuses_for(d.status)`.
  - `GET /with-access`: copy `inits/routes/initiatives.py:get_all_with_access`, without favorites.
  - `GET /{dashboard_id}`: VIEW required.
  - `POST /`:
    1. Validate core fields (required + lists), `validate_create_status`, then `validate_source_url`.
    2. Insert the `Dashboard` plus `DashboardPermission(target_type="USER", target_code=str(current.id), access_level="MANAGE")`.
    3. Run a single commit and log with `logger.info`.
  - `PUT /{dashboard_id}`:
    - Load the row with `select(...).with_for_update()`, then require MANAGE; reject an inactive dashboard.
    - Validate the sent core fields.
    - If `status` is sent, use `status_service.validate_transition`, which raises → 400. Drop `status` when it is unchanged.
    - If `source_url` or `sources_types` is sent, re-validate against the merged values.
    - Set `updated_at = datetime.utcnow()` and return `_with_access`.
  - `DELETE /{dashboard_id}`: MANAGE required, logical delete.
- [X] T018 [P] [US1] Create `ui/src/lib/dashboards.ts`.
  - `getDashboardsWithAccess(skip, limit)`.
  - `getAllDashboardsWithAccess()`: loops `limit=500` pages until a short page comes back, capped at 10,000 rows. This avoids the 100-row truncation from the known blocker.
  - `getDashboard(id)`, `createDashboard(body)`, `updateDashboard(id, body)`, `deleteDashboard(id)`.
- [X] T019 [P] [US1] Add i18n keys to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`:
  - `dashboard_table.*`: page title/subtitle, column headers name/type/source/status/tags/actions, filter labels type/source/status/privileges, the privileges options (reuse the initiative wording), the empty state with and without the create right, the `new` button, and the remove confirm title/body.
  - `dashboard_detail_modal.*`: `title_new`, `title_edit`, `title_view`, tab labels `tab_core`/`tab_parameters`/`tab_permissions`, field labels and placeholders, `source_url_hint_internal`/`source_url_hint_external`, required/invalid messages, `save_core`, `saved`, `create_first_hint` ("Save the dashboard to add parameters and permissions") and the discard dialog strings.
- [X] T020 [US1] Create `ui/src/components/ana/DashboardDetailModal.astro`, modelled on `ui/src/components/inits/InitiativeDetailModal.astro`.
  - A native `<dialog>` with a header (title + status pill) and the Core Fields form (name, description, type, source, source location with a hint that changes with the source, tags chips, detail textarea).
  - Type/source/status `<select>`s are filled from `getListItems` by list code through `toListOptions`/`fillListSelect` (`lib/listLang.ts`).
  - Client-side validation mirrors T016 using `setFieldInvalid` from `lib/formClasses.ts`.
  - A tab bar with Core Fields / Parameters / Permissions. In create mode only Core Fields is enabled and the other two show `create_first_hint`.
  - After a successful create, switch to edit mode on the returned id without closing.
  - View-only mode (`my_access === "VIEW"`) disables every input and hides save.
  - A tab-scoped save button: in this phase it saves Core Fields only (`createDashboard`/`updateDashboard` with only the core keys).
  - A snapshot-based dirty check and a discard-changes confirm dialog on close (FR-024).
  - On save, dispatch `datatable:row-update` (or reload) so the list reflects the change.
  - Expose `[data-dashboard-open]` triggers carrying `data-dashboard-id`.
- [X] T021 [US1] Create the page `ui/src/pages/ana/dashboards.astro`, modelled on `ui/src/pages/inits/initiatives.astro`.
  - Use `BaseLayout` and a breadcrumb.
  - Render a `DataTable` over `getAllDashboardsWithAccess()` with columns name (`as: "title"`, description as subtitle), type, source (`labelsKey` list labels), status (`as: "status"`), tags (`as: "tags"`) and actions.
  - Type/source/status are header-funnel filters (`filterNHeaderColumn`), and privileges is a toolbar filter over `permission_scopes` (same options as initiatives).
  - Search by name.
  - Use `manageKey` so VIEW rows hide edit/remove, and a remove action calling `deleteDashboard` after a `CrudModal` confirm.
  - Show a "New Dashboard" button only when the caller's `ANA/DASHBOARDS` privilege has `can_edit` (check with the same helper the sidebar/options use; read `ui/src/lib/` for the existing privilege lookup).
  - Show the empty state from T019 when there are no rows.
  - Mount `DashboardDetailModal`.
- [X] T022 [US1] Verify that the sidebar entry `ANA/DASHBOARDS` (`/ana/dashboards`, seeded in `db/sql/12-admin-insert.sql`) resolves its label through `menu_options.dashboards` in both i18n files. Add the key if it is missing, and check that it does not collide with an existing `menu_options.dashboards` from another module (the sidebar key ignores the module, see the 2026-08-25 decision). If it collides, use the existing module+code exception pattern in `SideBar.astro`/`SideBarMenuItem.astro`.
- [X] T023 [US1] Run `pytest -q tests/test_ana_dashboards.py` (green), `cd ui && bun run build` (clean) and `astro check` (no new errors beyond the baseline). Then walk through quickstart scenarios 1, 2 and 7 as `felipe.cardenas` after running `test-owner.sql`.

**Checkpoint**: US1 is a usable MVP, a governed inventory with create, edit and remove.

---

## Phase 4: User Story 2 — Control a dashboard's lifecycle status (Priority: P1)

**Goal**: the status control offers only allowed moves and the server refuses everything else
(FR-012/FR-013).

**Independent test**: quickstart scenario 3. Create, then Publish, Archive, Publish, Retire, and
check that the control is locked. A direct PUT with a disallowed status → 400 and nothing changes.

### Tests for User Story 2 (write first)

- [X] T024 [P] [US2] Write `api/tests/test_ana_status.py` against `PUT /api/dashboards/{id}`.
  - Every allowed pair → 200, with the status changed and `allowed_statuses` updated.
  - Every disallowed pair from the 4×4 matrix (incl. any move from RETIRED, any move to DRAFT, DRAFT → ARCHIVED/RETIRED) → 400, and the row is unchanged, including other fields sent in the same request.
  - An unchanged status sent together with a name change → 200 and only the name changes.
  - A legacy unknown status → `allowed_statuses` has a single entry, and any change → 400.
  - Status values are case/prefix-normalised (`2-PUBLISHED` counts as PUBLISHED).
  - Two sequential requests: the second is evaluated against the new status.

### Implementation for User Story 2

- [X] T025 [US2] Make the PUT atomic in `api/app/insights/routes/dashboards.py`: if any validation fails, the request applies nothing. Run every validation before the first `setattr`. Add `logger.info("Dashboard status changed: id=%s %s → %s by user=%s", …)` on a real change.
- [X] T026 [P] [US2] Add i18n keys `dashboard_detail_modal.status_hint_create` ("New dashboards start as Draft"), `status_hint_locked_retired` ("Retired dashboards are closed"), `status_hint_locked_unknown` and `status_transition_refused` to both `ui/src/i18n/en.json` and `ui/src/i18n/es.json`.
- [X] T027 [US2] Implement the status policy in `ui/src/components/ana/DashboardDetailModal.astro`, mirroring `applyStatusPolicy` in `ui/src/components/lib/AssetDetailModal.astro`.
  - In create mode, lock the control to DRAFT with `status_hint_create`.
  - In edit mode, hide and disable every option not in the row's `allowed_statuses`, and lock the control with the matching hint when only one remains.
  - Run the policy before taking the dirty-check snapshot, and again after a successful save using the returned `allowed_statuses`.
  - Show the server's 400 message through `apiErrorDetail()` in a toast.
- [X] T028 [US2] Run `pytest -q tests/test_ana_status.py tests/test_ana_dashboards.py` and `bun run build`, then do quickstart scenario 3 manually.

**Checkpoint**: US1 and US2 work independently. Drafts can be published and obsolete dashboards retired.

---

## Phase 5: User Story 3 — Declare a dashboard's parameters (Priority: P2)

**Goal**: a Parameters tab to add, edit and remove parameters with a validated default, an
allowed-values list and a grant binding. The value source is shown explicitly (FR-014–FR-018a).

**Independent test**: quickstart scenarios 4 and 5 (binding part). The tab shows exactly the saved
set, and no other tab changes.

### Tests for User Story 3 (write first)

- [X] T029 [P] [US3] Write `api/tests/test_ana_parameters.py`.
  - **GET**: VIEW → 200 with active parameters only, ordered, with `value_source` derived as GRANT/LIST/INPUT and `binding_label` set (e.g. "TEAM ANALYTICS"); no grant → 403.
  - **POST**:
    - MANAGE → 201.
    - Active duplicate name → 409.
    - Inactive duplicate → 200, reactivated with the new values.
    - Bad name (`Date From`, `1x`, over 100 characters) → 400.
    - Unknown `data_type` → 400.
    - Default checked against its type → 400: NUMBER `abc`, BOOLEAN `yes`, DATE `2026-13-01` and DATE `01/01/2026` all fail, while NUMBER `1.5`, BOOLEAN `true` and DATE `2026-01-01` are accepted.
    - `list` unknown, inactive or not `LIST_OF_VALUES` → 400.
    - Default not in the list → 400, a default in the list → 201.
    - `context_binding` that belongs to another dashboard, is revoked, is PUBLIC or does not exist → 400; a live TEAM grant of the same dashboard → 201.
    - VIEW → 403.
  - **PUT /{name}**:
    - Partial update.
    - A changed `data_type` re-validates the stored default → 400 when it no longer parses.
    - Setting `list` to null keeps a binding; setting `context_binding` to null with a list set gives `value_source` = LIST.
    - `name` in the body is ignored or rejected.
    - Missing → 404.
  - **DELETE /{name}**: logical, after which the parameter is gone from GET.
- [X] T030 [P] [US3] Write `api/tests/test_ana_parameter_lists.py`: `GET /api/dashboards/parameter-lists` returns only active `LIST_OF_VALUES` lists ordered by name; without `ANA/DASHBOARDS` → 403; 401 without a token.

### Implementation for User Story 3

- [X] T031 [P] [US3] Create `api/app/insights/internal/parameter_validation.py` (all checks raise `ValueError`).
  - `NAME_RE = ^[a-z][a-z0-9_]*$`.
  - `validate_name(name)`.
  - `validate_default(data_type, default, allowed_values: Optional[set])`: uses `decimal.Decimal` for NUMBER, `{"true","false"}` for BOOLEAN, and `date.fromisoformat` with a strict `YYYY-MM-DD` pattern for DATE.
  - `validate_list(session, code)`: the code must be an active `lists` row with `type == "LIST_OF_VALUES"`; returns its value set.
  - `validate_binding(session, dashboard_id, permission_id)`: the grant must exist, belong to the same dashboard, not be revoked (`permissions_service.is_revoked`) and have `target_type != "PUBLIC"`.
  - `value_source(param)`: GRANT if `context_binding`, else LIST if `list`, else INPUT.
  - `validate_parameter(session, dashboard_id, merged_fields)`: runs every check on the final merged state. `data_type` goes through `app/internal/list_values.validate_list_value(session, "PARAM_TYPE", …)`.
- [X] T032 [US3] Implement `api/app/insights/routes/parameters.py`, per [contracts](contracts/dashboards-api.md#parameters--apiappinsightsroutesparameterspy).
  - `GET /{dashboard_id}/parameters` (VIEW): build `ParameterRead` with `binding_label` from ONE batched `select(DashboardPermission).where(id.in_(binding_ids))`, formatted `"{target_type} {target_code}"`.
  - `POST /{dashboard_id}/parameters` (MANAGE): an inactive row with the same name is reactivated (overwrite fields, `is_active=True`, return 200 via `Response.status_code`); otherwise create and return 201.
  - `PUT /{dashboard_id}/parameters/{name}` (MANAGE): `exclude_unset`, merge, validate, set `updated_at`.
  - `DELETE /{dashboard_id}/parameters/{name}` (MANAGE): logical.
  - Missing or inactive dashboard → 404.
- [X] T033 [US3] Add `GET /parameter-lists` to `api/app/insights/routes/dashboards.py`, declared before `/{dashboard_id}`. It is gated `ANA/DASHBOARDS` read and returns `ListOption[]` built from `admin.internal.models.List` rows (check the actual class name in `api/app/admin/internal/models.py`) where `type == "LIST_OF_VALUES"` and `is_active`, ordered by name.
- [X] T034 [P] [US3] Create `ui/src/lib/dashboard_parameters.ts` with `getParameters(dashboardId)`, `createParameter(dashboardId, body)`, `updateParameter(dashboardId, name, body)` and `deleteParameter(dashboardId, name)` (URL-encode `name`). Also add `getParameterLists()` to `ui/src/lib/dashboards.ts`.
- [X] T035 [P] [US3] Add i18n keys to both `ui/src/i18n/en.json` and `ui/src/i18n/es.json`:
  - `dashboard_detail_modal.param_*`: the column headers name/label/type/required/default/source, the form labels, the value-source options `param_source_grant` ("Bound to a grant"), `param_source_list` ("From a list") and `param_source_input` ("Entered by the viewer"), and the binding sentence template (`param_binding_label`: "Bound to the grant for {type} {code}: value fixed for viewers who reach the dashboard through it").
  - Errors: duplicate, bad name, bad default per type, default not in list, missing fields.
  - `param_name_immutable_hint`, add/edit/remove buttons, `save_parameters`, and the empty state.
- [X] T036 [US3] Create `ui/src/components/svelte/DashboardDetailTabs.svelte` (Svelte 5 runes), mounted by `DashboardDetailModal.astro` into the Parameters/Permissions panel shells the way `InitiativeDetailModal.astro` mounts `InitiativeDetailTabs`. Expose `hydrate(dashboardId, myAccess)`, `reset()`, `parametersDirty()`, `flushParameters(dashboardId)` and `onTabChange`.
  - **Parameters tab**:
    - A list of staged parameters; each row shows the source label and the binding sentence.
    - An add/edit form with name (disabled when editing, with `param_name_immutable_hint`), label, data type, required switch, and a value-source radio group (grant / list / input).
    - Source *grant* shows a grant `<select>` built from `getDashboardPermissions` (non-PUBLIC live grants only, labelled with resolved target names using the same target loaders as initiatives). It also shows an optional fallback list picker, per the spec assumption.
    - Source *list* shows a list `<select>` from `getParameterLists()`.
    - The default control depends on type and list: a date input for DATE, a number input for NUMBER, a true/false select for BOOLEAN, a select of the chosen list's values (via `getListItems` + `toListOptions` under `langTick`) when a list is set, and free text otherwise.
    - Client-side validation mirrors T031.
  - `flushParameters` diffs the staged set against the loaded set: POST for added, PUT for changed, DELETE for removed. It surfaces each 4xx through `apiErrorDetail` and stops on the first failure, so state stays consistent. Then it reloads.
  - Read-only when `myAccess === "VIEW"`.
- [X] T037 [US3] Wire the Parameters tab into `ui/src/components/ana/DashboardDetailModal.astro`. When the Parameters tab is active, the footer save button is labelled `save_parameters` and calls `tabs.flushParameters(id)` only (core fields are untouched). Include `parametersDirty()` in the close-confirm check, and enable the tab only in edit mode.
- [X] T038 [US3] Run `pytest -q tests/test_ana_parameters.py tests/test_ana_parameter_lists.py` and `bun run build`, then do quickstart scenario 4 and the parameter half of scenario 5.

**Checkpoint**: parameters can be fully declared. US1, US2 and US3 each work on their own.

---

## Phase 6: User Story 4 — Grant and revoke access to a dashboard (Priority: P2)

**Goal**: a Permissions tab to grant View/Manage to a user, role, project, team, unit or everyone
with a validity window, and to revoke a grant (revoke = end now) (FR-019–FR-022).

**Independent test**: quickstart scenario 6 and the revoke half of scenario 5. A recipient
sees the dashboard, a revoke removes access, and the grant stays recorded.

### Tests for User Story 4 (write first)

- [X] T039 [P] [US4] Write `api/tests/test_ana_permissions.py`.
  - **POST**:
    - MANAGE → 201.
    - PUBLIC stores `target_code="ALL"`.
    - Unknown dashboard → 400.
    - `target_type` or `access_level` outside its list → 400.
    - `valid_to <= valid_from` → 400.
    - A live duplicate → 409, while a revoked duplicate is accepted (201).
    - VIEW caller → 403 (no self-escalation).
    - A future-dated grant is listed but does not grant access yet.
  - **PUT**: changes `access_level` or the window; a revoked grant → 400; VIEW → 403.
  - **DELETE**:
    - `valid_to` set to about now, and the row is still in the DB.
    - Already revoked → 400.
    - A future `valid_to` is overwritten.
    - `bound_parameters` lists the active parameters bound to the grant, and the binding is kept.
    - The recipient loses access immediately: `/with-access` and `GET /{id}` → 403.
  - **End to end**: MANAGE + VIEW for the same user → MANAGE; revoking your own last MANAGE leaves you with VIEW or no access.

### Implementation for User Story 4

- [X] T040 [US4] Add `POST /`, `PUT /{permission_id}` and `DELETE /{permission_id}` to `api/app/insights/routes/dashboard_permissions.py`, copied from `api/app/inits/routes/init_permissions.py`. On top of that copy:
  - Validate `target_type`/`access_level` with `validate_list_value` (`TARGET_TYPE`/`ACCESS_LEVEL`).
  - Force `target_code="ALL"` when `target_type == "PUBLIC"`.
  - DELETE returns `RevokedDashboardPermission` with `bound_parameters`: the sorted names of active `Parameter` rows where `context_binding == permission_id`, from one query.
  - Log with `logger.info` on create and revoke.
- [X] T041 [P] [US4] Add `createDashboardPermission(body)`, `updateDashboardPermission(id, body)` and `revokeDashboardPermission(id)` to `ui/src/lib/dashboard_permissions.ts`. `revokeDashboardPermission` returns a `RevokedDashboardPermission`.
- [X] T042 [US4] Extract the Permissions tab into a shared island, `ui/src/components/svelte/PermissionsTab.svelte`.
  - Move the permissions markup, staged state (`stagedPermissions`, `permType`/`permCode`/`permAccess`, `permCodeOptions`, `permError`), `TARGET_LOADERS`/`targetOptions`/`resolveTargetLabel`, the duplicate check, the window validation, the self-revoke warning and the diff flush out of `ui/src/components/svelte/InitiativeDetailTabs.svelte`.
  - Props: `resourceId: number | null`, `api: { list(id), create(body), update(id, body), revoke(id) }`, `resourceKey: string` (body key, `"init"` | `"dashboard"`), `i18nPrefix: string` (defaults to `"initiative_detail_modal"`), `readonly: boolean`, `currentUserId`, an `onRevokeWarning?: (grant) => string | null` hook for extra confirm text, and `onDirtyChange`.
  - Exported functions: `hydrate(id)`, `reset()`, `dirty()`, `flush(id)` and `count()`.
  - Keep every i18n key name and every DOM id the initiatives page relies on.
- [X] T043 [US4] Refactor `ui/src/components/svelte/InitiativeDetailTabs.svelte` to render `<PermissionsTab bind:this=… api={initPermissionsApi} resourceKey="init" i18nPrefix="initiative_detail_modal" …/>`. Its existing exported methods (`permissionsDirty`, the flush path used by `InitiativeDetailModal.astro`, tab counts) delegate to the child, so `InitiativeDetailModal.astro` needs no change. Afterwards, walk through the initiative Permissions tab manually (grant, revoke, duplicate, self-revoke warning) to confirm nothing changed. **Fallback**: if parity cannot be reached, revert T042/T043, give `DashboardDetailTabs` a local copy, and add a row to the plan's Complexity Tracking.
- [X] T044 [P] [US4] Add `dashboard_detail_modal.perm_*` keys to both `ui/src/i18n/en.json` and `ui/src/i18n/es.json`, mirroring `initiative_detail_modal.perm_*`: target type, target, access, valid from/to, public, add, revoke, revoked/expired/not-yet-in-effect badges, duplicate, window error, missing fields, self-revoke warning and `save_permissions`. Also add `perm_revoke_bound_warning` ("This grant is used by the parameter(s) {names}; their binding will stop applying.").
- [X] T045 [US4] Mount `PermissionsTab` inside `ui/src/components/svelte/DashboardDetailTabs.svelte` for the Permissions panel, with `api` = the `lib/dashboard_permissions.ts` functions, `resourceKey="dashboard"` and `i18nPrefix="dashboard_detail_modal"`. Its `onRevokeWarning` returns `perm_revoke_bound_warning` when any staged parameter's `context_binding` equals the grant id (US4-7). After a permissions flush, re-hydrate the Parameters tab so the grant options and binding labels refresh.
- [X] T046 [US4] Wire the Permissions tab into `ui/src/components/ana/DashboardDetailModal.astro`. When the Permissions tab is active, the footer save is labelled `save_permissions` and calls the permissions flush only. Include its dirty state in the close-confirm check. After a flush, call `getDashboard(id)`: if it now returns 403 (the owner revoked their own access), close the dialog and remove or refresh the row.
- [X] T047 [US4] Run `pytest -q tests/test_ana_permissions.py tests/test_inits_permissions.py` and `bun run build`, then do quickstart scenarios 5 (revoke half) and 6, plus a regression pass on the initiative Permissions tab.

**Checkpoint**: all four stories work. The analytics inventory is governed end to end.

---

## Phase 7: Polish & cross-cutting concerns

- [X] T048 Run the full suite with `docker compose exec -T api uv run pytest -q`. Expect the 570 baseline plus the new tests, with 0 failures. Also run `make test`.
- [X] T049 [P] Run `cd ui && bun run build` (clean) and `astro check` (no new errors beyond the baseline, apart from the known "Svelte file is not a module" line per new Svelte import).
- [ ] T050 Walk through the full quickstart (scenarios 1–8) as `felipe.cardenas` and `admin`, with the language switched to Spanish once. Then run the cleanup section.
- [X] T051 [P] Update `docs/user-stories/06-ana.md`: mark HU-AN01/02/03 as implemented, document the status transitions, the three parameter value sources and the parameters-window hand-off to HU-AN05, and update the `insights` domain note.
- [X] T052 [P] Update the stub domain lists. `insights` moves from stub to partial (Dashboard Management) in `AGENTS.md` ("What this is" paragraph), `api/AGENTS.md`/`api/CLAUDE.md` (domain list) and `.specify/memory/constitution.md` only if it lists `insights` as a stub. The constitution change is a PATCH wording fix; record it in its Sync Impact Report.
- [X] T053 Update `memory/MEMORY.md`:
  - Feature status: a "Dashboard Management (HU-AN01–03, SpecKit 006)" row as ✅, and `insights` in the "In progress / stubs" table moved to partial.
  - Decisions log: a 2026-10-01 row with the lifecycle rules, the derived value source (GRANT/LIST/INPUT) and the parameters-window hand-off, the third binding of `resource_permissions`, the `list_values` hoist, the `PermissionsTab` extraction, `/parameter-lists` (ADMINISTRATIVE lacks `ADMIN/LISTS`) and the provisioned-DB script.
  - Update the backend tests baseline.
- [X] T054 Add ONE rollup entry at the top of `memory/CHANGELOG.md` in the `## YYYY-MM-DD HH:MM — …` format (get the time with `date '+%Y-%m-%d %H:%M'`), covering the whole branch and listing the files affected. If an entry for this branch already exists, update it.

---

## Phase 8: Amendment (2026-10-02): favorites, permissions without dates, compact Parameters form

**Purpose**: the three changes the user asked for after the first implementation
(spec "Amended" note, research R14).

- [X] T055 [US1] Amend `specs/006-dashboard-management/spec.md`:
  - US1 gains scenarios 12–14 (favorites) and a "my favorites" filter, with FR-004/FR-004a and a Favorite dashboard entity.
  - US4 drops validity dates: scenarios 1–2 rewritten, the date-window scenario removed, and FR-019/FR-021 updated.
  - US3 gains scenario 12 (a compact form keeps the list in view).
  - The scope note now includes the management-side half of HU-AN06.
  - Mirror the changes in `research.md` (R14), `data-model.md`, `contracts/dashboards-api.md`, `quickstart.md` (scenario 7a and amended 4/6) and `plan.md`.
- [X] T056 [P] [US1] Write `api/tests/test_ana_favorites.py`:
  - mark and clear a favorite, and `is_favorite` on the list and single GET
  - logical removal and re-mark restores the row; calls are idempotent
  - favorites are personal
  - VIEW suffices, no grant → 403, missing/inactive → 404, no RBAC → 403
- [X] T057 [US1] Map `favorite_dashboards` in `api/app/insights/internal/models.py`: `FavoriteDashboard(table)` + `DashboardFavoriteState`, and `DashboardWithAccess.is_favorite`.
- [X] T058 [US1] Add favorites to `api/app/insights/routes/dashboards.py`: `_favorite_ids` (one batched query), `is_favorite` on `/with-access` and `GET /{id}`, and `PUT`/`DELETE /{dashboard_id}/favorite`. These are a copy of `inits/routes/initiatives.py:_set_favorite`, gated `ANA/DASHBOARDS` read + VIEW.
- [X] T059 [P] [US1] Add `setDashboardFavorite(id, on)` to `ui/src/lib/dashboards.ts` and `is_favorite` to `DashboardWithAccess` in `ui/src/types/api.ts`.
- [X] T060 [US1] Wire favorites into `ui/src/pages/ana/dashboards.astro`:
  - Rows get a `favorite` "yes"/"no" field.
  - Filter slot 3 becomes the *My favorites* toggle, and source moves to `extraFilters` (the `/inits/initiatives` layout).
  - Pass `favoriteAction` + `favoriteKey`.
  - Add the capture-phase star handler with optimistic repaint and a `datatable:row-update`, plus the `favorite:changed` listener.
  - The opener passes `data-favorite`.

  In `ui/src/components/ana/DashboardDetailModal.astro`, add the header star (hidden while creating). It saves at once, syncs from the server on open, and dispatches `favorite:changed` on close.
- [X] T061 [US4] Remove the validity window from the Permissions UI:
  - Drop the `withWindow` mode from `ui/src/components/svelte/PermissionsTab.svelte` (it is again exactly the initiative tab) and its use in `DashboardDetailTabs.svelte`.
  - Delete the six `dashboard_detail_modal.perm_valid_* / perm_window_* / perm_not_yet / perm_until` keys from both i18n files.
  - The backend keeps accepting the optional keys.
- [X] T062 [US3] Compact the Parameters form in `ui/src/components/svelte/DashboardDetailTabs.svelte` to two rows plus one help line:
  - Row 1: name · label · type · required · add.
  - Row 2: a source segmented control + binding / list / default.
  - The name hint and source help move to tooltips, and the help line shows only the active source.
- [X] T063 Verify and record:
  - Suite 670 passed / 0 failed, `bun run build` clean.
  - Live check as felipe: mark/clear through the API, `is_favorite` on the list, three row stars plus the *My favorites* toggle server-side rendered. The test favorite was cleared afterwards.
  - Update `docs/user-stories/06-ana.md`, `memory/MEMORY.md` and the branch's existing `memory/CHANGELOG.md` entry.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies. T001–T004 all run in parallel.
- **Foundational (Phase 2)**: needs T004 for its tests.
  - T005 first: T009 imports from it.
  - T006 before T007, T010 and T011.
  - T008, T009, T012 and T013 run in parallel once T005 and T006 are done.
  - T014 last.
  - **Blocks every story.**
- **US1 (Phase 3)**: after Phase 2.
- **US2 (Phase 4)**: after Phase 2. Its UI task T027 edits the modal created in T020, so in practice it runs after US1. The backend (T024/T025) can start right after T017.
- **US3 (Phase 5)**: after Phase 2. It reads grants through T010/T013 (foundational), so it does **not** wait for US4. UI tasks T036/T037 need the modal from T020.
- **US4 (Phase 6)**: after Phase 2. T045 mounts into the island created in T036. If US4 is done before US3, T045 creates `DashboardDetailTabs.svelte` with only the Permissions panel and T036 extends it.
- **Polish (Phase 7)**: after the stories you intend to ship.

### Story dependency graph

```text
Setup ─► Foundational ─┬─► US1 (MVP) ─┬─► US2 (status UI)
                       │              ├─► US3 (Parameters tab UI)
                       │              └─► US4 (Permissions tab UI)
                       └─► backend of US2 / US3 / US4 can start in parallel right after Foundational
```

### Within each story

Tests are written first and must fail. Then come services and validation, then routes, then the
UI service, then i18n, then components, then verification.

## Parallel Examples

### Phase 1

```text
T001 db/sql/61-ana-ddl.sql · T002 provisioned-db.sql · T003 test-owner.sql · T004 api/tests/ana_helpers.py
```

### User Story 1

```text
T015 tests/test_ana_dashboards.py · T016 source_validation.py · T018 lib/dashboards.ts · T019 i18n
then T017 routes → T020 modal → T021 page → T022 sidebar label → T023 verify
```

### User Story 3

```text
T029 test_ana_parameters.py · T030 test_ana_parameter_lists.py · T031 parameter_validation.py ·
T034 lib/dashboard_parameters.ts · T035 i18n
then T032 + T033 routes → T036 island → T037 modal wiring → T038 verify
```

### User Story 4

```text
T039 test_ana_permissions.py · T041 lib/dashboard_permissions.ts · T044 i18n
then T040 routes; T042 → T043 (extraction + initiative regression) → T045 → T046 → T047
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup, then Phase 2 Foundational.
2. Phase 3 (US1): the inventory with create, edit and remove. New dashboards stay Draft, and the
   PUT already refuses disallowed status moves because it calls `status_service` from T017.
3. **Stop and validate** with quickstart scenarios 1, 2 and 7.

### Incremental delivery

1. US1, the MVP inventory.
2. US2: the lifecycle UI and atomic PUT, so dashboards can be published and retired.
3. US3: parameters. Execute (HU-AN05) is unblocked from here.
4. US4: the permissions UI, which also brings the shared `PermissionsTab`.
5. Polish: docs, memory and the changelog.

## Implementation notes (2026-10-01)

- **Verified**:
  - Backend suite: 663 passed, 0 failed. That is 93 new `test_ana_*` tests, with `test_inits_*` unchanged and green.
  - `make test` is green and `bun run build` is clean.
  - `astro check` adds only the known "Svelte file is not a module" line for the new island import.
  - A 24-check live API smoke as `felipe.cardenas` (after `test-owner.sql`) and `admin` covered quickstart scenarios 1–7 at the API level.
  - A server-side fetch of `/ana/dashboards` showed 3 rows, a pencil only on the MANAGE row and the New button.
  - The smoke dashboard was logically removed afterwards.
- **T050 is still open.** There is no browser harness here, so two things need a manual pass:
  - The dialog click-through: create → edit switch, status control, Parameters form, Permissions window, discard dialog and the language switch.
  - A regression pass on the **initiative** Permissions tab, which T043 refactored.
- **Deviations from the task text**:
  - T021: "New Dashboard" is always shown. The UI has no client-side privilege lookup, and the page is only reachable with `ANA/DASHBOARDS`, which every seeded holder has with edit rights. The backend still refuses a create without edit rights (403).
  - T021: `manageKey` leaves VIEW rows without an open action, so the name cell now opens the dialog for every row. This needed an additive `data-row-id` on the `DataTableBody.astro` rows.
  - T022: `menu_options.dashboards` was wrong ("Dashboard Catalog"). It is now "Dashboard Management", and `menu_options.catalog` was added for the future Catalog page.
  - T029/T032: the length limits on parameter name and label moved from the pydantic model to the validator, so over-long values answer 400 instead of a bare 422.
  - T046: after a permissions save, the dialog re-reads the dashboard. If the caller dropped to VIEW, they see it read-only. If they lost access entirely, they get a notice and the dialog closes.
  - Quickstart scenario 1 was corrected: the seed grants dashboards 1 and 3 to PUBLIC/VIEW, so felipe sees all three.

## Notes

- 54 tasks in total. `[P]` means a different file with no dependency on an incomplete task.
- No DDL. If implementation seems to need a column, stop: the value source is derived on
  purpose (research R6).
- Never prove an access rule as the superuser alone. Use `felipe.cardenas` with `test-owner.sql`.
- Commit after each phase checkpoint. The changelog entry (T054) is one rollup for the branch.
