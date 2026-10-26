# Quickstart: Process Landscape Views

**Feature**: [spec.md](spec.md) · **Contract**: [contracts/landscape-api.md](contracts/landscape-api.md)

## Prerequisites

```bash
make dev                                   # API :8001, UI :4321, DB host :5433
docker compose exec -T api uv run pytest -q   # baseline 837 passed before this feature
```

Seeded users: `admin` / `Admin123!` (superuser), `felipe.cardenas` (ADMINISTRATIVE), `adriana.velez` (COLLABORATOR, read-only on both views, no Process Management), `santiago.marin` (REVIEWER, same). No DDL change: an existing dev database needs no rebuild.

## 1. Automated checks

```bash
docker compose exec -T api uv run pytest -q tests/test_proc_landscape.py
docker compose exec -T api uv run pytest -q       # whole suite stays green
cd ui && bun run build                            # clean build
```

`test_proc_landscape.py` covers: the access matrix of the contract (incl. a PROC/PROCESSES-only profile → 403 and no write methods), route ordering (`/landscape` not captured by `/{code}`), the shown rule (Deprecated and removed excluded), distinct rolled-up counts (an asset linked to parent and child counts once), inactive assets/initiatives excluded, `is_opportunity`, `chain_order` (seed order, isolated nodes, a cycle), the unit filter with context ancestors, the cap with `truncated`, the detail panel (incoming/outgoing, INTERACTS_WITH once, `via`), and a constant query count on 300 processes / 600 relations.

## 2. API smoke (as `adriana.velez`)

1. `GET /api/processes/landscape` → 200; `primary_order` = `INBL, OPER, OUTL, MKTS, SERV`; `can_manage` = false.
2. Compare each process's `assets`/`inits` with a hand count:
   ```sql
   -- rolled-up distinct assets for OPER and its descendants
   WITH RECURSIVE t AS (SELECT code FROM processes WHERE code='OPER'
     UNION ALL SELECT p.code FROM processes p JOIN t ON p.parent=t.code
     WHERE p.is_active AND p.status<>'DEPRECATED')
   SELECT count(DISTINCT pa.asset) FROM process_assets pa
     JOIN assets a ON a.id=pa.asset AND a.is_active
     WHERE pa.is_active AND pa.process IN (SELECT code FROM t);
   ```
3. `GET /api/processes/landscape/OPER` → incoming INBL (Precedes), TECH and HRMG (Supports); outgoing OUTL.
4. `GET /api/processes/OPER` → 403 (Process Management stays closed to her).
5. `GET /api/processes/landscape?unit=CORP` → CORP processes plus needed ancestors flagged `context`.

## 3. Browser walkthrough

**Value Chain** (`/proc/value_chain`, as `adriana.velez`)
- Five primary blocks in chain order ending in the margin marker; four support bands underneath.
- The whole chain fits one screen. Processes with no assets or initiatives are amber (the legend next to the switch says so; no badge); *Only opportunities* dims the rest and adds `opportunities=1` to the address.
- Expand Operations (chevron + count): its sub-processes are listed with their own counts; nothing deeper is listed.
- Put a process in Draft as `felipe.cardenas` in Process Management: it shows a Draft marker; Deprecate it: it disappears.
- Select Operations: the panel opens; *Show in Process Map* lands on the map focused on Operations; *Open in Process Management* is not offered.
- Switch the language: type, status and relation labels change.

**Process Map** (`/proc/process_map`, as `santiago.marin`)
- Two lanes with the top-level boxes; Precedes arrows between primaries, Supports association lines from support to primary; the legend (shown or hidden with the button next to +, −, Fit) lists all seven types.
- Click Operations' "+": the internal diagram replaces the map (pool, sub-processes, start/end events when they have Precedes links, outside processes below); Back returns. Uncheck Supports (address `types=` updates, no box moves); search "develop" and pick Software Development: the map opens Operations' level with it focused, the rest dimmed.
- Reload the copied address: same focus and filters.
- From the panel, *Show in Value Chain* lands on the chain with Operations highlighted.

**Process Management deep link** (as `felipe.cardenas`)
- In either view's panel, *Open in Process Management* opens `/proc/processes?open=OPER` with the edit dialog showing Operations.

**Access**
- A user holding neither view option: the sidebar shows neither, both pages are refused, and the API answers 403.

## 4. Scale check (manual, development only)

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < specs/010-process-landscape-views/synthetic-landscape.sql
``` It adds ~300 processes and ~600 relations, plus links to **existing** assets and initiatives only, all with a `SYN-` code prefix. Check SC-003 (draw under 4 s; expand, filter, focus under 1 s), then remove them with `synthetic-landscape-remove.sql`.
