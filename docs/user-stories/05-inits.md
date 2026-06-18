# Initiatives — User Stories

> Module `INITS` · API domain [`api/app/inits`](../../api/app) *(stub)* · DB band 50s
> ([`51-inits-ddl.sql`](../../db/sql/51-inits-ddl.sql)) · Diagram [5-inits.png](../diagrams/5-inits.png)

Initiatives supports the lifecycle of AI-adoption opportunities: registering a proposal,
diagnosing it against evaluation criteria, exploring and reviewing it collaboratively, and
promoting selected initiatives into reusable organizational assets.

| Code | Story |
|------|-------|
| HU-IN01 | Criterias |
| HU-IN02 | Propose |
| HU-IN03 | Explore |
| HU-IN04 | – Diagnosis |
| HU-IN05 | – Review Diagnosis |
| HU-IN06 | – Participations |
| HU-IN07 | – Vote |
| HU-IN08 | – Comment |
| HU-IN09 | – Related Assets |
| HU-IN10 | – Favorite |
| HU-IN11 | – Permission |

> Initiative lifecycle (`INITIATIVE_STATUS`), collaboration types (`COLLAB_TYPE`) and the six
> evaluation criteria with their 1–3 scales are detailed in the
> [States & Types appendix](appendix-states-and-types.md).

---

### HU-IN01 · Criterias
> As an **evaluation owner**, I want to **maintain the evaluation criteria** (clarity, support
> objective, complexity, data & integrations, risk & impact, sustainability) each with a
> scoring scale **so that** initiatives are diagnosed consistently.
- **Data:** `criterias` — `code`, `name`, `list` (FK → `lists.code` where `type='CRITERIA'`).
  Seeded: `CLARITY_MATURITY`, `SUPPORT_OBJECTIVE`, `COMPLEXITY`, `DATA_INTEGRATIONS`,
  `RISK_IMPACT`, `SUSTAINABILITY` (each with a 1–3 scale, en/es).

### HU-IN02 · Propose
> As a **collaborator**, I want to **propose an initiative** with its expected impact and
> priority **so that** AI-adoption opportunities are captured and triaged.
- **Data:** `initiatives` — `id`, `name`, `expected_impact` (→ `EXPECTED_IMPACT`),
  `priority_level` (→ `PRIORITY_LEVEL`), `status` (→ `INITIATIVE_STATUS`), `tags` (JSONB),
  `score`

### HU-IN03 · Explore
> As a **collaborator**, I want to **explore an initiative** through its assessment,
> exploration, prototyping and implementation activities **so that** its viability is worked
> through collaboratively.
- **Data:** `collaborations` — `init`, `user_id`, `type` (→ `COLLAB_TYPE`), `content`,
  `parent` (threaded)

### HU-IN04 · – Diagnosis
> As a **proposer**, I want to **score an initiative against each criterion** so that it gets
> an overall diagnostic score.
- **Data:** `diagnostics` — PK `(init, criteria)`, `creator_score`, `reviewer_score`,
  `rationale`. Detail of **HU-IN02**.

### HU-IN05 · – Review Diagnosis
> As a **reviewer**, I want to **review the diagnosis and add my own scores** so that the
> evaluation is validated by a second party.
- **Data:** `diagnostics.reviewer_score`. Detail of **HU-IN04**.

### HU-IN06 · – Participations
> As a **community member**, I want to **participate around an initiative** (questions,
> answers, requests) so that discussion stays attached to it.
- **Data:** `collaborations` (participation-type entries, threaded via `parent`).

### HU-IN07 · – Vote
> As a **community member**, I want to **vote on an initiative** so that priority reflects
> interest.
- **Data:** `collaborations` (vote-type entries).

### HU-IN08 · – Comment
> As a **community member**, I want to **comment on an initiative** so that I can give
> feedback.
- **Data:** `collaborations` (comment-type entries, threaded via `parent`).

### HU-IN09 · – Related Assets
> As a **collaborator**, I want to **link an initiative to related initiatives/assets** so
> that connected work is navigable.
- **Data:** `related_inits` — PK `(source, target)`, `type` (→ `RELATION_TYPE`), `rationale`.

### HU-IN10 · – Favorite
> As any **user**, I want to **favorite an initiative** so that I can track the ones I care
> about.
- **Data:** `favorite_inits` — PK `(user_id, init)`.

### HU-IN11 · – Permission
> As an **owner**, I want to **grant view/manage access to users, roles, teams or units** so
> that initiative visibility is controlled.
- **Data:** `init_permissions` — `init`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`), validity window.
