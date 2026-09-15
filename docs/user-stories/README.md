# SynapxIA — User Stories

Catalog of user stories (*Historias de Usuario*, HdeU) for the SynapxIA platform, grouped by
module. The source of truth for **codes and names** is the team's tracking board
**`Control H de U.xlsx`** (sheet *Dashboard*). Each story is enriched here with the backing
database tables ([`db/sql/`](../../db/sql), [`docs/diagrams/`](../diagrams)) and the UI page
that implements it ([`ui/src/`](../../ui/src)).

> Living documentation. When a story's scope or data model changes, update the matching
> module file here **and** the `Control H de U.xlsx` board together.

---

## Modules

SynapxIA is a modular monolith. Stories are numbered per module with an `HU-` prefix plus a
two-letter module code; the ordering mirrors the sidebar (`modules.sort_order`).

| # | Module | Code | Prefix | Stories | Diagram |
|---|--------|------|--------|:-------:|---------|
| 1 | [Administration](01-admin.md) | `ADMIN` | `HU-AD` | 18 | [1-admin.png](../diagrams/1-admin.png) |
| 2 | [Asset Taxonomy](02-taxo.md) | `TAXO` | `HU-TA` | 4 | [2-taxo.png](../diagrams/2-taxo.png) |
| 3 | [Collaboration](03-collab.md) | `COLLAB` | `HU-CO` | 7 | [3-collab.png](../diagrams/3-collab.png) |
| 4 | [AI Library](04-lib.md) | `LIB` | `HU-LI` | 26 | [4-lib.png](../diagrams/4-lib.png) |
| 5 | [Initiatives](05-inits.md) | `INITS` | `HU-IN` | 17 | [5-inits.png](../diagrams/5-inits.png) |
| 6 | [Analytics](06-ana.md) | `ANA` | `HU-AN` | 7 | [6-ana.png](../diagrams/6-ana.png) |
| 7 | [Processes](07-proc.md) | `PROC` | `HU-PR` | 6 | [7-proc.png](../diagrams/7-proc.png) |
| | **Total** | | | **85** | [synapxia.png](../diagrams/synapxia.png) |

**Appendix:** [States & types](states-and-types.md) — the asset (`actions`) and initiative
(`collaborations`) **workflow matrices**, the **tab option matrices** for asset and
initiative detail screens, and the lifecycle states / classification types as seeded in the
database.

**Sources for the workflow detail:** [`lib-status.md`](lib-status.md) ·
[`inits-status.md`](inits-status.md).

---

## How to read a story

Each story is a small card:

```
### HU-AD01 · Business Units
> As an administrator, I want … so that …
- Data:  business_units (self-referencing hierarchy)
- UI:    ui/src/pages/admin/business_units.astro
```

- **Data** — the tables (and their key columns) the story reads or writes.
- **UI** — the page, modal or widget that implements it.
- **Behavior** — only where the story is a workflow step rather than plain CRUD.

### Naming conventions kept from the board

| Prefix | Meaning |
|--------|---------|
| `– Name` | Sub-story: a detail, modal or step of the nearest preceding parent story |
| `[Asset Tab] Name` | A tab of the shared asset detail/edit surface (see the [tab matrix](states-and-types.md#asset-tab-options-by-user-story)) |
| `[Initiative Tab] Name` | A tab of the shared initiative detail/edit surface |
| `[Notifications] Name` | Reached from the header notification bell |
| `[Account Menu] Name` | Reached from the account menu's *My Workspace* section |
| `[Explore Category] Name` | A category-scoped instance of **Explore Category** |
