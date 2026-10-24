# Quickstart: Process Management validation

**Feature**: `009-process-management` · Contracts: [contracts/processes-api.md](contracts/processes-api.md) · Rules: [data-model.md](data-model.md)

## Prerequisites

1. The DDL and seed are edited in place (research R2), so recreate the database:
   ```bash
   make rebuild && make dev
   ```
2. Check the seed:
   ```bash
   make shell
   -- inside psql:
   SELECT value FROM list_items WHERE list = 'PROCESS_RELATION_TYPE' AND lang = 'es' ORDER BY sort_order;  -- 7 rows
   SELECT source, target, type FROM related_processes ORDER BY type, source;  -- PRECEDES chain + SUPPORTS
   SELECT process, asset, type FROM process_assets;                            -- all RELATED_TO
   ```
3. Get tokens for `admin` (superuser), an ADMINISTRATIVE user and a COLLABORATOR (`adriana.velez`).

## Automated checks

```bash
docker compose exec -T api uv run pytest -q tests/test_proc_*.py   # new suites
docker compose exec -T api uv run pytest -q                        # full suite, baseline 749 passed + new
make test
cd ui && bun run build
```

## API scenarios (as ADMINISTRATIVE)

| # | Call | Expect |
|---|------|--------|
| 1 | `GET /api/processes/?type=SUPPORT&limit=500` | Only support processes |
| 2 | `GET /api/processes/form-options` | `can_edit: true`, `relation_rules` present |
| 3 | `POST /api/processes/` OPER-QA with one link of each kind | 201, `status: DRAFT`, three links present |
| 4 | Same POST again | 409 |
| 5 | POST with `status: PUBLISHED` | 400 |
| 6 | POST with a link of `type: SIMILAR_TO` in `relations` | 400, and the process **not** created |
| 7 | `PUT /api/processes/OPER-QA` `{status: PUBLISHED}` | 400 (DRAFT → PUBLISHED not allowed) |
| 8 | `{status: REVIEW}`, then `{status: DRAFT}`, `{status: REVIEW}`, `{status: PUBLISHED}`, `{status: DEPRECATED}` | 200 each; then `{status: PUBLISHED}` → 400 |
| 9 | `PUT /api/processes/OPER {parent: "OPER-QA"}` | 400 (cycle) |
| 10 | `PUT /api/processes/HRMG/relations` with `{target: "TECH", type: "SUPPORTS"}` | 400 (Support → Support) |
| 11 | `PUT /api/processes/INBL/relations` with `{target: "TECH", type: "PRECEDES"}` | 400 (Primary → Support) |
| 12 | `PUT /api/processes/OUTL/relations` keeping `MKTS PRECEDES` + adding `SERV INTERACTS_WITH` | 200; `GET /api/processes/SERV/relations` shows it as `incoming` |
| 13 | `PUT /api/processes/SERV/relations` with the incoming `OUTL` row **and** a new `{target: "OUTL", type: "INTERACTS_WITH"}` in the same set | 400 duplicate (both orientations are one link; sending it once keeps the stored row) |
| 14 | `PUT /api/processes/TECH {type: "PRIMARY"}` | 400 listing `TECH SUPPORTS OPER` |
| 15 | `DELETE /api/processes/OPER` | 409 (has children) |
| 16 | Remove a link through PUT, then add it back | Same row reactivated (`created_at` unchanged) |
| 17 | Any call as COLLABORATOR | 403; without a token → 401 |

Clean up: `DELETE /api/processes/OPER-QA`.

## UI scenarios (`/proc/processes`, browser, en and es)

1. The sidebar shows **Process Management / Gestión de Procesos**. The table lists the seeded processes, and the type, status and unit filters and the search work. Switching the language relabels type and status.
2. **New Process**: the tabs are, in order, **Core Fields, Related processes, Related assets, Related inits**. Status is not selectable. Stage one link per tab and save once; reopen and see all three.
3. **Related processes**:
   - Pick *Supports* on a Support process: the target picker offers only Primary processes.
   - Pick *Precedes*: it offers only processes of the same type.
   - The current process is never offered.
   - Picking a target and then switching to an incompatible type shows the inline rule message.
   - A missing field or a duplicate shows the same inline messages as Asset Management.
4. **Edit**: each tab shows a dot while it has unsaved changes. *Save related processes* saves only that tab; the other tabs keep their dots.
5. **Status control**:
   - In Review it offers Review, Published and Draft.
   - In Published it offers Published and Deprecated.
   - In Deprecated it is read-only.
6. **Visual parity**: compare the three process Related tabs side by side with `/lib/assets` → Edit Asset → Related Assets. Controls, spacing, messages and the list rows should match.
7. Closing with unsaved changes asks for confirmation.
8. **Read-only**: give a test profile `PROC/PROCESSES` with `can_edit = FALSE`. There is no New Process button, the dialog opens without save buttons or add rows, and there is no remove action.
9. **Dark mode**: the dialog and tabs are readable.
