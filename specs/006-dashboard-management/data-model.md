# Data Model — Dashboard Management (006)

All three tables already exist in `db/sql/61-ana-ddl.sql`. This feature adds **no DDL**. It
adds SQLModel mappings in `api/app/insights/internal/models.py`, request/read projections, and
Spanish rows for the analytics lists.

## Entities

### Dashboard — `dashboards`

| Field | Type | Rules |
|-------|------|-------|
| `id` | bigint identity | PK |
| `name` | varchar(100) | required, non-blank |
| `description` | varchar(500) | optional |
| `type` | varchar(100) | required, a `DASHBOARD_TYPE` value |
| `sources_types` | varchar(100) | required, a `SOURCE_TYPE` value (column name kept as in DDL) |
| `source_url` | text | required. INTERNAL_PAGE → platform path (`/…`, not `//`, no scheme). Every other source → absolute `https://` URL. At most 2048 characters |
| `status` | varchar(100) | a `DASHBOARD_STATUS` value. Always `DRAFT` on create. Changes follow the state machine below |
| `tags` | JSONB | optional list of strings |
| `detail` | text | optional long text |
| `is_active` | bool | logical delete |
| `created_at` / `updated_at` | timestamptz | `updated_at` set on every PUT |

SQLModel classes: `DashboardBase`, `Dashboard(table)`, `DashboardCreate` (no `status`, no `id`),
`DashboardUpdate` (all optional, includes `status`), `DashboardWithAccess` (adds `id`, `my_access`,
`allowed_statuses: List[str]`, `permission_scopes: List[str]`).

### Parameter — `parameters`

| Field | Type | Rules |
|-------|------|-------|
| `dashboard` | bigint | PK part, FK → `dashboards.id` |
| `name` | varchar(100) | PK part. `^[a-z][a-z0-9_]*$`. Immutable |
| `label` | varchar(100) | required, non-blank |
| `data_type` | varchar(100) | required, a `PARAM_TYPE` value: STRING / NUMBER / BOOLEAN / DATE |
| `default_value` | text | optional. Must parse for `data_type` (NUMBER decimal, BOOLEAN `true`/`false`, DATE `YYYY-MM-DD`). If `list` is set, it must be one of the list's values |
| `is_required` | bool | default false |
| `list` | varchar(50) | optional. FK → `lists.code`, an active list of type `LIST_OF_VALUES` |
| `context_binding` | bigint | optional. FK → `dashboard_permissions.id`. Must be a live grant of the **same** dashboard with `target_type ≠ PUBLIC` when set |
| `is_active` | bool | logical delete. Re-adding the same name reactivates the row |
| `created_at` / `updated_at` | timestamptz | |

SQLModel classes: `Parameter(table)` (composite PK), `ParameterCreate` (all fields except
`dashboard`, which comes from the path), `ParameterUpdate` (everything optional except `name`),
`ParameterRead` (row + derived `value_source` + `binding_label`).

**Derived `value_source`** (never stored):

```text
context_binding IS NOT NULL → GRANT   (value = the bound grant's target_code)
else list IS NOT NULL       → LIST    (viewer picks from the list)
else                        → INPUT   (viewer types a value valid for data_type)
```

`binding_label` is a short description of the bound grant, e.g. `"TEAM ANALYTICS"`. It is
resolved in one batched query per listing.

### Dashboard Permission — `dashboard_permissions`

| Field | Type | Rules |
|-------|------|-------|
| `id` | bigint identity | PK |
| `dashboard` | bigint | FK → `dashboards.id` |
| `target_type` | varchar(100) | a `TARGET_TYPE` value: USER/ROLE/PROJECT/TEAM/UNIT/PUBLIC |
| `target_code` | varchar(50) | recipient id/code. `"ALL"` for PUBLIC |
| `access_level` | varchar(100) | a `ACCESS_LEVEL` value: VIEW / MANAGE |
| `valid_from` | timestamptz | default now. Managed internally: the Permissions tab never shows or sends it |
| `valid_to` | timestamptz | optional. Revoke sets it to now. It must be later than `valid_from`. Managed internally, as above |

There is no `is_active`, by design (revoke-not-delete, as for `asset_permissions` /
`init_permissions`). SQLModel classes: `DashboardPermission(table)`,
`DashboardPermissionCreate`, `DashboardPermissionUpdate` (`access_level`, `valid_from`,
`valid_to`), `RevokedDashboardPermission` (row + `bound_parameters: List[str]`).

### Favorite dashboard — `favorite_dashboards` (amendment R14)

| Field | Type | Rules |
|-------|------|-------|
| `user_id` | bigint | PK part, FK → `users.id`. Always the caller (from the session) |
| `dashboard` | bigint | PK part, FK → `dashboards.id`. The caller needs VIEW on it |
| `is_active` | bool | logical removal; marking again reactivates the row |
| `created_at` / `updated_at` | timestamptz | |

SQLModel classes: `FavoriteDashboard(table)` and `DashboardFavoriteState(dashboard, is_favorite)`.
`DashboardWithAccess` gains `is_favorite`.

## Relationships

```text
dashboards 1 ── * parameters               (parameters.dashboard)
dashboards 1 ── * dashboard_permissions    (dashboard_permissions.dashboard)
dashboard_permissions 1 ── * parameters    (parameters.context_binding, same dashboard only)
lists 1 ── * parameters                    (parameters.list)
dashboards 1 ── * favorite_dashboards      (favorite_dashboards.dashboard, one per user)
```

## State machine — `dashboards.status`

```text
          create
            │
            ▼
         DRAFT ──────► PUBLISHED ◄──────┐
                        │      │        │
                        ▼      ▼        │
                    RETIRED  ARCHIVED ──┘
                        ▲      │
                        └──────┘
```

| From → To | Result |
|-----------|--------|
| DRAFT → PUBLISHED | ✅ |
| PUBLISHED → ARCHIVED, RETIRED | ✅ |
| ARCHIVED → PUBLISHED, RETIRED | ✅ |
| unchanged / blank | no-op |
| anything else (incl. any move from RETIRED, any move back to DRAFT) | 400, nothing changed |
| unknown current value (legacy) | control locked, every change → 400 |

`allowed_statuses` = `[current, *targets]`. A single entry means the control is locked.

## Access resolution

`app/internal/resource_permissions` bound to `DashboardPermission` / `"dashboard"`. The scopes are
USER (id), UNIT (`users.unit`), ROLE/TEAM (active assignments) and PROJECT (projects of those
teams), plus PUBLIC. A grant counts only inside its validity window. MANAGE beats VIEW.
Superusers get MANAGE everywhere.

| Operation | Module RBAC | Per-dashboard |
|-----------|-------------|---------------|
| list `/with-access`, parameter-lists | `ANA/DASHBOARDS` read | list filtered to granted |
| read one dashboard / its parameters / its grants | `ANA/DASHBOARDS` read | VIEW |
| mark / clear own favorite | `ANA/DASHBOARDS` read | VIEW |
| create dashboard | `ANA/DASHBOARDS` edit | — (creator auto-granted MANAGE) |
| update / remove dashboard, any parameter or grant write | `ANA/DASHBOARDS` edit | MANAGE |

## Seed changes (no DDL)

- `db/sql/61-ana-ddl.sql`: add `es` `list_items` for `DASHBOARD_TYPE` (Tablero, Informe, Cuadro de
  mando, Vista de KPI, Vista analítica), `SOURCE_TYPE` (Página interna, Power BI, Looker Studio,
  Tableau, Qlik Sense, Metabase, Superset, Iframe personalizado), `DASHBOARD_STATUS` (Borrador,
  Publicado, Archivado, Retirado), `PARAM_TYPE` (Texto, Número, Booleano, Fecha) and
  `EXECUTION_STATUS` (Exitosa, Fallida, Cancelada, Tiempo agotado, No autorizada).
- `db/sql/62-ana-insert.sql`: unchanged. Seeded parameters stay `INPUT` (no list, no binding).
- `specs/006-dashboard-management/provisioned-db.sql`: the same `es` INSERTs for existing DBs.
- `specs/006-dashboard-management/test-owner.sql`: grants for a non-superuser analyst
  (`felipe.cardenas`, ADMINISTRATIVE): MANAGE on dashboard 1, VIEW on dashboard 2, none on 3.
  This is test data, not seed data.
