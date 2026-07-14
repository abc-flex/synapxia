# Initiatives — User Stories

> Module `INITS` · API domain [`api/app/inits`](../../api/app) *(stub)* · DB band 50s
> ([`51-inits-ddl.sql`](../../db/sql/51-inits-ddl.sql)) · Diagram [5-inits.png](../diagrams/5-inits.png)

Initiatives supports the lifecycle of AI-adoption opportunities: an initiative is activated,
diagnosed against evaluation criteria, accepted or rejected, and delivered — mirroring the
Library's contribution/review workflow but over the `collaborations` table. Selected
initiatives can be promoted into reusable organizational assets.

| Code | Story |
|------|-------|
| HU-IN01 | Criterias |
| HU-IN02 | Explore |
| HU-IN03 | – Propose (Activation) |
| HU-IN04 | – Details (Include Delivery) |
| HU-IN05 | –– Favorite |
| HU-IN06 | –– Vote |
| HU-IN07 | –– Discussion (Comments / Questions) |
| HU-IN08 | –– Related Inits |
| HU-IN09 | –– Permission |
| HU-IN10 | –– Versioning (Include Archiving) |
| HU-IN11 | –– History |
| HU-IN12 | Notifications |
| HU-IN13 | – Diagnosis |
| HU-IN14 | – Show Collab |

> The activation/diagnosis workflow runs on the `collaborations` table via its `type` and
> `workflow_status` (`ASSIGNED` → `NOTIFIED` → `FINISHED`) columns. The full type ×
> status → story matrix is in the [States & Types appendix](appendix-states-and-types.md#initiative-collaboration-workflow-collaborations).

---

## Criteria & exploration

### HU-IN01 · Criterias
> As an **evaluation owner**, I want to **maintain the evaluation criteria** (clarity, support
> objective, complexity, data & integrations, risk & impact, sustainability) each with a
> scoring scale **so that** initiatives are diagnosed consistently.
- **Data:** `criterias` — `code`, `name`, `list` (FK → `lists.code` where `type='CRITERIA'`).
  Seeded: `CLARITY_MATURITY`, `SUPPORT_OBJECTIVE`, `COMPLEXITY`, `DATA_INTEGRATIONS`,
  `RISK_IMPACT`, `SUSTAINABILITY` (each with a 1–3 scale, en/es).

### HU-IN02 · Explore
> As a **collaborator**, I want to **explore and browse initiatives** **so that** I can find
> opportunities, see their status and decide where to contribute.
- **Data:** read/browse over `initiatives` — `id`, `name`, `expected_impact`
  (→ `EXPECTED_IMPACT`), `priority_level` (→ `PRIORITY_LEVEL`), `status`
  (→ `INITIATIVE_STATUS`: Activated, Accepted, Rejected, In Progress, Delivered, Archived),
  `type` (→ `INITIATIVE_TYPE`), `tags` (JSONB), `score`. Parent of HU-IN03…HU-IN11.

### HU-IN03 · – Propose (Activation)
> As a **collaborator**, I want to **propose (activate) an initiative and request a
> reviewer** **so that** it enters the diagnosis workflow.
- **Data:** transactionally creates, on save: an `initiatives` row (`status = ACTIVATED`); a
  `collaborations` row for the proposer (`type = ACTIVATION`, `workflow_status = FINISHED`);
  a `collaborations` row for the chosen reviewer — a user with the `ADMINISTRATIVE` role
  (`type = DIAGNOSIS`, `workflow_status = ASSIGNED`); and two `init_permissions` rows
  (`access_level = MANAGE`, open validity) for the proposer and the reviewer.

### HU-IN04 · – Details (Include Delivery)
> As any **user**, I want to **open an initiative's detail view** and, when work is complete,
> **record its delivery** **so that** I can follow it and close the loop.
- **Data:** read view over `initiatives` + `diagnostics`; "delivery" inserts a
  `collaborations` row for the proposer (`type = DELIVERY`, `workflow_status = ASSIGNED`).
  Parent of the detail panels HU-IN05…HU-IN11.

### HU-IN05 · –– Favorite
> As any **user**, I want to **favorite an initiative** so that I can track the ones I care
> about.
- **Data:** `favorite_inits` — PK `(user_id, init)`. Detail panel of **HU-IN04**.

### HU-IN06 · –– Vote
> As a **community member**, I want to **vote on an initiative** so that priority reflects
> interest.
- **Data:** `collaborations` of `type = VOTE`. Detail panel of **HU-IN04**.

### HU-IN07 · –– Discussion (Comments / Questions)
> As a **community member**, I want to **comment on and ask/answer questions about an
> initiative** so that discussion stays attached to it.
- **Data:** `collaborations` of `type = COMMENT` / `QUESTION` / `ANSWER`, threaded via
  `parent`. Detail panel of **HU-IN04**.

### HU-IN08 · –– Related Inits
> As a **collaborator**, I want to **link an initiative to related initiatives** so that
> connected work is navigable.
- **Data:** `related_inits` — PK `(source, target)`, `type` (→ `RELATION_TYPE`), `rationale`.
  Detail panel of **HU-IN04**.

### HU-IN09 · –– Permission
> As an **owner**, I want to **grant view/manage access to users, roles, teams or units** so
> that initiative visibility is controlled per audience.
- **Data:** `init_permissions` — `init`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`), validity window. Detail panel of **HU-IN04**.

### HU-IN10 · –– Versioning (Include Archiving)
> As an **owner**, I want to **create a new version of an initiative, or archive it** **so
> that** evolution is tracked and obsolete initiatives are retired.
- **Data:** `collaborations` of `type = VERSIONING` / `ARCHIVING`; archiving sets
  `status = ARCHIVED`. Detail panel of **HU-IN04**.

### HU-IN11 · –– History
> As any **user**, I want to **see an initiative's activity timeline** (activation,
> diagnosis, votes, comments, delivery, …) **so that** I understand how it evolved.
- **Data:** read-only view over `collaborations` for the initiative, newest first. Detail
  panel of **HU-IN04**.

---

## Diagnosis workflow & notifications

These stories implement the activation/diagnosis workflow on `collaborations`
(`workflow_status` = `ASSIGNED` → `NOTIFIED` → `FINISHED`). See the
[workflow matrix](appendix-states-and-types.md#initiative-collaboration-workflow-collaborations).

### HU-IN12 · Notifications
> As an **assignee** (reviewer or proposer), I want a **list of my pending workflow
> collaborations** **so that** I know what needs my attention.
- **Behavior:** lists the user's `collaborations` grouped by initiative whose latest
  `workflow_status` is `ASSIGNED` (shown **bold**) or `NOTIFIED` (not bold, with a dismiss
  option), for `type` in `DIAGNOSIS` / `ACCEPTANCE` / `REJECTION` / `DELIVERY`. Opening one
  routes to **HU-IN13 Diagnosis** (`DIAGNOSIS`) or **HU-IN14 Show Collab** (`ACCEPTANCE` /
  `REJECTION` / `DELIVERY`). Dismissing a `NOTIFIED` collaboration removes it from the list
  and inserts the collaboration with `workflow_status = FINISHED`.
- **Data:** `collaborations` (`type`, `workflow_status`).

### HU-IN13 · – Diagnosis
> As a **reviewer**, I want to **diagnose an activated initiative against the criteria and
> accept or reject it** **so that** only viable initiatives proceed.
- **Behavior:** on open, if the collaboration is `ASSIGNED`, un-bold it in notifications and
  insert the `DIAGNOSIS` collaboration as `NOTIFIED`. On save (accept / reject): insert the
  `DIAGNOSIS` collaboration as `FINISHED`; set the initiative `status` to `ACCEPTED` /
  `REJECTED` respectively; and insert a new collaboration for the proposer of `type`
  `ACCEPTANCE` / `REJECTION` (respectively) with `workflow_status = ASSIGNED`.
- **Data:** `collaborations`, `diagnostics` (`creator_score` / `reviewer_score` per
  criterion), `initiatives.status`.

### HU-IN14 · – Show Collab
> As a **proposer**, I want to **see the outcome of my initiative** (accepted, rejected or
> delivered) **so that** I learn the result and clear the notification.
- **Behavior:** on open, if the collaboration is `ASSIGNED`, un-bold it in notifications and
  insert the `ACCEPTANCE` / `REJECTION` / `DELIVERY` collaboration as `NOTIFIED`.
- **Data:** `collaborations`.
