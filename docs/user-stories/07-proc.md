# Processes — User Stories

> Module `PROC` · API domain `api/app/proc` *(not yet created)* · DB band 70s
> ([`71-proc-ddl.sql`](../../db/sql/71-proc-ddl.sql)) · Diagram [7-proc.png](../diagrams/7-proc.png)

Processes maps the organizational process landscape — value chains, process maps and process
models — to connect business operations with AI opportunities, assets and measurable
improvements. Processes are typed as primary or support activities (Porter's value chain),
can be nested, and can be linked to assets, other processes and initiatives.

| Code | Story |
|------|-------|
| HU-PR01 | Process Catalog |
| HU-PR02 | – Related Processes |
| HU-PR03 | – Related Assets |
| HU-PR04 | – Related Inits |
| HU-PR05 | Value Chain |
| HU-PR06 | Process Map |

> Process types (`PROCESS_TYPE`: Primary / Support) and statuses (`PROCESS_STATUS`) are
> listed in the [States & Types appendix](appendix-states-and-types.md).

---

### HU-PR01 · Process Catalog
> As a **process owner**, I want to **register the organization's processes** (typed as
> primary/support, optionally nested, owned by a user and a unit) **so that** there is a
> single inventory of business processes.
- **Data:** `processes` — `code`, `name`, `type` (→ `PROCESS_TYPE`), `parent` (self-FK),
  `unit` (FK → `business_units.code`), `owner` (FK → `users.id`), `status`
  (→ `PROCESS_STATUS`), `tags` (JSONB)

### HU-PR02 · – Related Processes
> As a **process owner**, I want to **link a process to related processes** so that
> dependencies and flows between processes are explicit.
- **Data:** `related_processes` — PK `(source, target)`, `type` (→ `RELATION_TYPE`),
  `rationale`. Detail of **HU-PR01**.

### HU-PR03 · – Related Assets
> As a **process owner**, I want to **link assets to a process** so that the AI/digital
> assets supporting it are visible.
- **Data:** `process_assets` — PK `(process, asset)`, `rationale`. Detail of **HU-PR01**.

### HU-PR04 · – Related Inits
> As a **process owner**, I want to **link initiatives to a process** so that improvement
> opportunities are tied to the processes they affect.
- **Data:** `process_inits` — PK `(process, init)`, `rationale`. Detail of **HU-PR01**.

### HU-PR05 · Value Chain
> As a **manager**, I want to **see processes arranged as a value chain** (primary vs support
> activities) **so that** I understand how operations create value end-to-end.
- **Data:** view over `processes` grouped by `type` (`PRIMARY` / `SUPPORT`).

### HU-PR06 · Process Map
> As a **manager**, I want to **see a process map** (the hierarchy and relationships between
> processes) **so that** the process landscape is navigable visually.
- **Data:** view over `processes` (`parent` hierarchy) + `related_processes`.
