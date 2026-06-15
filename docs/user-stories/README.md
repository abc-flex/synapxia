# SynapxIA — User Stories

Catalog of user stories (Historias de Usuario, HdeU) for the SynapxIA platform, grouped
by module. The source of truth for the codes and names is the team's tracking board
**`Control H de U.xlsx`** (sheet *Tablero*). Each story is enriched here with the backing
database tables (see [`db/sql/`](../../db/sql) and [`docs/diagrams/`](../diagrams)) and the
UI page that implements it (under [`ui/src/`](../../ui/src)).

> This is living documentation. When a story's scope or data model changes, update the
> matching module file here and the `Control H de U.xlsx` board together.

---

## Modules

SynapxIA is a modular monolith. Stories are numbered per module with an `HU-` prefix plus a
two-letter module code; the ordering mirrors the sidebar (`sort_order`).

| # | Module | Code | Prefix | Stories | Diagram |
|---|--------|------|--------|:-------:|---------|
| 1 | [Administration](01-admin.md) | `ADMIN` | `HU-AD` | 8 | [1-admin.png](../diagrams/1-admin.png) |
| 2 | [Asset Taxonomy](02-taxo.md) | `TAXO` | `HU-TA` | 4 | [2-taxo.png](../diagrams/2-taxo.png) |
| 3 | [Collaboration](03-collab.md) | `COLLAB` | `HU-CO` | 7 | [3-collab.png](../diagrams/3-collab.png) |
| 4 | [Asset Library](04-lib.md) | `LIB` | `HU-LI` | 19 | [4-lib.png](../diagrams/4-lib.png) |
| 5 | [Initiatives](05-inits.md) | `INITS` | `HU-IN` | 11 | [5-inits.png](../diagrams/5-inits.png) |
| 6 | [Analytics](06-ana.md) | `ANA` | `HU-AN` | 6 | [6-ana.png](../diagrams/6-ana.png) |
| 7 | [Processes](07-proc.md) | `PROC` | `HU-PR` | 6 | [7-proc.png](../diagrams/7-proc.png) |
| | **Total** | | | **61** | [synapxia.png](../diagrams/synapxia.png) |

**Appendix:** [State machines & type catalogs](appendix-states-and-types.md) — the
lifecycle states and classification types (as seeded in the database) referenced by the
Library, Initiatives and Process stories.

---

## How to read a story

Each story is presented as a card:

```
### HU-AD01 · Business Units
> As an administrator, I want … so that …
- Data:  `business_units` (self-referencing hierarchy)
- UI:    ui/src/pages/admin/business_units.astro
```

### Sub-stories

Stories whose name starts with a dash (e.g. `- Privileges`, `- Metrics`) are **detail
features of the preceding parent story** — usually a master-detail relationship or a tab
within the parent's page. They keep that dash here to stay faithful to the board.
