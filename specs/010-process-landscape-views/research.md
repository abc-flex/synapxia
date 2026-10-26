# Research: Process Landscape Views (Value Chain + Process Map)

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-10-24

## R1 — How the diagrams are drawn

- **Decision**: No new dependency. The **Value Chain** is HTML/CSS (a CSS grid: one row of primary blocks ending in a margin chevron, support bands spanning the full width underneath), because it is a fixed Porter layout, not a graph. The **Process Map** is a Svelte 5 island that renders **SVG** with a **deterministic, purpose-built layout** computed in a pure TypeScript module (`ui/src/lib/processLandscape.ts`):
  - two horizontal lanes, Primary on top and Support below (the same reading order as the chain);
  - top-level processes in a row per lane, primaries in chain order (R3), supports by code;
  - one level at a time (amended 2026-10-25, user feedback): the overview draws only top-level boxes; a box's BPMN collapsed-sub-process "+" marker replaces the diagram with that process's **internal diagram** — a pool with its sub-processes placed in columns by longest PRECEDES path (`flowOrder`, the client twin of `chain_order`, over the edges actually drawn), start/end events wired to the flow's first and last tasks, sub-processes outside any flow on a row below, and the outside processes they relate to in a dashed lane underneath; Back and a breadcrumb return. Layout always uses every relation type, so hiding a type never moves a box. (The first version nested expanded children inside containers; replaced because it grew tall and unreadable.)
  - connectors are SVG paths between box edges (cubic curves; lane-crossing edges leave from the bottom/top, same-lane edges from the sides), with one `<marker>` per relation type for the BPMN style (FR-011);
  - pan (drag) and zoom (wheel + buttons + "fit") by a `viewBox` transform; no node dragging.
- **Rationale**: the repo has a working precedent for dependency-free SVG charts (`UsageTimeline.svelte`, SpecKit 008) and dependency-free formats (`lib/xlsx.ts`). A process landscape is a compound (nested) graph whose most meaningful arrangement is already known: Porter lanes plus chain order. A general layout engine would put nodes in different places than the Value Chain, which breaks the "same picture, more detail" link between the views (SC-002). The map opens collapsed (9 top-level boxes in the seed), so the layout is small; even at 300 processes with everything expanded it is a few hundred boxes and paths, which SVG handles easily.
- **Alternatives considered**:
  - *elkjs* (ELK layered, compound graphs): the best automatic layout, but ~1.4 MB of JS (or a worker setup), asynchronous layout, and placements unrelated to the chain order. Rejected for size and for the loss of the chain correspondence. It remains the upgrade path if real landscapes become dense meshes (noted in the plan).
  - *Cytoscape.js* (+ cose-bilkent for compounds): ~400 kB, a force layout (non-deterministic: the map would change between visits), and its own canvas styling outside Tailwind/dark mode. Rejected.
  - *dagre*: unmaintained, weak support for compound nodes. Rejected.
  - *Mermaid* flowcharts: static text-to-diagram rendering; no expand/collapse, focus or per-node selection without hacks. Rejected.
  - *bpmn-js*: a BPMN modeller for process internals (tasks, gateways), not a landscape of processes; heavy and editing-oriented. Rejected.

## R2 — One shared read (FR-001), its gate and its bound

- **Decision**: one new endpoint `GET /api/processes/landscape` returns the whole landscape for both views (processes, relations, own and rolled-up counts, the primary chain order). A second endpoint `GET /api/processes/landscape/{code}` returns the detail panel for one process. Both are gated by **`PROC/VALUE_CHAIN` OR `PROC/MAP`** at read level via the existing `check_any_privilege` (`api/app/internal/permissions.py`); neither requires `PROC/PROCESSES` (FR-018). They live in a new route module `api/app/workflows/routes/landscape.py`, included in `main.py` **before** `processes.py` so `/api/processes/{code}` cannot capture `landscape` (a test pins this).
- **Bound**: the landscape is an aggregate, not a paginated list. It is bounded by a hard cap of **2 000 processes** (`LANDSCAPE_MAX_PROCESSES`); beyond it the response carries `truncated: true` and the first 2 000 by code, and the UI shows a notice. Relations and links are read only for the processes returned. The query count is constant (6 queries, see data-model), never per process.
- **Rationale**: Principle II asks list endpoints for bounded inputs; a landscape cut by `skip`/`limit` would draw a meaningless half-chain, so the bound is a cap plus an explicit flag (Complexity Tracking). Separate endpoints from Process Management keep its contract untouched and avoid giving view-only users the management reads.
- **Alternatives considered**: reusing `GET /api/processes/` (paginated, PROCESSES-gated, no counts) plus per-process link calls — N+1 and wrong gate; widening the Process Management GETs to OR the view privileges — leaks the management dialog's data (owners list, all assets) to view-only users and couples two features' gates.

## R3 — Chain order (FR-006)

- **Decision**: computed **on the server** in a pure function `chain_order(codes, precedes_edges)` in a new `api/app/workflows/internal/landscape_service.py`, and returned in the landscape as `primary_order` (top-level primaries) and, per process, `child_order` (its direct children, same rule, all types). Algorithm:
  1. *Connected* nodes = those with at least one PRECEDES edge inside the group; *isolated* = the rest.
  2. Kahn's topological sort over the connected nodes, choosing the smallest code among ready nodes.
  3. When no node is ready (a cycle), emit the smallest-code remaining node and continue (this is "placed in code order at the point where the cycle is entered").
  4. Append isolated nodes in code order.
  Only PRECEDES edges whose two ends are in the same group count. Edges are taken between the shown processes themselves (no redirection), because Process Management already restricts PRECEDES to same-type processes.
- **Rationale**: one definition, unit-testable in pytest (the UI has no test framework); the map's lane order reuses it, so both views agree.
- **Alternatives considered**: a stored `sort_order` column (rejected in the spec's Assumptions: owners would maintain order twice); ordering on the client (untestable, two copies).

## R4 — Rolled-up counts (FR-001, FR-007, SC-004)

- **Decision**: counts are computed on the server. For each shown process: `own_assets`/`own_inits` = distinct active assets/initiatives linked to it (active link, active target, any relation type); `assets`/`inits` = distinct ids over it **and all its shown descendants** (any depth). Deprecated or removed processes are not shown, so their links never count. Implemented with one projected query per link table (`(process, asset_id)` pairs joined to active targets) and a single post-order pass over the shown tree using sets.
- **Rationale**: distinct-over-subtree cannot be summed from children (the same asset may be linked twice), so sets are needed; the seed and realistic inventories are small (hundreds of processes, a few thousand links). Server-side keeps SC-004's "independent count" checkable in tests.
- **Value Chain depth (Q2 = B)**: the chain lists only level-one children; their `assets`/`inits` already include deeper levels, so no special case is needed.
- **Opportunity (Q3 = C)**: `is_opportunity = (assets == 0 and inits == 0)` on the rolled-up figures, returned per process, so a parent with any covered sub-process is not an opportunity.

## R5 — Unit filter and missing parents

- **Decision**: `unit` is a query parameter of the landscape. The server keeps the processes of that unit plus every ancestor needed to place them (ancestors are flagged `context: true`, drawn muted). A process whose parent is not shown (Deprecated parent, or cap) is attached to its nearest shown ancestor (`display_parent`), or to the top level. Counts use the shown tree, so they "recompute over what is shown". The detail panel is unaffected by the filter.
- **Rationale**: done server-side so the counts and the chain order (which depend on the shown set) stay one definition.

## R6 — Collapsed connectors, focus and view state (FR-012, FR-013, FR-017)

- **Decision**: pure client-side functions in `ui/src/lib/processLandscape.ts`, operating on the landscape payload and the view state:
  - `visibleAncestor(code, expanded)`: walk `display_parent` up to the first process whose ancestors are all expanded.
  - `mergeEdges(relations, expanded, enabledTypes)`: redirect both ends, drop self-loops, group by (source, target, type) — and by the unordered pair for INTERACTS_WITH — with a `count`.
  - `neighborhood(code)`: the process, its parent, its children and the other end of every relation touching it.
  - `readViewState(url)` / `writeViewState(state)`: `focus`, `unit`, `in` + `types` (map), `opportunities` (chain), written with `history.replaceState` so the address reproduces the view; focusing expands the focused process's ancestors.
- **Rationale**: these depend only on viewer state (expanded parents, enabled types), which the spec keeps off the server.
- **Amendment 2026-10-25**: on the map, "expanded" is no longer a free set of open containers: it is `drillPath(in)`, the drilled process plus its ancestors, so `visibleAncestor` maps every process onto a box of the level on screen (a child of the drilled process, or an outside box). `layoutDrill` keeps only the edges touching a child of the drilled process.

## R7 — Labels and language

- **Decision**: PROCESS_TYPE, PROCESS_STATUS, PROCESS_RELATION_TYPE and RELATION_TYPE labels come from `GET /api/list_items/list/{code}` (open to any authenticated user since 2026-09-06) and are rendered through `lib/listLang.ts` (`toListOptions`/`listLabel` under `langTick` in Svelte), as the project rule requires. UI strings go under new `value_chain.*`, `process_map.*` and `process_landscape.*` keys in `en.json` and `es.json`.

## R8 — "Open in Process Management" (FR-016)

- **Decision**: the landscape returns `can_manage` (holds `PROC/PROCESSES` at read level). The panel's action links to `/proc/processes?open=<CODE>`; `processes.astro` gains an additive handler that, on load, opens the existing edit dialog for that code (the same path a row click takes). No change to Process Management's API.

## R9 — Performance check (SC-003)

- **Decision**: a pytest benchmark-style test builds 300 processes / 600 relations / 1 000 links on SQLite and asserts the landscape service stays under a generous bound and issues a constant number of queries (counted with a SQLAlchemy `before_cursor_execute` listener). Front-end timing (draw under 4 s, interactions under 1 s) is verified manually with `specs/010-process-landscape-views/synthetic-landscape.sql`, a development-only script that writes **only process rows and their relations/links** — per the standing rule, synthetic data stays in the tables under test — and its companion `synthetic-landscape-remove.sql`.
