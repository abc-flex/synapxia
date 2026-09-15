# Initiatives — User Stories

> Module `INITS` · API domain [`api/app/inits`](../../api/app) · DB band 50s
> ([`51-inits-ddl.sql`](../../db/sql/51-inits-ddl.sql)) · Diagram [5-inits.png](../diagrams/5-inits.png)

Initiatives covers the lifecycle of AI-adoption opportunities: an initiative is **activated →
diagnosed → accepted or rejected → delivered**, then archived. It mirrors the AI Library's
contribution workflow, but over the `collaborations` table and with a **diagnosis against
scored criteria** instead of a review. Accepted initiatives feed the library through
[Related Inits](04-lib.md#hu-li09--asset-tab-related-inits).

| Code | Story | | Code | Story |
|------|-------|-|------|-------|
| HU-IN01 | Criterias | | HU-IN10 | [Initiative Tab] Permissions |
| HU-IN02 | Initiative Management | | HU-IN11 | [Initiative Tab] Discussion |
| HU-IN03 | – Edit Initiative (Include Delivery / Archiving) | | HU-IN12 | [Initiative Tab] History |
| HU-IN04 | Explore Initiatives (Include Favorite / Vote) | | HU-IN13 | [Notifications] Initiative Notifications |
| HU-IN05 | – Propose Initiative | | HU-IN14 | [Account Menu] My Initiative Requests |
| HU-IN06 | – Initiative Detail | | HU-IN15 | – Diagnosis of the Initiative |
| HU-IN07 | [Initiative Tab] Core Fields | | HU-IN16 | – Modify Initiative |
| HU-IN08 | [Initiative Tab] Diagnosis Questions | | HU-IN17 | – Initiative Request Detail |
| HU-IN09 | [Initiative Tab] Related Assets | | | |

> The activation/diagnosis workflow runs on the `collaborations` table through `type` and
> `workflow_status` (`ASSIGNED` → `NOTIFIED` → `FINISHED`). Full matrix:
> [Initiative Collaboration Workflows](states-and-types.md#initiative-collaboration-workflows-collaborations-table).
> What each tab does per parent story:
> [Initiative tab options](states-and-types.md#initiative-tab-options-by-user-story).

---

## Criteria & management

### HU-IN01 · Criterias
> As an **evaluation owner**, I want to **maintain the diagnosis criteria**, each backed by its
> own scoring scale, **so that** every initiative is evaluated against the same questions.
- **Data:** `criterias` — `code`, `name`, `description`, `list` (FK → `lists.code` where
  `type='CRITERIA'`). Seeded: `CLARITY_MATURITY`, `SUPPORT_OBJECTIVE`, `COMPLEXITY`,
  `DATA_INTEGRATIONS`, `RISK_IMPACT`, `SUSTAINABILITY`, each with a bilingual 1–3 scale.
- **UI:** [`inits/criterias.astro`](../../ui/src/pages/inits/criterias.astro)

### HU-IN02 · Initiative Management
> As an **initiative owner**, I want to **manage the initiatives I am responsible for**,
> filtered by status, type, priority, impact, privileges and favorites, **so that** the
> portfolio stays curated across the whole lifecycle.
- **Data:** `initiatives` — `id`, `name`, `description`, `expected_impact`
  (→ `EXPECTED_IMPACT`), `priority_level` (→ `PRIORITY_LEVEL`), `type` (→ `INITIATIVE_TYPE`:
  Exploration, Prototyping, Implementation), `status` (→ `INITIATIVE_STATUS`: Activated,
  Feedback Provided, Accepted, Rejected, In Progress, Delivered, Archived), `reference`,
  `tags` (JSONB), `detail`, `score`. Scoped by `init_permissions`.
- **Option:** `INITS.INITIATIVES` → `/inits/initiatives`

### HU-IN03 · – Edit Initiative (Include Delivery / Archiving)
> As an **initiative owner**, I want to **edit an initiative one tab at a time**, **record its
> delivery** when the work is done and **archive** it when it is no longer relevant, **so
> that** the portfolio reflects reality.
- **Behavior:** each tab saves its own slice — core fields, related assets, permissions;
  diagnosis questions and history are read-only here. Moving the initiative to *Delivered*
  records a `DELIVERY` collaboration; archiving sets `status = ARCHIVED` and records an
  `ARCHIVING` collaboration. Both are terminal records (`workflow_status = FINISHED`), not
  assignments.
- **Data:** `initiatives`, `collaborations` (`DELIVERY` / `ARCHIVING`)
- Detail of **HU-IN02**.

---

## Explore Initiatives

### HU-IN04 · Explore Initiatives (Include Favorite / Vote)
> As a **collaborator**, I want to **browse the initiative portfolio**, search and filter it,
> **favorite** the ones I follow and **vote** on them, **so that** I can see where the
> organization is investing and signal what matters.
- **Data:** `initiatives` + `favorite_inits` (PK `(user_id, init)`) + `collaborations` of
  `type = VOTE` (one active vote per user and initiative). Scoped by `init_permissions`.
- **Option:** `INITS.EXPLORE` → `/inits/explore`

### HU-IN05 · – Propose Initiative
> As a **collaborator**, I want to **propose (activate) an initiative and request a diagnosis**
> **so that** it enters the evaluation workflow.
- **Behavior:** a wizard over the initiative tabs — **Core Fields → Diagnosis Questions**, the
  second step scoring every criterion and submitting the request.
- **Data:** one transaction inserts — an `initiatives` row (`status = ACTIVATED`); one
  `diagnostics` row per criterion carrying the proposer's `creator_score`; a `collaborations`
  row for the proposer (`type = ACTIVATION`, `workflow_status = FINISHED`); a `collaborations`
  row for the chosen reviewer (`type = DIAGNOSIS`, `workflow_status = ASSIGNED`); and
  `init_permissions` rows (`access_level = MANAGE`, open validity) for the proposer and the
  reviewer.
- Detail of **HU-IN04**.

### HU-IN06 · – Initiative Detail
> As any **user**, I want to **open an initiative's full detail** — description, scoring,
> related assets, discussion and history — **so that** I understand the opportunity and can
> contribute to it.
- **Behavior:** read-mostly view. Core fields, diagnosis questions, related assets and history
  are read-only; Discussion stays fully interactive; Permissions is not shown.
- **Data:** read view over `initiatives` + `diagnostics` + `asset_inits` + `collaborations`.
- Detail of **HU-IN04**.

---

## Initiative tabs

The same six tabs back every initiative surface; what each one *does* depends on the parent
story (Edit Initiative / Propose Initiative / Initiative Detail) — see the
[initiative tab matrix](states-and-types.md#initiative-tab-options-by-user-story).

### HU-IN07 · [Initiative Tab] Core Fields
> As a **collaborator**, I want to **describe the initiative** — name, description, type,
> expected impact, priority, reference, tags and detail — **so that** the opportunity is clear
> to whoever evaluates it.
- **Data:** `initiatives` — `name`, `description`, `type`, `expected_impact`, `priority_level`,
  `reference`, `status`, `tags`, `detail`
- **Options:** Edit Initiative → *Save core fields* · Propose Initiative → *Go to diagnosis
  questions* · Initiative Detail → read-only

### HU-IN08 · [Initiative Tab] Diagnosis Questions
> As a **collaborator**, I want to **score the initiative against each criterion** with a
> rationale — and, as a **reviewer**, to add my own score beside it — **so that** the decision
> rests on a shared, comparable evaluation.
- **Data:** `diagnostics` — PK `(init, criteria)`, `creator_score` (the proposer's answer),
  `reviewer_score` (filled during the diagnosis), `rationale`. Allowed values come from the
  criterion's own scale (`criterias.list`); the resulting total feeds `initiatives.score`.
- **Options:** Edit Initiative → read-only · Propose Initiative → *Request diagnosis* (final
  step) · Initiative Detail → read-only

### HU-IN09 · [Initiative Tab] Related Assets
> As a **collaborator**, I want to **link an initiative to the library assets it uses or
> produces** **so that** reuse between initiatives and assets is visible.
- **Data:** `asset_inits` — PK `(asset, init, type)`, `type` (→ `RELATION_TYPE`), `rationale`.
  The same table backs [HU-LI09](04-lib.md#hu-li09--asset-tab-related-inits) from the asset side.
- **Options:** Edit Initiative → *Save related assets* · Propose Initiative → not applicable ·
  Initiative Detail → read-only

### HU-IN10 · [Initiative Tab] Permissions
> As an **initiative owner**, I want to **grant view or manage access to users, roles,
> projects, teams, units or everyone**, for a validity window, **so that** visibility and
> editing are controlled per audience.
- **Data:** `init_permissions` — `init`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`), `valid_from`, `valid_to`. A grant is **revoked** by
  stamping `valid_to`, never deleted.
- **Options:** Edit Initiative → *Save permissions* · Propose Initiative → not applicable ·
  Initiative Detail → not applicable

### HU-IN11 · [Initiative Tab] Discussion
> As a **community member**, I want to **comment on an initiative and ask or answer questions
> about it** **so that** the conversation stays attached to the opportunity.
- **Data:** `collaborations` of `type = COMMENT` / `QUESTION` / `ANSWER`; answers are threaded
  to their question through `parent`.
- **Options:** Edit Initiative → read-only · Propose Initiative → not applicable · Initiative
  Detail → fully interactive

### HU-IN12 · [Initiative Tab] History
> As any **user**, I want to **see an initiative's activity timeline** — activation, diagnosis,
> acceptance or rejection, votes, comments, delivery, archiving — **so that** I understand how
> it evolved.
- **Data:** read-only view over `collaborations` for the initiative, newest first, with the
  acting user.
- **Options:** read-only wherever it is shown (Edit Initiative, Initiative Detail).

---

## Diagnosis workflow

These stories implement the activation/diagnosis loop on `collaborations`. See the
[workflow matrix](states-and-types.md#initiative-collaboration-workflows-collaborations-table).

### HU-IN13 · [Notifications] Initiative Notifications
> As an **assignee** (reviewer or proposer), I want a **notification bell listing the
> collaborations waiting on me** **so that** I know what needs my attention.
- **Behavior:** lists the user's `collaborations` grouped by initiative whose **latest**
  `workflow_status` is `ASSIGNED` (bold) or `NOTIFIED` (not bold), for `type` in `DIAGNOSIS` /
  `MODIFICATION` / `ACCEPTANCE` / `REJECTION` / `DELIVERY`. Opening one routes to **HU-IN15
  Diagnosis of the Initiative** (`DIAGNOSIS`), **HU-IN16 Modify Initiative** (`MODIFICATION`)
  or **HU-IN17 Initiative Request Detail** (`ACCEPTANCE` / `REJECTION` / `DELIVERY`).
  Dismissing is offered only for the informational outcomes and inserts that collaboration with
  `workflow_status = FINISHED`.
- **Data:** `collaborations` (`type`, `workflow_status`, `content`)

### HU-IN14 · [Account Menu] My Initiative Requests
> As a **reviewer or proposer**, I want a **durable list of my initiative requests** — open and
> already resolved — **so that** I can find my pending work without depending on a transient
> notification.
- **Behavior:** lists the user's `collaborations` grouped by initiative with status `ASSIGNED`
  (bold), `NOTIFIED` (plain) or `FINISHED` (muted), for `type` in `DIAGNOSIS` / `MODIFICATION`
  / `ACCEPTANCE` / `REJECTION` / `DELIVERY`. Every `FINISHED` collaboration — and every
  `ACCEPTANCE` / `REJECTION` / `DELIVERY` — opens **HU-IN17**; the rest open **HU-IN15**
  (`DIAGNOSIS`) or **HU-IN16** (`MODIFICATION`). Reached from the account menu's *My Workspace*
  section.
- **Data:** `collaborations` (`type`, `workflow_status`)

### HU-IN15 · – Diagnosis of the Initiative
> As a **reviewer**, I want to **score an activated initiative against the criteria and accept
> it, reject it or request changes** **so that** only viable initiatives proceed.
- **Behavior:** on open, an `ASSIGNED` collaboration is un-bolded in the notifications and
  re-inserted as `NOTIFIED`. On decision, one transaction writes the `reviewer_score` and
  rationale per criterion, inserts the `DIAGNOSIS` collaboration as `FINISHED`, sets the
  initiative `status` to `ACCEPTED` / `REJECTED` / `FEEDBACK`, and inserts a collaboration for
  the **proposer** of `type` `ACCEPTANCE` / `REJECTION` / `MODIFICATION` with
  `workflow_status = ASSIGNED` and the feedback in `content`.
- **Data:** `collaborations`, `diagnostics` (`creator_score` / `reviewer_score`),
  `initiatives.status` / `.score`
- Detail of **HU-IN14**.

### HU-IN16 · – Modify Initiative
> As a **proposer**, I want to **apply the changes a reviewer asked for and resubmit** **so
> that** the diagnosis cycle can continue.
- **Behavior:** on open, an `ASSIGNED` collaboration is un-bolded and re-inserted as
  `NOTIFIED`. On save, one transaction updates the initiative and its diagnosis answers in
  place, inserts the `MODIFICATION` collaboration as `FINISHED`, returns the initiative to
  `ACTIVATED`, and re-arms the **same reviewer** with a new `DIAGNOSIS` collaboration as
  `ASSIGNED`.
- **Data:** `collaborations`, `initiatives`, `diagnostics`
- Detail of **HU-IN14**.

### HU-IN17 · – Initiative Request Detail
> As a **proposer**, I want to **see the outcome of my initiative** — accepted, rejected or
> delivered, with the reviewer's message — **so that** I learn the result and can clear the
> notification.
- **Behavior:** read-only outcome card. On open, an `ASSIGNED` collaboration is un-bolded and
  re-inserted as `NOTIFIED`; dismissing inserts it as `FINISHED`.
- **Data:** `collaborations`, `initiatives`
- Detail of **HU-IN14**.
