# API Contract — Dashboard Catalog, Execute, Favorite (007)

Every endpoint lives under `/api/`, so responses come wrapped in the `{ data, error, meta }` envelope. All of them need a JWT; without one the answer is 401.

Unless stated otherwise, module RBAC is `ANA/CATALOG` at **read** level (`can_edit = False`): executing and favoriting count as consumption, not edits (spec FR-013, R1). Error codes follow the convention: 400 validation, 403 RBAC or per-dashboard access, 404 missing, 409 conflict.

Every endpoint here is new, with one exception: the favorite endpoints keep their existing contract and only gain a wider module gate. That makes the whole change additive (Principle II).

Static paths (`/catalog`) are declared before `/{dashboard_id}` in `dashboards.py`.

---

## Catalog — `api/app/insights/routes/catalog.py` (prefix `/api/dashboards`)

### `GET /api/dashboards/catalog?skip=0&limit=100` (`limit ≤ 500`)

Returns active **Published** dashboards the caller can access, ordered by name. Visibility is filtered **before** `skip`/`limit` (FR-006). A superuser gets every Published dashboard. 403 without `ANA/CATALOG`.

→ `200 CatalogDashboard[]`

```json
{ "id": 3, "name": "GenAI Adoption — by Team", "description": "…",
  "type": "DASHBOARD", "sources_types": "LOOKER_STUDIO",
  "tags": ["genai","adoption","team"], "detail": "# …", "created_at": "…",
  "is_favorite": false, "permission_scopes": ["PUBLIC","TEAM"], "parameter_count": 4 }
```

`source_url` is deliberately absent (see data-model).

### `GET /api/dashboards/{dashboard_id}/run-form`

Returns everything the detail and the parameters window need, already resolved for **this** viewer.

- 404 if the dashboard is missing or inactive.
- 403 if there is no live grant **or** the dashboard is not Published. Nothing is recorded: this is a read, not a run attempt.

→ `200 RunForm`

```json
{ "dashboard": 3, "name": "GenAI Adoption — by Team", "mode": "TAB", "has_last_values": true,
  "parameters": [
    { "name": "date_from", "label": "From date", "data_type": "DATE", "is_required": true,
      "default_value": "2026-01-01", "effective_source": "INPUT" },
    { "name": "team", "label": "Team", "data_type": "STRING", "is_required": false,
      "default_value": null, "effective_source": "GRANT",
      "bound_value": "ANALYTICS", "bound_label": "TEAM ANALYTICS" },
    { "name": "granularity", "label": "Granularity", "data_type": "STRING", "is_required": false,
      "default_value": "MONTH", "effective_source": "LIST", "list": "GRANULARITY",
      "list_unavailable": false,
      "options": [ { "value": "MONTH", "lang": "en", "label": "Month", "sort_order": 10 },
                   { "value": "MONTH", "lang": "es", "label": "Mes",   "sort_order": 10 } ] }
  ] }
```

The parameters come in name order. `options` lists **every language** of the list, so the client relabels it with `listLang`. `list_unavailable` is true when the list is empty or inactive.

---

## Executions — `api/app/insights/routes/executions.py`

### `POST /api/dashboards/{dashboard_id}/executions`

Starts a run. The body carries the values the viewer supplied, as strings; Boolean is `"true"`/`"false"` and Date is `YYYY-MM-DD`:

```json
{ "values": { "date_from": "2026-04-01", "granularity": "MONTH" } }
```

The server checks, in this order, and **always inserts exactly one `executions` row** once the module gate passes:

| Check | Fails → row | Response |
|-------|-------------|----------|
| Dashboard exists | *no row* | 404 |
| Active, Published, caller holds a live grant | `UNAUTHORIZED`, error message | **403** |
| GRANT-applied parameters | Value forced to the grant's `target_code`; a submitted value is ignored | — |
| Defaults | An absent or empty value takes `default_value` | — |
| Required present, type valid, list membership, ≤ 1 000 chars, required list available | `FAILED`, error message = the first violation | **400** |
| All valid | `status = NULL` (in progress) | **201** |

Unknown names in `values` are ignored.

→ `201 ExecutionStarted`

```json
{ "execution_id": 42,
  "launch_url": "https://lookerstudio.google.com/embed/reporting/…?date_from=2026-04-01&granularity=MONTH&team=ANALYTICS",
  "mode": "TAB" }
```

How `launch_url` is built:

1. Start from `source_url`.
2. Merge in its existing query string.
3. Add one `name=value` pair per value, urlencoded.
4. For Internal Page only, append `embed=1`. Internal Page sets `mode` to `VIEWER`; every other source sets `TAB`.

### `POST /api/executions/{execution_id}/finish`

Reports the outcome of a started run, **once**:

```json
{ "status": "SUCCESS", "error_message": null }
```

`status` must be one of `SUCCESS | FAILED | TIMEOUT | CANCELLED`, otherwise 400. The server sets `duration_ms = now − executed_at`, and `error_message` is truncated to 1 000 characters.

→ `200 ExecutionRead`. Errors:

- 404 if the execution does not exist.
- 403 if it is not the caller's own.
- **409** if its status is already set.

### `POST /api/dashboards/{dashboard_id}/executions/cancelled`

Records a parameters window that was closed without pressing Execute:

```json
{ "values": { "date_from": "2026-04-01" }, "duration_ms": 8400 }
```

- 404 if the dashboard does not exist.
- No live grant or not Published → an `UNAUTHORIZED` row and **403**.
- Otherwise → a `CANCELLED` row. Its payload keeps the window's values, active parameter names only, each value truncated. `duration_ms` is clamped to 0 … 86 400 000.

→ `201 ExecutionRead`

### `GET /api/dashboards/{dashboard_id}/executions/last-values`

Returns the values of the caller's most recent `SUCCESS` execution of this dashboard, filtered by spec FR-009a:

- GRANT-effective parameters are left out.
- Inactive or removed parameters are left out.
- Values that no longer validate are left out, so the client keeps the default.

A legacy flat payload is read as `values`. It has the same 404 / 403 rules as `run-form`.

→ `200 LastValues`

```json
{ "values": { "date_from": "2026-04-01", "granularity": "MONTH" }, "executed_at": "2026-10-03T15:20:11Z" }
```

With no previous SUCCESS → `{ "values": {}, "executed_at": null }`.

---

## Favorites — `api/app/insights/routes/dashboards.py` *(existing, gate widened)*

### `PUT /api/dashboards/{dashboard_id}/favorite` · `DELETE /api/dashboards/{dashboard_id}/favorite`

The request, the response (`DashboardFavoriteState`) and the semantics are unchanged.

**Module gate**: `ANA/DASHBOARDS` **or** `ANA/CATALOG`, read level (was `ANA/DASHBOARDS` only). VIEW on the dashboard is still required, so it is still 403 without a live grant. The catalog does **not** require the dashboard to be Published here: a favorite on a dashboard that later gets archived simply stops showing in the catalog, and it still shows in Management.

---

## Not changed

`/api/dashboards/with-access`, `/{id}`, `/{id}/parameters*`, `/api/dashboard_permissions*` and the create, update and delete routes keep their `ANA/DASHBOARDS` gate and their contracts.
