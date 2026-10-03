# Research — Dashboard Management (006)

Phase 0 of [plan.md](plan.md). Every decision below was taken by reading the code that already
exists. The closest precedent is Initiative Management (`specs/004-initiative-management`).
Technical Context had no open unknowns.

---

## R1 — Owning domain: `insights` (module code `ANA`)

- **Decision**: All backend code goes in `api/app/insights/` (`internal/` models and services,
  `routes/`). The module RBAC code is `ANA`, the option is `ANA/DASHBOARDS`, and the UI page is
  `ui/src/pages/ana/dashboards.astro` (the path already seeded in `options.path`).
- **Rationale**: `docs/user-stories/06-ana.md` names `api/app/insights` as the API domain for the
  `ANA` module, and `insights` is the stub reserved for it (only `dependencies.py` plus empty
  `models.py`/`routes/`). The constitution says to promote a stub only behind a SpecKit spec, and
  this is that spec.
- **Alternatives**: a new `ana/` domain folder was rejected. It would duplicate the existing stub
  and break the documented module ↔ domain mapping.

## R2 — Per-dashboard permissions: bind the shared engine, don't copy it

- **Decision**: New `insights/internal/permissions_service.py` binds
  `app/internal/resource_permissions.py` to `DashboardPermission` with `_FK = "dashboard"`. It is
  a line-for-line twin of `inits/internal/permissions_service.py`:
  `accessible_dashboards`, `dashboards_user_access`, `dashboards_user_scopes`,
  `user_dashboard_access`, `require_dashboard_manage` / `require_dashboard_view`,
  `DashboardAccessForbidden` (→ 403), `not_revoked_clause`, `is_revoked`.
- **Rationale**: the decisions log (2026-09-23) says "Any future per-resource grant table should
  bind this engine, not copy it", and Constitution I forbids duplicated permission plumbing.
  `dashboard_permissions` already has the exact shape the engine needs: `target_type`,
  `target_code`, `access_level`, `valid_from`/`valid_to`, and no `is_active`. That covers FR-021
  (same behaviour as assets and initiatives) for free.
- **Alternatives**: a generic "grants" route factory parameterised by model. It was rejected as
  premature. Only the route bodies would be shared, and their guards and 404 messages differ per
  domain. The existing precedent is a per-domain route module (`init_permissions.py`).

## R3 — Grant routes: mirror `init_permissions.py`

- **Decision**: New `insights/routes/dashboard_permissions.py` at `/api/dashboard_permissions`,
  with `GET /dashboard/{id}`, `POST /`, `PUT /{id}` and `DELETE /{id}` (revoke =
  `valid_to = now`). Module RBAC is `ANA/DASHBOARDS` (edit rights for writes), MANAGE on the
  dashboard is required for writes, and VIEW for reads. A live duplicate returns 409. A window
  where `valid_to <= valid_from` returns 400. `target_type`/`access_level` are validated against
  `TARGET_TYPE`/`ACCESS_LEVEL`, and a PUBLIC grant stores `target_code = "ALL"`.
- **Extra rule (FR-018 / US4-7)**: `DELETE` on a grant that a parameter uses as its context
  binding still revokes. It returns the revoked row plus `bound_parameters: [names]` so the UI can
  warn (the warning itself is client-side, before the call). Revoking does not clear the binding.
  The FK stays valid because the row is retained, and FR-018a sends viewers who don't come through
  that grant to the parameters window.
- **Alternatives**: refusing to revoke a bound grant (409) was rejected. The spec says the
  parameter "keeps working without it".

## R4 — Status lifecycle: a small service, server-enforced, no activity log

- **Decision**: `insights/internal/status_service.py` holds the transition map from the
  clarified spec:

  | From | Allowed to |
  |------|-----------|
  | DRAFT | PUBLISHED |
  | PUBLISHED | ARCHIVED, RETIRED |
  | ARCHIVED | PUBLISHED, RETIRED |
  | RETIRED | — (final) |

  It also provides `validate_create_status` (create always lands in DRAFT; any other sent
  status → 400), `validate_transition`, and `allowed_statuses_for(current)` (current status
  first, then its moves). The API returns `allowed_statuses` on every dashboard row so the UI
  never re-derives the rule, as Initiative Management does. Status values go through the shared
  `app/internal/status.normalize`.
- **Rationale**: same shape as `inits/internal/status_service.py` and
  `lib/internal/status_service.py`. `StatusTransitionForbidden(ValueError)` lets routes map it to
  400 uniformly.
- **No history row**: the analytics domain has no activity substrate. `actions.asset` and
  `collaborations.init` are both NOT NULL to other domains, and the spec's Assumptions keep
  History out of scope. A status change is just a field update with `updated_at`.
- **Alternatives**: adding an `ANA` activity table was rejected. It is unrequested scope plus a
  DDL change, and it can be revisited when a History tab is asked for.

## R5 — Dashboard creation auto-grants the creator MANAGE

- **Decision**: `POST /api/dashboards/` inserts the dashboard in DRAFT and a
  `DashboardPermission(target_type="USER", target_code=str(user.id), access_level="MANAGE")` in
  the same transaction. Gate: `ANA/DASHBOARDS` with edit rights.
- **Rationale**: FR-009, and it mirrors plain asset create (`lib/routes/assets.py` auto-grants
  USER/MANAGE). It keeps the grant-scoped list from hiding a dashboard from its own creator.

## R6 — Parameters: a nested resource keyed by `(dashboard, name)`

- **Decision**: New `insights/routes/parameters.py`, nested under `/api/dashboards/{id}/parameters`:
  `GET` (active, ordered by `created_at, name`, bounded `skip`/`limit`), `POST`,
  `PUT /{name}` and `DELETE /{name}` (logical: `is_active=False`). All writes need MANAGE on the
  dashboard and reads need VIEW. `name` is immutable because it is part of the PK, so `PUT` has no
  `name` key. A `POST` with a name whose row is inactive **reactivates** it with the new values;
  an active duplicate → 409 (US3-3/4).
- **Validation** (`insights/internal/parameter_validation.py`, raises `ValueError` → 400):
  - `data_type` ∈ `PARAM_TYPE` values.
  - `name`: `^[a-z][a-z0-9_]*$`, at most 100 characters. Parameter names are machine keys that
    appear in `executions.payload` (the seed uses `date_from`, `team`, …), so they are
    identifiers, not free text.
  - `default_value` parses for its `data_type`: NUMBER → decimal; BOOLEAN → `true`/`false`;
    DATE → ISO `YYYY-MM-DD`; STRING → anything. When `list` is set, the default must be one of
    that list's `list_items.value` (any language row).
  - `list` must be an active `lists.code` of type `LIST_OF_VALUES`.
  - `context_binding` must be the id of a **live** grant of the **same** dashboard whose
    `target_type` ≠ PUBLIC (US3-11).
- **Value source (FR-018)** is **derived** and never stored: `GRANT` when `context_binding` is
  set, else `LIST` when `list` is set, else `INPUT`. Read models expose it as `value_source`.
  This needs no DDL, and it keeps the user's extension: a grant-bound parameter may also carry a
  list for the parameters-window fallback.
- **Alternatives**: a stored `source` column was rejected. It would be redundant with the two
  nullable columns and could disagree with them.

## R7 — Allowed-values list picker needs its own read endpoint

- **Decision**: `GET /api/dashboards/parameter-lists` returns the active lists of type
  `LIST_OF_VALUES` as `{value: code, label: name}`, gated `ANA/DASHBOARDS`. The default-value
  picker reuses `GET /api/list_items/list/{code}` (already open to any authenticated user) plus
  `lib/listLang.ts` for the language switch.
- **Rationale**: `/api/lists/*` is gated `ADMIN/LISTS`, which ADMINISTRATIVE (the seeded analyst
  profile) does not hold. Opening that admin route instead would be a wider privilege change than
  the feature needs.

## R8 — List endpoint scoping and the privileges filter

- **Decision**: `GET /api/dashboards/with-access` copies Initiative Management's
  `/with-access`. Non-superusers are filtered to `accessible_dashboards` before `skip`/`limit`.
  Each row carries `my_access`, `allowed_statuses` and `permission_scopes` (drives the
  six-option privileges filter), plus `is_favorite` (added by the R14 amendment). The UI fetches
  every page through a `getAllDashboardsWithAccess()` loop (`limit=500`), so the client-side
  DataTable never truncates (FR-007, the P1 known blocker).
- `GET /api/dashboards/{id}` (single, VIEW required) returns the same projection for the dialog.

## R9 — Source location validation

- **Decision** (`insights/internal/source_validation.py`): when `sources_types = INTERNAL_PAGE`,
  `source_url` must be a platform path: it starts with `/`, is not `//`, has no scheme, and is at
  most 2048 characters. For every other source it must be an absolute `https://` URL with a host.
  The check runs on create and whenever either field changes on update. Nothing is fetched (spec
  Assumption).
- **Rationale**: FR-010 plus the edge case. An absolute https URL is the minimum an embed can use
  safely.

## R10 — Core-field validation reuses the inits pattern

- **Decision**: `insights/internal/list_validation.py` with
  `LIST_FIELDS = {type: DASHBOARD_TYPE, sources_types: SOURCE_TYPE, status: DASHBOARD_STATUS}` and
  `REQUIRED_FIELDS = (name, type, sources_types, source_url)`. It works like
  `inits/internal/list_validation.py`.
- **Generalising?** Both modules are about 40 lines and only the field map differs. Hoisting a
  shared `validate_list_value` into `app/internal/list_values.py` and keeping per-domain field
  maps is a cheap Principle-I improvement. It is done here because there are now two callers
  (inits + insights). `inits/internal/list_validation.py` re-exports it, so its suites must pass
  unchanged.

## R11 — UI: derive from Initiative Management, reuse shared pieces

- **Decision**:
  - The page `ui/src/pages/ana/dashboards.astro` mirrors `inits/initiatives.astro`: DataTable,
    columns name/type/source/status/tags/actions, header-funnel filters for type/source/status,
    the privileges filter and search, a "New Dashboard" button, plus `manageKey` so VIEW rows hide
    edit/remove.
  - The `components/ana/DashboardDetailModal.astro` shell holds Core Fields, the status policy
    (`allowed_statuses` → narrow + lock the `<select>`, mirroring `applyStatusPolicy`),
    tab-scoped save and the discard dialog.
  - New Svelte island `components/svelte/DashboardDetailTabs.svelte` holds Parameters and
    Permissions. Both are staged + diff-flushed like `InitiativeDetailTabs.svelte`'s permissions,
    and its target-type → target loaders (`TARGET_LOADERS`) are reused.
- **Reuse over fork**: the permissions UI is the third copy (assets, initiatives, dashboards).
  It gets extracted into a shared `components/svelte/PermissionsTab.svelte` with props
  `{ resourceId, api: {list, create, update, revoke}, i18nPrefix, readonly, onDirty }`, and
  `InitiativeDetailTabs` is switched to it. Assets is left alone: its tab predates the pattern
  and lives in a different island, so changing it is not needed for this feature. If the
  extraction turns out to change initiative behaviour, fall back to a local copy and record it
  in Complexity Tracking.
- **Create mode**: a new dashboard has no grants or parameters until it exists. In create mode
  only Core Fields is enabled; after the first save the dialog switches to edit mode on the new
  id. This is simpler than asset-style staged create, and the creator already gets MANAGE (R5).
- **Language**: every list value is rendered with `lib/listLang.ts`, per the 2026-10-01
  decision.

## R12 — Seeds: Spanish rows only, no DDL

- **Decision**: add `es` rows to `db/sql/61-ana-ddl.sql` for `DASHBOARD_TYPE`, `SOURCE_TYPE`,
  `DASHBOARD_STATUS`, `PARAM_TYPE` and `EXECUTION_STATUS`, and give the seeded parameters
  `list = NULL` (unchanged). Provisioned DBs get the same `INSERT`s in
  `specs/006-dashboard-management/provisioned-db.sql`. Test grants for a non-superuser analyst go
  in `specs/006-dashboard-management/test-owner.sql` (run by hand, not seed data, same convention
  as 004).
- **No DDL**: every needed column exists. The value source is derived (R6).

## R13 — Tests (Principle III: auth / contract / permission changes)

New modules, using an `ana_helpers.py` modelled on `inits_helpers.py`:

| Module | Covers |
|--------|--------|
| `test_ana_dashboards.py` | create (DRAFT forced, auto-MANAGE, required/list/source-url validation), PUT core fields, logical DELETE, `/with-access` scoping before pagination, superuser sees all, `my_access`/`permission_scopes`, 401/403 RBAC |
| `test_ana_status.py` | the full transition table: allowed → 200, every other → 400 with nothing changed, RETIRED locked, `allowed_statuses` per status |
| `test_ana_permissions.py` | grant/update/revoke, 409 live duplicate, re-grant after revoke, window 400, VIEW cannot write (no self-escalation), MANAGE beats VIEW, future-dated grant listed, `bound_parameters` on revoke |
| `test_ana_parameters.py` | add/edit/remove/reactivate, 409 active duplicate, name format, default per data type, default ∈ list, list must exist, binding must be a live non-PUBLIC grant of the same dashboard, `value_source` derivation, VIEW read / MANAGE write |
| `test_ana_parameter_lists.py` | only LIST_OF_VALUES, gated ANA/DASHBOARDS |

Plus the existing `test_inits_*` suites must pass unchanged, since they guard the R10 hoist and
the R11 extraction's backend-neutral half.

## R14 — Amendment (2026-10-02): favorites, permissions without dates, compact Parameters form

The user asked for three changes after the first implementation.

- **Favorites → `favorite_dashboards`.** The user wrote "usando la tabla Favorite_Inits", but
  `favorite_inits.init` is a foreign key to `initiatives`, so it cannot hold a dashboard. The
  analytics counterpart already exists in `61-ana-ddl.sql`: `favorite_dashboards`, with PK
  `(user_id, dashboard)` and `is_active`. That is the table used, so there is no DDL. The
  behaviour copies Initiative Management:
  - `PUT` / `DELETE /api/dashboards/{id}/favorite` take read RBAC plus VIEW on the dashboard.
    They are idempotent, and removal is logical.
  - `is_favorite` is added to `/with-access` and `GET /{id}` (one batched query).
  - The list gets a star in the actions column (`favoriteAction` / `favoriteKey`) and a
    "My favorites" toggle in filter slot 3. Source moves to `extraFilters`, the same layout as
    `/inits/initiatives`.
  - The dialog header gets a star that saves at once and reports `favorite:changed` on close.
- **Permissions tab without dates.** Asset Management and Initiative Management never show or
  ask for `valid_from`/`valid_to`: a grant starts when it is given (`valid_from` defaults to
  now) and ends when it is revoked (`valid_to` = now). The optional `withWindow` mode that R11
  had added to `PermissionsTab.svelte` is **removed**, so the shared tab is again exactly the
  initiative tab, and its six i18n keys are deleted. The API still accepts the optional
  fields, for parity with `/api/init_permissions`. The UI simply never sends them.
- **Compact Parameters form.** The add/edit form becomes two dense rows plus a single help line,
  down from roughly 330 px to roughly 150 px:
  1. name · label · data type · required · add button
  2. a value-source segmented control, then binding / list / default
  
  The name hint and each source's help text move into `title` tooltips, and the help line shows
  only the active source's text. Declared parameters therefore stay visible below the form
  (spec US3-12).
