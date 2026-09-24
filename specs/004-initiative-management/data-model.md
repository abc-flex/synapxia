# Data Model: Initiative Management

**Branch**: `004-initiative-management` | **Phase**: 1 | **Date**: 2026-09-23

**No DDL changes.** Every table already exists in `db/sql/51-inits-ddl.sql`. The work is: new
SQLModel mappings for four existing tables, one new model for updates, list-value seed additions,
and a seed realignment. Decisions are referenced as R# from [research.md](research.md).

---

## 1. Entities

### Initiative — `initiatives` (model exists: `inits/internal/models.py`)

| Field | Type | Editable here | Rule |
|-------|------|---------------|------|
| `id` | bigint PK | — | |
| `name` | varchar(100) | ✅ | required, non-blank |
| `description` | varchar(500) | ✅ | optional |
| `type` | varchar(100) | ✅ | optional; must be a `INITIATIVE_TYPE` value |
| `expected_impact` | varchar(100) | ✅ | required; must be an `EXPECTED_IMPACT` value |
| `priority_level` | varchar(100) | ✅ | required; must be a `PRIORITY_LEVEL` value |
| `reference` | text | ✅ | optional |
| `tags` | jsonb | ✅ | optional list of strings |
| `detail` | text | ✅ | optional |
| `status` | varchar(100) | ⚠️ | only via § 2 transitions; must be an `INITIATIVE_STATUS` value |
| `score` | smallint | ❌ | diagnosis result; read-only |
| `is_active` | bool | via DELETE | logical delete |
| `created_at` / `updated_at` | timestamptz | — | `updated_at` stamped on every PUT |

**New** `InitiativeUpdate(SQLModel)` — all fields above marked ✅/⚠️, all `Optional`, applied with
`model_dump(exclude_unset=True)`. List-value validation reads `list_items` (any language row
counts; values are language-independent).

**New response** `InitiativeWithAccess(Initiative)` + `my_access: "MANAGE"|"VIEW"` +
`is_favorite: bool` + `allowed_statuses: list[str]` (the current status plus
`allowed_targets(status)`, so the UI never re-derives the policy).

### Collaboration — `collaborations` (**new model**, `inits/internal/models.py`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | bigint PK identity | |
| `init` | bigint FK → initiatives | |
| `user_id` | bigint FK → users | actor |
| `type` | varchar(100) | `COLLAB_TYPE` value |
| `workflow_status` | varchar(100) \| null | `PENDING` / `HANDLED`; null for VOTE/COMMENT/QUESTION/ANSWER |
| `content` | text \| null | message / discussion text |
| `reference`, `detail` | text \| null | unused here |
| `parent` | bigint FK → collaborations \| null | answer → question |
| `is_active`, `created_at`, `updated_at` | | |

Rows written by this feature: **only** status-change rows — `type ∈ {KICKOFF, DELIVERY,
ARCHIVING}`, `workflow_status = HANDLED`, `user_id = actor`, `content = null` (FR-020, FR-020a).

### InitPermission — `init_permissions` (**new model**)

`id`, `init` (FK), `target_type` (`TARGET_TYPE`: USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC),
`target_code`, `access_level` (`ACCESS_LEVEL`: VIEW/MANAGE), `valid_from` (default now),
`valid_to` (null = open). **No `is_active`** — revoke = `valid_to = now()` (Constitution
per-resource permissions pattern). Plus `InitPermissionCreate` / `InitPermissionUpdate`.

- **Live** (listed, blocks duplicates): `valid_to IS NULL OR valid_to > now` — `valid_from`
  deliberately ignored, so future-dated grants stay visible/manageable.
- **In effect** (grants access): live **and** `valid_from <= now`.
- **Effective level** per (user, init): MANAGE if any in-effect matching grant is MANAGE, else
  VIEW if any, else none. Superuser = MANAGE everywhere.
- **Matching**: `PUBLIC`, or `(target_type, target_code)` ∈ the user's scopes from
  `resolve_user_scopes` (USER id, UNIT, ROLE/TEAM via active assignments, PROJECT via teams).

### Diagnostic — `diagnostics` (**new model**, read-only in this feature)

PK `(init, criteria)`; `creator_score` smallint NOT NULL, `reviewer_score` smallint null,
`rationale` text null, `is_active`, timestamps. Scores are values of the criterion's own list
(`criterias.list` → `list_items.value`, `'1'..'3'` today, stored as smallint).

**Read projection** `DiagnosticRow` (one per criterion, R6):

```text
criteria, name, description, list, is_active_criteria,
creator_score, creator_label, reviewer_score, reviewer_label, rationale
```

Row set = active criteria ∪ criteria with an active diagnostic for this init; ordered by
criterion `created_at`, then `code`. Missing diagnostic → all score/label fields null. Label
resolution: `list_items(list, lang=?, value=str(score))`, falling back to `lang='en'`, then to the
raw value.

### FavoriteInit — `favorite_inits` (**new model**, read-only here)

PK `(user_id, init)`, `is_active`, timestamps. Used only to compute `is_favorite` for the caller.

### AssetInit — `asset_inits` (model exists in `lib/internal/models.py`, reused)

`asset`, `init`, `type` (`RELATION_TYPE`), `rationale`, `is_active`, timestamps. Key
**`(asset, init, type)`**, matching the DDL: the same pair may be linked once per relation type
(R13). POST on an inactive identical link reactivates it with the new rationale; on an active one
→ 409. The same applies to `related_assets` (`AssetRelation`, key `(source, target, type)`) on
the asset side.

**Read projection** `InitiativeAsset`: `asset`, `asset_name`, `category`, `asset_status`,
`type`, `rationale`, `created_at`. An asset the caller cannot see is still listed by name
(spec edge case) — the name is not sensitive, the link would otherwise be invisible.

---

## 2. Initiative status state machine

```text
                         propose / diagnose / modify (other features)
  ACTIVATED ──► FEEDBACK ──► ACTIVATED          ACTIVATED ──► REJECTED
  ACTIVATED ──► ACCEPTED

  ── owner moves (this feature) ──────────────────────────────────────
  ACCEPTED ──KICKOFF──► IN_PROGRESS ──DELIVERY──► DELIVERED ──ARCHIVING──► ARCHIVED
  ACCEPTED ──DELIVERY──────────────────────────► DELIVERED
  ACCEPTED ──ARCHIVING─────────────────────────────────────────────────► ARCHIVED
  IN_PROGRESS ──ARCHIVING──────────────────────────────────────────────► ARCHIVED
```

| From | To | Collaboration written (HANDLED, actor) |
|------|----|----------------------------------------|
| ACCEPTED | IN_PROGRESS | `KICKOFF` |
| ACCEPTED | DELIVERED | `DELIVERY` |
| ACCEPTED | ARCHIVED | `ARCHIVING` |
| IN_PROGRESS | DELIVERED | `DELIVERY` |
| IN_PROGRESS | ARCHIVED | `ARCHIVING` |
| DELIVERED | ARCHIVED | `ARCHIVING` |
| X | X (unchanged / omitted / blank) | none — not a transition |
| anything else | — | **400**, nothing written |

- Comparison uses `normalize()` (strip, upper-case, drop a leading `N-` sort prefix), so
  legacy values compare correctly; an unknown current value has no outgoing moves (locked).
- `allowed_targets(ACCEPTED) = [IN_PROGRESS, DELIVERED, ARCHIVED]`,
  `(IN_PROGRESS) = [DELIVERED, ARCHIVED]`, `(DELIVERED) = [ARCHIVED]`, everything else `[]`.
- Status change and collaboration row commit together or not at all; the row is re-read
  `FOR UPDATE` before validation (R2).
- No pending notices or assignments are created by any of these moves (FR-020a).

---

## 3. List values (seed, `51-inits-ddl.sql`)

| List | Change |
|------|--------|
| `COLLAB_TYPE` | + `('en','KICKOFF','Kickoff',55)`; + `es` rows for all 12 values (`KICKOFF` → "Arranque") |
| `INITIATIVE_STATUS` | + `es` rows (Activada, Retroalimentación, Aceptada, Rechazada, En progreso, Entregada, Archivada) |
| `EXPECTED_IMPACT`, `PRIORITY_LEVEL`, `INITIATIVE_TYPE` | + `es` rows |

Every UI consumer of these lists filters by language with an `en` fallback.

## 4. Seed realignment (`52-inits-insert.sql`)

| Init | Status now | New status | Why |
|------|-----------|-----------|-----|
| 1 | `3-ENGAGING` | `IN_PROGRESS` | exercises IN_PROGRESS → Delivered/Archived |
| 2 | `4-DELIVERED` | `DELIVERED` | exercises Delivered → Archived |
| 3 | `3-ENGAGING` | `ACCEPTED` | exercises all three Accepted moves |
| 4 | `2-ASSESSMENT` | `ACTIVATED` | locked; proposer answers only ("pending diagnosis") |
| 5 | `1-ACTIVATED` | `ACTIVATED` | locked; no answers ("not answered") |

Each initiative also gets a `type`. The seed had no non-superuser ADMINISTRATIVE account, so
`felipe.cardenas` is made `ADMINISTRATIVE` directly in `32-collab-insert.sql` (next to the
REVIEWER promotion of `santiago.marin`). His per-initiative **test grants are not seed data**:
they live in [`test-owner.sql`](test-owner.sql), run by hand when validating (MANAGE on 1 and 3,
VIEW on 2, none on 4–5).

## 5. Validation summary

| Rule | Where | Error |
|------|-------|-------|
| Caller holds `INITS/INITIATIVES` (edit for writes) | route dependency | 403 |
| Initiative exists | route | 404 (400 if inactive on GET/PUT) |
| Caller has init MANAGE for any write | `require_init_manage` | 403 |
| Caller has init VIEW for per-init reads | `require_init_view` | 403 |
| `name` / `expected_impact` / `priority_level` non-blank when present | `InitiativeUpdate` handling | 400 |
| list-backed fields hold a known value | PUT | 400 |
| status move in § 2 | `status_service.validate_transition` | 400 |
| linked asset exists, active, visible to caller | init-assets POST | 400 / 403 |
| link already active | init-assets POST | 409 |
| grant duplicate of a live grant | init-permissions POST | 409 |
| revoke an already-revoked grant | init-permissions DELETE | 400 |
