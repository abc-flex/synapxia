# Asset Library — User Stories

> Module `LIB` · API domain [`api/app/lib`](../../api/app) · DB band 40s
> ([`41-lib-ddl.sql`](../../db/sql/41-lib-ddl.sql)) · Diagram [4-lib.png](../diagrams/4-lib.png)

The Asset Library manages the reusable digital and AI-asset repository: every asset can be
characterized, reviewed, versioned, discussed, related to other assets, favorited and
permissioned. On top of the generic repository, the module exposes curated catalogs per
asset family (prompts, MCPs, agents, flows, skills, assistants, RAG apps, models).

| Code | Story |
|------|-------|
| HU-LI01 | Asset Repository |
| HU-LI02 | – Characterization |
| HU-LI03 | – Review |
| HU-LI04 | – Review Suggestions |
| HU-LI05 | – Versioning |
| HU-LI06 | – Participations |
| HU-LI07 | – Vote |
| HU-LI08 | – Comment |
| HU-LI09 | – Related Assets |
| HU-LI10 | – Favorite |
| HU-LI11 | – Permission |
| HU-LI12 | Prompt Gallery |
| HU-LI13 | MCP Directory |
| HU-LI14 | Agent Index |
| HU-LI15 | Agentic Flows |
| HU-LI16 | Skill Catalog |
| HU-LI17 | Assistants |
| HU-LI18 | RAG Apps |
| HU-LI19 | Models |

> Lifecycle states (`ASSET_STATUS`) and action types (`ACTION_TYPE`, used by review,
> versioning, participations, vote and comment) are described in the
> [States & Types appendix](appendix-states-and-types.md).

---

## Asset repository & its details

### HU-LI01 · Asset Repository
> As a **contributor**, I want to **register and browse reusable assets** classified by
> taxonomy category **so that** the organization has a single discoverable catalog of AI and
> digital assets.
- **Data:** `assets` — `id`, `name`, `description`, `category` (FK → `categories.code`),
  `reference`, `status` (→ `ASSET_STATUS`), `tags` (JSONB), `detail`
- **UI:** [`ui/src/pages/lib/assets.astro`](../../ui/src/pages/lib/assets.astro)
  (tabbed modal: core fields + Characterizations + Related Assets + favorite star)

### HU-LI02 · – Characterization
> As a **contributor**, I want to **set feature values for an asset** so that it is described
> against the features its category expects.
- **Data:** `characterizations` — PK `(asset, feature)`, `value`, `detail`. Detail of **HU-LI01**.
- **UI:** Characterizations tab in `lib/assets.astro`

### HU-LI03 · – Review
> As a **reviewer** (MANAGE access), I want to **review an asset and set its outcome**
> (publish, reject, request changes) **so that** only vetted assets reach a published state.
- **Data:** `actions` rows of type `2-REVIEW` (and resulting `3-PUBLICATION` / `4-REJECTION`);
  asset `status` transitions per `ASSET_STATUS`.

### HU-LI04 · – Review Suggestions
> As a **reviewer**, I want to **record suggestions during review** so that the owner knows
> what to change before the asset is published.
- **Data:** `actions` (review feedback entries linked via `parent`).

### HU-LI05 · – Versioning
> As an **owner**, I want to **create a new version of an asset** so that improvements are
> tracked without losing the original.
- **Data:** `actions` of type `6-VERSIONING`; a new `assets` row with `reference` to the
  previous one plus a `related_assets` link of type `EXTENDS`.

### HU-LI06 · – Participations
> As a **community member**, I want to **participate around an asset** (questions, answers,
> requests) so that knowledge about it is captured alongside it.
- **Data:** `actions` of types `6-QUESTION` / `6-ANSWER` / `6-REQUEST` (threaded via `parent`).

### HU-LI07 · – Vote
> As a **community member**, I want to **vote on an asset** so that the most valuable assets
> surface.
- **Data:** `actions` of type `6-VOTE`.

### HU-LI08 · – Comment
> As a **community member**, I want to **comment on an asset** so that I can give feedback or
> share usage context.
- **Data:** `actions` of type `6-COMMENT` (threaded via `parent`).

### HU-LI09 · – Related Assets
> As a **contributor**, I want to **link an asset to related assets** (depends-on, extends,
> similar-to, …) **so that** users can navigate between connected assets.
- **Data:** `related_assets` — PK `(source, target)`, `type` (→ `RELATION_TYPE`), `rationale`.
  Detail of **HU-LI01**.
- **UI:** Related Assets tab in `lib/assets.astro`

### HU-LI10 · – Favorite
> As any **user**, I want to **favorite an asset** so that I can quickly find the ones I care
> about.
- **Data:** `favorite_assets` — PK `(user_id, asset)`. Detail of **HU-LI01**.
- **UI:** Favorite star in the asset modal header in `lib/assets.astro`

### HU-LI11 · – Permission
> As an **owner**, I want to **grant view/manage access to users, roles, teams or units**
> **so that** asset visibility and editing are controlled per audience.
- **Data:** `asset_permissions` — `asset`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`: View, Manage), validity window.

---

## Curated asset catalogs

These are specialized, category-scoped views of the **Asset Repository** (`assets` filtered
by the matching `GEN_AI` taxonomy category). They share the asset data model and its detail
features above.

### HU-LI12 · Prompt Gallery
> As a **contributor**, I want a **gallery of reusable prompts** so that I can discover and
> reuse proven prompts.
- **Category:** `PROMPTS`

### HU-LI13 · MCP Directory
> As a **contributor**, I want a **directory of MCP servers** so that I can find connectors
> to plug into AI tools.
- **Category:** `MCPS`

### HU-LI14 · Agent Index
> As a **contributor**, I want an **index of agents** so that I can reuse existing agents.
- **Category:** `AGENTS`

### HU-LI15 · Agentic Flows
> As a **contributor**, I want a **catalog of agentic flows** so that multi-step automations
> can be discovered and reused.
- **Category:** `FLOWS`

### HU-LI16 · Skill Catalog
> As a **contributor**, I want a **catalog of skills** so that reusable capabilities are
> findable.
- **Category:** `SKILLS`

### HU-LI17 · Assistants
> As a **contributor**, I want a **catalog of assistants** so that purpose-built assistants
> can be shared.
- **Category:** `ASSISTANTS`

### HU-LI18 · RAG Apps
> As a **contributor**, I want a **catalog of RAG applications** so that retrieval-augmented
> apps can be reused.
- **Category:** `RAG_APPS`

### HU-LI19 · Models
> As a **contributor**, I want a **catalog of models** so that available models are
> documented and discoverable.
- **Category:** `MODELS`
