# Asset Library — User Stories

> Module `LIB` · API domain [`api/app/lib`](../../api/app) · DB band 40s
> ([`41-lib-ddl.sql`](../../db/sql/41-lib-ddl.sql)) · Diagram [4-lib.png](../diagrams/4-lib.png)

The Asset Library manages the reusable digital and AI-asset repository: assets are proposed,
reviewed and published through a workflow, then characterized, discussed, voted, related,
favorited, permissioned and versioned. On top of the generic repository, the module exposes
curated catalogs per asset family (prompts, MCPs, agents, flows, skills, assistants, RAG
apps, models).

| Code | Story |
|------|-------|
| HU-LI01 | Asset Repository |
| HU-LI02 | – Propose |
| HU-LI03 | – Details (Include Report Usage) |
| HU-LI04 | –– Favorite |
| HU-LI05 | –– Vote |
| HU-LI06 | –– Discussion (Comments / Questions) |
| HU-LI07 | –– Related Assets |
| HU-LI08 | –– Permission |
| HU-LI09 | –– Versioning (Include Deprecation) |
| HU-LI10 | –– History |
| HU-LI11 | Notifications |
| HU-LI12 | – Review |
| HU-LI13 | – Show Action |
| HU-LI14 | – Modify |
| HU-LI15 | Prompt Gallery |
| HU-LI16 | MCP Directory |
| HU-LI17 | Agent Index |
| HU-LI18 | Agentic Flows |
| HU-LI19 | Skill Catalog |
| HU-LI20 | Assistants |
| HU-LI21 | RAG Apps |
| HU-LI22 | Models |

> The contribution/review workflow runs on the `actions` table via its `type` and
> `workflow_status` (`ASSIGNED` → `NOTIFIED` → `FINISHED`) columns. The full type ×
> status → story matrix is in the [States & Types appendix](appendix-states-and-types.md#asset-contribution--review-workflow-actions).

---

## Asset repository & contribution

### HU-LI01 · Asset Repository
> As a **contributor**, I want to **browse and manage reusable assets** classified by
> taxonomy category **so that** the organization has a single discoverable catalog of AI and
> digital assets.
- **Data:** `assets` — `id`, `name`, `description`, `category` (FK → `categories.code`),
  `reference`, `status` (→ `ASSET_STATUS`: Proposed, Feedback Provided, Published, Rejected,
  Deprecated), `tags` (JSONB), `detail`
- **UI:** [`ui/src/pages/lib/assets.astro`](../../ui/src/pages/lib/assets.astro)

### HU-LI02 · – Propose
> As a **contributor**, I want to **propose a new asset and request a reviewer** **so that**
> it enters the review workflow before being published.
- **Data:** transactionally creates, on save: an `assets` row (`status = PROPOSED`); one
  `characterizations` row per feature in the category's `specifications`; an `actions` row
  for the proposer (`type = PROPOSAL`, `workflow_status = FINISHED`); an `actions` row for
  the chosen reviewer — a user with the `ADMINISTRATIVE` role (`type = REVIEW`,
  `workflow_status = ASSIGNED`); and two `asset_permissions` rows (`access_level = MANAGE`,
  open validity) for the proposer and the reviewer.
- **UI:** propose flow in `lib/assets.astro`

### HU-LI03 · – Details (Include Report Usage)
> As any **user**, I want to **open an asset's detail view** (full description,
> characterizations and activity) and **report that I used it** **so that** I can evaluate it
> for reuse and usage is tracked.
- **Data:** read view over `assets` + `characterizations`; "report usage" inserts an
  `actions` row (`type = USAGE`). Parent of the detail panels HU-LI04…HU-LI10.
- **UI:** detail modal in `lib/assets.astro` (and the curated catalogs below)

### HU-LI04 · –– Favorite
> As any **user**, I want to **favorite an asset** so that I can quickly find the ones I care
> about.
- **Data:** `favorite_assets` — PK `(user_id, asset)`. Detail panel of **HU-LI03**.

### HU-LI05 · –– Vote
> As a **community member**, I want to **vote on an asset** so that the most valuable assets
> surface.
- **Data:** `actions` of `type = VOTE`. Detail panel of **HU-LI03**.

### HU-LI06 · –– Discussion (Comments / Questions)
> As a **community member**, I want to **comment on and ask/answer questions about an asset**
> so that knowledge about it is captured alongside it.
- **Data:** `actions` of `type = COMMENT` / `QUESTION` / `ANSWER`, threaded via `parent`.
  Detail panel of **HU-LI03**.

### HU-LI07 · –– Related Assets
> As a **contributor**, I want to **link an asset to related assets** (depends-on, extends,
> similar-to, …) **so that** users can navigate between connected assets.
- **Data:** `related_assets` — PK `(source, target, type)`, `type` (→ `RELATION_TYPE`),
  `rationale`. Detail panel of **HU-LI03**.

### HU-LI08 · –– Permission
> As an **owner**, I want to **grant view/manage access to users, roles, teams or units**
> **so that** asset visibility and editing are controlled per audience.
- **Data:** `asset_permissions` — `asset`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`: View, Manage), validity window. Detail panel of **HU-LI03**.

### HU-LI09 · –– Versioning (Include Deprecation)
> As an **owner**, I want to **create a new version of an asset, or deprecate it** **so that**
> improvements are tracked without losing history and obsolete assets are retired.
- **Data:** `actions` of `type = VERSIONING` / `DEPRECATION` (`workflow_status = FINISHED`);
  a new version creates a new `assets` row with `reference` to the previous one and a
  `related_assets` link of `type = EXTENDS`; deprecation sets `status = DEPRECATED`. Detail
  panel of **HU-LI03**.

### HU-LI10 · –– History
> As any **user**, I want to **see an asset's activity timeline** (proposal, review, votes,
> comments, versioning, …) **so that** I understand how it evolved.
- **Data:** read-only view over `actions` for the asset, newest first. Detail panel of **HU-LI03**.

---

## Review workflow & notifications

These stories implement the asset contribution/review workflow on `actions`
(`workflow_status` = `ASSIGNED` → `NOTIFIED` → `FINISHED`). See the
[workflow matrix](appendix-states-and-types.md#asset-contribution--review-workflow-actions).

### HU-LI11 · Notifications
> As an **assignee** (reviewer or proposer), I want a **list of my pending workflow actions**
> **so that** I know what needs my attention.
- **Behavior:** lists the user's `actions` grouped by asset whose latest `workflow_status`
  is `ASSIGNED` (shown **bold**) or `NOTIFIED` (not bold, with a dismiss option), for
  `type` in `REVIEW` / `MODIFICATION` / `PUBLICATION` / `REJECTION`. Opening an action routes
  to **HU-LI12 Review** (`REVIEW`), **HU-LI14 Modify** (`MODIFICATION`) or **HU-LI13 Show
  Action** (`PUBLICATION` / `REJECTION`). Dismissing a `NOTIFIED` action removes it from the
  list and inserts the action with `workflow_status = FINISHED`.
- **Data:** `actions` (`type`, `workflow_status`).

### HU-LI12 · – Review
> As a **reviewer**, I want to **review a proposed asset and give feedback, approve or
> reject it** **so that** only vetted assets are published.
- **Behavior:** on open, if the action is `ASSIGNED`, un-bold it in notifications and insert
  the `REVIEW` action as `NOTIFIED`. On save (feedback / approve / reject): insert the
  `REVIEW` action as `FINISHED`; set the asset `status` to `FEEDBACK` / `PUBLISHED` /
  `REJECTED` respectively; and insert a new action for the proposer of `type` `MODIFICATION`
  / `PUBLICATION` / `REJECTION` (respectively) with `workflow_status = ASSIGNED`.
- **Data:** `actions`, `assets.status`.

### HU-LI13 · – Show Action
> As a **proposer**, I want to **see the outcome of my proposal** (published or rejected)
> **so that** I learn the result and clear the notification.
- **Behavior:** on open, if the action is `ASSIGNED`, un-bold it in notifications and insert
  the `PUBLICATION` / `REJECTION` action as `NOTIFIED`.
- **Data:** `actions`.

### HU-LI14 · – Modify
> As a **proposer**, I want to **modify my asset after a reviewer requested changes** and
> resubmit it **so that** the review cycle can continue.
- **Behavior:** on open, if the action is `ASSIGNED`, un-bold it in notifications and insert
  the `MODIFICATION` action as `NOTIFIED`. On save: remove it from notifications and insert
  the `MODIFICATION` action as `FINISHED`; and insert a new action for the reviewer of
  `type = REVIEW`, `workflow_status = ASSIGNED`.
- **Data:** `actions`, `assets`, `characterizations`.

---

## Curated asset catalogs

These are specialized, category-scoped views of the **Asset Repository** (`assets` filtered
by the matching `GEN_AI` taxonomy category). They share the asset data model and the detail
panels above.

### HU-LI15 · Prompt Gallery
> As a **contributor**, I want a **gallery of reusable prompts** so that I can discover and
> reuse proven prompts.
- **Category:** `PROMPTS`

### HU-LI16 · MCP Directory
> As a **contributor**, I want a **directory of MCP servers** so that I can find connectors
> to plug into AI tools.
- **Category:** `MCPS`

### HU-LI17 · Agent Index
> As a **contributor**, I want an **index of agents** so that I can reuse existing agents.
- **Category:** `AGENTS`

### HU-LI18 · Agentic Flows
> As a **contributor**, I want a **catalog of agentic flows** so that multi-step automations
> can be discovered and reused.
- **Category:** `FLOWS`

### HU-LI19 · Skill Catalog
> As a **contributor**, I want a **catalog of skills** so that reusable capabilities are
> findable.
- **Category:** `SKILLS`

### HU-LI20 · Assistants
> As a **contributor**, I want a **catalog of assistants** so that purpose-built assistants
> can be shared.
- **Category:** `ASSISTANTS`

### HU-LI21 · RAG Apps
> As a **contributor**, I want a **catalog of RAG applications** so that retrieval-augmented
> apps can be reused.
- **Category:** `RAG_APPS`

### HU-LI22 · Models
> As a **contributor**, I want a **catalog of models** so that available models are
> documented and discoverable.
- **Category:** `MODELS`
