---
description: "Task list for Initiative Management"
---

# Tasks: Initiative Management

**Input**: Design documents from `specs/004-initiative-management/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/initiatives-api.md](contracts/initiatives-api.md),
[quickstart.md](quickstart.md)

**Tests**: REQUIRED. Constitution Principle III mandates automated tests for contract,
permission and status-transition changes; plan.md § Constitution Check lists them. UI behaviour
is verified manually (no browser harness) per quickstart.md.

**Organization**: Tasks are grouped by user story so each can be implemented and verified on its
own. Decision references (R1–R12) point to research.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 from spec.md
- Paths are relative to the repository root

## Path Conventions

- API: `api/app/{internal,lib,inits}/…`, tests in `api/tests/`
- UI: `ui/src/{pages,components,lib,types,i18n}/…`
- DB seeds: `db/sql/`

## Conventions every task must follow

- API routes return bare models / raise `HTTPException`; the global middleware adds the
  `{data,error,meta}` envelope. Literal routes (`/with-access`, `/init/{id}`) are declared before
  `/{id}` routes.
- Every list endpoint takes `skip: int = Query(0, ge=0)`, `limit: int = Query(100, ge=1, le=500)`.
- Authorization is layered: `require_privilege("INITS","INITIATIVES", can_edit=…)` (or
  `check_any_privilege(session, user, "INITS", ["INITIATIVES","EXPLORE"])` for per-init reads) is
  the outer gate; `require_init_manage` / `require_init_view` → 403 is the inner gate. Superusers
  bypass both.
- Tests use the `session`/`client` fixtures in `api/tests/conftest.py` and per-file helpers in the
  style of `api/tests/test_lib_access_enforcement.py` (`_user`, `_override`, `_seed_privileges`,
  `_mk_perm` with `NOW/PAST/FUTURE`). Run: `docker compose exec -T api uv run pytest -q`.
- Every user-facing string goes in BOTH `ui/src/i18n/en.json` and `ui/src/i18n/es.json`.
- Svelte islands are mounted manually with `mount()` from a bundled `<script>` (never
  `client:*`); Svelte template comments use `<!-- -->`.

---

## Phase 1: Setup

**Purpose**: record baselines so regressions are measurable.

- [X] T001 Record the baselines in the PR notes: run `docker compose exec -T api uv run pytest -q` (expect 8 pre-existing failures in `api/tests/test_auth.py`, `test_health.py`, `test_users.py`) and `cd ui && bunx astro check` (expect the 138-error baseline); confirm the branch is `004-initiative-management`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: seeds, models, the shared permission engine and the `inits` access service. Every
user story depends on these.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

### Seeds (R10, data-model §3–§4)

- [X] T002 [P] In `db/sql/51-inits-ddl.sql`: add `('COLLAB_TYPE','en','KICKOFF','Kickoff',55)` to the COLLAB_TYPE block, and add `lang='es'` rows (separate `INSERT INTO list_items` blocks after each English block, same pattern as the criteria lists at the end of the file) for `INITIATIVE_STATUS` (Activada, Retroalimentación, Aceptada, Rechazada, En progreso, Entregada, Archivada), `COLLAB_TYPE` (all 12 values; `KICKOFF` → "Arranque"; keep the same `sort_order`s), `EXPECTED_IMPACT`, `PRIORITY_LEVEL`, `INITIATIVE_TYPE`
- [X] T003 [P] In `db/sql/52-inits-insert.sql`: set initiative statuses 1 `IN_PROGRESS`, 2 `DELIVERED`, 3 `ACCEPTED`, 4 `ACTIVATED`, 5 `ACTIVATED` and give each a `type` (`INITIATIVE_TYPE` value); add `UPDATE users SET profile='ADMINISTRATIVE' WHERE username='felipe.cardenas';` to `db/sql/32-collab-insert.sql` (next to the REVIEWER promotion) and put his test `init_permissions` rows in `specs/004-initiative-management/test-owner.sql` (NOT the seed — with `target_type='USER'` and `target_code=(SELECT id::text FROM users WHERE username='felipe.cardenas')` giving MANAGE on inits 1 and 3 and VIEW on init 2 (none on 4–5). Keep the existing grants, including PUBLIC/VIEW on init 1 (felipe's MANAGE on init 1 wins over it)
- [X] T004 Apply the seed changes from `db/sql/51-inits-ddl.sql` and `db/sql/52-inits-insert.sql` to the local stack with `make rebuild`, then verify via `make shell`: `SELECT id,status,type FROM initiatives;`, `SELECT * FROM list_items WHERE list='COLLAB_TYPE' AND value='KICKOFF';`, `SELECT * FROM init_permissions;` — *done by applying the one-off SQL (T053) to the running dev DB instead of `make rebuild`, which would have wiped the local volume*

### Shared plumbing (R2, R3)

- [X] T005 [P] Create `api/app/internal/status.py` with `normalize(status: Optional[str]) -> str` (strip, upper-case, remove a leading `^\d+-` sort prefix) moved from `api/app/lib/internal/status_service.py`; make the lib module import and re-export it so `status_service.normalize` still works
- [X] T006 Create `api/app/internal/resource_permissions.py` by extracting the resource-agnostic logic from `api/app/lib/internal/permissions_service.py`: `SCOPE_*`/`ACCESS_*` constants, `_as_naive_utc`, `is_valid_now(valid_from, valid_to, now)`, `resolve_user_scopes(session, user)`, and model-parameterised `not_revoked_clause(model, now=None)`, `is_revoked(grant, now=None)`, `matching_grants(session, user, model, fk_col, ids=None)` (one SQL query OR-ing PUBLIC with each `(target_type, target_code IN codes)`, optional `fk_col.in_(ids)`, then Python `is_valid_now` filter), `effective_levels(grants, fk_attr) -> Dict[int,str]` (MANAGE wins), and `user_scopes_for(session, user, model, fk_col, ids)` (the generalised `assets_user_scopes`)
- [X] T007 Refactor `api/app/lib/internal/permissions_service.py` into thin wrappers over `resource_permissions` bound to `AssetPermission` / `AssetPermission.asset`, keeping every public name and signature unchanged (`not_revoked_clause`, `is_revoked`, `resolve_user_scopes`, `assets_user_access`, `accessible_assets`, `user_asset_access`, `require_asset_manage`, `AssetAccessForbidden`, `assets_user_scopes`, and the `_as_naive_utc`/`_is_valid_now` names if any test imports them)
- [X] T008 Run `docker compose exec -T api uv run pytest -q api/tests/test_lib_permissions.py api/tests/test_lib_access_enforcement.py api/tests/test_assets_access.py api/tests/test_assets_category_with_access.py` — all must pass unchanged; fix the refactor, never the tests

### Models (data-model §1)

- [X] T009 Add to `api/app/inits/internal/models.py`: `Collaboration` (table `collaborations`, fields per data-model §1, `id` identity PK, FKs to `initiatives.id`, `users.id`, self `parent`), `InitPermission` (table `init_permissions`, no `is_active`) + `InitPermissionCreate` (`init`, `target_type`, `target_code`, `access_level`, optional `valid_from`/`valid_to`) + `InitPermissionUpdate` (optional `access_level`, `valid_from`, `valid_to`), `Diagnostic` (table `diagnostics`, composite PK `init`+`criteria`), `FavoriteInit` (table `favorite_inits`, composite PK `user_id`+`init`), `InitiativeUpdate` (all optional: `name`, `description`, `type`, `expected_impact`, `priority_level`, `reference`, `tags: Optional[List[str]]`, `detail`, `status`), `InitiativeWithAccess(InitiativeBase)` + `id`, timestamps, `my_access: str`, `is_favorite: bool`, `allowed_statuses: List[str]`, `DiagnosticRow` + `DiagnosticsResponse{init, score, items}`, `InitiativeAsset` (+ `InitiativeAssetCreate{asset, type, rationale?}`), `InitDiscussionItem` (same fields as lib `DiscussionItem` with `init` instead of `asset`). Import `HistoryEntry` from `app.lib.internal.models` for history responses; update the module docstring that says the domain is read-only
- [X] T010 Confirm the new tables are created by `SQLModel.metadata.create_all` in the test fixture: ensure `api/app/inits/internal/models.py` is imported where the test app loads models (it already is via `api/app/main.py` routers); add a smoke test `api/tests/test_inits_models.py` that inserts and reads back one row of each new model on the SQLite `session`

### Initiative access service (R3, data-model §1 InitPermission)

- [X] T011 Create `api/app/inits/internal/permissions_service.py` over `resource_permissions` bound to `InitPermission` / `InitPermission.init`: `class InitAccessForbidden(Exception)`, `inits_user_access(session, user, init_ids) -> Dict[int,str]`, `accessible_inits(session, user) -> Dict[int,str]`, `user_init_access(session, user, init_id) -> Optional[str]`, `require_init_manage(session, user, init_id)`, `require_init_view(session, user, init_id)` (superuser bypass first; VIEW satisfied by VIEW or MANAGE)
- [X] T012 [P] Write `api/tests/test_inits_permissions_service.py`: MANAGE beats VIEW; future `valid_from` grants nothing; past `valid_to` grants nothing; PUBLIC grants VIEW to anyone; ROLE/TEAM/UNIT/PROJECT scopes match through collab assignments (reuse the `_mk_assignment`/`_mk_project` helper style of `api/tests/test_lib_permissions.py`); superuser bypasses `require_init_manage`/`require_init_view`; non-holder raises `InitAccessForbidden`

### UI shared types

- [X] T013 [P] Add to `ui/src/types/api.ts` (three-interface convention where applicable): `InitiativeWithAccess` (extends `Initiative` with `my_access`, `is_favorite`, `allowed_statuses`), `InitiativeUpdate`, `DiagnosticRow`, `DiagnosticsResponse`, `InitiativeAsset`, `InitiativeAssetCreate`, `InitPermission`, `InitPermissionCreate`, `InitPermissionUpdate`, `InitDiscussionItem`

**Checkpoint**: seeds applied, lib permission suites green, `inits` models + access service tested.

---

## Phase 3: User Story 1 — See and filter the initiatives I am responsible for (Priority: P1) 🎯 MVP

**Goal**: `/inits/initiatives` lists exactly the initiatives the caller can access, with filters
and search, and no way to create one.

**Independent Test**: quickstart.md S1 as `felipe.cardenas` (sees 1, 2, 3 — plus any PUBLIC
ones — with VIEW-only rows lacking edit/delete) and as `admin` (sees all 5); no "New" button.

### Tests for User Story 1 ⚠️

- [X] T014 [P] [US1] Write `api/tests/test_inits_access.py` (list part): `GET /api/initiatives/with-access` returns only granted initiatives for a non-superuser holding `INITS/INITIATIVES`; `[]` with no grants; all active initiatives for a superuser with `my_access="MANAGE"`; inactive initiatives excluded; filtering happens before `skip`/`limit` (seed 5 accessible + 5 inaccessible, `limit=3` returns 3 accessible); `is_favorite` reflects `favorite_inits` for the caller only; `allowed_statuses` equals `[status]` for ACTIVATED; 403 without the module privilege; 401 without a user

### Backend for User Story 1

- [X] T015 [US1] Add `allowed_statuses_for(status) -> List[str]` to a new `api/app/inits/internal/status_service.py` (for now: return `[normalize(status)]`; US3 extends it with real targets) so the list response has a stable shape from US1 onward — *written in full (not a stub); see T046*
- [X] T016 [US1] Implement `GET /api/initiatives/with-access` in `api/app/inits/routes/initiatives.py`, declared before `/{init_id}`: gate `require_privilege("INITS","INITIATIVES")`; superuser → all active; else `accessible_inits` → empty map returns `[]`, otherwise `Initiative.id.in_(ids)`; `order_by(Initiative.name).offset(skip).limit(limit)` (limit ≤ 500); one `IN` query on `FavoriteInit` (`user_id=current.id`, `is_active`) for `is_favorite`; build `InitiativeWithAccess` rows with `my_access` and `allowed_statuses_for(status)`

### Frontend for User Story 1

- [X] T017 [P] [US1] Add `getInitiativesWithAccess(skip = 0, limit = 500)` to `ui/src/lib/initiatives.ts` calling `/api/initiatives/with-access`
- [X] T018 [P] [US1] Add i18n keys to `ui/src/i18n/en.json` and `es.json`: `initiative_modal.{one_title,many_title,edit,delete,empty_message,name,status,type,priority_level,expected_impact,score,access}` (DataTable convention for `i18Item="initiative"`; empty message must NOT invite creating one), `initiative_table.{fav_filter_mine,access_filter_all,access_manage,access_view,page_title,page_subtitle}`
- [X] T019 [US1] Create `ui/src/pages/inits/initiatives.astro` modelled on `ui/src/pages/lib/assets.astro`: breadcrumb `modules.INITS` › `menu_options.initiatives`; SSR fetch `getInitiativesWithAccess()` and `getListItemsbyList` for `INITIATIVE_STATUS`, `INITIATIVE_TYPE`, `PRIORITY_LEVEL`, `EXPECTED_IMPACT`, filtering each list to the current language with `en` fallback (same logic as `langItems()` in `AssetDetailTabs.svelte`) and resolving labels by bare value; columns: name (`as:"title"`, subtitle `updated_at` relative), status (`as:"status"`), type, priority, impact, score, my access; hidden raw columns for filtering; `DataTable` with `tableId="initiatives"`, `i18Item="initiative"`, `showAddButton={false}`, header-funnel filters for status/type/priority/impact (`filterHeaderColumn`…`filter4HeaderColumn` — use the available slots; put the remaining filters in the toolbar), favorites as a toggle (`filterNAsToggle`, value `"yes"`), access level filter (MANAGE/VIEW), `manageKey="can_manage"` (`my_access==="MANAGE"`); no create bridge and no favorite action. Row edit/delete wiring is added in US2 — *type/impact/priority/status as header funnels needed 6 filter slots: added an additive `extraFilters` (slots 5+) prop to the shared DataTable*
- [ ] T020 [US1] Manually verify `specs/004-initiative-management/quickstart.md` S1 against `ui/src/pages/inits/initiatives.astro` (both accounts, both languages) and note the result in the PR — *PARTIAL: automated checks + live API/SSR verification done (as felipe.cardenas, COLLABORATOR, admin); in-browser click-through still pending (no browser harness here)*

**Checkpoint**: US1 is shippable on its own as a read-only, correctly scoped portfolio list.

---

## Phase 4: User Story 2 — Edit an initiative one tab at a time (Priority: P1)

**Goal**: a six-tab edit dialog where Core Fields, Related Assets and Permissions each save only
their own slice, and Diagnosis Questions, Discussion and History are read-only.

**Independent Test**: quickstart.md S2 and the authorization rows of S4.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] Extend `api/tests/test_inits_access.py` (edit part): `PUT /api/initiatives/{id}` updates only sent fields and stamps `updated_at`; 403 for VIEW holder and for no grant; 404 unknown; 400 inactive; 400 blank `name`/`expected_impact`/`priority_level`; 400 unknown `type`/`expected_impact`/`priority_level` value; `score` in body ignored; a changed `status` returns 400 (until US3); same-status body is accepted and writes no collaboration. `DELETE /api/initiatives/{id}`: sets `is_active=False`, 400 when already inactive, 403 for VIEW holder, writes no collaboration
- [X] T022 [P] [US2] Write `api/tests/test_inits_diagnostics.py`: one item per active criterion; an inactive criterion appears only when the initiative has an answer for it; missing diagnostic → null scores/labels; `lang=es` returns Spanish labels; `lang=es` falls back to `en` when an `es` row is missing, then to the raw value; `score` echoed; 403 without VIEW; 404 unknown initiative
- [X] T023 [P] [US2] Write `api/tests/test_inits_initiative_assets.py`: GET lists active links with asset name/category/status; POST creates (201); POST on an active pair → 409; POST on an inactive pair reactivates with the new `type`/`rationale`; unknown/inactive asset → 400; unknown `RELATION_TYPE` → 400; VIEW holder → 403; asset the caller cannot see (no asset grant, not superuser) → 403; DELETE logical, 400 when already inactive, 404 when no link; the link is visible from `GET /api/asset_inits/asset/{asset_id}` (shared record)
- [X] T024 [P] [US2] Write `api/tests/test_inits_permissions.py`: `GET /api/init_permissions/init/{id}` returns live grants incl. future-dated, excludes revoked; POST 201; live duplicate → 409; duplicate of a revoked grant → 201; `valid_to <= valid_from` → 400; PUT partial update, 400 on revoked grant; DELETE sets `valid_to≈now` and keeps the row, overwrites a future `valid_to`, 400 when already revoked; a VIEW holder cannot POST a MANAGE grant for themselves (403); reads require VIEW (403 with no grant)
- [X] T025 [P] [US2] Write `api/tests/test_inits_collaborations.py`: history is newest first, includes a synthetic `CREATED` entry (id null) last, resolves `actor` usernames in one batch, keeps `content` only for COMMENT/QUESTION/ANSWER, excludes inactive rows, honours `skip`/`limit`; discussion returns COMMENT/QUESTION/ANSWER oldest first with `author` and `parent`; both 403 without VIEW, 400/404 for unknown initiative

### Backend for User Story 2

- [X] T026 [US2] Implement `PUT /api/initiatives/{init_id}` and `DELETE /api/initiatives/{init_id}` in `api/app/inits/routes/initiatives.py` per contracts: gate `require_privilege("INITS","INITIATIVES", can_edit=True)`; 404 → `require_init_manage` (map `InitAccessForbidden` to 403 with a local `_ensure_manage`) → 400 if inactive; for PUT, `model_dump(exclude_unset=True)`, reject blank required fields, validate `type`/`expected_impact`/`priority_level` against `list_items` values of their lists (one query), reject a `status` that differs (after `normalize`) from the current one with 400 (placeholder replaced in US3), apply fields, stamp `updated_at`, commit once, return `InitiativeWithAccess`; DELETE is a logical delete — *implemented directly with the final US3 status logic instead of a temporary 400 placeholder; covered by T045*
- [X] T027 [P] [US2] Create `api/app/inits/internal/diagnostics_service.py` with `get_diagnostics(session, init_id, lang) -> DiagnosticsResponse`: three queries (criterias; active diagnostics for the init; `list_items` for the involved lists in `lang` and `en`), row set and ordering per data-model §1 Diagnostic, label fallback `lang → en → str(value)`
- [X] T028 [US2] Add `GET /api/initiatives/{init_id}/diagnostics?lang=` to `api/app/inits/routes/initiatives.py`: `check_any_privilege(session, user, "INITS", ["INITIATIVES","EXPLORE"])` + `require_init_view` (403), 404 unknown initiative
- [X] T029 [P] [US2] Create `api/app/inits/routes/initiative_assets.py` (router prefix `/api/initiatives`, tag `initiative-assets`): `GET /{init_id}/assets` (per-init read gate; join `Asset` for name/category/status; newest first; bounded), `POST /{init_id}/assets` (write gate + init MANAGE; asset must exist and be active; caller must see the asset via `app.lib.internal.permissions_service.user_asset_access` unless superuser → 403; validate `type` against `RELATION_TYPE`; `session.get(AssetInit,(asset, init))` → active 409 / inactive reactivate / none create; 201), `DELETE /{init_id}/assets/{asset_id}` (write gate + MANAGE; logical)
- [X] T030 [P] [US2] Create `api/app/inits/routes/init_permissions.py` (prefix `/api/init_permissions`) mirroring `api/app/lib/routes/asset_permissions.py`: `GET /init/{init_id}` (module read gate + `require_init_view`; `not_revoked_clause`; bounded), `POST /` (write gate; 400 unknown init; `require_init_manage`; 400 invalid window; 409 live duplicate on `(init,target_type,target_code,access_level)`), `PUT /{permission_id}` (MANAGE on `permission.init`; 400 when revoked; partial update), `DELETE /{permission_id}` (MANAGE; revoke `valid_to = utcnow()`; 400 when already revoked)
- [X] T031 [P] [US2] Create `api/app/inits/internal/collaborations_service.py`: constants for COLLAB types (`ACTIVATION`, `DIAGNOSIS`, `MODIFICATION`, `ACCEPTANCE`, `REJECTION`, `KICKOFF`, `DELIVERY`, `ARCHIVING`, `VOTE`, `COMMENT`, `QUESTION`, `ANSWER`), `DISCUSSION_TYPES`, `_HISTORY_SUMMARIES` / `_WORKFLOW_SUMMARIES` English summaries (e.g. KICKOFF → "kicked off the initiative", DELIVERY/HANDLED → "delivered the initiative", ARCHIVING → "archived the initiative", DIAGNOSIS/PENDING → "was asked to diagnose the initiative"), `get_initiative_history(session, init_id) -> List[HistoryEntry]` and `list_discussion(session, init_id) -> List[InitDiscussionItem]`, mirroring `get_asset_history` / `list_discussion` in `api/app/lib/internal/actions_service.py` (batched actor lookup, synthetic CREATED marker from `initiatives.created_at`, sort `(created_at, id or -1)` desc for history, asc for discussion)
- [X] T032 [US2] Create `api/app/inits/routes/collaborations.py` (prefix `/api/collaborations`): `GET /history/init/{init_id}` (slice `[skip:skip+limit]`) and `GET /discussion/init/{init_id}`, both with the per-init read gate; 404 unknown initiative
- [X] T033 [US2] Register the three new routers (`initiative_assets`, `init_permissions`, `collaborations`) in `api/app/main.py` next to the existing `initiatives`/`criterias` includes; make sure `initiative_assets` is included such that `/api/initiatives/with-access` and `/api/initiatives/{init_id}` still resolve (no path collision with `/{init_id}/assets`)
- [X] T034 [US2] Run the US2 test modules (T021–T025) and the full suite; only the 8 baseline failures may remain

### Frontend for User Story 2

- [X] T035 [P] [US2] Extend `ui/src/lib/initiatives.ts`: `updateInitiative(id, data: InitiativeUpdate)`, `deleteInitiative(id)`, `getInitiativeDiagnostics(id, lang)`, `getInitiativeAssets(id)`, `addInitiativeAsset(id, data: InitiativeAssetCreate)`, `removeInitiativeAsset(id, assetId)`
- [X] T036 [P] [US2] Create `ui/src/lib/init_permissions.ts` mirroring `ui/src/lib/asset_permissions.ts`: `getInitPermissionsByInit`, `createInitPermission`, `updateInitPermission`, `deleteInitPermission`
- [X] T037 [P] [US2] Create `ui/src/lib/collaborations.ts`: `getInitiativeHistory(id)` → `/api/collaborations/history/init/{id}`, `getInitiativeDiscussion(id)` → `/api/collaborations/discussion/init/{id}`
- [X] T038 [P] [US2] Parameterise `ui/src/lib/history.ts` `mountHistory(config)`: optional `fetcher?: (id: number) => Promise<HistoryEntry[]>` (default `getAssetHistory`) and `idAttr?: string` (default `"assetId"`, read from the opener's `dataset`); add `KICKOFF`, `DELIVERY`, `ARCHIVING`, `ACTIVATION`, `DIAGNOSIS`, `ACCEPTANCE` to `DOT_COLORS` if absent. Existing asset callers must behave identically
- [X] T039 [P] [US2] Parameterise `ui/src/components/svelte/Foro.svelte`: optional `api` prop (`{ getDiscussion, addComment, addQuestion, addAnswer, deleteParticipation }`, default = the current `lib/foro.ts` functions) and `idAttr` prop (default `"assetId"`); with `readonly`, only `getDiscussion` is required. Existing callers pass nothing and must behave identically — *implemented as `fetchDiscussion` + `idAttr` props (only the read is needed, since initiatives pass `readonly`)*
- [X] T040 [US2] Create `ui/src/components/svelte/InitiativeDetailTabs.svelte`, derived from `ui/src/components/svelte/AssetDetailTabs.svelte` without the characteristics/versions machinery: tabs in order `core`, `diagnosis`, `related`, `permissions`, `discussion`, `history` (`$derived` `tabOrder`, keyboard nav, dirty dots); `core` is an empty shell `#{idPrefix}-core` for the parent to re-parent into; `diagnosis` renders `getInitiativeDiagnostics(id, lang)` read-only as a table (criterion name + description, proposer answer label, reviewer answer label or "pending diagnosis"/"not answered", rationale) plus the overall score; `related` stages links against `getInitiativeAssets` using an asset picker from `getAssetsSelect` and `RELATION_TYPE` via `langItems()`, with diff-`flush` (removals → `removeInitiativeAsset`, additions → `addInitiativeAsset`); `permissions` is the asset Permissions tab re-pointed at `init_permissions.ts` (`init:` payload key, same `TARGET_LOADERS`, revoke semantics) and shows a confirm before revoking the caller's own MANAGE grant; `discussion` nests `<Foro modalId={idPrefix} readonly api={{ getDiscussion: getInitiativeDiscussion }} idAttr="initId" />`; `history` is the `#{idPrefix}-history` shell with `[data-history-status]` and `[data-history-list]`. Exports: `hydrate(id)`, `reset()`, `activateTab(name)`, `setCoreDirty(bool)`, `relationsDirty()`, `permissionsDirty()`, `focusFirstPending()`, `flush(id, { skipRelations, skipPermissions })`; props `idPrefix`, `onError`, `onTabChange`
- [X] T041 [US2] Create `ui/src/components/inits/InitiativeDetailModal.astro`, derived from `ui/src/components/lib/AssetDetailModal.astro` with `modalId` taken from the prop (do not hard-code): header title `initiative_detail_modal.title_edit` + name suffix, favorite indicator read-only, close button; core section with name, type, expected impact, priority, status select + hint, description, reference, tags, detail (list options filtered by language); mount `InitiativeDetailTabs` with `mount()` and re-parent the core section into `#{modalId}-core`; `mountHistory({ modalId, fetcher: getInitiativeHistory, idAttr: "initId" })`; open handler reads `data-init-id` and is a no-op without an id (no create mode); `paintFooterForTab`: diagnosis/discussion/history hide Submit, core/related/permissions show `initiative_detail_modal.save_{core,related,permissions}`; submit saves ONLY the active tab (`core` → `updateInitiative` with the core payload, no-op if unchanged; `related` → `tabs.flush(id,{skipPermissions:true})`; `permissions` → `tabs.flush(id,{skipRelations:true})`), keeps the dialog open and re-snapshots; required fields enforced only while `core` is active; discard-confirm dialog on Cancel/X/Esc when any tab is dirty. Status: in US2 the select shows the current status only and is locked (US3 enables moves)
- [X] T042 [US2] Wire the modal into `ui/src/pages/inits/initiatives.astro`: render `<InitiativeDetailModal modalId="initiative-detail-modal" …/>`; capture-phase listener turning the row pencil (`data-modal-open="initiative-edit-modal"`, `data-id`) into a synthetic trigger `data-modal-open="initiative-detail-modal"` with `data-init-id`; delete via `CrudModal` + `initCrudPage` calling `deleteInitiative` and reloading; VIEW rows open nothing editable (pencil hidden by `manageKey`)
- [X] T043 [P] [US2] Add i18n keys to `ui/src/i18n/en.json` and `es.json`: `initiative_detail_modal.*` (`title_edit`, `core_section`, `tab_core`, `tab_diagnosis`, `tab_related`, `tab_permissions`, `tab_discussion`, `tab_history`, `save_core`, `save_related`, `save_permissions`, `core_saved`, `related_saved`, `permissions_saved`, `no_changes`, `unsaved_indicator`, `discard_*`, `diag_criterion`, `diag_creator`, `diag_reviewer`, `diag_rationale`, `diag_score`, `diag_pending`, `diag_not_answered`, `related_*`, `perm_*`, `perm_self_revoke_confirm`, `error_*`, field labels), and `history.action.{ACTIVATION,DIAGNOSIS,DIAGNOSIS_PENDING,DIAGNOSIS_HANDLED,MODIFICATION,ACCEPTANCE,REJECTION,KICKOFF,DELIVERY,ARCHIVING}` plus `history.action.CREATED` wording for initiatives if the existing one says "asset" (add `history.action.CREATED_INIT` and have the initiative fetcher map `CREATED` → it only if needed)
- [ ] T044 [US2] `cd ui && bun run build && bunx astro check` (no new errors vs. T001 baseline), then manually verify quickstart.md S2 and the API rows of S4; note results in the PR — *PARTIAL: automated checks + live API/SSR verification done (as felipe.cardenas, COLLABORATOR, admin); in-browser click-through still pending (no browser harness here)*

**Checkpoint**: US1 + US2 work; status is visible but locked.

---

## Phase 5: User Story 3 — Record kickoff, delivery and archiving (Priority: P2)

**Goal**: the six owner transitions work end to end and each writes its collaboration; every
other move is refused by the server.

**Independent Test**: quickstart.md S3 (UI table + direct API refusals).

### Tests for User Story 3 ⚠️

- [X] T045 [P] [US3] Write `api/tests/test_inits_status.py`: pure `status_service` tests — `validate_transition` returns `KICKOFF`/`DELIVERY`/`ARCHIVING` for each of the six allowed pairs, `None` for unchanged/blank/omitted, raises `StatusTransitionForbidden` for every other pair across all seven statuses (parametrised full 7×7 matrix), tolerates `N-` prefixes and lower-case; `allowed_statuses_for` per data-model §2. HTTP tests on `PUT /api/initiatives/{id}`: each allowed move changes status and writes exactly one `HANDLED` collaboration of the right type with `user_id` = caller and `content` null; each refused move returns 400 and writes nothing (status unchanged); a core-field-only edit writes nothing; no `PENDING` collaboration is created by any move; `/with-access` and the PUT response expose the correct `allowed_statuses`

### Implementation for User Story 3

- [X] T046 [US3] Complete `api/app/inits/internal/status_service.py`: status constants, `class StatusTransitionForbidden(ValueError)`, `ALLOWED_TRANSITIONS` (six pairs → collab type, data-model §2), `allowed_targets(current)`, `allowed_statuses_for(current)` (current + targets), `validate_transition(current, new) -> Optional[str]`, `log_status_collaboration(session, init_id, user_id, collab_type) -> Collaboration` (adds a `HANDLED` row, never commits); import `normalize` from `api/app/internal/status.py`
- [X] T047 [US3] Replace the US2 status placeholder in `PUT /api/initiatives/{init_id}` (`api/app/inits/routes/initiatives.py`): load the row with `select(Initiative).where(...).with_for_update()` before validating; `validate_transition(row.status, data["status"])` → `StatusTransitionForbidden` = 400 with message `"Status transition X → Y is not allowed"`; `None` → pop `status`; otherwise set the status and `log_status_collaboration(...)` in the same session; single commit (an exception rolls back both)
- [X] T048 [US3] In `ui/src/components/inits/InitiativeDetailModal.astro` implement `applyStatusPolicy(currentStatus, allowed: string[])` from `allowed_statuses` (fetched with the initiative): hide + disable options outside `allowed`; lock the select when `allowed.length < 2`; hint `data-i18n` = `initiative_detail_modal.status_hint_{workflow,closed,moves}` (`closed` when ARCHIVED, `workflow` for other locked statuses, `moves` when a move is available); run it inside reset BEFORE taking the core snapshot and again after a successful core save (using the PUT response's `allowed_statuses`); after a status save, repaint History by re-triggering the history load
- [X] T049 [P] [US3] Add i18n keys `initiative_detail_modal.status_hint_{workflow,closed,moves}` and `initiative_detail_modal.error_status_transition` to `ui/src/i18n/en.json` and `es.json`; confirm `history.action.KICKOFF` = "Kickoff" / "Arranque", `DELIVERY` = "Delivery" / "Entrega", `ARCHIVING` = "Archiving" / "Archivo"
- [ ] T050 [US3] Run T045 + full suite; manually verify quickstart.md S3 as `felipe.cardenas` (initiative 3) and note results in the PR — *PARTIAL: automated checks + live API/SSR verification done (as felipe.cardenas, COLLABORATOR, admin); in-browser click-through still pending (no browser harness here)*

**Checkpoint**: all three stories complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T051 [P] Update `docs/user-stories/states-and-types.md`: initiative status transitions table (replace `IN_PROGRESS → DELIVERED` / `any → ARCHIVED` with the six owner moves and their collaboration types), add `KICKOFF` to the Initiative Collaboration Workflows table and to the `COLLAB_TYPE` row of the catalog table, note the Edit Initiative tab matrix (Diagnosis/Discussion read-only)
- [X] T052 [P] Update `docs/user-stories/05-inits.md` HU-IN03 (kickoff + delivery + archiving, all `HANDLED`, no notices) and `docs/user-stories/inits-status.md` "HU-Edit Initiative" (replace "DELIVERY … PENDING for the creator" with the HANDLED log-only rule and add KICKOFF)
- [X] T053 [P] Add a "Provisioned DBs" section to `specs/004-initiative-management/quickstart.md` with the exact one-off SQL mirroring T002/T003 (KICKOFF insert, `es` list_items inserts, initiative status/type UPDATEs, felipe profile UPDATE, init_permissions inserts), for Neon or a kept local volume
- [X] T054 Security review of the new routes (`api/app/inits/routes/*.py`): every write has the edit-level module gate + `require_init_manage`; every per-init read has `require_init_view`; no route trusts a user id from the body; superuser bypass intact; no secrets/logging changes
- [ ] T055 Full validation: `make test`; `docker compose exec -T api uv run pytest -q` (only baseline failures); `cd ui && bun run build && bunx astro check`; complete quickstart.md S1–S4 as `felipe.cardenas`, a COLLABORATOR and `admin` — *PARTIAL: automated checks + live API/SSR verification done (as felipe.cardenas, COLLABORATOR, admin); in-browser click-through still pending (no browser harness here)*
- [X] T056 Update `memory/MEMORY.md`: decisions-log row (inits no longer read-only; per-resource permission engine moved to `api/app/internal/resource_permissions.py` and shared by lib+inits; `collaborations` as the inits activity substrate; owner transitions + KICKOFF; one link per (asset, init, type) — the same pair once per relation type (amended; see research R13); tab-scoped saves), feature-status row for Initiative Management, Known-blockers P2 `inits` row updated, Tech-snapshot/test baseline if changed
- [X] T057 Add ONE rollup entry at the top of `memory/CHANGELOG.md` (`## YYYY-MM-DD HH:MM — …`, time from `date '+%Y-%m-%d %H:%M'`) covering the whole branch, calling out the architectural decisions and the files affected; update it (not append) on later commits to this branch

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (T001)** → **Foundational (T002–T013)** → user stories → **Polish (T051–T057)**
- Inside Foundational: T002/T003 → T004; T005 ∥ T006 → T007 → T008; T009 → T010, T011 → T012;
  T013 independent

### User story dependencies

- **US1** needs Foundational only.
- **US2** needs Foundational; its UI (T042) extends the US1 page, so US1's T019 must exist first.
  Its backend (T021–T034) is independent of US1's UI.
- **US3** needs US2's PUT (T026) and modal (T041).

### Within each story

Tests first (they must fail), then services/models, then routes, then UI, then manual check.

### Parallel opportunities

- Foundational: T002 ∥ T003; T005 ∥ T006; T012 ∥ T013.
- US1: T014 ∥ T017 ∥ T018.
- US2 tests: T021 ∥ T022 ∥ T023 ∥ T024 ∥ T025. US2 backend: T027 ∥ T029 ∥ T030 ∥ T031 (different
  files), then T028/T032/T033. US2 frontend: T035 ∥ T036 ∥ T037 ∥ T038 ∥ T039 ∥ T043, then
  T040 → T041 → T042.
- US3: T045 ∥ T049.
- Polish: T051 ∥ T052 ∥ T053.

## Parallel Example: User Story 2 tests

```text
T021 api/tests/test_inits_access.py (edit part)
T022 api/tests/test_inits_diagnostics.py
T023 api/tests/test_inits_initiative_assets.py
T024 api/tests/test_inits_permissions.py
T025 api/tests/test_inits_collaborations.py
```

## Parallel Example: User Story 2 frontend services

```text
T035 ui/src/lib/initiatives.ts
T036 ui/src/lib/init_permissions.ts
T037 ui/src/lib/collaborations.ts
T038 ui/src/lib/history.ts
T039 ui/src/components/svelte/Foro.svelte
T043 ui/src/i18n/{en,es}.json
```

## Implementation Strategy

### MVP (Setup + Foundational + US1)

A correctly permission-scoped, filterable, read-only portfolio list at `/inits/initiatives`.
Stop and validate with quickstart S1 before continuing. The permission-engine extraction (T006–
T008) lands here, guarded by the existing lib suites.

### Incremental delivery

1. MVP → demo the list.
2. US2 → tabbed editing (status locked) → demo quickstart S2.
3. US3 → owner status moves → demo quickstart S3.
4. Polish → docs, memory, changelog, full validation → PR.
