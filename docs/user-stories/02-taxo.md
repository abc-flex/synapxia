# Asset Taxonomy — User Stories

> Module `TAXO` · API domain [`api/app/taxo`](../../api/app) · DB band 20s
> ([`21-taxo-ddl.sql`](../../db/sql/21-taxo-ddl.sql)) · Diagram [2-taxo.png](../diagrams/2-taxo.png)

Asset Taxonomy defines the classification framework used across SynapxIA: the category
tree, the features (metadata attributes) an asset can have, and the per-category
specifications that say which features apply and with what defaults.

| Code | Story |
|------|-------|
| HU-TA01 | Features |
| HU-TA02 | Categories |
| HU-TA03 | – Specification |
| HU-TA04 | View Taxonomy |

---

### HU-TA01 · Features
> As a **taxonomy editor**, I want to **define the features** (attributes) that can describe
> an asset — optionally backed by a list of allowed values — **so that** assets can be
> characterized consistently.
- **Data:** `features` — `code`, `name`, `type` (→ `FEAT_TYPE`: General, Technical,
  Commercial, Usability, Documentation, Platform), `list` (optional FK → `lists.code` where
  `type='FEATURE'`)
- **UI:** [`ui/src/pages/taxo/features.astro`](../../ui/src/pages/taxo/features.astro)

### HU-TA02 · Categories
> As a **taxonomy editor**, I want to **organize asset categories in a tree** so that assets
> and specifications can be grouped along a meaningful hierarchy.
- **Data:** `categories` — `code`, `name`, `parent` (self-FK), `icon`. Seed is a 14-node
  tree under `AI_ASSETS` (`CLASSIC_AI`, `GEN_AI`, …).
- **UI:** [`ui/src/pages/taxo/categories.astro`](../../ui/src/pages/taxo/categories.astro)

### HU-TA03 · – Specification
> As a **taxonomy editor**, I want to **attach features to a category with a default value**
> **so that** each category declares which features its assets are expected to have.
- **Data:** `specifications` — PK `(category, feature)`, `default_value`. Detail of **HU-TA02**
  (master-detail: category → features).
- **UI:** [`ui/src/pages/taxo/specifications.astro`](../../ui/src/pages/taxo/specifications.astro)

### HU-TA04 · View Taxonomy
> As any **user**, I want to **browse the full taxonomy** (categories with their features and
> defaults) **so that** I understand how assets are classified before contributing.
- **Data:** read-only view over `categories` + `specifications` + `features`.
- **UI:** [`ui/src/pages/taxo/taxonomy.astro`](../../ui/src/pages/taxo/taxonomy.astro)
