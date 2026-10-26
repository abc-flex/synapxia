# Processes — User Stories

> Module `PROC` · API domain `api/app/workflows` · DB band 70s
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
- **Behavior:** the code is immutable after creation; the parent hierarchy stays acyclic; a
  process with active sub-processes cannot be removed (logical removal otherwise). A new process
  starts in Draft; status moves are Draft → Review, Review → Published or back to Draft,
  Published → Deprecated (final). The dialog's tabs are, in order, Core Fields, Related
  processes, Related assets, Related inits; in edit mode each tab saves only its own set, and
  creating a process saves it with every staged link at once. Access: `PROC/PROCESSES`.
- **Option:** `PROC.PROCESSES` → `/proc/processes`
- **UI:** [`proc/processes.astro`](../../ui/src/pages/proc/processes.astro) +
  [`ProcessDetailModal.astro`](../../ui/src/components/proc/ProcessDetailModal.astro).
  Spec: [`specs/009-process-management`](../../specs/009-process-management/spec.md).

### HU-PR02 · – Related Processes
> As a **process owner**, I want to **link a process to other processes** with a relation type
> and rationale **so that** dependencies and flows between processes are explicit.
- **Data:** `related_processes` — PK `(source, target, type)`, `type` (→ `PROCESS_RELATION_TYPE`),
  `rationale`. Detail of **HU-PR01**.
- **Relation types** (dedicated list, each mapped to a BPMN connecting object so the Value Chain
  and Process Map can draw it): Precedes (sequence flow), Triggers (event start), Calls (call
  activity), Feeds Into (data association), Interacts With (message flow — undirected), Supports
  and Governs (association). Hierarchy is `parent`, never a relation.
- **Rules:** Supports only from a Support process to a Primary one; Precedes only between
  processes of the same type; no self-relation; a type change that would break existing
  Supports/Precedes links is refused.

### HU-PR03 · – Related Assets
> As a **process owner**, I want to **link library assets to a process** **so that** the AI and
> digital assets supporting it are visible from the process itself.
- **Data:** `process_assets` — PK `(process, asset, type)`, `type` (→ `RELATION_TYPE`),
  `rationale`; targets come from
  [`assets`](04-lib.md#hu-li01--asset-management). Detail of **HU-PR01**.

### HU-PR04 · – Related Inits
> As a **process owner**, I want to **link initiatives to a process** **so that** improvement
> opportunities are tied to the processes they affect.
- **Data:** `process_inits` — PK `(process, init, type)`, `type` (→ `RELATION_TYPE`),
  `rationale`; targets come from
  [`initiatives`](05-inits.md#hu-in02--initiative-management). Detail of **HU-PR01**.

### HU-PR05 · Value Chain
> As a **manager**, I want to **see the processes arranged as a value chain**, primary
> activities across the flow and support activities underneath, **so that** I understand how
> operations create value end to end — and where AI could help.
- **Data:** view over `processes` grouped by `type` (`PRIMARY` / `SUPPORT`), enriched with the
  count of related assets and initiatives.
- **Behavior:** primary activities in one row ordered along their Precedes links, ending in the
  margin marker; support activities as bands underneath. Shows every active process except
  Deprecated (Draft and Review marked). Each block shows its asset and initiative counts rolled
  up over its sub-processes and expands one level; processes with neither are highlighted as AI
  opportunities, and *Only opportunities* dims the rest. Business-unit filter; a read-only
  detail panel leads to the Process Map and, for process managers, to Process Management.
  Access: `PROC/VALUE_CHAIN` (read).
- **Option:** `PROC.VALUE_CHAIN` → `/proc/value_chain`
- **UI:** [`proc/value_chain.astro`](../../ui/src/pages/proc/value_chain.astro) +
  [`ValueChain.svelte`](../../ui/src/components/svelte/ValueChain.svelte).
  Spec: [`specs/010-process-landscape-views`](../../specs/010-process-landscape-views/spec.md).

### HU-PR06 · Process Map
> As a **manager**, I want to **see a process map** — the hierarchy of processes and the
> relations between them — **so that** the landscape is navigable visually.
- **Data:** view over `processes` (`parent` hierarchy) + `related_processes`.
- **Behavior:** two lanes (Primary, Support) in the Value Chain's order, one level at a time:
  a process's "+" (BPMN collapsed sub-process) replaces the map with its internal diagram —
  sub-processes along their sequence flows with start and end events, and the outside
  processes they relate to — with Back and a breadcrumb to return. Relations are drawn after
  their BPMN counterpart, with a legend (shown or hidden) and a per-type filter, merged onto
  the nearest drawn ancestor. Search, focus on a process's neighborhood, pan and zoom; the
  shared detail panel leads back to the Value Chain. Access: `PROC/MAP` (read).
- **Option:** `PROC.MAP` → `/proc/process_map`
- **UI:** [`proc/process_map.astro`](../../ui/src/pages/proc/process_map.astro) +
  [`ProcessMap.svelte`](../../ui/src/components/svelte/ProcessMap.svelte).
  Spec: [`specs/010-process-landscape-views`](../../specs/010-process-landscape-views/spec.md).
