# Asset Taxonomy — User Stories

> Module `TAXO` · API domain [`api/app/taxo`](../../api/app) · DB band 20s
> ([`21-taxo-ddl.sql`](../../db/sql/21-taxo-ddl.sql)) · Diagram [2-taxo.png](../diagrams/2-taxo.png)

Asset Taxonomy defines the classification framework used across SynapxIA: the category tree,
the features (metadata attributes) an asset can have, and the per-category specifications
that say **which** features apply, with what default, whether they are required, and whether
their value is copyable.

| Code | Story |
|------|-------|
| HU-TA01 | Features |
| HU-TA02 | Categories |
| HU-TA03 | – Specification |
| HU-TA04 | View Taxonomy |

---

### HU-TA01 · Features
> As a **taxonomy editor**, I want to **define the features** (attributes) that can describe an
> asset — optionally backed by a list of allowed values — **so that** assets are characterized
> consistently.
- **Data:** `features` — `code`, `name`, `description`, `type` (→ `FEAT_TYPE`: General,
  Technical, Commercial, Usability, Documentation), `list` (optional FK →
  `lists.code` where `type='FEATURE'`, which turns the feature into a select)
- **UI:** [`taxo/features.astro`](../../ui/src/pages/taxo/features.astro)

### HU-TA02 · Categories
> As a **taxonomy editor**, I want to **organize asset categories in a tree** **so that**
> assets and specifications are grouped along a meaningful hierarchy.
- **Data:** `categories` — `code`, `name`, `description`, `parent` (self-FK), `icon`, `option`
  (the AI Library option this category is browsed through). Seeded as a tree under
  `AI_ASSETS` (`CLASSIC_AI`, `GEN_AI`, → `PROMPTS`, `MCPS`, `AGENTS`, `FLOWS`, `SKILLS`,
  `RAG_APPS`, `MODELS`, …).
- **UI:** [`taxo/categories.astro`](../../ui/src/pages/taxo/categories.astro)

### HU-TA03 · – Specification
> As a **taxonomy editor**, I want to **attach features to a category** with a default value,
> a required flag, a copyable flag and an order **so that** each category declares exactly how
> its assets must be characterized.
- **Data:** `specifications` — PK `(category, feature)`, `default_value`, `required` (blocks
  the propose/characterize step until filled), `copyable` (renders the value in a copy box on
  the asset detail), `sort_order`. Detail of **HU-TA02** (category → features).
- **UI:** [`taxo/specifications.astro`](../../ui/src/pages/taxo/specifications.astro)
- **Used by:** [HU-LI07 Characteristics](04-lib.md#hu-li07--asset-tab-characteristics-include-report-usage)
  builds its form from this table.

### HU-TA04 · View Taxonomy
> As any **user**, I want to **browse the full taxonomy as a tree**, with how many assets each
> category holds, **so that** I understand the classification before contributing — and can
> jump straight into a category.
- **Data:** read-only view over `categories` + `specifications` + `features`, plus the asset
  count per category. A leaf with assets links to `categories.option`
  (→ [HU-LI03 Explore Category](04-lib.md#hu-li03--explore-category-include-favorite--vote)).
- **UI:** [`taxo/taxonomy.astro`](../../ui/src/pages/taxo/taxonomy.astro),
  [`treeview/TreeChart.astro`](../../ui/src/components/treeview/TreeChart.astro)
