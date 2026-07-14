# Analytics — User Stories

> Module `ANA` · API domain [`api/app/insights`](../../api/app) *(stub)* · DB band 60s
> ([`61-ana-ddl.sql`](../../db/sql/61-ana-ddl.sql)) · Diagram [6-ana.png](../diagrams/6-ana.png)

Analytics consolidates measurement and reporting: a catalog of dashboards (internal pages or
embedded BI like Power BI, Looker, Tableau, …), the parameters they take, their executions,
and usage metrics — enabling analysis by unit, team and return on investment.

| Code | Story |
|------|-------|
| HU-AN01 | Dashboard Catalog |
| HU-AN02 | – Parameters |
| HU-AN03 | – Execute |
| HU-AN04 | – Favorite |
| HU-AN05 | – Permission |
| HU-AN06 | Usage Metrics |

---

### HU-AN01 · Dashboard Catalog
> As an **analyst**, I want to **register dashboards and reports** (internal or embedded BI)
> **so that** the organization has one place to discover and open its analytics.
- **Data:** `dashboards` — `id`, `name`, `type` (→ `DASHBOARD_TYPE`), `sources_types`
  (→ `SOURCE_TYPE`: Internal Page, Power BI, Looker Studio, Tableau, …), `source_url`,
  `status` (→ `DASHBOARD_STATUS`), `tags` (JSONB)

### HU-AN02 · – Parameters
> As an **analyst**, I want to **define the parameters a dashboard accepts** (with type,
> required flag and default) **so that** it can be filtered and bound to context at run time.
- **Data:** `parameters` — PK `(dashboard, name)`, `label`, `data_type` (→ `PARAM_TYPE`),
  `is_required`, `default_value`, `list`, `context_binding`. Detail of **HU-AN01**.

### HU-AN03 · – Execute
> As any **user**, I want to **execute a dashboard with parameter values** and have the run
> recorded **so that** results are produced and usage is traceable.
- **Data:** `executions` — `dashboard`, `user_id`, `payload` (JSONB), `status`
  (→ `EXECUTION_STATUS`), `duration_ms`, `error_message`. Detail of **HU-AN01**.

### HU-AN04 · – Favorite
> As any **user**, I want to **favorite a dashboard** so that I can quickly reopen the ones I
> use most.
- **Data:** `favorite_dashboards` — PK `(user_id, dashboard)`.

### HU-AN05 · – Permission
> As an **owner**, I want to **grant view/manage access to users, roles, teams or units** so
> that dashboard visibility is controlled per audience.
- **Data:** `dashboard_permissions` — `dashboard`, `target_type` (→ `TARGET_TYPE`),
  `target_code`, `access_level` (→ `ACCESS_LEVEL`), validity window.

### HU-AN06 · Usage Metrics
> As a **manager**, I want to **see usage metrics** (executions, durations, adoption by unit
> and team) **so that** I can evaluate adoption, impact and return on investment.
- **Data:** aggregate view over `executions` (+ users/teams/units context).
