# Implementation Plan: Process Landscape Views (Value Chain + Process Map)

**Branch**: `010-process-landscape-views` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-process-landscape-views/spec.md`

## Summary

Two read-only views of the process landscape, HU-PR05 **Value Chain** (`/proc/value_chain`) and HU-PR06 **Process Map** (`/proc/process_map`), plus a shared read-only detail panel and navigation between them. The backend adds one read model in the existing `workflows` (Processes) domain: `GET /api/processes/landscape` (processes, relations, own and rolled-up asset/initiative counts, opportunity flag, chain order computed from PRECEDES) and `GET /api/processes/landscape/{code}` (the panel). Both are gated by `PROC/VALUE_CHAIN` or `PROC/MAP`, never by Process Management. The UI draws the chain as an HTML/CSS Porter grid and the map as dependency-free SVG with a deterministic lane layout (research R1). Nothing is stored: no DDL, no seed change.

## Technical Context

**Language/Version**: Python ≥ 3.14 (per `api/pyproject.toml`) for the API; TypeScript 5 + Svelte 5 + Astro 5 for the UI.

**Primary Dependencies**: FastAPI + SQLModel (API); Astro 5 SSR, Svelte 5 via manual `mount()`, Tailwind 3 (UI). **No new dependency** (R1).

**Storage**: PostgreSQL 18, existing tables only (`processes`, `related_processes`, `process_assets`, `process_inits`, `assets`, `initiatives`, `business_units`, `users`, `list_items`).

**Testing**: pytest in the API container (`docker compose exec -T api uv run pytest -q`, SQLite test DB); `bun run build`; documented manual browser walkthrough (no UI test framework).

**Target Platform**: Docker Compose locally; Vercel (API via Mangum, UI SSR) + Neon in production.

**Project Type**: web application (API + UI + DB modular monolith).

**Performance Goals**: seed landscape drawn within 2 s; 300 processes / 600 relations within 4 s, interactions under 1 s (SC-003). Landscape read in a constant number of queries (≤ 6).

**Constraints**: read-only; no per-process requests; bounded payload (cap 2 000 processes + `truncated`); every string in en/es; list values through `lib/listLang.ts`; serverless API (no long-lived connections — irrelevant here, all reads are request/response).

**Scale/Scope**: seed = 9 top-level processes + their sub-processes, 8 relations, 9 links. Two pages, three Svelte islands, two endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — still passing.*

| Principle | Design decision | Status |
|-----------|-----------------|--------|
| **I. Modular monolith boundaries** | All server code in the owning domain `api/app/workflows` (the Processes domain): `internal/landscape_service.py` + `routes/landscape.py`, models in `internal/models.py`. Reuses `app/internal/permissions.check_any_privilege`, the managed session (`get_db_session`) and `process_service.full_name`. No duplicated auth or session plumbing. Reads `assets`/`initiatives` models from `lib`/`inits` read-only, as `processes.py` already does. | ✅ |
| **II. API-first contract stability** | Two **additive** endpoints; no existing route, request key or response key changes. `processes.astro` gains an additive `?open=` query handler. The landscape is an aggregate, bounded by a cap + `truncated` instead of `skip`/`limit` — justified in Complexity Tracking. | ✅ (justified) |
| **III. Risk-based testing** | New permission surface (view privileges reading process data) ⇒ automated tests required: `api/tests/test_proc_landscape.py` covers the access matrix, route ordering, shown rule, counts, chain order, unit filter, cap, panel and query count. UI drawing is verified by the documented quickstart walkthrough (UI-only rendering). `make test` + full pytest suite. | ✅ |
| **IV. Security & secret hygiene** | JWT auth unchanged; gate via existing RBAC helpers (superuser bypass and `is_active` semantics preserved). No write route. The panel exposes only names/categories of assets and initiatives linked to a process — the same exposure Process Management's pickers accepted — and only to holders of a PROC view privilege. No secrets touched. | ✅ |
| **V. Performance & operability** | Constant query count, projected columns, no N+1 (pinned by a test with a query counter); cap bounds the payload; structured `logger.info` on truncation. Runs under existing Compose/Make; no new service. | ✅ |
| **Established Domain Patterns** | *Per-resource permissions*: not applicable (Processes has module-level access only, as decided in SpecKit 009). *Content versioning*: not applicable. *Contribution workflows*: not applicable (read-only). | ✅ N/A |

## Project Structure

### Documentation (this feature)

```text
specs/010-process-landscape-views/
├── spec.md
├── plan.md                 # this file
├── research.md             # R1–R9
├── data-model.md
├── quickstart.md
├── contracts/
│   └── landscape-api.md
├── checklists/
│   └── requirements.md
├── synthetic-landscape.sql          # created in implementation (dev-only scale data)
├── synthetic-landscape-remove.sql   # created in implementation
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
api/
├── app/
│   ├── main.py                                   # include landscape router BEFORE processes router
│   └── workflows/
│       ├── internal/
│       │   ├── models.py                         # + Landscape* read models
│       │   └── landscape_service.py              # NEW: shown set, tree, roll-up, chain_order, detail
│       └── routes/
│           └── landscape.py                      # NEW: GET /api/processes/landscape[/{code}]
└── tests/
    └── test_proc_landscape.py                    # NEW (reuses tests/proc_helpers.py)

ui/src/
├── pages/proc/
│   ├── value_chain.astro                         # NEW
│   ├── process_map.astro                         # NEW
│   └── processes.astro                           # + ?open=CODE handler (additive)
├── components/svelte/
│   ├── ValueChain.svelte                         # NEW (HTML/CSS Porter grid)
│   ├── ProcessMap.svelte                         # NEW (SVG lanes, connectors, pan/zoom)
│   └── ProcessLandscapePanel.svelte              # NEW (shared read-only detail panel)
├── lib/
│   └── processLandscape.ts                       # NEW: service calls + pure view helpers + URL state
├── types/api.ts                                  # + Landscape* interfaces
└── i18n/{en,es}.json                             # + value_chain.*, process_map.*, process_landscape.*
```

**Structure Decision**: the existing web-application layout. Server work stays in `api/app/workflows` (there is no `api/app/proc`); UI pages follow `ui/src/pages/{module}/{option}.astro` with the paths already seeded in `options`. The two views share one TS module and one panel component so the navigation and labels are defined once.

### Component responsibilities

| Piece | Owns |
|-------|------|
| `landscape_service.py` | the shown rule, the cap, `display_parent`/`depth`, roll-up sets, `is_opportunity`, `chain_order`, `primary_order`/`support_order`/`child_order`, the panel's incoming/outgoing/`via` lists, `can_*` flags |
| `routes/landscape.py` | the `VALUE_CHAIN` OR `MAP` gate, `unit` validation (400), 404 for non-shown processes |
| `processLandscape.ts` | `getLandscape`, `getLandscapeDetail`; `visibleAncestor`, `mergeEdges`, `neighborhood`; `readViewState`/`writeViewState`; the relation-type style table (marker, dash, arrowheads) used by the map **and** its legend |
| `ValueChain.svelte` | Porter grid from `primary_order`/`support_order`; one-level expansion via `child_order`; counts, status markers, opportunity highlight + *Only opportunities*; unit filter; opens the panel |
| `ProcessMap.svelte` | lane layout, recursive containers, connectors and legend, type filter, search, focus/dim, pan/zoom/fit; opens the panel |
| `ProcessLandscapePanel.svelte` | core fields, outgoing/incoming relations, asset/initiative links with `via`, the three cross-navigation actions gated by `can_*` |

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|-----------|------------|--------------------------------------|
| Landscape endpoint bounded by a cap (2 000) + `truncated`, not `skip`/`limit` (Principle II) | Both views need the whole tree and every relation at once to draw the chain order and the connectors; the counts roll up over subtrees | A page of processes draws a broken chain, orphaned connectors and wrong roll-ups; paging the diagram has no meaning |
| UI types without `Create`/`Update` variants (three-interface convention) | The entities are read models; nothing is created or updated | Empty `Create`/`Update` interfaces would advertise writes that do not exist |
| Custom SVG layout instead of a graph-layout library (R1) | Keeps the map in the same arrangement as the chain and avoids a ~0.4–1.4 MB dependency | elkjs/Cytoscape place nodes independently of chain order (and Cytoscape non-deterministically); kept as the upgrade path if real landscapes become dense meshes |
