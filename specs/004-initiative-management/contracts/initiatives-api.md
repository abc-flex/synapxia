# API Contracts: Initiative Management

**Branch**: `004-initiative-management` | **Phase**: 1 | **Date**: 2026-09-23
**Auth**: every endpoint requires a valid JWT (Bearer header or auth cookie); `401` otherwise.
**Envelope**: responses are wrapped by the global middleware as `{ data, error, meta }`; bodies
below show the inner `data`. Errors carry `error.code` / `error.message`.
**Superusers** bypass every privilege and per-initiative check.

> **Additive only.** No existing endpoint, request key or response key is removed or renamed
> (Principle II). The three existing `GET /api/initiatives/*` routes are unchanged.

## Summary

| Endpoint | Status | Gate (outer RBAC) | Per-initiative |
|----------|--------|-------------------|----------------|
| `GET /api/initiatives/with-access` | **new** | `INITS/INITIATIVES` read | scoped to accessible |
| `PUT /api/initiatives/{id}` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `DELETE /api/initiatives/{id}` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `GET /api/initiatives/{id}/diagnostics` | **new** | `INITS` any of `INITIATIVES`,`EXPLORE` | VIEW |
| `GET /api/initiatives/{id}/assets` | **new** | `INITS` any of `INITIATIVES`,`EXPLORE` | VIEW |
| `POST /api/initiatives/{id}/assets` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `DELETE /api/initiatives/{id}/assets/{asset_id}/{type}` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `GET /api/init_permissions/init/{init_id}` | **new** | `INITS/INITIATIVES` read | VIEW |
| `POST /api/init_permissions/` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `PUT /api/init_permissions/{id}` | **new** | `INITS/INITIATIVES` edit | MANAGE |
| `DELETE /api/init_permissions/{id}` | **new** (revoke) | `INITS/INITIATIVES` edit | MANAGE |
| `GET /api/collaborations/history/init/{init_id}` | **new** | `INITS` any of `INITIATIVES`,`EXPLORE` | VIEW |
| `GET /api/collaborations/discussion/init/{init_id}` | **new** | `INITS` any of `INITIATIVES`,`EXPLORE` | VIEW |

Route order: `/with-access` is declared **before** `/{init_id}` in `initiatives.py`.

---

## GET /api/initiatives/with-access

Active initiatives the caller can access, filtered **before** pagination.

| Query | Type | Default | Bound |
|-------|------|---------|-------|
| `skip` | int | 0 | ≥ 0 |
| `limit` | int | 100 | 1–500 |

`200` — ordered by `name`:

```json
[
  {
    "id": 3, "name": "Knowledge Assistant (RAG)", "description": "…",
    "type": "PROTOTYPING", "expected_impact": "TIME_REDUCTION", "priority_level": "HIGH",
    "status": "ACCEPTED", "reference": null, "tags": ["genai","rag"], "detail": "…",
    "score": 15, "is_active": true, "created_at": "…", "updated_at": null,
    "my_access": "MANAGE",
    "is_favorite": false,
    "allowed_statuses": ["ACCEPTED", "IN_PROGRESS", "DELIVERED", "ARCHIVED"]
  }
]
```

No grants → `[]`. `allowed_statuses` is `[status]` when no move is available (control locked).

## PUT /api/initiatives/{id}

Body — `InitiativeUpdate`, every key optional; only sent keys are applied:

```json
{ "name": "…", "description": "…", "type": "IMPLEMENTATION",
  "expected_impact": "COST_SAVINGS", "priority_level": "MEDIUM",
  "reference": "https://…", "tags": ["a","b"], "detail": "…", "status": "IN_PROGRESS" }
```

| Result | When |
|--------|------|
| `200` updated `InitiativeWithAccess` | success; if status changed, one `KICKOFF`/`DELIVERY`/`ARCHIVING` collaboration (`HANDLED`, actor) was written in the same commit |
| `400` | blank required field; unknown list value; status move not allowed (`"Status transition ACTIVATED → DELIVERED is not allowed"`); inactive initiative |
| `403` | missing privilege or no MANAGE |
| `404` | unknown id |

`score` in the body is ignored (not part of `InitiativeUpdate`). Sending the current status, or
omitting it, is not a transition and writes nothing.

## DELETE /api/initiatives/{id}

Logical delete (`is_active=false`). `200` → the initiative; `400` already inactive; `403`; `404`.
No collaboration is written.

## GET /api/initiatives/{id}/diagnostics

| Query | Type | Default |
|-------|------|---------|
| `lang` | `en` \| `es` | `en` |

`200`:

```json
{
  "init": 4,
  "score": null,
  "items": [
    {
      "criteria": "CLARITY_MATURITY",
      "name": "Clarity and maturity of the need",
      "description": "Level of definition of the need",
      "list": "CLARITY_MATURITY",
      "is_active_criteria": true,
      "creator_score": 2,
      "creator_label": "Definida de forma parcial y requiere validación",
      "reviewer_score": null,
      "reviewer_label": null,
      "rationale": null
    }
  ]
}
```

One item per active criterion plus any inactive criterion with an answer. `403` without VIEW;
`404` unknown initiative.

## GET /api/initiatives/{id}/assets

`200` — active links, newest first:

```json
[
  { "asset": 8, "asset_name": "Filesystem MCP", "category": "MCPS",
    "asset_status": "PUBLISHED", "type": "USED_BY",
    "rationale": "Access to files is required for the platform.", "created_at": "…" }
]
```

## POST /api/initiatives/{id}/assets

Body `{ "asset": 8, "type": "USED_BY", "rationale": "…" }` (`rationale` optional).

| Result | When |
|--------|------|
| `201` `InitiativeAsset` | created, or an inactive link with the same asset AND type reactivated with the new rationale |
| `400` | unknown/inactive asset; unknown `RELATION_TYPE` value |
| `403` | no init MANAGE, or the caller cannot see the asset |
| `409` | an active link to that asset with that type already exists (the same asset with a different type is allowed) |

## DELETE /api/initiatives/{id}/assets/{asset_id}/{type}

Logical delete of that (asset, type) link only. `200`; `400` already inactive; `403`; `404` no such link.

---

## GET /api/init_permissions/init/{init_id}

`200` — live grants (not revoked; future-dated included), `skip`/`limit` (default 0/100, max
500):

```json
[
  { "id": 12, "init": 3, "target_type": "USER", "target_code": "5",
    "access_level": "MANAGE", "valid_from": "…", "valid_to": null }
]
```

## POST /api/init_permissions/

Body `{ "init": 3, "target_type": "TEAM", "target_code": "LAB", "access_level": "VIEW",
"valid_from": "…?", "valid_to": "…?" }`. `201`; `400` unknown initiative / invalid window
(`valid_to <= valid_from`); `403`; `409` live duplicate of
`(init, target_type, target_code, access_level)` — a revoked grant does not block.

## PUT /api/init_permissions/{id}

Partial update of `access_level`, `valid_from`, `valid_to`. `200`; `400` revoked grant / invalid
window; `403`; `404`.

## DELETE /api/init_permissions/{id}

**Revoke**: sets `valid_to = now()` (overwrites a future `valid_to`); row retained. `200` → the
grant; `400` already revoked; `403`; `404`.

---

## GET /api/collaborations/history/init/{init_id}

`skip`/`limit` (default 0/100, max 500). `200` — `HistoryEntry[]`, newest first, same shape as
`/api/actions/history/asset/{id}`:

```json
[
  { "id": 41, "type": "KICKOFF", "workflow_status": "HANDLED",
    "actor": "maria.lopez", "summary": "kicked off the initiative", "content": null,
    "created_at": "…" },
  { "id": null, "type": "CREATED", "workflow_status": null,
    "actor": null, "summary": "created the initiative", "content": null,
    "created_at": "…" }
]
```

`content` is populated only for COMMENT / QUESTION / ANSWER. The UI localises with
`history.action.{type}` / `{type}_{workflow_status}` and falls back to `summary`.

## GET /api/collaborations/discussion/init/{init_id}

`200` — `DiscussionItem[]`, oldest first, same shape as `/api/actions/discussion/asset/{id}`
except that `asset` is replaced by `init` (`id`, `init`, `user_id`, `author`, `type`, `content`, `parent`, `created_at`); answers reference their
question through `parent`. Read-only — no write routes are added by this feature.

---

## Amendment (2026-09-23) — several links per pair on the `lib` side too

Additive routes (existing pair routes unchanged for single-link pairs; see research R13):

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/asset_relations/{source}/{target}/{type}` | **new** | one link |
| `PUT /api/asset_relations/{source}/{target}/{type}` | **new** | `rationale` / `is_active`; changing `type` → 400 |
| `DELETE /api/asset_relations/{source}/{target}/{type}` | **new** | logical delete of that link only |
| `GET`/`PUT`/`DELETE /api/asset_inits/{asset}/{init}/{type}` | **new** | same semantics |
| `…/asset_relations/{source}/{target}`, `…/asset_inits/{asset}/{init}` | **changed (compatible)** | act on the pair's single link; **409** when the pair holds several (use the typed route) |
| `POST /api/asset_relations/`, `POST /api/asset_inits/` | **changed (compatible)** | duplicate = same pair AND type (409 if active); an inactive identical link is reactivated (201) |
| `GET /api/asset_relations/related/{id}` | **changed (compatible)** | lists every outgoing link (one entry per type); incoming only for assets with no outgoing link |
