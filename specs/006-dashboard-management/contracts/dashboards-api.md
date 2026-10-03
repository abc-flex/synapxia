# API Contract — Dashboard Management (006)

All endpoints are **new** (Principle II: additive only). All live under `/api/`, so they are
wrapped in the `{ data, error, meta }` envelope. All require a JWT (401 without one). Module RBAC
is `ANA/DASHBOARDS` (`can_edit` for writes) unless stated otherwise. Per-dashboard access is
explained in [data-model.md](../data-model.md#access-resolution). Error codes follow the
convention: 400 validation / transition, 403 RBAC or per-dashboard access, 404 missing, 409
conflict.

Static paths (`/with-access`, `/parameter-lists`) are declared before `/{dashboard_id}`.

## Dashboards — `api/app/insights/routes/dashboards.py`

### `GET /api/dashboards/with-access?skip=0&limit=100` (`limit ≤ 500`)
Active dashboards the caller can access, filtered **before** pagination and ordered by name.
Superusers get all of them.
→ `200 DashboardWithAccess[]`

```json
{ "id": 1, "name": "GenAI Adoption — Development Team", "description": "…",
  "type": "DASHBOARD", "sources_types": "POWER_BI",
  "source_url": "https://app.powerbi.com/view?r=…", "status": "PUBLISHED",
  "tags": ["genai","adoption"], "detail": "# …", "is_active": true,
  "created_at": "…", "updated_at": null,
  "my_access": "MANAGE",
  "allowed_statuses": ["PUBLISHED", "ARCHIVED", "RETIRED"],
  "permission_scopes": ["PUBLIC", "ROLE"] }
```

### `GET /api/dashboards/parameter-lists`
The lists an analyst may attach to a parameter: active `lists` with `type = LIST_OF_VALUES`,
ordered by name. → `200 [{ "value": "<list code>", "label": "<list name>" }]`

### `GET /api/dashboards/{dashboard_id}`
VIEW required. → `200 DashboardWithAccess` · 404 missing/inactive · 403 no grant.

### `POST /api/dashboards/`
Edit RBAC. The body is `DashboardCreate`:

```json
{ "name": "…", "description": "…", "type": "REPORT", "sources_types": "INTERNAL_PAGE",
  "source_url": "/ana/usage", "tags": ["…"], "detail": "…" }
```

The dashboard is created in `DRAFT`, and in the same transaction the caller gets a
`USER/<id>/MANAGE` grant. → `201 DashboardWithAccess` (`my_access = MANAGE`). 400: blank required
field, value outside its list, invalid `source_url` for the source, or a `status` sent other
than `DRAFT`.

### `PUT /api/dashboards/{dashboard_id}`
MANAGE required. The body is `DashboardUpdate`, and only sent keys are applied. A `status`
change must be an allowed transition, otherwise → 400 and nothing changes. An unchanged status
is a no-op. `source_url` is re-validated whenever `source_url` or `sources_types` is sent.
The row is locked `FOR UPDATE`.
→ `200 DashboardWithAccess` · 400 · 403 · 404.

### `DELETE /api/dashboards/{dashboard_id}`
MANAGE required. Logical delete: `is_active = false`. Parameters and grants are retained.
→ `200 Dashboard` · 403 · 404.

### `PUT /api/dashboards/{dashboard_id}/favorite` · `DELETE /api/dashboards/{dashboard_id}/favorite` *(amendment R14)*
Read RBAC plus VIEW on the dashboard; favoriting is personal, not an edit. The calls mark or clear
the caller's favorite in `favorite_dashboards`. Both are idempotent, and the removal is logical.
→ `200 { "dashboard": 3, "is_favorite": true }` · 403 no grant · 404 missing/inactive.
`DashboardWithAccess` rows (list and single GET) carry `is_favorite`.

## Parameters — `api/app/insights/routes/parameters.py`

### `GET /api/dashboards/{dashboard_id}/parameters?skip=0&limit=100` (`limit ≤ 500`)
VIEW required. Active parameters, ordered by `created_at, name`. → `200 ParameterRead[]`

```json
{ "dashboard": 3, "name": "team", "label": "Team", "data_type": "STRING",
  "default_value": null, "is_required": false, "list": null,
  "context_binding": 6, "is_active": true, "created_at": "…", "updated_at": null,
  "value_source": "GRANT", "binding_label": "TEAM ANALYTICS" }
```

### `POST /api/dashboards/{dashboard_id}/parameters`
MANAGE required. The body is `ParameterCreate`
(`name, label, data_type, default_value?, is_required?, list?, context_binding?`).
If an inactive row has the same name, it is **reactivated** with the new values (200).
Otherwise a new row is created (201).
→ `201|200 ParameterRead` · 409 active duplicate name · 400 validation (name format, data type,
default vs type or list, unknown/non-LoV list, binding not a live non-PUBLIC grant of this
dashboard).

### `PUT /api/dashboards/{dashboard_id}/parameters/{name}`
MANAGE required. The body is `ParameterUpdate` (any of `label, data_type, default_value,
is_required, list, context_binding`; send `null` to clear an optional one). `name` cannot be
changed. The result is validated as a whole (e.g. a changed `data_type` re-checks the stored
default). → `200 ParameterRead` · 400 · 403 · 404.

### `DELETE /api/dashboards/{dashboard_id}/parameters/{name}`
MANAGE required. Logical delete. → `200 ParameterRead` · 403 · 404.

## Grants — `api/app/insights/routes/dashboard_permissions.py`

### `GET /api/dashboard_permissions/dashboard/{dashboard_id}?skip=0&limit=100` (`limit ≤ 500`)
VIEW required. Grants that are not revoked (future-dated ones included), ordered by id.
→ `200 DashboardPermission[]`

### `POST /api/dashboard_permissions/`
MANAGE on `body.dashboard` required. The body is `DashboardPermissionCreate`
(`dashboard, target_type, target_code, access_level, valid_from?, valid_to?`). `target_type` and
`access_level` must belong to their lists. For PUBLIC, `target_code` is stored as `"ALL"`.
→ `201 DashboardPermission` · 400 unknown dashboard, list value or window (`valid_to ≤
valid_from`) · 403 · 409 live duplicate `(dashboard, target_type, target_code, access_level)`.
A revoked duplicate does not block the grant.

The Dashboard Management UI never sends `valid_from`/`valid_to`, the same as Asset and
Initiative Management: a grant starts now and ends when revoked. The optional keys stay for
parity with `/api/init_permissions` and for non-UI clients.

### `PUT /api/dashboard_permissions/{permission_id}`
MANAGE required. The body is `DashboardPermissionUpdate` (`access_level?, valid_from?,
valid_to?`). → `200` · 400 revoked or bad window · 403 · 404.

### `DELETE /api/dashboard_permissions/{permission_id}`
MANAGE required. Revokes the grant: `valid_to = now`, and the row is retained. A future
`valid_to` is overwritten.
→ `200 RevokedDashboardPermission` (the grant + `bound_parameters: ["team", …]`, the names of
active parameters whose `context_binding` is this grant; the binding is kept) · 400 already
revoked · 403 · 404.

## Reused, unchanged

- `GET /api/list_items/list/{code}` provides the type/source/status/data-type/target-type/access-level
  option sets and the allowed values of a parameter's list.
- The target-option loaders used by Initiative Management's Permissions tab (users, roles,
  projects, teams, units `/select` endpoints).

## UI service layer (`ui/src/lib/`)

- `dashboards.ts`: `getDashboardsWithAccess(skip, limit)`, `getAllDashboardsWithAccess()` (loops
  pages until exhausted), `getDashboard`, `createDashboard`, `updateDashboard`, `deleteDashboard`,
  `getParameterLists`, `setDashboardFavorite(id, on)`.
- `dashboard_parameters.ts`: `getParameters`, `createParameter`, `updateParameter`,
  `deleteParameter`.
- `dashboard_permissions.ts`: `getDashboardPermissions`, `createDashboardPermission`,
  `updateDashboardPermission`, `revokeDashboardPermission`.
- `types/api.ts`: `Dashboard`, `DashboardCreate`, `DashboardUpdate`, `DashboardWithAccess`,
  `DashboardParameter`, `DashboardParameterCreate`, `DashboardParameterUpdate`,
  `DashboardPermission`, `DashboardPermissionCreate`, `DashboardPermissionUpdate`.
