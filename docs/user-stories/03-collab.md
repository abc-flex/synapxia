# Collaboration — User Stories

> Module `COLLAB` · API domain [`api/app/collab`](../../api/app) · DB band 30s
> ([`31-collab-ddl.sql`](../../db/sql/31-collab-ddl.sql)) · Diagram [3-collab.png](../diagrams/3-collab.png)

Collaboration provides the structures to coordinate AI-adoption work across the
organization: teams, the roles people play, their assignments, the projects teams own, the
dimensions used to measure adoption, and the metrics recorded against assignments.

| Code | Story |
|------|-------|
| HU-CO01 | Roles |
| HU-CO02 | Teams |
| HU-CO03 | – Assignments (Users / Roles / Teams) |
| HU-CO04 | Projects |
| HU-CO05 | Dimensions (Include Metrics) |
| HU-CO06 | Assignment Dashboard |
| HU-CO07 | – Metrics |

---

### HU-CO01 · Roles
> As a **team manager**, I want to **maintain the catalog of collaboration roles** (Backend,
> Frontend, QA, PO, TL, …) **so that** people can be assigned to teams with a clear role.
- **Data:** `roles` — `code`, `name`, `description`, `icon`
- **UI:** [`ui/src/pages/collab/roles.astro`](../../ui/src/pages/collab/roles.astro)

### HU-CO02 · Teams
> As a **team manager**, I want to **create teams** (with an optional lead and links to their
> chat channel and kanban board) **so that** collaboration is organized around real groups.
- **Data:** `teams` — `code`, `name`, `lead` (FK → `users.id`), `chat_channel_url`,
  `kanban_board_url`
- **UI:** [`ui/src/pages/collab/teams.astro`](../../ui/src/pages/collab/teams.astro)

### HU-CO03 · – Assignments (Users / Roles / Teams)
> As a **team manager**, I want to **assign a user to a team with a role for a validity
> period** **so that** team composition is tracked over time (with at most one active
> assignment per user per team).
- **Data:** `assignments` — `id`, `user_id`, `team`, `role`, `valid_from`, `valid_to`;
  unique active assignment per `(team, user_id)` while `valid_to IS NULL`. Detail of **HU-CO02**.
- **UI:** [`ui/src/pages/collab/assignments.astro`](../../ui/src/pages/collab/assignments.astro)

### HU-CO04 · Projects
> As a **team manager**, I want to **register the projects a team owns** (with status, repo
> and dates) **so that** initiatives and work are anchored to concrete deliverables.
- **Data:** `projects` — `code`, `name`, `team` (FK), `repo_url`, `status` (→ `PROJECT_STATUS`:
  Planned, In Progress, On Hold, Completed), `start_date`, `end_date`
- **UI:** [`ui/src/pages/collab/projects.astro`](../../ui/src/pages/collab/projects.astro)

### HU-CO05 · Dimensions (Include Metrics)
> As an **analyst**, I want to **define measurement dimensions** with a unit and a scale —
> and manage their metrics inline — **so that** adoption can be measured on consistent axes.
- **Data:** `dimensions` — `code`, `name`, `unit` (→ `DIMENSIONS_UNIT`), `scale` (FK →
  `lists.code` where `type='SCALE'`, e.g. `GENAI_DEV_ADOPTION`, `GENAI_QA_ADOPTION`);
  master-detail over `metrics` (see **HU-CO07**)
- **UI:** [`ui/src/pages/collab/dimensions.astro`](../../ui/src/pages/collab/dimensions.astro)

### HU-CO06 · Assignment Dashboard
> As a **team member**, I want a **dashboard of my assignment** (team, role, projects and my
> metrics) **so that** I see my collaboration context and progress at a glance.
- **Data:** read view over `assignments` + `teams` + `metrics`.
- **UI:** [`ui/src/pages/collab/assignment.astro`](../../ui/src/pages/collab/assignment.astro)

### HU-CO07 · – Metrics
> As an **analyst**, I want to **record a metric value for a dimension against an assignment**
> **so that** adoption is measured per person/team over time.
- **Data:** `metrics` — `id`, `dimension` (FK), `assignment` (FK), `value`, `measured_at`.
  Detail of **HU-CO05** (master-detail: dimension → metrics).
- **UI:** [`ui/src/pages/collab/metrics.astro`](../../ui/src/pages/collab/metrics.astro)
