# API Contracts: Asset Notification Scheme Redesign

**Branch**: `003-asset-notifications-redesign` | **Phase**: 1 | **Date**: 2026-09-16
**Base path**: `/api/actions`
**Auth**: every endpoint requires `Authorization: Bearer <JWT>` (or the auth cookie).
**Envelope**: all responses are wrapped by the global middleware as `{ data, error, meta }`;
bodies below show the inner `data`. The UI unwraps centrally in `ui/src/lib/api.ts`.

> ⚠ **Breaking change notice.** This feature removes endpoints and a response key, departing
> from Constitution Principle II. Justified in `plan.md` § Complexity Tracking: the product is
> unreleased and the bundled UI is the sole consumer. Every removal below is adapted in the
> same PR.

---

## Summary of changes

| Endpoint | Status |
|----------|--------|
| `GET /api/actions/requests` | **new** |
| `GET /api/actions/notifications` | **changed** (narrowed; `unread` removed) |
| `POST /api/actions/notifications/{id}/acknowledge` | **renamed** from `.../dismiss` |
| `POST /api/actions/notifications/{id}/notified` | **removed** |
| `GET /api/actions/reviews` | **removed** |
| `GET /api/actions/modifications` | **removed** |

---

## GET /api/actions/requests

Every asset the caller has taken part in — requests directed at them plus assets they
proposed. One entry per asset (FR-006b). Backs the "My Asset Requests" page.

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `state` | `"pending" \| "handled"` | `"pending"` | Which view to return |
| `skip` | `int` | `0` | Records to skip |
| `limit` | `int` | `50` | Max records (bounded, per Principle II) |

### Response `200 OK`

Newest change first.

```json
[
  {
    "asset": 12,
    "asset_name": "Prompt de prueba 2",
    "asset_status": "PROPOSED",
    "category": "PROMPTS",
    "roles": ["PROPOSER"],
    "state": "PENDING",
    "awaited_party": "OTHER",
    "pending_action_id": null,
    "pending_action_type": null,
    "last_change_at": "2026-09-16T10:31:02Z"
  },
  {
    "asset": 7,
    "asset_name": "PostgreSQL MCP Server",
    "asset_status": "PROPOSED",
    "category": "MCPS",
    "roles": ["REVIEWER"],
    "state": "PENDING",
    "awaited_party": "SELF",
    "pending_action_id": 48,
    "pending_action_type": "REVIEW",
    "last_change_at": "2026-09-16T09:12:44Z"
  }
]
```

### Field notes

- `awaited_party` is `"SELF"`, `"OTHER"`, or `null` when `state` is `"HANDLED"`.
- `pending_action_id` / `pending_action_type` are non-null only when `awaited_party` is
  `"SELF"`; they are what the client opens the action screen with.
- `roles` contains `"PROPOSER"`, `"REVIEWER"`, or both (an administrative user may hold both
  on the same asset).
- `asset_name` may be `null` if the asset row is gone; clients fall back to `#<asset>`.

### Errors

| Status | When |
|--------|------|
| `401` | no or invalid credentials |

No `403` case: the endpoint is inherently scoped to the caller's own rows, following the
2026-09-09 precedent where self-scoping endpoints dropped the never-seeded `LIB/ACTIONS`
privilege gate in favour of `current_active_user`.

---

## GET /api/actions/notifications

**Changed.** Now returns only threads that are `PENDING` **and** awaiting the caller — the
`awaited_party == "SELF"` subset of `participations` (INV-2). Previously it returned both
`ASSIGNED` and `NOTIFIED` threads.

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | `int` | `5` | Max entries for the panel (FR-016) |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": 48,
      "asset": 7,
      "asset_name": "PostgreSQL MCP Server",
      "type": "REVIEW",
      "created_at": "2026-09-16T09:12:44Z"
    }
  ],
  "total": 3
}
```

`total` is the full count of entries awaiting the caller, so the panel can say "3 pending"
and indicate that more exist beyond the `limit` (FR-016) without a second request.

### Removed from the previous response

- **`unread`** — deleted. Every entry in this feed is by definition awaiting the caller;
  there is no second axis (FR-002).
- **`workflow_status`** — deleted. It is invariably `PENDING` here.

### Breaking-change note

The response shape moves from a bare array to `{ items, total }`. `ui/src/lib/notifications.ts`
and `NotificationBell.svelte` are updated in the same PR.

---

## POST /api/actions/notifications/{id}/acknowledge

**Renamed** from `POST /api/actions/notifications/{id}/dismiss`. Records that the caller has
taken note of an informational outcome, moving the thread to `HANDLED` (FR-010a).

### Path parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `int` | The action row id from `participations` or `notifications` |

### Request body

None.

### Response `200 OK`

The newly inserted terminal row.

```json
{
  "id": 132,
  "asset": 7,
  "user_id": 4,
  "type": "PUBLICATION",
  "workflow_status": "HANDLED",
  "created_at": "2026-09-16T12:40:00Z"
}
```

### Errors

| Status | When |
|--------|------|
| `400` | the action is `REVIEW` or `MODIFICATION` — those are resolved by deciding or resubmitting, never acknowledged |
| `403` | the action is not addressed to the caller |
| `404` | no such action |
| `409` | data conflict inserting the terminal row |

The `400` guard is today's `DISMISSIBLE_TYPES` check kept intact under an accurate name: it
still admits only `PUBLICATION` and `REJECTION`. What changes is the meaning — acknowledging
is now *resolving* the item, not hiding an unresolved one (FR-017).

---

## Removed endpoints

### `POST /api/actions/notifications/{id}/notified`

Removed. It existed to record that a user had viewed an item, which FR-002 and FR-003
forbid. Callers removed in the same PR: `ReviewAction.svelte:142`, `ModifyAction.svelte:200`,
`ShowAction.svelte:113`, and `markNotified` in `ui/src/lib/notifications.ts`.

### `GET /api/actions/reviews` and `GET /api/actions/modifications`

Removed. Each returned a single-type slice of what `participations` now returns whole;
retaining them would leave exactly the partial duplicate lists FR-027 requires retiring.
Callers removed in the same PR: `getReviewRequests` / `getPendingModifications` in
`ui/src/lib/notifications.ts`, `my_asset_requests.astro`, and `modifications.astro` (deleted).

---

## Unchanged

`POST /api/assets/{id}/review` and `POST /api/assets/{id}/resubmit` keep their paths,
request bodies and status codes. Their internals change only in which enum value they write
(`HANDLED` instead of `FINISHED`, `PENDING` instead of `ASSIGNED`). The asset activity
history endpoints are likewise unchanged in shape; only the state labels they render differ.
