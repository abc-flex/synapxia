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

### HU-AN02 · – Parameters
> As an **analyst**, I want to **declare the parameters a dashboard accepts** — type, required
> flag, default, allowed values and context binding — **so that** it can be filtered and bound
> to the viewer's context at run time.
- **Data:** `parameters` — PK `(dashboard, name)`, `label`, `data_type` (→ `PARAM_TYPE`:
  String, Number, Boolean, Date), `is_required`, `default_value`, `list` (optional list of
  allowed values), `context_binding`. Detail of **HU-AN01**.

### HU-AN03 · – Permission
> As a **dashboard owner**, I want to **grant view or manage access to users, roles, projects,
> teams, units or everyone**, for a validity window, **so that** sensitive analytics reach only
> their intended audience.
- **Data:** `dashboard_permissions` — `dashboard`, `target_type` (→ `TARGET_TYPE`),
  `target_code`, `access_level` (→ `ACCESS_LEVEL`: View / Manage), `valid_from`, `valid_to`.
  Detail of **HU-AN01**.

---

## Consumption

### HU-AN04 · Dashboard Catalog
> As any **user**, I want to **browse the dashboards I am allowed to see**, searchable and
> filterable by type, source and tags, **so that** I can find the right analytics quickly.
- **Data:** read view over `dashboards` (published) scoped by `dashboard_permissions`, plus the
  viewer's `favorite_dashboards`.
- **Option:** `ANA.CATALOG` → `/ana/catalog`

### HU-AN05 · – Execute
> As any **user**, I want to **run a dashboard with parameter values** and have the run
> recorded **so that** I get results and usage stays traceable.
- **Data:** `executions` — `id`, `dashboard`, `user_id`, `executed_at`, `payload` (JSONB, the
  parameter values used), `status` (→ `EXECUTION_STATUS`: Success, Failed, Cancelled, Timeout,
  Unauthorized), `duration_ms`, `error_message`. Detail of **HU-AN04**.

### HU-AN06 · – Favorite
> As any **user**, I want to **favorite a dashboard** **so that** the ones I use most are one
> click away.
- **Data:** `favorite_dashboards` — PK `(user_id, dashboard)`. Detail of **HU-AN04**.

---

### HU-AN07 · Usage Metrics
> As a **manager**, I want to **see how the analytics are actually used** — executions over
> time, success rate, duration, and adoption by unit and team — **so that** I can evaluate
> adoption, impact and return on investment.
- **Data:** aggregate view over `executions`, joined to `users` → `business_units` and to the
  user's `assignments` → `teams`.
- **Option:** `ANA.USAGE` → `/ana/usage`
