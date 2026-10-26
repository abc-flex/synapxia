# Tasks: Process Landscape Views (Value Chain + Process Map)

**Input**: Design documents from `specs/010-process-landscape-views/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/landscape-api.md](contracts/landscape-api.md), [quickstart.md](quickstart.md)

**Tests**: INCLUDED for the backend. Constitution Principle III requires automated tests for a new permission and contract surface (view privileges reading process data). The diagrams are verified manually through `quickstart.md` (no UI test framework).

**Organization**: tasks are grouped by user story (spec.md US1–US3), so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: the user story the task belongs to (US1…US3)

## Conventions for every task

- **Backend**:
  - Domain `api/app/workflows/` (the Processes domain; there is no `api/app/proc`). Models in `internal/models.py`, logic in `internal/landscape_service.py`, routes in `routes/landscape.py`.
  - Gate both endpoints with `check_any_privilege(session, current, "PROC", ["VALUE_CHAIN", "MAP"])` from `app/internal/permissions.py` (read level), after `current_active_user`; never with `PROC/PROCESSES`.
  - Session from `..internal.dependencies.get_db_session`. Read-only: no commit, no write route.
  - Bad `unit` → 400 (`HTTPException`), process not shown → 404. Routes return bare models; the global envelope wraps them.
  - Constant query count: projected `select(...)` of the needed columns, never a query inside a loop over processes.
- **Tests**:
  - SQLite fixtures from `api/tests/conftest.py` (`session`, `client`); builders from `api/tests/proc_helpers.py` (`mk_process`, `mk_relation`, `mk_asset`, `mk_asset_link`, `mk_init_link`, `mk_unit`, `seed_proc_lists`, `user`, `superuser`, `override`).
  - Run with `docker compose exec -T api uv run pytest -q tests/test_proc_landscape.py`.
- **UI**:
  - Every string in both `ui/src/i18n/en.json` and `es.json`.
  - List values (PROCESS_TYPE, PROCESS_STATUS, PROCESS_RELATION_TYPE, RELATION_TYPE) loaded with `GET /api/list_items/list/{code}` and rendered through `ui/src/lib/listLang.ts` (`toListOptions`, `listLabel` under `langTick`); never filter by language by hand, never write `textContent` into Svelte-owned DOM.
  - Svelte islands mounted manually with `mount()` from a bundled `<script>` in their `.astro` page (mirror `ui/src/pages/ana/usage.astro`); Svelte template comments use `<!-- -->`.
  - Colors as Tailwind classes with `dark:` variants; no new dependency (research R1).
  - Pages are thin SSR shells; access is enforced by the API — on 403 the island shows the standard "not authorized" empty state.

---

## Phase 1: Setup

**Purpose**: test scaffolding and i18n namespaces shared by every story.

- [X] T001 [P] Add `seed_view_privileges(session, profile, options=("VALUE_CHAIN", "MAP"), can_edit=False)` to `api/tests/proc_helpers.py` (adds `Privilege(profile, module="PROC", option=…)` rows), next to the existing `seed_privileges`.
- [X] T002 [P] Add the shared namespaces to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`: `process_landscape.*` (loading, empty state "No processes to show", not authorized, truncated notice, unit filter label "All units", status markers Draft/Review, counts "{n} assets" / "{n} initiatives", "Opportunity", "Focus not found"). Keep `menu_options.value_chain` / `menu_options.map` as they are (add them if missing, matching the option codes `VALUE_CHAIN`/`MAP`).

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the shared landscape read (FR-001–FR-004, FR-006 order, FR-018) used by both views.

**⚠️ CRITICAL**: no user story work starts before this phase is complete.

### Tests (write first, they must fail)

- [X] T003 Create `api/tests/test_proc_landscape.py` with the access and contract tests for `GET /api/processes/landscape` (contract table in `contracts/landscape-api.md`): no token → 401; a profile holding only `PROC/PROCESSES` → 403; a profile holding only `PROC/VALUE_CHAIN` (read) → 200; only `PROC/MAP` (read) → 200; superuser → 200; `POST`/`PUT`/`DELETE` on `/api/processes/landscape` → 405; route ordering: a view-only profile gets 200 from `/api/processes/landscape` (not the 403 of `/api/processes/{code}`); `can_value_chain`/`can_map`/`can_manage` reflect the caller's privileges.
- [X] T004 Add shown-rule and count tests to `api/tests/test_proc_landscape.py`: Deprecated and `is_active=False` processes absent; relations with an absent end absent; inactive links and links to inactive assets/initiatives not counted; an asset linked to a parent and to its child counts once in the parent's `assets` and once in each `own_assets`; `is_opportunity` true only when rolled-up `assets == 0 and inits == 0`; a child under a Deprecated parent gets `display_parent` = the nearest shown ancestor (or null) and the right `depth`.
- [X] T005 Add chain-order tests to `api/tests/test_proc_landscape.py`, calling `landscape_service.chain_order` directly and through the endpoint: the seed chain INBL→OPER→OUTL→MKTS→SERV (inserted in shuffled code order) comes back in flow order; primaries without PRECEDES follow the connected ones in code order; a cycle A→B→C→A yields each node once, starting at the smallest code; `support_order` is by code; `child_order` of a parent orders its children by PRECEDES among siblings, then code.
- [X] T006 Add unit-filter, cap and performance tests to `api/tests/test_proc_landscape.py`: `?unit=X` returns X's processes plus their ancestors with `context=true`, and counts over that set only; unknown or inactive unit → 400; with `LANDSCAPE_MAX_PROCESSES` monkeypatched to 3, five processes → 3 returned by code and `truncated=true`; with 300 processes / 600 relations / 1 000 links built in the fixture, the request issues a constant number of SQL statements (counted with a `sqlalchemy.event.listen(engine, "before_cursor_execute", …)` counter on the test engine; ≤ 12 including the privilege checks) independent of the process count.

### Implementation

- [X] T007 Add the read models to `api/app/workflows/internal/models.py` (data-model.md): `LandscapeProcess`, `LandscapeRelation`, `ProcessLandscape` (with `processes`, `relations`, `primary_order`, `support_order`, `unit`, `truncated`, `can_value_chain`, `can_map`, `can_manage`). Plain `SQLModel` classes (not tables), in a new "Landscape (Value Chain / Process Map)" section after `ProcessFormOptions`.
- [X] T008 Create `api/app/workflows/internal/landscape_service.py` with module docstring (spec 010, FR references) and:
  - `LANDSCAPE_MAX_PROCESSES = 2000`, `HIDDEN_STATUSES = ("DEPRECATED",)`.
  - `chain_order(codes: List[str], edges: List[Tuple[str, str]]) -> List[str]` per research R3 (connected vs isolated, Kahn with smallest-code choice, cycle break by smallest remaining code, isolated appended by code). Pure function, no session.
  - `_shown_processes(session, unit)`: one projected query of active non-Deprecated processes ordered by code (with `limit(cap + 1)` to detect truncation); when `unit` is set, keep that unit's processes and add their ancestors from the same fetched rows (`context=True`). Validate `unit` against active `BusinessUnit` (raise `ValueError` → 400).
  - `_display_parents(rows)`: nearest shown ancestor + `depth`, with a visited guard.
  - Four projected queries for the shown codes: active `RelatedProcess` with both ends shown; `(ProcessAsset.process, ProcessAsset.asset)` joined to active `Asset`; `(ProcessInit.process, ProcessInit.init)` joined to active `Initiative`; unit and owner names (`process_service.full_name`).
  - Post-order roll-up with sets → `own_assets`, `own_inits`, `assets`, `inits`, `is_opportunity`.
  - `primary_order` / `support_order` over top-level shown processes (`display_parent is None`) by type, and `child_order` per process (all children, PRECEDES among siblings).
  - `build_landscape(session, user, unit) -> ProcessLandscape`, filling `can_*` with `has_privilege(session, user, "PROC", "VALUE_CHAIN"|"MAP"|"PROCESSES")`; `logger.info("landscape truncated", extra={"cap": …})` when truncated.
- [X] T009 Create `api/app/workflows/routes/landscape.py`: `router = APIRouter(prefix="/api/processes", tags=["processes"])`; `GET /landscape` (`unit: Optional[str] = None`) → `ProcessLandscape`, gate per Conventions, `ValueError` → 400. Docstring states it is the shared read of both views and is registered before `processes.py`.
- [X] T010 Register the router in `api/app/main.py`: import `from .workflows.routes import landscape as landscape_router` next to the other workflows imports (around line 68) and `app.include_router(landscape_router.router)` **before** `app.include_router(processes_router.router)` (around line 392), with a one-line comment on why the order matters.
- [X] T011 [P] Add the UI types to `ui/src/types/api.ts`: `LandscapeProcess`, `LandscapeRelation`, `ProcessLandscape` (read-only, no Create/Update variants — plan, Complexity Tracking).
- [X] T012 Create `ui/src/lib/processLandscape.ts` with:
  - `getLandscape(unit?: string): Promise<ProcessLandscape>` over `lib/api.ts` (`apiGet`), `getProcessLists()` loading the four list codes in parallel via the existing list-items service.
  - `readViewState(url: URL)` / `writeViewState(state)` (`focus`, `unit`, `opportunities`, `types`) using `history.replaceState`, per data-model "View state".
  - `byCode(landscape)` map and `ancestors(code, landscape)` (via `display_parent`), used by both views to expand the path to a focus.

**Checkpoint**: T003–T006 pass; `GET /api/processes/landscape` answers 200 for `adriana.velez` with `primary_order = INBL, OPER, OUTL, MKTS, SERV`.

---

## Phase 3: User Story 1 - See the value chain (Priority: P1) 🎯 MVP

**Goal**: `/proc/value_chain` shows the Porter chain with counts, status markers, opportunity highlight + *Only opportunities*, one-level expansion and the unit filter (FR-005–FR-008, scenarios 1.1–1.7, 1.9).

**Independent Test**: spec US1 "Independent Test" and quickstart §3 *Value Chain* (all bullets except the panel/navigation ones).

- [X] T013 [P] [US1] Add `value_chain.*` keys to `ui/src/i18n/en.json` and `es.json`: title, subtitle, "Primary activities", "Support activities", "Margin", "Only opportunities", "Expand"/"Collapse", "Sub-processes", opportunity tooltip ("No linked assets or initiatives").
- [X] T014 [US1] Create `ui/src/components/svelte/ValueChain.svelte`:
  - loads `getLandscape(state.unit)` and the lists on mount and when the unit changes; loading / empty / 403 / truncated states with `process_landscape.*` keys;
  - layout: CSS grid of primary blocks in `primary_order` ending in a chevron "Margin" marker; support bands in `support_order` full-width underneath; blocks `context=true` muted;
  - block content: name, code, status marker for DRAFT/REVIEW (labels via `listLabel`), asset and initiative counts (rolled up), opportunity highlight (amber ring + icon) when `is_opportunity`;
  - expand/collapse per block listing `child_order` children with their own counts/markers/highlight, nothing deeper; blocks start collapsed;
  - *Only opportunities* switch (Show/Hide switch style: icon + label + track) that dims non-opportunities with `opacity` without removing them; unit `<select>` built from the distinct `unit`/`unit_name` of the first, unfiltered load (cached, so filtering does not shrink the options; when the page opens with `?unit=`, load once without it first);
  - selection highlights a block/child and calls an `onSelect(code)` prop (the panel is wired in US3); `focus` from the address expands the containing block and highlights it;
  - every state change goes through `writeViewState`; labels re-render under `langTick`.
- [X] T015 [US1] Create `ui/src/pages/proc/value_chain.astro` mirroring `ui/src/pages/ana/usage.astro`: `getOption("PROC", "VALUE_CHAIN")` for the title, `Breadcrumb` with `moduleNameKey="modules.PROC"` and `pageNameKey="menu_options.value_chain"`, a `#value-chain-root` host, bundled script mounting `ValueChain` + `loadClientTranslations()` + `installGlobalToast()`.

**Checkpoint**: US1 is usable on its own (MVP).

---

## Phase 4: User Story 2 - Navigate the process map (Priority: P2)

**Goal**: `/proc/process_map` draws lanes, nested containers, BPMN-styled connectors with a legend, the relation-type filter, search, focus/dim and pan/zoom (FR-010–FR-013, scenarios 2.1–2.7, 2.9).

**Independent Test**: spec US2 "Independent Test" and quickstart §3 *Process Map* (except the panel bullet).

- [X] T016 [P] [US2] Add `process_map.*` keys to `ui/src/i18n/en.json` and `es.json`: title, "Primary"/"Support" lane labels, "Relations" (filter), "Legend", "Search a process", "Clear focus", "Zoom in"/"Zoom out"/"Fit", "{n} relations" (merged connector), "Expand"/"Collapse".
- [X] T017 [US2] Extend `ui/src/lib/processLandscape.ts` with the pure map helpers (research R6):
  - `RELATION_STYLES`: per PROCESS_RELATION_TYPE value → `{ dash, width, markerStart, markerEnd, directed }` matching spec scenario 2.3 (PRECEDES solid arrow; TRIGGERS arrow with an event circle at the start; CALLS bold arrow; FEEDS_INTO dotted arrow; INTERACTS_WITH dashed, no arrowheads; SUPPORTS dotted with open-arrow end; GOVERNS dotted with diamond end) — the single table used by connectors and legend;
  - `visibleAncestor(code, expanded, landscape)`, `mergeEdges(relations, expanded, enabledTypes, landscape)` (redirect ends, drop self-loops, group by (source, target, type) and by unordered pair for INTERACTS_WITH, with `count`), `neighborhood(code, landscape)` (self, parent, children, both-direction relation ends);
  - `layoutMap(landscape, expanded)` → `{ nodes: {code, x, y, w, h, depth}[], width, height }`: Primary lane on top then Support lane; top-level boxes in `primary_order` / `support_order`; expanded boxes become containers stacking `child_order` children vertically, recursively; constant box sizes and gaps.
- [X] T018 [US2] Create `ui/src/components/svelte/ProcessMap.svelte`:
  - loads landscape + lists like T014; same loading/empty/403/truncated states;
  - SVG with `<defs>` markers from `RELATION_STYLES`; lane backgrounds and labels; nodes from `layoutMap` (name, code, Draft/Review marker, type styling, `context` muted); expand/collapse toggle on any node with children (every level);
  - connectors from `mergeEdges` as cubic paths between box edges (lane-crossing from bottom/top, same lane from the sides), count badge when `count > 1`;
  - relation-type filter (checkboxes with the legend swatch, labels via `listLabel`) bound to `state.types`; legend always listing all seven types;
  - search input over code/name (type-ahead list); choosing a result expands `ancestors(code)` and focuses it;
  - focus: highlight `neighborhood(code)` and dim the rest; "Clear focus";
  - pan by drag and zoom by wheel/buttons through the `viewBox`; "Fit" resets; no node dragging;
  - node click → `onSelect(code)` prop (panel wired in US3); state changes through `writeViewState`; `focus` from the address on load expands ancestors and focuses.
- [X] T019 [US2] Create `ui/src/pages/proc/process_map.astro` as T015, with `getOption("PROC", "MAP")`, `pageNameKey="menu_options.map"`, host `#process-map-root`, mounting `ProcessMap`.

**Checkpoint**: US2 works on its own; US1 still works.

---

## Phase 5: User Story 3 - Move between the views and read a process's details (Priority: P2)

**Goal**: the shared read-only panel, cross-navigation and the Process Management deep link (FR-014–FR-017, scenarios 1.8, 2.8, 3.1–3.7).

**Independent Test**: spec US3 "Independent Test" and quickstart §2 steps 3–4 plus the panel/navigation bullets of §3.

### Tests

- [X] T020 [US3] Add detail-endpoint tests to `api/tests/test_proc_landscape.py` for `GET /api/processes/landscape/{code}`: same access matrix as T003; seed-like data gives OPER `incoming` = INBL (PRECEDES), TECH and HRMG (SUPPORTS) and `outgoing` = OUTL; an INTERACTS_WITH link appears once, in `outgoing`, with `directed=false`, whichever end is requested; `assets`/`inits` list own links with `via=null` and sub-process links with `via=<child code>`; links to inactive targets and relations to non-shown processes omitted; Deprecated, removed or unknown code → 404.

### Implementation

- [X] T021 [US3] Add `LandscapeRelationDetail`, `LandscapeAssetLink`, `LandscapeInitLink` and `LandscapeProcessDetail` to `api/app/workflows/internal/models.py` (data-model.md).
- [X] T022 [US3] Add `build_detail(session, code) -> LandscapeProcessDetail` to `api/app/workflows/internal/landscape_service.py`: the process must be shown (active, not Deprecated) else raise `LookupError`; core fields with parent/unit/owner names; outgoing/incoming split (INTERACTS_WITH once in `outgoing`, `directed=False`); asset/initiative links of the process and its shown descendants with `via`, active targets only, names and asset category; a constant number of queries.
- [X] T023 [US3] Add `GET /landscape/{code}` to `api/app/workflows/routes/landscape.py` (same gate; `LookupError` → 404), declared after `GET /landscape`.
- [X] T024 [P] [US3] Add `LandscapeRelationDetail`, `LandscapeAssetLink`, `LandscapeInitLink`, `LandscapeProcessDetail` to `ui/src/types/api.ts` and `getLandscapeDetail(code)` to `ui/src/lib/processLandscape.ts`.
- [X] T025 [P] [US3] Add panel keys to `process_landscape.*` in `ui/src/i18n/en.json` and `es.json`: "Details", field labels (code, description, type, parent, unit, owner, status, tags), "Outgoing relations", "Incoming relations", "Linked assets", "Linked initiatives", "via {code}", "{n} from sub-processes", "None", "Show in Process Map", "Show in Value Chain", "Open in Process Management", "Close".
- [X] T026 [US3] Create `ui/src/components/svelte/ProcessLandscapePanel.svelte`: props `code`, `from: "chain" | "map"`, `landscape` (for `can_*` and the top-level ancestor), `lists`, `onClose`; fetches `getLandscapeDetail(code)` on change; right-side slide-over (full width on mobile) with core fields, outgoing/incoming relations (other process, relation label via `listLabel`, rationale; INTERACTS_WITH without arrow), asset links (name, category, type, rationale, "via") and initiative links, with the "from sub-processes" count; actions: *Show in Process Map* → `/proc/process_map?focus=CODE` when `from==="chain" && can_map`; *Show in Value Chain* → `/proc/value_chain?focus=<top-level ancestor>` when `from==="map" && can_value_chain`; *Open in Process Management* → `/proc/processes?open=CODE` when `can_manage`; Esc and the close button call `onClose`.
- [X] T027 [US3] Wire the panel into `ui/src/components/svelte/ValueChain.svelte` and `ui/src/components/svelte/ProcessMap.svelte`: render `<ProcessLandscapePanel>` for the selected code (`from` = "chain"/"map"), keep `focus` in the address while it is open (FR-017), and show the "Focus not found" message when an address `focus` is not in the landscape.
- [X] T028 [US3] Add the additive deep link to `ui/src/pages/proc/processes.astro`: on load, read `?open=CODE`; if present, open the existing edit dialog for that code through the same trigger a row's edit action uses (`data-modal-open="process-edit-modal"` with `data-process-code`), then drop `open` from the address with `history.replaceState`; ignore unknown codes with the existing not-found toast.

**Checkpoint**: all three stories work together; navigation round-trips per SC-002.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Create `specs/010-process-landscape-views/synthetic-landscape.sql` (development only, never seed): deterministic ~300 processes with codes `SYN-…` (top-level primaries chained with PRECEDES, supports, two levels of sub-processes, owner = an existing user id, unit = existing units), ~600 relations among `SYN-` processes covering all seven types (respecting the SUPPORTS/PRECEDES rules), and links to **existing** assets/initiatives only; and `specs/010-process-landscape-views/synthetic-landscape-remove.sql` deleting rows whose process codes start with `SYN-` (links and relations first). Wait for the user's confirmation on scope before running it (plan report).
- [X] T030 Run the full backend suite and the build: `docker compose exec -T api uv run pytest -q` (baseline 837 + new tests, 0 failures), `make test`, `cd ui && bun run build` (clean), and record the numbers.
- [ ] T031 Execute `specs/010-process-landscape-views/quickstart.md` §2 (API smoke as `adriana.velez`, including the SQL hand count) and §3 (browser walkthrough, both languages, light and dark) and §4 (scale check, then removal); note anything not verified.
  - *Status 2026-10-24:* §2 done (API smoke as adriana.velez / santiago.marin / felipe.cardenas; counts equal the SQL hand count for all 9 top-level processes). §3 pending: no browser automation here, both pages only checked by SSR. §4 pending: the scale script was validated in a rolled-back transaction, not run, awaiting the user's OK on its scope.
- [X] T032 [P] Update `docs/user-stories/07-proc.md` HU-PR05/HU-PR06 with the UI files and spec link (as HU-PR01 has), and `api/CLAUDE.md` / `ui/CLAUDE.md` route and page lists if they enumerate PROC routes/pages.
- [X] T033 Update `memory/MEMORY.md` (decisions log entry: landscape read gated by the view privileges, server-side chain order and roll-ups, dependency-free SVG map, `?open=` deep link; feature status rows for Value Chain and Process Map; `workflows` row in "In progress / stubs") and add one rollup entry to `memory/CHANGELOG.md` (`date '+%Y-%m-%d %H:%M'`).

---

## Phase 7: Follow-up after review (2026-10-25, spec Clarifications session 2026-10-25)

UI-only; the API and its tests are unchanged.

- [X] T034 [US1] Compact `ui/src/components/svelte/ValueChain.svelte` so the chain fits one screen: primary blocks share the width (`flex-1 min-w-0`), smaller type, counts as icon + number, expand as chevron + count, one-line support bands with sub-processes in a grid; drop the star and "AI opportunity" badge; the amber fill (`tone()`) is the opportunity marker, explained by `value_chain.legend_opportunity` next to the *Only opportunities* switch.
- [X] T035 [US3] Restyle `ui/src/components/svelte/ProcessLandscapePanel.svelte`: a small title (name + code) with an arrow button that closes it; compact properties; Outgoing / Incoming / Assets / Initiatives as tabs with counts (`process_landscape.tab_*`, full names as tooltips, arrow-key navigation) whose body alone scrolls; actions in a bottom footer.
- [X] T036 [US2] In `ui/src/lib/processLandscape.ts` replace the nested-container `layoutMap` with `layoutOverview` (top-level boxes in two lanes) and `layoutDrill` (BPMN-style internal diagram: pool, sequence-flow columns via `flowOrder`, start/end events, isolated row, outside lane), add `drillPath`, `connectorPath` on real box heights, and `in` in the view state.
- [X] T037 [US2] Rework `ui/src/components/svelte/ProcessMap.svelte`: one level at a time; BPMN collapsed sub-process "+" marker opens the internal diagram; Back + breadcrumb; legend/filter as an overlay shown or hidden by a button next to +, −, Fit (remembered in `localStorage`); layout from all relation types so the filter never moves boxes; search and address `focus` open the level where the process is drawn.
- [X] T038 Update `ui/src/i18n/{en,es}.json` (new keys, removed `process_map.expand/collapse/hierarchy` and `process_landscape.opportunity`), the spec, research R1/R6, data model, contract, quickstart and `docs/user-stories/07-proc.md`; rebuild (`bun run build` clean, `svelte-check` clean for these files) and check the drill layout on seed data plus injected relations.
- [X] T039 [US3] `ProcessLandscapePanel.svelte`: `z-[60]` so the panel sits above the sticky header (`z-50`), which was hiding its title and close arrow; larger type and spacing so the content fills the height down to the actions.
- [X] T040 [US2] Seed relations between sub-processes in `db/sql/72-proc-insert.sql`: a Precedes flow inside each of the nine activities, plus Feeds Into / Triggers / Supports / Governs / Interacts With links inside and across activities (29 rows, within the SUPPORTS/PRECEDES rules). Applied to the dev DB with `ON CONFLICT DO NOTHING`; every internal diagram now has start and end events.
- [X] T042 [US2] Fix in `ProcessMap.svelte`: `focusVisible`/`lit` apply only when the focused process is a box of the level on screen, and `drillInto` clears focus and panel. Before, a focus on the drilled process faded all its internal connectors to 10% and the start/end flows to 20%.
- [X] T043 [US2] `ProcessMap.svelte`: one-row toolbar (truncated subtitle, unlabeled unit select, narrower search); the legend becomes a `w-60` panel docked on the right of the map frame, with an "x", separate start/end event items, and AI opportunity and outside-process items; a larger "Legend" button sits under +, −, Fit; the breadcrumb shows "code · name".
- [X] T044 [US3] `ProcessLandscapePanel.svelte`: title "code + name" with an "x" close; smaller, `whitespace-nowrap` buttons in a non-wrapping footer; shorter labels (`show_in_map`, `show_in_chain`, `open_in_management`).
- [X] T045 [US1] `ValueChain.svelte`: one-row toolbar; code bold and larger than the name in blocks and bands, sub-processes as "code name"; Margin `text-sm`, padded to the chevron's centroid.
- [X] T046 [US2] `ProcessMap.svelte`: the "Legends" button joins the +, −, Fit row (`h-7`, `text-xs`, same `btn` class); lane titles `text-[14px] font-bold`, indigo for Primary; `process_map.legend` → "Legends" / "Leyendas".
- [X] T047 [US1] `ValueChain.svelte`: *Expand all / Collapse all* (`expandable`, `allExpanded`, `toggleAll`; `value_chain.expand_all/collapse_all`).
- [X] T048 [US1] `ValueChain.svelte`: opportunity-aware dimming. `blockDim` (no opportunity anywhere), `oppHint` (collapsed with opportunity sub-processes → amber ring, not dimmed) and `headDim` (expanded → only the header dims; the sub-process items keep their own dimming).
- [X] T049 [US2] `ProcessMap.svelte`: legend "Elements" at `text-xs`, one line each (`whitespace-nowrap`, shorter `legend_subprocess/draft/outside`); "Clear focus" moves from the page toolbar to the left of +, −, Fit, Legends (`h-7`, `text-xs`), and the breadcrumb leaves room for it.
- [X] T050 [US1] `ValueChain.svelte`: narrower Margin chevron (88px; notch 14px, point 22px), label re-centred on its colored area.
- [X] T051 [US1] `ValueChain.svelte`: the AI-opportunity legend follows the subtitle (left group); the Margin label shifts right (`pl-5 pr-3`) to sit on the chevron's colored area.
- [X] T052 [US2] `ProcessMap.svelte`: legend Relations at `text-xs`, one line each, with smaller checkboxes and icons; Elements aligned to the same columns (icon `w-8`, text indented past the checkbox).
- [X] T053 [US3] Navigation from the panel's Assets and Initiatives tabs. In `ProcessLandscapePanel.svelte`, names become links (`assetHref`/`initHref`, external-link icon, type label now gray). `ui/src/pages/lib/explore.astro` opens `?asset=ID` in its detail modal and drops the parameter. `ui/src/pages/inits/explore.astro` opens `?initiative=ID` when its list holds it, else it shows the `inits_explore.not_listed` notice. Keys added: `process_landscape.open_asset/open_initiative`.
- [X] T041 [US1] `ValueChain.svelte`: taller support bands; counts use the sidebar icons (`ai-library` for assets, `rocket-launch` for initiatives, small); the Margin chevron spans the primary and support activities.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies; T001 and T002 in parallel.
- **Foundational (Phase 2)**: depends on T001 (tests). Order: T003–T006 (tests, failing) → T007 → T008 → T009 → T010; T011 in parallel with the backend; T012 after T011. **Blocks all stories.**
- **US1 (Phase 3)**: depends on Phase 2. T013 ∥ T014 → T015.
- **US2 (Phase 4)**: depends on Phase 2 only (not on US1). T016 ∥ T017 → T018 → T019.
- **US3 (Phase 5)**: backend T020 → T021 → T022 → T023 depends only on Phase 2; UI T026–T027 need T014 and T018 (it wires into both views), T028 is independent of both views.
- **Polish (Phase 6)**: after the desired stories; T029 any time after Phase 2.

### Within each story

- Backend tests before implementation (they must fail first).
- Models → service → route; types → lib → component → page.

### Shared files (avoid parallel edits)

- `api/tests/test_proc_landscape.py`: T003–T006, T020 sequential.
- `api/app/workflows/internal/models.py`: T007 then T021.
- `api/app/workflows/internal/landscape_service.py`: T008 then T022.
- `ui/src/lib/processLandscape.ts`: T012 → T017 → T024.
- `ui/src/i18n/{en,es}.json`: T002, T013, T016, T025 touch different namespaces but the same files — apply one at a time.
- `ValueChain.svelte` / `ProcessMap.svelte`: T014 / T018 before T027.

---

## Parallel Examples

### Phase 2

```text
T011 UI types in ui/src/types/api.ts
  ∥ T007–T010 backend models / service / route / main.py
```

### After Phase 2

```text
Developer A: US1 → T013, T014, T015
Developer B: US2 → T016, T017, T018, T019
Developer C: US3 backend → T020, T021, T022, T023 (+ T024, T025, T028)
then T026, T027 once T014 and T018 are in
```

---

## Implementation Strategy

### MVP first (US1)

1. Phase 1 + Phase 2 (shared read, tested).
2. Phase 3 (Value Chain).
3. **Stop and validate** with the US1 independent test; ship if desired — the chain already answers "where could AI help".

### Incremental delivery

1. + US2 → the map, independently testable.
2. + US3 → the panel and navigation that join both views.
3. Polish: scale check, docs, memory/changelog.

---

## Notes

- No DDL, no seed changes, no new dependency: an existing dev database needs no `make rebuild`.
- The Value Chain draws no relation connectors (spec Assumptions); only the map does.
- The synthetic scale script (T029) writes to the four process tables and references existing assets, initiatives, users and units; run it only after the user confirms that scope.
