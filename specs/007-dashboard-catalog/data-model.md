# Data Model: Dashboard Catalog (with Execute and Favorite)

**Feature**: `007-dashboard-catalog` · **Date**: 2026-10-04

**No DDL.** Every table already exists in `db/sql/61-ana-ddl.sql`. This feature maps `executions`, which no code reads yet, and reads the tables SpecKit 006 already maps (`dashboards`, `parameters`, `dashboard_permissions`, `favorite_dashboards`). The only seed change is rewriting the six `executions` payloads in `db/sql/62-ana-insert.sql` to the new shape (R5).

---

## Execution *(new mapping — `executions`)*

| Field | Type | Rules |
|-------|------|-------|
| `id` | BIGINT identity | PK |
| `dashboard` | BIGINT FK → `dashboards.id` | NOT NULL |
| `user_id` | BIGINT FK → `users.id` | NOT NULL. **Always the session user**, never the request body |
| `executed_at` | TIMESTAMPTZ | Default now. The start of the attempt |
| `payload` | JSONB | See *Payload* below |
| `status` | VARCHAR(100), nullable | `EXECUTION_STATUS` value, or **NULL = in progress** (R4) |
| `error_message` | TEXT, nullable | Set for FAILED / UNAUTHORIZED / TIMEOUT. At most 1 000 characters |
| `duration_ms` | INTEGER, nullable | Server-computed on finish. Client-measured and clamped to 0 … 86 400 000 only for a cancelled window |

**There is no `is_active`, no update route and no delete route.** The record is append-only: the only allowed change is the one-time completion described below.

### Status lifecycle

```text
                    ┌─ (no live grant / not Published) ─► UNAUTHORIZED   (final, at start)
POST …/executions ──┼─ (invalid values) ────────────────► FAILED         (final, at start)
                    └─ (valid) ──► NULL "in progress" ──► finish once ──► SUCCESS | FAILED | TIMEOUT | CANCELLED

POST …/executions/cancelled ───────────────────────────► CANCELLED      (final; parameters window closed without Execute)
```

| Status | Set when |
|--------|----------|
| SUCCESS | Internal Page: the viewer's iframe fired `load`. External: the tab was opened |
| FAILED | Values rejected at start; a required list is empty or inactive; popup blocked; viewer load error |
| UNAUTHORIZED | At start (or cancel): no live grant, dashboard not active, or not Published |
| TIMEOUT | Internal Page did not load within **30 s**. Never used for external tabs |
| CANCELLED | Parameters window closed without Execute; viewer closed before the Internal Page loaded |
| NULL | Started; no outcome reported yet (browser closed mid-run). Treated as *incomplete* by HU-AN07 |

Finish rules: only the row's `user_id` may finish it (else 403). Only while `status IS NULL` (else 409). `status` must be one of SUCCESS/FAILED/TIMEOUT/CANCELLED (else 400). A late iframe `load` after TIMEOUT changes nothing (the finish call answers 409 and the client ignores it).

### Payload

```json
{
  "values":  { "<param name>": "<value as string>" },
  "sources": { "<param name>": "GRANT | LIST | INPUT | DEFAULT" },
  "mode":    "VIEWER | TAB"
}
```

- `values` contains only parameters that ended with a value; an empty optional parameter is omitted.
- `sources` is derived by the server. GRANT means the binding applied. DEFAULT means a non-GRANT value equal to the parameter's `default_value`. Otherwise it is LIST or INPUT, from the parameter's effective source.
- A FAILED-at-start or UNAUTHORIZED row stores the submitted values for active parameter names only (unknown names dropped, each value truncated to 1 000 characters). `sources` is omitted.
- A cancelled-window row stores the window's values under the same restriction. Its `mode` is omitted.
- Readers must tolerate the **legacy flat shape** (`{"date_from": "…"}`): it is treated as `values` with unknown sources.

---

## Dashboard *(existing — read)*

The catalog reads rows with `is_active = TRUE` **and** `status = 'PUBLISHED'` (after `normalize`). Fields shown: `id, name, description, type, sources_types, source_url (never displayed; used to build launch_url), tags, detail, created_at`.

## Parameter *(existing — read)*

For a viewer, each active parameter gets an **effective source**, computed per request (R3):

| Stored | Viewer reached the dashboard through the bound grant? | Effective source | Window shows |
|--------|------------------------------------------------------|------------------|--------------|
| `context_binding` set | yes (bound grant ∈ caller's matching grants, live) | **GRANT** | Read-only value = grant `target_code` |
| `context_binding` set, `list` set | no / binding revoked | **LIST** | Selector over the list |
| `context_binding` set, no `list` | no / binding revoked | **INPUT** | Control by `data_type` |
| `list` set | — | **LIST** | Selector over the list |
| neither | — | **INPUT** | Control by `data_type` |

Run-value validation (R7), shared with defaults: NUMBER is a finite decimal; BOOLEAN is `true`/`false`; DATE is `YYYY-MM-DD` and a real date; LIST values must belong to the list; any value is at most 1 000 characters. A required parameter with no value after applying the binding → 400. A required LIST parameter with an empty or inactive list → 400, recorded FAILED.

## Dashboard Grant *(existing — read)*

`resource_permissions.matching_grants(…, DashboardPermission, "dashboard", [id])` gives the caller's live grants on a dashboard. These grants decide visibility (any grant), `permission_scopes` (their `target_type`s) and grant-bound values (R3).

## Favorite Dashboard *(existing — read/write)*

Unchanged table and semantics (`PUT`/`DELETE /api/dashboards/{id}/favorite`, logical removal). Only the outer module gate widens to `ANA/DASHBOARDS` **or** `ANA/CATALOG` (R2).

---

## Read projections (API models)

### `CatalogDashboard`

`id, name, description, type, sources_types, tags, detail, created_at, is_favorite: bool, permission_scopes: List[str], parameter_count: int`.

`source_url` is deliberately **not** exposed in the list. The client never builds the launch address itself, so values can't skip server validation by pasting a URL.

### `RunForm`

`dashboard: int, name: str, mode: "VIEWER" | "TAB", has_last_values: bool, parameters: List[RunFormParameter]`

### `RunFormParameter`

`name, label, data_type, is_required, default_value, effective_source: GRANT|LIST|INPUT, bound_value?: str (GRANT only), bound_label?: str (GRANT only, e.g. "TEAM ANALYTICS"), list?: str, options?: List[{value, lang, label, sort_order}] (LIST only, every language, for listLang), list_unavailable: bool (LIST with empty/inactive list)`

### `ExecutionStarted`

`execution_id: int, launch_url: str, mode: "VIEWER" | "TAB"`

### `ExecutionRead`

`id, dashboard, user_id, executed_at, payload, status, error_message, duration_ms`, returned by finish and cancel.

### `LastValues`

`values: Dict[str, str], executed_at: Optional[datetime]`
