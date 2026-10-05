# Analytics — User Stories

> Module `ANA` · API domain [`api/app/insights`](../../api/app) · DB band 60s
> ([`61-ana-ddl.sql`](../../db/sql/61-ana-ddl.sql)) · Diagram [6-ana.png](../diagrams/6-ana.png)

Analytics consolidates measurement and reporting: a managed catalog of dashboards (internal
pages or embedded BI — Power BI, Looker Studio, Tableau, …), the parameters they accept, the
audiences allowed to open them, their executions, and the usage metrics derived from those
executions.

| Code | Story |
|------|-------|
| HU-AN01 | Dashboard Management |
| HU-AN02 | – Parameters |
| HU-AN03 | – Permission |
| HU-AN04 | Dashboard Catalog |
| HU-AN05 | – Execute |
| HU-AN06 | – Favorite |
| HU-AN07 | Usage Metrics |

---

## Management

### HU-AN01 · Dashboard Management
> As an **analyst**, I want to **register and maintain dashboards and reports**, internal or
> embedded, **so that** the organization has one governed place to publish its analytics.
- **Data:** `dashboards` — `id`, `name`, `description`, `type` (→ `DASHBOARD_TYPE`: Dashboard,
  Report, Scorecard, KPI View, Analytical View), `sources_types` (→ `SOURCE_TYPE`: Internal
  Page, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Custom Iframe),
  `source_url`, `status` (→ `DASHBOARD_STATUS`: Draft, Published, Archived, Retired), `tags`
  (JSONB), `detail`
- **Option:** `ANA.DASHBOARDS` → `/ana/dashboards`
- **Status:** ✅ implemented (SpecKit [`specs/006-dashboard-management`](../../specs/006-dashboard-management/spec.md)).
  The list is grant-scoped, and the edit dialog has Core Fields, Parameters and Permissions
  tabs, each saving its own slice. A new dashboard starts as **Draft** and its creator gets
  MANAGE. Status moves, enforced by the server: Draft → Published · Published →
  Archived/Retired · Archived → Published/Retired · **Retired is final**. Source location is a
  platform path for Internal Page and an absolute `https://` URL for every other source. Each
  row has a **favorite star**, and there is a *My favorites* filter, as in Asset/Initiative
  Management (stored in `favorite_dashboards`; see HU-AN06).

### HU-AN02 · – Parameters
> As an **analyst**, I want to **declare the parameters a dashboard accepts** — type, required
> flag, default, allowed values and context binding — **so that** it can be filtered and bound
> to the viewer's context at run time.
- **Data:** `parameters` — PK `(dashboard, name)`, `label`, `data_type` (→ `PARAM_TYPE`:
  String, Number, Boolean, Date), `is_required`, `default_value`, `list` (optional list of
  allowed values), `context_binding`. Detail of **HU-AN01**.
- **Status:** ✅ implemented (SpecKit 006). Each parameter's **value source** is derived from
  `context_binding` and `list`, not stored:
  - **Bound to a grant**: `context_binding` points at one of the dashboard's live grants to a
    user, role, project, team or unit, and the value is that grant's recipient (e.g. a grant to
    team ANALYTICS fixes `team = ANALYTICS`).
  - **From a list**: `list` names a `LIST_OF_VALUES` list, and the viewer picks one of its
    values.
  - **Entered by the viewer**: the viewer types a value valid for the data type.

  Lists and viewer input, plus a grant-bound parameter whose viewer reached the dashboard
  through another grant, are asked for in a **parameters window before the run**. That
  window is part of **HU-AN05 Execute**.

### HU-AN03 · – Permission
> As a **dashboard owner**, I want to **grant view or manage access to users, roles, projects,
> teams, units or everyone**, for a validity window, **so that** sensitive analytics reach only
> their intended audience.
- **Data:** `dashboard_permissions` — `dashboard`, `target_type` (→ `TARGET_TYPE`),
  `target_code`, `access_level` (→ `ACCESS_LEVEL`: View / Manage), `valid_from`, `valid_to`.
  Detail of **HU-AN01**.
- **Status:** ✅ implemented (SpecKit 006) on the shared per-resource permission engine
  (`api/app/internal/resource_permissions.py`), with the same rules as asset and initiative
  grants: Manage beats View, a grant is revoked (`valid_to` = now) and never deleted, and
  PUBLIC grants store `target_code = 'ALL'`. As in those two screens, the tab shows only
  recipient type, recipient and access level. `valid_from`/`valid_to` are managed internally:
  a grant starts when given and ends when revoked. Revoking a grant that a parameter is bound to
  is allowed with a warning; the binding is kept but stops applying.

---

## Consumption

### HU-AN04 · Dashboard Catalog
> As any **user**, I want to **browse the dashboards I am allowed to see**, searchable and
> filterable by type, source and tags, **so that** I can find the right analytics quickly.
- **Data:** read view over `dashboards` (published) scoped by `dashboard_permissions`, plus the
  viewer's `favorite_dashboards`.
- **Option:** `ANA.CATALOG` → `/ana/catalog`
- **Status:** ✅ implemented (SpecKit [`specs/007-dashboard-catalog`](../../specs/007-dashboard-catalog/spec.md)).
  A card grid with the same privileges filter (Public, Shared with me, My role, My team, My
  unit, My projects; Public by default, no "all"), search and favorites as Explore Category
  and Explore Initiatives. It shows only Published dashboards reached by a live grant. Type
  and source are searchable in both languages; there are no separate dropdowns for them.

### HU-AN05 · – Execute
> As any **user**, I want to **run a dashboard with parameter values** and have the run
> recorded **so that** I get results and usage stays traceable.
- **Data:** `executions` — `id`, `dashboard`, `user_id`, `executed_at`, `payload` (JSONB, the
  parameter values used), `status` (→ `EXECUTION_STATUS`: Success, Failed, Cancelled, Timeout,
  Unauthorized), `duration_ms`, `error_message`. Detail of **HU-AN04**.
- **Status:** ✅ implemented (SpecKit 007). Execute opens a parameters window built for the
  viewer.
  - A grant-bound value is fixed only when the viewer came through the bound grant. Otherwise
    the value comes from the parameter's list or from free input.
  - Fields start at their defaults, and "Use my last values" fills them from the viewer's last
    successful run.
  - Internal Page dashboards open in a viewer inside the catalog; external BI opens in a new
    tab.

  Every attempt is recorded. Start always writes one row: Unauthorized, Failed, or in
  progress. The outcome is then set once: Success, Failed, Timeout (30 s, Internal Page only)
  or Cancelled. A parameters window closed without running is recorded as Cancelled.
  `payload` = `{values, sources, mode}`, where `sources` says per parameter whether the value
  came from the grant, a list, the viewer's input or the default.

### HU-AN06 · – Favorite
> As any **user**, I want to **favorite a dashboard** **so that** the ones I use most are one
> click away.
- **Data:** `favorite_dashboards` — PK `(user_id, dashboard)`. Detail of **HU-AN04**.
- **Status:** ✅ implemented. The storage, the API (`PUT`/`DELETE /api/dashboards/{id}/favorite`,
  VIEW required, logical removal) and the star and filter in **Dashboard Management** shipped
  with SpecKit 006. The Catalog's star and "★ My favorites" toggle (SpecKit 007) use the same
  favorites; the endpoints now accept `ANA/CATALOG` as well as `ANA/DASHBOARDS`.

---

### HU-AN07 · Usage Metrics
> As a **manager**, I want to **see how the analytics are actually used** — executions over
> time, success rate, duration, and adoption by unit and team — **so that** I can evaluate
> adoption, impact and return on investment.
- **Data:** aggregate view over `executions`, joined to `users` → `business_units` and to the
  user's `assignments` → `teams`.
- **Option:** `ANA.USAGE` → `/ana/usage`
