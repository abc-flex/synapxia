# Contract: Process Landscape API

**Feature**: [../spec.md](../spec.md) · **Data model**: [../data-model.md](../data-model.md)

Both endpoints are additive, read-only and wrapped in the standard `{ data, error, meta }` envelope (`api/app/main.py`). Route module: `api/app/workflows/routes/landscape.py`, included **before** `processes.py`.

**Access (both)**: authenticated active user holding `PROC/VALUE_CHAIN` **or** `PROC/MAP` at read level (`check_any_privilege(session, user, "PROC", ["VALUE_CHAIN", "MAP"])`); superusers bypass as usual. `PROC/PROCESSES` is not required.

| Caller | Result |
|--------|--------|
| no token | 401 |
| holds neither view privilege (even with PROC/PROCESSES) | 403 |
| COLLABORATOR / REVIEWER (seeded read-only on both views) | 200 |
| ADMINISTRATOR / ADMINISTRATIVE | 200 |

No POST/PUT/PATCH/DELETE exists under `/api/processes/landscape` (405).

---

## `GET /api/processes/landscape`

**Query**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `unit` | string | no | business unit code; unknown or inactive unit → 400 |

**200** `data`: `ProcessLandscape`

```json
{
  "processes": [
    { "code": "OPER", "name": "Operations", "type": "PRIMARY", "status": "PUBLISHED",
      "unit": "ENG", "unit_name": "Engineering", "owner_name": "Admin",
      "parent": null, "display_parent": null, "depth": 0,
      "child_order": ["OPER-DEVELOP", "…"], "context": false,
      "own_assets": 0, "own_inits": 0, "assets": 2, "inits": 0, "is_opportunity": false }
  ],
  "relations": [
    { "source": "INBL", "target": "OPER", "type": "PRECEDES", "directed": true }
  ],
  "primary_order": ["INBL", "OPER", "OUTL", "MKTS", "SERV"],
  "support_order": ["HRMG", "INFR", "PROC", "TECH"],
  "unit": null,
  "truncated": false,
  "can_value_chain": true, "can_map": true, "can_manage": false
}
```

`meta`: `{ "count": <processes returned> }`.

**Guarantees**: shown rule and cap per data-model; `primary_order`/`child_order` per research R3; counts distinct and rolled up per R4; constant number of queries.

---

## `GET /api/processes/landscape/{code}`

**200** `data`: `LandscapeProcessDetail`

```json
{
  "code": "OPER", "name": "Operations", "description": "…", "type": "PRIMARY",
  "parent": null, "parent_name": null, "unit": "ENG", "unit_name": "Engineering",
  "owner_name": "Admin", "reference": null, "status": "PUBLISHED", "tags": [],
  "outgoing": [
    { "other": "OUTL", "other_name": "Outbound Logistics", "other_type": "PRIMARY",
      "type": "PRECEDES", "rationale": "…", "directed": true }
  ],
  "incoming": [
    { "other": "INBL", "other_name": "Inbound Logistics", "other_type": "PRIMARY",
      "type": "PRECEDES", "rationale": "…", "directed": true },
    { "other": "TECH", "other_name": "Technology Development", "other_type": "SUPPORT",
      "type": "SUPPORTS", "rationale": "…", "directed": true }
  ],
  "assets": [
    { "asset": 1, "asset_name": "…", "category": "PROMPTS", "type": "RELATED_TO",
      "rationale": "…", "via": "OPER-DEVELOP" }
  ],
  "inits": []
}
```

**404**: unknown, removed or Deprecated process (not shown in the views).

---

## UI contract (pages and query strings)

| Page | Privilege (SSR middleware + sidebar) | Query string |
|------|--------------------------------------|--------------|
| `/proc/value_chain` | `PROC/VALUE_CHAIN` | `focus`, `unit`, `opportunities=1` |
| `/proc/process_map` | `PROC/MAP` | `focus`, `unit`, `in=<CODE>` (drilled process), `types=<comma list>` |
| `/proc/processes` (existing, additive) | `PROC/PROCESSES` | `open=<CODE>` opens that process's edit dialog |

Panel actions: *Show in Process Map* → `/proc/process_map?focus=CODE` (if `can_map`); *Show in Value Chain* → `/proc/value_chain?focus=<top-level CODE>` (if `can_value_chain`); *Open in Process Management* → `/proc/processes?open=CODE` (if `can_manage`).
