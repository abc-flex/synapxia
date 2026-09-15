# Collaboration — User Stories

> Module `COLLAB` · API domain [`api/app/collab`](../../api/app) · DB band 30s
> ([`31-collab-ddl.sql`](../../db/sql/31-collab-ddl.sql)) · Diagram [3-collab.png](../diagrams/3-collab.png)

Collaboration provides the structures to coordinate AI-adoption work across the organization:
teams, the roles people play, their assignments over time, the projects teams own, the
dimensions used to measure adoption, and the metrics recorded against each assignment.

| Code | Story |
|------|-------|
| HU-CO01 | Roles |
| HU-CO02 | Teams |
| HU-CO03 | – Assignments (Users / Roles / Teams) |
| HU-CO04 | Projects |
| HU-CO05 | Dimensions (Include "Metrics") |
| HU-CO06 | Assignment Dashboard |
| HU-CO07 | – Metrics |

---

### HU-CO01 · Roles
> As a **team manager**, I want to **maintain the catalog of collaboration roles** (Backend,
> Frontend, QA, PO, TL, …) **so that** people can be assigned to a team with a clear role.
- **Data:** `roles` — `code`, `name`, `description`, `icon`
- **UI:** [`collab/roles.astro`](../../ui/src/pages/collab/roles.astro)

### HU-CO02 · Teams
> As a **team manager**, I want to **create teams**, with a lead and links to their chat
> channel and kanban board, **so that** collaboration is organized around real groups.
- **Data:** `teams` — `code`, `name`, `description`, `icon`, `lead` (FK → `users.id`),
  `chat_channel_url`, `kanban_board_url`
- **UI:** [`collab/teams.astro`](../../ui/src/pages/collab/teams.astro)

### HU-CO03 · – Assignments (Users / Roles / Teams)
> As a **team manager**, I want to **assign a user to a team with a role for a validity
> period** **so that** team composition is tracked over time.
- **Data:** `assignments` — `id`, `team`, `user_id`, `role`, `observation`, `valid_from`,
  `valid_to` (open-ended while `NULL`); at most one open assignment per `(team, user_id)`.
  Detail of **HU-CO02**; dates are picked from a calendar control.
- **UI:** [`collab/assignments.astro`](../../ui/src/pages/collab/assignments.astro)

### HU-CO04 · Projects
> As a **team manager**, I want to **register the projects a team owns** (status, repository,
> dates) **so that** work is anchored to concrete deliverables.
- **Data:** `projects` — `code`, `name`, `description`, `team` (FK), `repo_url`, `status`
  (→ `PROJECT_STATUS`: Planned, In Progress, On Hold, Completed), `start_date`, `end_date`,
  `detail`
- **UI:** [`collab/projects.astro`](../../ui/src/pages/collab/projects.astro)

### HU-CO05 · Dimensions (Include "Metrics")
> As an **analyst**, I want to **define measurement dimensions** with a unit and a scale — and
> manage their metrics inline — **so that** adoption is measured on consistent axes.
- **Data:** `dimensions` — `code`, `name`, `description`, `unit` (→ `DIMENSIONS_UNIT`),
  `scale` (FK → `lists.code` where `type='SCALE'`, e.g. `GENAI_DEV_ADOPTION`,
  `GENAI_QA_ADOPTION`). Master-detail over `metrics`; selecting a dimension reloads the
  allowed values from its scale.
- **UI:** [`collab/dimensions.astro`](../../ui/src/pages/collab/dimensions.astro)

### HU-CO06 · Assignment Dashboard
> As a **team member**, I want a **dashboard of my assignment** — team, role, projects and my
> measured dimensions — **so that** I see my collaboration context and progress at a glance.
- **Data:** read view over `assignments` + `teams` + `roles` + `projects` + `metrics`.
- **UI:** [`collab/dashboard.astro`](../../ui/src/pages/collab/dashboard.astro)

### HU-CO07 · – Metrics
> As an **analyst**, I want to **record a metric value for a dimension against an assignment**
> **so that** adoption is measured per person and team over time.
- **Data:** `metrics` — `id`, `dimension` (FK), `assignment` (FK), `value` (free or from the
  dimension's scale), `observation`, `measured_at`. Detail of **HU-CO06**; each row resolves
  its assignment into the owning **team** and **user**.
- **UI:** [`collab/metrics.astro`](../../ui/src/pages/collab/metrics.astro)
