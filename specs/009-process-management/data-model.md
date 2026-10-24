# Data Model: Process Management

**Feature**: `009-process-management` · **Date**: 2026-10-23 · Decisions referenced as R# are in [research.md](research.md).

All tables already exist in `db/sql/71-proc-ddl.sql` except where marked **CHANGED** or **NEW**. Per R2, those changes are made in place in the existing SQL files, with no migration.

---

## Process (`processes`), unchanged

| Field | Type | Rules |
|-------|------|-------|
| `code` | VARCHAR(50), PK | Required. Trimmed and uppercased; must match `^[A-Z0-9][A-Z0-9_-]{0,49}$`; unique, including logically removed rows (→ 409); **immutable** after creation (R12). |
| `name` | VARCHAR(100) | Required, non-blank, at most 100 characters (→ 400). |
| `description` | VARCHAR(500) | Optional, at most 500 characters. |
| `type` | VARCHAR(100) | Required; a `PROCESS_TYPE` value: `PRIMARY` or `SUPPORT`. A change is refused if it breaks active SUPPORTS/PRECEDES links (R6). |
| `parent` | VARCHAR(50), FK → `processes.code` | Optional; must be an active process; not itself and not a descendant (R7). |
| `unit` | VARCHAR(50), FK → `business_units.code` | Optional; must be an active unit. |
| `owner` | BIGINT, FK → `users.id` | Required; must be an active user. Defaults to the caller when omitted on create. |
| `reference` | TEXT | Optional. |
| `status` | VARCHAR(100) | A `PROCESS_STATUS` value. Always `DRAFT` on create; changes follow the lifecycle below. |
| `tags` | JSONB | Optional list of non-blank strings. |
| `detail` | TEXT | Optional. |
| `is_active` | BOOLEAN | Logical removal. A process with active children cannot be removed (→ 409). |
| `created_at` / `updated_at` | TIMESTAMPTZ | `updated_at` is set on every update. |

### Status lifecycle (R5)

```text
          ┌──────── back ────────┐
          ▼                      │
 (create) DRAFT ──► REVIEW ──► PUBLISHED ──► DEPRECATED (final)
```

| From | Allowed to |
|------|-----------|
| DRAFT | REVIEW |
| REVIEW | PUBLISHED, DRAFT |
| PUBLISHED | DEPRECATED |
| DEPRECATED | none |

Keeping the current status is always valid and is not a transition. Any other change returns 400. `allowed_statuses` lists the current status first, then the allowed moves.

## Process relation (`related_processes`), type list CHANGED

| Field | Type | Rules |
|-------|------|-------|
| `source` | VARCHAR(50), PK, FK → processes | The process being edited. |
| `target` | VARCHAR(50), PK, FK → processes | Active process; ≠ `source`. |
| `type` | VARCHAR(100), PK | A **`PROCESS_RELATION_TYPE`** value (no longer `RELATION_TYPE`). |
| `rationale` | TEXT | Optional. |
| `is_active` | BOOLEAN | Logical removal; an identical row is reactivated, never duplicated. |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Rules (R6):

- **Uniqueness**: unique per `(source, target, type)` among active rows. For `INTERACTS_WITH` the pair is **unordered**: an active `(B, A, INTERACTS_WITH)` blocks `(A, B, INTERACTS_WITH)`.
- **Compatibility**: `SUPPORTS` is accepted only when the source is `SUPPORT` and the target is `PRIMARY`. `PRECEDES` is accepted only when source and target have the same type. Every other type accepts any combination.
- **Visibility**: process X's Related processes tab shows its active outgoing rows plus active `INTERACTS_WITH` rows where X is the **target**. Each such row carries `direction: "incoming"`, so it can be removed from either side.

## Process–asset link (`process_assets`), CHANGED

| Field | Type | Rules |
|-------|------|-------|
| `process` | VARCHAR(50), PK, FK → processes | |
| `asset` | BIGINT, PK, FK → assets.id | Active asset. |
| **`type`** | VARCHAR(100), **PK, NEW** | A `RELATION_TYPE` value (the shared list). |
| `rationale` | TEXT | Optional. |
| `is_active` / timestamps | | As above. |

The primary key changes from `(process, asset)` to **`(process, asset, type)`**.

## Process–initiative link (`process_inits`), CHANGED

The same shape as `process_assets`, with `init` (BIGINT, FK → initiatives.id; must be an active initiative) instead of `asset`. The primary key changes from `(process, init)` to **`(process, init, type)`**.

## Process relation type list (`lists` / `list_items`), NEW

The list `PROCESS_RELATION_TYPE` (module `PROC`, type `LIST_OF_VALUES`):

| value | en | es | sort | BPMN counterpart |
|-------|----|----|------|------------------|
| PRECEDES | Precedes | Precede a | 10 | Sequence flow |
| TRIGGERS | Triggers | Dispara | 20 | Event start |
| CALLS | Calls | Invoca a | 30 | Call activity |
| FEEDS_INTO | Feeds Into | Alimenta a | 40 | Data association |
| INTERACTS_WITH | Interacts With | Interactúa con | 50 | Message flow (undirected) |
| SUPPORTS | Supports | Apoya a | 60 | Association |
| GOVERNS | Governs | Regula a | 70 | Association (annotation) |

The BPMN counterpart is documentation for HU-PR05 and HU-PR06; it is not stored.

## Referenced (read-only)

`business_units` (code, name, is_active) · `users` (id, names, is_active) · `assets` (id, name, category, is_active) · `initiatives` (id, name, is_active) · lists `PROCESS_TYPE`, `PROCESS_STATUS`, `RELATION_TYPE`.

## Seed changes (R13) in `72-proc-insert.sql`

| Before | After |
|--------|-------|
| `OPER DEPENDS_ON INBL`, `OUTL DEPENDS_ON OPER`, `MKTS DEPENDS_ON OUTL`, `SERV DEPENDS_ON MKTS` | `INBL PRECEDES OPER`, `OPER PRECEDES OUTL`, `OUTL PRECEDES MKTS`, `MKTS PRECEDES SERV` |
| `TECH/PROC/HRMG/INFR USED_BY …` | Same pairs as `SUPPORTS` |
| `process_assets` rows (no type) | + `type = 'RELATED_TO'` |
| `process_inits` rows (no type) | + `type = 'RELATED_TO'` |

## Access matrix (R9)

| Profile | List / read / form-options | Create / update / remove / save links |
|---------|----------------------------|----------------------------------------|
| Superuser | ✓ | ✓ |
| ADMINISTRATOR | ✓ | ✓ |
| ADMINISTRATIVE | ✓ | ✓ |
| COLLABORATOR, REVIEWER | 403 | 403 |
| Unauthenticated | 401 | 401 |
