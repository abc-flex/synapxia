# Contract: Processes API

**Feature**: `009-process-management` · All routes are **new** and additive (Constitution II). Every response under `/api/` is wrapped in the `{ data, error, meta }` envelope by the global middleware; the shapes below are the `data` part. All routes require a JWT (401 without one) and `PROC/PROCESSES`: read for GET and edit for writes (403 otherwise; superusers bypass).

Error mapping: 400 validation (with a message naming the field or rule) · 404 unknown or removed process · 409 conflict (duplicate code, removal with active children).

---

## Processes

### `GET /api/processes/`

Query: `skip` (≥ 0, default 0), `limit` (1–500, default 100), `type`, `status`, `unit` (all optional, exact match), `q` (optional; case-insensitive match on code, name and description). Active processes only, ordered by code.

```json
[{
  "code": "OPER-DEVELOP", "name": "Software Development", "description": "…",
  "type": "PRIMARY", "parent": "OPER", "parent_name": "Operations",
  "unit": "ENG", "unit_name": "Engineering",
  "owner": 0, "owner_name": "Admin User",
  "reference": null, "status": "PUBLISHED", "tags": ["devops"], "detail": null,
  "created_at": "…", "updated_at": null
}]
```

`meta` echoes `skip`, `limit` and the count returned.

### `GET /api/processes/form-options`

```json
{
  "can_edit": true,
  "processes":   [{"code": "OPER", "name": "Operations", "type": "PRIMARY"}],
  "units":       [{"code": "ENG", "name": "Engineering"}],
  "owners":      [{"id": 0, "name": "Admin User"}],
  "assets":      [{"id": 1, "name": "Python web prompt", "category": "PROMPTS"}],
  "initiatives": [{"id": 1, "name": "Organizational Knowledge Management Platform"}],
  "relation_rules": {
    "SUPPORTS": {"source": ["SUPPORT"], "target": ["PRIMARY"]},
    "PRECEDES": {"same_type": true}
  }
}
```

Active records only. Declared before `/{code}`, so `form-options` is never read as a process code.

### `GET /api/processes/{code}`

Returns the list shape plus `"allowed_statuses": ["REVIEW", "PUBLISHED", "DRAFT"]`, with the current status first. Returns 404 if the process is unknown or inactive.

### `POST /api/processes/` → 201

```json
{
  "code": "OPER-QA", "name": "Quality Assurance", "description": null,
  "type": "PRIMARY", "parent": "OPER", "unit": "ENG", "owner": 0,
  "reference": null, "tags": ["quality"], "detail": null,
  "status": "DRAFT",
  "relations": [{"target": "OPER-DEVELOP", "type": "PRECEDES", "rationale": "…"}],
  "assets":    [{"asset": 1, "type": "RELATED_TO", "rationale": null}],
  "inits":     [{"init": 3, "type": "RELATED_TO", "rationale": null}]
}
```

- `status` is optional; any value other than `DRAFT` returns 400.
- `owner` is optional and defaults to the caller.
- `relations`, `assets` and `inits` are optional.
- **All-or-nothing**: if any field or link fails validation, nothing is written.
- Returns the detail shape.

### `PUT /api/processes/{code}`

Core fields only: `name`, `description`, `type`, `parent`, `unit`, `owner`, `reference`, `status`, `tags` and `detail`, all optional (partial update). There is no `code` key; one sent is ignored. Validation:
- `status` must follow the lifecycle.
- `parent` must keep the hierarchy acyclic.
- A `type` change must not break active SUPPORTS/PRECEDES links; the 400 lists those links.

Links are untouched. Returns the detail shape.

### `DELETE /api/processes/{code}`

Logical removal (`is_active = false`). Returns 409 while active child processes exist. Links are kept. Returns the removed process.

---

## Links (one atomic replace per tab)

Each `PUT` takes the tab's **full desired set** and applies it in one transaction:
- a stored active row missing from the set is deactivated;
- an identical inactive row is reactivated;
- a new row is inserted;
- a row whose rationale changed is updated.

Any invalid item returns 400 and nothing changes. Each `PUT` returns the resulting active set, in the same shape as the matching `GET`.

### `GET /api/processes/{code}/relations`

```json
[{"source": "OUTL", "target": "MKTS", "target_name": "Marketing & Sales", "target_type": "PRIMARY",
  "target_active": true, "type": "PRECEDES", "rationale": "…", "direction": "outgoing"},
 {"source": "SERV", "target": "OUTL", "target_name": "Service", "target_type": "PRIMARY",
  "target_active": true, "type": "INTERACTS_WITH", "rationale": null, "direction": "incoming"}]
```

For an `incoming` row, `target`, `target_name` and `target_type` describe the **other** process, so the UI renders every row the same way.

### `PUT /api/processes/{code}/relations`

```json
{"relations": [{"target": "MKTS", "type": "PRECEDES", "rationale": "…"},
               {"target": "SERV", "type": "INTERACTS_WITH", "rationale": null}]}
```

`target` is always "the other process". The server keeps an existing incoming `INTERACTS_WITH` row as stored rather than flipping it. The request is refused (400) when any item:
- relates the process to itself;
- has a target that is unknown or inactive;
- has a type outside `PROCESS_RELATION_TYPE`;
- is a duplicate within the set, including an unordered `INTERACTS_WITH` pair;
- breaks the SUPPORTS/PRECEDES compatibility rule.

### `GET /api/processes/{code}/assets` · `PUT /api/processes/{code}/assets`

```json
// GET item
{"asset": 1, "asset_name": "Python web prompt", "category": "PROMPTS", "asset_active": true,
 "type": "RELATED_TO", "rationale": "…"}
// PUT body
{"assets": [{"asset": 1, "type": "RELATED_TO", "rationale": "…"}]}
```

Validation: the asset must be active, the type must be in `RELATION_TYPE`, and there are no duplicate `(asset, type)` pairs.

### `GET /api/processes/{code}/inits` · `PUT /api/processes/{code}/inits`

The same as assets, with `init`, `init_name` and `init_active`; the body key is `inits`.

---

## UI service layer (`ui/src/lib/processes.ts`)

`getProcesses(skip, limit, filters)`, `getProcess(code)`, `getProcessFormOptions()`, `createProcess(body)`, `updateProcess(code, body)`, `deleteProcess(code)`, `getProcessRelations(code)` / `saveProcessRelations(code, items)`, `getProcessAssets` / `saveProcessAssets`, `getProcessInits` / `saveProcessInits`. All go through `lib/api.ts`, which unwraps `.data`.

Types in `ui/src/types/api.ts`: `Process`, `ProcessCreate`, `ProcessUpdate`, `ProcessDetail`, `ProcessRelation`, `ProcessAssetLink`, `ProcessInitLink`, `ProcessFormOptions`.
