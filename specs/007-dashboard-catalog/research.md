# Research: Dashboard Catalog (with Execute and Favorite)

**Feature**: `007-dashboard-catalog` · **Date**: 2026-10-04 · **Spec**: [spec.md](spec.md)

The spec's clarifications settled the product questions. This file records the technical decisions taken to implement them, with the code facts they rest on.

---

## R1 — The catalog needs its own read endpoints, gated on `ANA/CATALOG`

**Decision**: Add catalog-specific read endpoints under `/api/dashboards/…` gated `require_privilege("ANA", "CATALOG", can_edit=False)`: `GET /api/dashboards/catalog` (the list) and `GET /api/dashboards/{id}/run-form` (detail parameters + what the window needs). Do not widen the existing Management reads.

**Rationale**: Every existing dashboard read (`/with-access`, `/{id}`, `/{id}/parameters`) is gated `ANA/DASHBOARDS`. COLLABORATOR and REVIEWER hold only `ANA/CATALOG` (seed `db/sql/12-admin-insert.sql:250,270`, `can_edit = FALSE`), so they would get 403 everywhere. The catalog also needs a different projection from Management: Published only, no `allowed_statuses`, no `my_access`-driven editing. A separate route keeps Management's contract untouched (Constitution II) and states the catalog's rule (Published + live grant) in one place.

**Alternatives considered**: (a) OR `CATALOG` into the Management guards with `check_any_privilege` — rejected: Management lists Drafts and Retired dashboards the catalog must never show, so the filter would have to branch on the caller's privilege, which is the kind of conditional that leaks. (b) Seeding `ANA/DASHBOARDS` read to collaborators — rejected: it would expose the Management sidebar entry to consumers.

## R2 — Favorites: widen the existing endpoints' module gate, don't fork them

**Decision**: `PUT`/`DELETE /api/dashboards/{id}/favorite` accept a caller holding **either** `ANA/DASHBOARDS` or `ANA/CATALOG` (read level), via the existing `check_any_privilege(session, user, "ANA", ["DASHBOARDS", "CATALOG"])`. The per-dashboard VIEW check underneath (`_set_favorite` → `_ensure_view`) is unchanged.

**Rationale**: Spec FR-020 requires one set of favorites shared by both screens; the rows already live in `favorite_dashboards` and the endpoints already implement the semantics (idempotent, logical removal, VIEW suffices). Widening only the outer RBAC gate is the established repo precedent (2026-09-02 / 2026-09-06 entries in `memory/MEMORY.md`). Request/response shape does not change (Constitution II); the auth change gets tests (Constitution III).

**Alternatives considered**: Catalog-only `/api/dashboards/catalog/{id}/favorite` routes — rejected as duplicate plumbing (Constitution I).

## R3 — "Reached through the bound grant" uses the engine's matching grants

**Decision**: For a run, compute the caller's live grants on the dashboard with `resource_permissions.matching_grants(session, user, DashboardPermission, "dashboard", [id])`. A GRANT-source parameter applies its binding iff `param.context_binding` is in the ids of those grants **and** that grant is not revoked. Its value is the grant's `target_code`. Otherwise the parameter falls back to LIST (if `list` is set) or INPUT. Superusers who match no grant get the fallback too.

**Rationale**: `matching_grants` already returns the exact grant rows that give the user access (PUBLIC or scope-matched, temporally valid). Reusing it means the binding rule and the access rule can never disagree. It is one query per run, bounded to the user's own scope pairs.

**Alternatives considered**: Re-deriving scope membership per parameter — rejected as a second copy of the engine.

**Consequence for the client**: The server computes the per-viewer *effective* source and the bound value in `run-form`; the client renders it but never sends bound values. The run endpoint ignores any bound name in the request body (FR-011).

## R4 — Run lifecycle: start, then finish once (two-step record)

**Decision**: An execution is recorded in two steps:

1. `POST /api/dashboards/{id}/executions` — the server checks privilege → active + Published + live grant → values. It always inserts **one** `executions` row:
   - no live grant or not Published → status `UNAUTHORIZED`, response **403**;
   - invalid values → status `FAILED` with the validation message in `error_message`, response **400**;
   - valid → status **NULL** ("in progress"), response **201** with `{execution_id, launch_url, mode}`.
2. `POST /api/executions/{execution_id}/finish` with `{status, error_message?}` where status ∈ `SUCCESS | FAILED | TIMEOUT | CANCELLED`. Allowed only for the row's own user, only while status is NULL (else **409**). The server sets `duration_ms = now − executed_at`.

Cancelling the parameters window (no start happened) uses `POST /api/dashboards/{id}/executions/cancelled` with `{values, duration_ms}`: one row, status `CANCELLED`, payload = the window's values, `duration_ms` from the client clamped to 0 … 24 h.

**Rationale**: An external tab's success (it opened) and a popup block (FAILED) are only known in the browser; an internal page's load / 30 s timeout / close-before-load likewise. The server must therefore learn the outcome after the start. Setting status exactly once, from NULL to a final value, is the record's *completion*, not an edit: FR-018's "append-only" is preserved by refusing any second change (409) and by having no update or delete route. Server-side duration for started runs can't be tampered with; only the cancel path (which never reached a start) takes the client's measure, and it is bounded.

**Stale "in progress" rows**: If the browser dies between the two steps, the row keeps status NULL. That is truthful ("outcome unknown"). HU-AN07 will treat NULL as *incomplete*. No sweeper job in this feature.

**Alternatives considered**: (a) Record only at the end, from the client — rejected: Unauthorized and server-side validation failures would depend on the client reporting them, and the client could skip the record. (b) Record SUCCESS at start for external sources — rejected: a blocked popup must become FAILED (spec US2-13), which would then need an edit anyway.

## R5 — Payload shape

**Decision**: `executions.payload` (JSONB) =

```json
{ "values":  { "date_from": "2026-01-01", "team": "ANALYTICS" },
  "sources": { "date_from": "DEFAULT",    "team": "GRANT" },
  "mode": "VIEWER" }
```

`values` holds each parameter that has a value (string form, as parameters store defaults). `sources` per name is `GRANT | LIST | INPUT | DEFAULT`; DEFAULT means a non-GRANT value equal to the parameter's `default_value`, derived on the server. `mode` is `VIEWER` (Internal Page) or `TAB` (external).

**Rationale**: FR-016 asks for name, value and source per parameter. A flat `values` object stays trivially queryable for HU-AN07 (`payload->'values'->>'team'`) and matches the shape of the existing seed rows. Deriving DEFAULT on the server keeps sources tamper-free.

**Seeds**: The six seed rows in `db/sql/62-ana-insert.sql` use the flat legacy shape. They are rewritten to the new shape in place (seed-only; product unreleased, same precedent as SpecKit 003). Readers still tolerate a legacy flat object, treating it as `values` with unknown sources.

## R6 — "Use my last values" is a server query over the payload

**Decision**: `GET /api/dashboards/{id}/executions/last-values` returns `{ values: {name: value}, executed_at }` from the caller's most recent `SUCCESS` execution of that dashboard, or `{ values: {}, executed_at: null }` when there is none. The server applies FR-009a: skip names whose current source is GRANT, skip names no longer active, re-validate each value against the current data type / list (invalid → omitted, so the client keeps the default), and omit new parameters. `run-form` also returns `has_last_values` so the button can be hidden without a second call.

**Rationale**: The rules depend on the current parameter definitions and lists, which the server already validates (`parameter_validation.validate_default`, `validate_list`). Doing it server-side means one implementation of "valid value".

**Performance**: The query is `WHERE user_id = ? AND dashboard = ? AND status = 'SUCCESS' ORDER BY executed_at DESC LIMIT 1`. There is no index on `executions` yet. At the expected volume (hundreds to low thousands of rows) a scan is fine. The additive index `(user_id, dashboard, executed_at DESC)` is deferred to HU-AN07, which will need its own indexes anyway. Recorded in Complexity Tracking.

## R7 — Value validation for a run reuses parameter validation

**Decision**: Extend `insights/internal/parameter_validation.py` with `validate_run_value(data_type, value, allowed)`. It applies the same rules as `validate_default` (NUMBER finite decimal, BOOLEAN `true|false`, DATE `YYYY-MM-DD`, list membership) and adds a 1 000-character cap. A required parameter with no value after defaults → 400. A required LIST parameter whose list is empty or inactive → 400 "cannot be run", recorded FAILED (spec edge case). Unknown names in the request → ignored. A value for a GRANT-applied parameter → ignored and replaced.

**Rationale**: One definition of a valid parameter value, shared by Management (defaults) and Execute (run values). `validate_default` is refactored to call the new function, so behaviour stays identical.

## R8 — Launch URL and Internal Page embedding

**Decision**: The server builds `launch_url` from `source_url`. It merges the existing query string with one `name=value` pair per value (urlencoded, parameter name as key). For Internal Page it also adds `embed=1`. External → `mode = TAB` (client `window.open(launch_url, "_blank", "noopener")`). Internal → `mode = VIEWER` (client loads it in a same-origin `<iframe>` inside the viewer dialog).

`BaseLayout.astro` gains an additive embed mode: when the request has `embed=1`, it renders the page content without SideBar and Header, so an internal page fits the viewer. Pages that don't use BaseLayout are unaffected.

**Rationale**: Internal Page `source_url` is validated as a platform path (`source_validation.py`), so the iframe is same-origin. Same origin means the auth cookie flows and the `load` event is observable, which is what makes SUCCESS / TIMEOUT (30 s) / CANCELLED (viewer closed before load) measurable (spec US2-11). No CSP or `X-Frame-Options` header is set anywhere in `ui/` today, so same-origin framing works. Query parameters are the only vendor-neutral way to pass values (vendor embed APIs are out of scope per the spec).

**Popup blocking**: `window.open` must run in the click's user activation. The start call is an `await`ed fetch, which can lose it. Mitigation: open a blank tab synchronously on click (`const tab = window.open("", "_blank")`), then set `tab.location = launch_url` after the start succeeds. If `tab` is null → the popup was blocked → finish FAILED ("popup blocked") and show the manual link (spec US2-13). If the start fails → close the blank tab.

## R9 — Catalog list: server visibility, client filtering (Explore pattern)

**Decision**: `GET /api/dashboards/catalog?skip&limit` returns Published, active dashboards the caller can access (superusers: every Published one), with `permission_scopes` and `is_favorite`. It filters before `skip`/`limit` (FR-006), using `accessible_dashboards` + `dashboards_user_scopes` + the existing `_favorite_ids`: three batched queries, no N+1. The page fetches it on the server (SSR, `limit=500` like both Explore pages) and filters on the client with `initCardGallery`.

**Rationale**: Identical to `/lib/explore` and `/inits/explore` (SSR fetch + `CardGallery` + `initCardGallery`). FR-003/004 require behaviour identical to those pages, and SC-007's < 1 s for 200 dashboards is trivially met by client filtering.

**Search over type and source in both languages** (FR-004 clarification): The SSR row builds `data-search` from name, description, tags **plus the en and es labels** of its type and source (read once via `getListItemsbyList` for `DASHBOARD_TYPE` and `SOURCE_TYPE`). Searching "Informe" or "Report" both match.

**Superuser caveat**: As on the Explore pages, a superuser's `permission_scopes` list only grants that really match them. With no "all" option, a dashboard with no matching grant is not shown under any privilege option. This is accepted for parity with Explore and noted in the quickstart.

## R10 — UI composition (reuse over forks)

**Decision**:

- **Page** `ui/src/pages/ana/catalog.astro`: mirrors `lib/explore.astro`. It gets the header from `getOption("ANA", "CATALOG")` with `moduleNameKey="modules.ANA"`, and renders `CardGallery` (`layout="grid"`, `statuses={[]}`, no propose) with `privileges` = the six `dashboard_table.perm_filter_*` keys (Public first), and `initCardGallery({ galleryId, idAttr: "dashboardId", services: { toggleFavorite: setDashboardFavorite } })`.
- **Card** `ui/src/components/ana/CatalogCard.astro`: wraps `GalleryCard`. Icon by source (a small `SOURCE_TYPE → icon` map; unknown → `chart-pie`), type + source chips, `#tags`, star, and an **Execute** button (`data-action="execute"`). No votes/discussion.
- **Detail** `ui/src/components/ana/CatalogDetailModal.astro`: a read-only dialog (description, detail rendered as markdown like the asset detail, parameters table, star, Execute).
- **Run island** `ui/src/components/svelte/DashboardRun.svelte`: owns the parameters window, the viewer, the timers and the finish calls. It is mounted once per page with Svelte `mount()` (repo pattern), listens for `[data-action="execute"]` clicks (delegated), calls `run-form`, renders fields by effective source (selects via `listLang.toListOptions` under `langTick`; String/Number/Boolean/Date inputs; read-only GRANT rows), uses `lib/formClasses.ts`, and validates inline with `setFieldInvalid`.
- **Services** `ui/src/lib/dashboardExecutions.ts`: `getCatalog`, `getRunForm`, `startExecution`, `finishExecution`, `recordCancelled`, `getLastValues`.

`initCardGallery` needs no change. The Execute button sits inside the card's `actions` slot, and the gallery's card-click handler already ignores clicks on `button`/`a` elements. That is verified during implementation; if it does not ignore them, a one-line `data-action` exclusion is added there.

**Rationale**: The parameters window has a per-dashboard dynamic field set, so neither `CrudModal` (fixed server-side fields) nor `AckDialog` fits. A Svelte island is the repo's tool for heavy interactive UI (MEMORY "Svelte 5 for heavy islands, manual `mount()`").

## R11 — Sidebar option type

**Decision**: Leave `ANA.CATALOG` as seeded (`type = 'FORM'`, path `/ana/catalog`, icon `chart-pie`). The page exists now, so the link resolves.

**Rationale**: `options.type` does not change routing; the sidebar reads `path`.

## R12 — Testing scope (Constitution III)

**Decision**: Backend pytest suites for every new or changed contract:

- Catalog visibility: Published only, grant-scoped, superuser, pagination after filtering, `permission_scopes`, `is_favorite`, 403 without `ANA/CATALOG`.
- `run-form`: effective sources (GRANT applied vs fallback to LIST/INPUT, revoked binding), list options in every language, `has_last_values`.
- Start: UNAUTHORIZED record + 403, FAILED record + 400 per validation rule, GRANT value forced (tampered value ignored), `launch_url` building (existing query string, encoding, `embed=1`), payload sources incl. DEFAULT.
- Finish: owner-only (403), once only (409), allowed statuses, server duration.
- Cancel: record, clamped duration, 403 without VIEW (UNAUTHORIZED record).
- Last values: SUCCESS-only, GRANT excluded, removed param skipped, invalid value omitted, legacy flat payload tolerated.
- Favorites: COLLABORATOR with CATALOG-only can PUT/DELETE, still 403 without VIEW.

UI: documented manual verification in [quickstart.md](quickstart.md) (no Playwright in this repo), plus `bun run build` and `astro check` at the existing baseline.
