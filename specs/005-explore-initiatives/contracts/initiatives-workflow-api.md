# API Contracts: Explore Initiatives, Propose, Diagnosis, Modify & Notifications

**Branch**: `005-explore-initiatives` | **Phase**: 1 | **Date**: 2026-09-24

- **Auth.** Every endpoint requires a valid JWT (Bearer header or auth cookie); otherwise `401`.
- **Envelope.** Bodies below show the inner `data` of `{ data, error, meta }`.
- **Superusers.** They bypass privilege and per-initiative checks. The workflow-assignment checks (holding the PENDING thread) still apply, as on the asset side.

> **Additive only (Principle II).** No existing endpoint, request key or response key is removed or renamed. All spec 004 routes and all `lib` routes keep their contracts. The `lib` reviewer functions move to `app/internal/reviewers.py` behind unchanged re-exports.

Legend:
- `INITS:any` = `check_any_privilege(session, user, "INITS", ["EXPLORE", "INITIATIVES"])` (read)
- `INITS:any+edit` = the same check with `can_edit=True`
- `self` = `current_active_user`, with every row scoped to `current.id`

## Summary

| # | Endpoint | Gate | Per-initiative / assignment |
|---|---|---|---|
| 1 | `GET /api/initiatives/explore` | `INITS:any` | scoped to accessible, `EXPLORE_STATUSES` |
| 2 | `GET /api/initiatives/reviewers` | `INITS:any` | — |
| 3 | `GET /api/initiatives/linkable-assets` | `INITS:any` | assets visible to the caller |
| 4 | `POST /api/initiatives/propose` | `INITS:any+edit` | — |
| 5 | `POST /api/initiatives/{id}/diagnose` | `self` | PENDING DIAGNOSIS + eligible reviewer |
| 6 | `POST /api/initiatives/{id}/resubmit` | `self` | PENDING MODIFICATION + proposer |
| 7 | `GET /api/collaborations/votes/init/{id}` | `INITS:any` | VIEW |
| 8 | `PUT /api/collaborations/votes/init/{id}` | `INITS:any+edit` | VIEW |
| 9 | `DELETE /api/collaborations/votes/init/{id}` | `INITS:any+edit` | VIEW |
| 10 | `GET /api/collaborations/requests` | `self` | own rows |
| 11 | `GET /api/collaborations/notifications` | `self` | own rows |
| 12 | `POST /api/collaborations/notifications/{id}/acknowledge` | `self` | owner of the row |
| 13 | `GET /api/collaborations/{id}` | `self` | owner of the row (or superuser), workflow rows only |
| 14 | `GET /api/initiatives/diagnosis-form` | `INITS:any` | — |

**Route order.**
- In `initiatives.py`, `/explore`, `/reviewers`, `/linkable-assets`, `/diagnosis-form` and `/propose` are declared **before** `/{init_id}`.
- In `collaborations.py`, `/votes/*`, `/requests` and `/notifications*` are declared **before** `/{collab_id}`.

---

## 1. GET /api/initiatives/explore

| Query | Type | Default | Bound |
|---|---|---|---|
| `skip` | int | 0 | ≥ 0 |
| `limit` | int | 100 | 1–500 |

- Filtered before pagination to: active, status ∈ {ACCEPTED, IN_PROGRESS, DELIVERED}, reachable through a live grant (superuser: all).
- Ordered by `created_at` desc, then `id` desc.

`200`:

```json
[
  {
    "id": 3, "name": "Knowledge Assistant (RAG)", "description": "…",
    "type": "PROTOTYPING", "expected_impact": "TIME_REDUCTION", "priority_level": "HIGH",
    "status": "ACCEPTED", "reference": null, "tags": ["genai","rag"], "detail": null,
    "score": 15, "is_active": true, "created_at": "…", "updated_at": null,
    "my_access": "MANAGE", "is_favorite": false,
    "permission_scopes": ["TEAM","USER"],
    "votes": { "init": 3, "positive": 2, "negative": 0, "score": 2, "my_vote": null },
    "discussion_count": 4,
    "related_assets_count": 1
  }
]
```

- No accessible initiatives → `[]`.
- Constant query count: a grants query, the page query, and one grouped query each for favorites, votes, discussion and links.

## 2. GET /api/initiatives/reviewers

`200` → `ReviewerOption[]` `{value, label, profile, is_superuser}`. The eligible reviewers per `app/internal/reviewers.list_reviewers`, excluding the caller unless the caller is an admin or superuser.

## 3. GET /api/initiatives/linkable-assets

`200` → `[{ "value": 8, "label": "Customer Support Prompt", "category": "PROMPTS" }]`: active assets the caller can see (superuser: all), ordered by name. Unpaginated, like the other `select` endpoints.

## 4. POST /api/initiatives/propose

Request (`InitiativeProposeRequest`, see data-model.md):

```json
{
  "name": "Contract Clause Extractor",
  "description": "Extract key clauses from vendor contracts.",
  "type": "PROTOTYPING", "expected_impact": "TIME_REDUCTION", "priority_level": "MEDIUM",
  "reference": null, "tags": ["legal"], "detail": null,
  "reviewer_id": 2,
  "answers": {
    "CLARITY_MATURITY":  { "score": 2, "rationale": "Scope mostly clear" },
    "SUPPORT_OBJECTIVE": { "score": 2 },
    "COMPLEXITY":        { "score": 2 },
    "DATA_INTEGRATIONS": { "score": 3 },
    "RISK_IMPACT":       { "score": 2 },
    "SUSTAINABILITY":    { "score": 2 }
  },
  "assets": [ { "asset": 8, "type": "USED_BY", "rationale": "Reuses the extraction prompt" } ]
}
```

`201` → the created `Initiative` (`status: "ACTIVATED"`, `score: null`).

A single transaction writes:
- the initiative;
- one `diagnostics` row per answer (`creator_score`, `rationale`);
- the `asset_inits` rows;
- `collaborations` ACTIVATION/HANDLED (proposer) and DIAGNOSIS/PENDING (reviewer);
- `init_permissions` USER/MANAGE for the proposer and the reviewer (one row if they are the same person).

| Status | When |
|---|---|
| 400 | Blank name. Missing or invalid list value. Answers incomplete, unknown or out of scale. Reviewer not found, inactive, ineligible or self (non-admin). No eligible reviewer. Asset missing, inactive or not visible. Invalid relation type. Duplicate `(asset, type)` |
| 403 | Missing `INITS` edit privilege |
| 409 | Integrity conflict (rolled back) |

## 5. POST /api/initiatives/{id}/diagnose

```json
{ "decision": "changes", "feedback": "Clarify the data sources.",
  "answers": { "CLARITY_MATURITY": 2, "SUPPORT_OBJECTIVE": 2, "COMPLEXITY": 3,
               "DATA_INTEGRATIONS": 3, "RISK_IMPACT": 2, "SUSTAINABILITY": 2 } }
```

`200` → `Initiative` with the new `status` and `score` (Σ reviewer scores).

The transaction:
- writes `reviewer_score` per criterion;
- inserts DIAGNOSIS/HANDLED (caller);
- sets the status (ACCEPTED / REJECTED / FEEDBACK);
- inserts ACCEPTANCE / REJECTION / MODIFICATION as PENDING for the proposer, with `content = feedback`.

Errors are evaluated in this order:

| Order | Status | When |
|---|---|---|
| 1 | 400 | Unknown decision |
| 2 | 400 | Initiative missing or inactive |
| 3 | 403 | Caller not an eligible reviewer |
| 4 | 403 | No PENDING DIAGNOSIS held by the caller |
| 5 | 409 | Status ≠ ACTIVATED |
| 6 | 400 | Answers incomplete or out of scale; feedback missing for reject or changes |

## 6. POST /api/initiatives/{id}/resubmit

```json
{ "description": "Now with named data sources.",
  "answers": { "CLARITY_MATURITY": { "score": 3, "rationale": "Sources confirmed" },
               "SUPPORT_OBJECTIVE": { "score": 2 }, "COMPLEXITY": { "score": 2 },
               "DATA_INTEGRATIONS": { "score": 3 }, "RISK_IMPACT": { "score": 2 },
               "SUSTAINABILITY": { "score": 2 } } }
```

`200` → `Initiative` (`status: "ACTIVATED"`).

The transaction:
- applies the sent core fields;
- upserts `creator_score` / `rationale`;
- inserts MODIFICATION/HANDLED (caller);
- sets the status to ACTIVATED;
- inserts DIAGNOSIS/PENDING for the user of the newest DIAGNOSIS row.

| Status | When |
|---|---|
| 400 | Initiative missing. Invalid field or answer values. No reviewer to re-arm |
| 403 | No PENDING MODIFICATION held by the caller, or the caller is not the proposer |
| 409 | Status ≠ FEEDBACK |

## 7–9. Votes

- `GET /api/collaborations/votes/init/{id}` → `InitVoteTally`.
- `PUT /api/collaborations/votes/init/{id}`, body `{ "content": "POSITIVE" | "NEGATIVE" }` → `InitVoteTally`. The same value as the active vote withdraws it; the other value switches it.
- `DELETE /api/collaborations/votes/init/{id}` → `InitVoteTally`, `404` if there is no active vote.
- The voter is always `current.id`; no `user_id` is accepted.

Errors: `400` for an invalid content or an inactive initiative, `403` without VIEW or without the privilege, `409` on an integrity conflict.

## 10. GET /api/collaborations/requests

| Query | Default | Bound |
|---|---|---|
| `state` | `PENDING` | `PENDING` \| `HANDLED` |
| `skip` | 0 | ≥ 0 |
| `limit` | 50 | 1–200 |

`200` → `InitiativeRequest[]`, one row per initiative, newest `last_change_at` first:

```json
[{ "init": 7, "init_name": "Contract Clause Extractor", "init_status": "ACTIVATED",
   "roles": ["PROPOSER"], "state": "PENDING", "awaited_party": "OTHER",
   "pending_collab_id": null, "pending_collab_type": null,
   "last_change_at": "…" }]
```

## 11. GET /api/collaborations/notifications

`?limit=5` (1–50) → `InitNotificationFeed`:

```json
{ "items": [{ "id": 41, "init": 7, "init_name": "Contract Clause Extractor",
              "type": "DIAGNOSIS", "created_at": "…" }],
  "total": 1 }
```

This is always the `awaited_party == "SELF"` subset of #10.

## 12. POST /api/collaborations/notifications/{id}/acknowledge

`200` → the new HANDLED `Collaboration` row. It is idempotent: an already-handled thread returns its current row.

| Status | When |
|---|---|
| 404 | Row missing, not the caller's, or not a notification type |
| 400 | Type not ACCEPTANCE or REJECTION |
| 409 | Integrity conflict |

## 13. GET /api/collaborations/{id}

`200` → `Collaboration` `{id, init, user_id, type, workflow_status, content, reference, parent, detail, is_active, created_at, updated_at}` plus `initiative` (`InitiativeBase` + `id`), `actor_name` and `current_status`.

- `current_status` is the status of the thread's **newest** row. The row itself never changes status (resolving inserts a new row), so the action pages check `current_status` to know whether the request is still open.
- Only **workflow** rows (non-null `workflow_status`) are served. A comment or vote id returns `404`, so an old discussion entry can't become a way to read an initiative after access is revoked. `404` unless the row belongs to the caller or the caller is a superuser. The action pages use it to resolve `?collab=`.

## 14. GET /api/initiatives/diagnosis-form

`?lang=en|es` → the empty questionnaire the Propose, Diagnose and Modify pages render:

```json
{ "items": [ { "criteria": "CLARITY_MATURITY", "name": "Clarity and maturity of the need",
                "description": "…", "list": "CLARITY_MATURITY", "is_active_criteria": true,
                "creator_score": null, "reviewer_score": null, "rationale": null } ],
  "scales": { "CLARITY_MATURITY": [ { "value": 1, "label": "Exploratoria o aún no está bien definida" } ] } }
```

- `items` are the active criteria.
- `scales` maps each list code to its options in `lang`, falling back to English.
- **Why it exists.** `GET /api/criterias/*` requires the `INITS/CRITERIAS` admin privilege, which proposers and reviewers don't hold. This endpoint only needs read access to Explore Initiatives. It was added during implementation.

---

## Reused unchanged

- `PUT` / `DELETE /api/initiatives/{id}/favorite` (Explore star)
- `GET /api/initiatives/{id}/diagnostics` (detail and action pages)
- `GET /api/initiatives/{id}/assets` (detail and diagnose page)
- `GET /api/collaborations/{history,discussion}/init/{id}`
- `POST /api/collaborations/{comments,questions,answers}`
- `DELETE /api/collaborations/{collab_id}`
- `GET /api/criterias/*`
- `GET /api/list_items/list/{code}`

For COLLABORATOR and REVIEWER, the discussion writes start working once the R4 seed change grants `INITS/EXPLORE` with edit.

**Core fields without widening `GET /api/initiatives/{id}`.** That route stays gated on `INITS/INITIATIVES` only (Known blocker P2, left unchanged). The pages get core fields in two ways:

- The Explore detail view uses the `/explore` item already on the page.
- The action pages (diagnose, modify, show-collab) use the `initiative` object embedded in `GET /api/collaborations/{id}` (#13).

That embed is additive to the plain `Collaboration` shape and safe: the caller owns a workflow row on that initiative. Diagnostics and links come from the existing VIEW-gated `/diagnostics` and `/assets` routes. The proposer and the reviewer both hold MANAGE through the propose grants.
