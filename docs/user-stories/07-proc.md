# Processes — User Stories

> Module `PROC` · API domain `api/app/proc` · DB band 70s
> ([`71-proc-ddl.sql`](../../db/sql/71-proc-ddl.sql)) · Diagram [7-proc.png](../diagrams/7-proc.png)

Processes maps the organizational process landscape — value chains, process maps and process
models — so business operations can be connected to AI opportunities, assets and measurable
improvements. Processes are typed as **primary** or **support** activities, can be nested, and
link out to other processes, library assets and initiatives.

| Code | Story |
|------|-------|
| HU-PR01 | Process Management |
| HU-PR02 | – Related Processes |
| HU-PR03 | – Related Assets |
| HU-PR04 | – Related Inits |
| HU-PR05 | Value Chain |
| HU-PR06 | Process Map |

---

### HU-PR01 · Process Management
> As a **process owner**, I want to **register and maintain the organization's processes** —
> typed as primary or support, optionally nested, owned by a person and a business unit — **so
> that** there is a single inventory of how the organization operates.
- **Data:** `processes` — `code`, `name`, `description`, `type` (→ `PROCESS_TYPE`: Primary,
  Support), `parent` (self-FK), `unit` (FK → `business_units.code`), `owner` (FK → `users.id`),
  `reference`, `status` (→ `PROCESS_STATUS`: Draft, Review, Published, Deprecated), `tags`
  (JSONB), `detail`
- **Option:** `PROC.PROCESSES` → `/proc/processes`

### HU-PR02 · – Related Processes
> As a **process owner**, I want to **link a process to other processes** with a relation type
> and rationale **so that** dependencies and flows between processes are explicit.
- **Data:** `related_processes` — PK `(source, target, type)`, `type` (→ `RELATION_TYPE`),
  `rationale`. Detail of **HU-PR01**.

### HU-PR03 · – Related Assets
> As a **process owner**, I want to **link library assets to a process** **so that** the AI and
> digital assets supporting it are visible from the process itself.
- **Data:** `process_assets` — PK `(process, asset)`, `rationale`; targets come from
  [`assets`](04-lib.md#hu-li01--asset-management). Detail of **HU-PR01**.

### HU-PR04 · – Related Inits
> As a **process owner**, I want to **link initiatives to a process** **so that** improvement
> opportunities are tied to the processes they affect.
- **Data:** `process_inits` — PK `(process, init)`, `rationale`; targets come from
  [`initiatives`](05-inits.md#hu-in02--initiative-management). Detail of **HU-PR01**.

### HU-PR05 · Value Chain
> As a **manager**, I want to **see the processes arranged as a value chain**, primary
> activities across the flow and support activities underneath, **so that** I understand how
> operations create value end to end — and where AI could help.
- **Data:** view over `processes` grouped by `type` (`PRIMARY` / `SUPPORT`), enriched with the
  count of related assets and initiatives.
- **Option:** `PROC.VALUE_CHAIN` → `/proc/value_chain`

### HU-PR06 · Process Map
> As a **manager**, I want to **see a process map** — the hierarchy of processes and the
> relations between them — **so that** the landscape is navigable visually.
- **Data:** view over `processes` (`parent` hierarchy) + `related_processes`.
- **Option:** `PROC.MAP` → `/proc/process_map`
