# Data Model: Process Landscape Views

**Feature**: [spec.md](spec.md) · **Date**: 2026-10-24

**No DDL and no seed change.** Everything here is a read model derived from the Process Management tables (`db/sql/71-proc-ddl.sql`): `processes`, `related_processes`, `process_assets`, `process_inits`, plus `assets`, `initiatives`, `business_units`, `users` and `list_items`. The options `PROC.VALUE_CHAIN` / `PROC.MAP` and their privileges already exist in `db/sql/12-admin-insert.sql`.

## Source rows and the "shown" rule

| Source | Included when | Spec |
|--------|---------------|------|
| `processes` | `is_active = TRUE` and `status <> 'DEPRECATED'` (Draft, Review, Published) | FR-002 |
| `related_processes` | `is_active = TRUE` and both `source` and `target` are shown | FR-001, Edge Cases |
| `process_assets` | `is_active = TRUE`, the process is shown, and `assets.is_active = TRUE` | FR-001 |
| `process_inits` | `is_active = TRUE`, the process is shown, and `initiatives.is_active = TRUE` | FR-001 |

With `unit=X`: shown = processes of unit X plus their ancestors (ancestors flagged `context`). Cap: at most 2 000 processes by code; `truncated = true` when more exist.

## Read models (API, `api/app/workflows/internal/models.py`)

### `LandscapeProcess`

| Field | Type | Notes |
|-------|------|-------|
| `code` | str | |
| `name` | str | as stored |
| `type` | str | PROCESS_TYPE value (PRIMARY / SUPPORT) |
| `status` | str | PROCESS_STATUS value; DRAFT/REVIEW get a marker |
| `unit`, `unit_name` | str? | |
| `owner_name` | str? | |
| `parent` | str? | stored parent |
| `display_parent` | str? | nearest **shown** ancestor (null = top level) |
| `depth` | int | 0 for top level, from `display_parent` |
| `child_order` | List[str] | direct shown children in chain order (R3) |
| `context` | bool | shown only as an ancestor of a unit-filtered process |
| `own_assets`, `own_inits` | int | distinct active links of the process itself |
| `assets`, `inits` | int | distinct over the process and its shown descendants |
| `is_opportunity` | bool | `assets == 0 and inits == 0` |

### `LandscapeRelation`

| Field | Type | Notes |
|-------|------|-------|
| `source`, `target` | str | shown process codes |
| `type` | str | PROCESS_RELATION_TYPE value |
| `directed` | bool | false for INTERACTS_WITH |

Rationale is not included here (it is read in the panel), to keep the payload small.

### `ProcessLandscape` (response of `GET /api/processes/landscape`)

| Field | Type | Notes |
|-------|------|-------|
| `processes` | List[LandscapeProcess] | ordered by code |
| `relations` | List[LandscapeRelation] | |
| `primary_order` | List[str] | top-level PRIMARY codes in chain order |
| `support_order` | List[str] | top-level SUPPORT codes by code |
| `unit` | str? | the filter applied |
| `truncated` | bool | cap reached |
| `can_value_chain`, `can_map`, `can_manage` | bool | caller holds PROC/VALUE_CHAIN, PROC/MAP, PROC/PROCESSES (read) — drives the panel's actions |

### `LandscapeProcessDetail` (response of `GET /api/processes/landscape/{code}`)

| Field | Type | Notes |
|-------|------|-------|
| core fields | — | `code, name, description, type, parent, parent_name, unit, unit_name, owner_name, status, tags` (no `detail`, `reference` kept) |
| `outgoing` | List[LandscapeRelationDetail] | relations where this is the source (INTERACTS_WITH included once) |
| `incoming` | List[LandscapeRelationDetail] | relations where this is the target, except INTERACTS_WITH (already in `outgoing` as undirected) |
| `assets` | List[LandscapeAssetLink] | own and sub-process links |
| `inits` | List[LandscapeInitLink] | own and sub-process links |

`LandscapeRelationDetail`: `other`, `other_name`, `other_type`, `type`, `rationale`, `directed`.
`LandscapeAssetLink`: `asset`, `asset_name`, `category`, `type`, `rationale`, `via` (null = own link, else the sub-process code that holds it).
`LandscapeInitLink`: `init`, `init_name`, `type`, `rationale`, `via`.

Only shown processes are listed as `other` and `via`; links to inactive targets are omitted.

## Derivations (`api/app/workflows/internal/landscape_service.py`)

1. **Queries (constant count, ≤ 6 per landscape)**: shown processes (projected columns); active relations among them; `(process, asset)` pairs joined to active assets; `(process, init)` pairs joined to active initiatives; unit names; owner names. No query per process.
2. **Tree**: `display_parent` = walk `parent` until a shown process (cycle-safe by the acyclic rule, with a visited guard anyway).
3. **Roll-up**: post-order pass, `assets(p) = own(p) ∪ ⋃ assets(child)` as sets; counts are set sizes.
4. **Chain order**: `chain_order(codes, edges)` (research R3) for `primary_order` and every `child_order`.
5. **Opportunity**: on the rolled-up counts.

## View state (client only, `ui/src/lib/processLandscape.ts`)

| State | View | In the address | Default |
|-------|------|----------------|---------|
| `focus` | both | `?focus=CODE` | none |
| `unit` | both | `?unit=CODE` | all units |
| `opportunities` | Value Chain | `?opportunities=1` | off |
| `types` | Process Map | `?types=PRECEDES,SUPPORTS,…` | all seven |
| drilled process | Process Map | `?in=CODE` | none (main diagram); a `focus` without `in` opens the level where the focused process is drawn |
| legend shown | Process Map | not in the address; `localStorage` per viewer | shown |

## UI types (`ui/src/types/api.ts`)

`ProcessLandscape`, `LandscapeProcess`, `LandscapeRelation`, `LandscapeProcessDetail`, `LandscapeRelationDetail`, `LandscapeAssetLink`, `LandscapeInitLink` — read-only interfaces mirroring the API (no `Create`/`Update` variants, since nothing is written; see plan, Complexity Tracking).
