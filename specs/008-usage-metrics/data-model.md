# Data Model: Usage Metrics (SpecKit 008)

This feature adds no tables. Every figure is derived from existing tables, and the only DDL is two additive indexes.

## Source tables (read-only)

| Table | Columns used | Role |
|-------|--------------|------|
| `executions` (`61-ana-ddl.sql`) | `id`, `dashboard`, `user_id`, `executed_at`, `status`, `duration_ms`, `error_message` | One attempt each. `status` is NULL for Incomplete. `error_message` is read only by the errors endpoint. `payload` is **never** read. |
| `dashboards` | `id`, `name`, `type`, `sources_types`, `status`, `is_active` | Labels the dashboards table. Published + active dashboards in scope feed the "show unused" rows. |
| `dashboard_permissions` | through `permissions_service.accessible_dashboards` | The MANAGE scope for non-Administrator managers (research R4). |
| `users` | `id`, `unit`, `profile`, `is_superuser`, `is_active` | The person behind each run, their current unit, and member counts. |
| `business_units` | `code`, `name`, `parent`, `is_active` | The unit tree (research R7). |
| `assignments` | `user_id`, `team`, `valid_from`, `valid_to`, `is_active` | Team attribution (research R8) and team member counts. |
| `teams` | `code`, `name`, `is_active` | Team labels. |
| `list_items` | `EXECUTION_STATUS`, `DASHBOARD_TYPE`, `SOURCE_TYPE`, `DASHBOARD_STATUS` | Labels in each language. The UI reads them through `lib/listLang.ts`. |

## DDL (additive)

```sql
CREATE INDEX IF NOT EXISTS ix_executions_executed_at
    ON executions (executed_at);
CREATE INDEX IF NOT EXISTS ix_executions_dashboard_executed_at
    ON executions (dashboard, executed_at);
```

- Add to `db/sql/61-ana-ddl.sql` for fresh volumes.
- Provisioned DBs (local and Neon) run `specs/008-usage-metrics/provisioned-db.sql` once.
- Rollback: `DROP INDEX IF EXISTS ix_executions_executed_at, ix_executions_dashboard_executed_at;`

## Derived concepts

### Outcome class (research R5)

| `status` | `outcome` key | class |
|----------|---------------|-------|
| `SUCCESS` | `SUCCESS` | run |
| `FAILED` | `FAILED` | run |
| `TIMEOUT` | `TIMEOUT` | run |
| `NULL` | `INCOMPLETE` | run |
| `CANCELLED` | `CANCELLED` | attempt |
| `UNAUTHORIZED` | `UNAUTHORIZED` | attempt |
| any other value | the raw value | run (reported under its own key) |

- **runs** = count of run-class records.
- **attempts** = count of attempt-class records.
- **success_rate** = `SUCCESS / (SUCCESS + FAILED + TIMEOUT)`, or `null` when the denominator is 0.
- **median_ms / avg_ms** = over `SUCCESS` records with `duration_ms IS NOT NULL`, or `null` when there are none.
- **users** = distinct `user_id` over runs. **dashboards** = distinct `dashboard` over runs.

### Period

- **Input.** `date_from` and `date_to` are local dates in `APP_TIMEZONE` and inclusive. They must satisfy `date_from ≤ date_to`, `date_to − date_from ≤ 731 days` (24 months), and `date_to ≤ today + 1`.
- **Window.** `[date_from 00:00 local, date_to + 1 day 00:00 local)`, converted to UTC for the query.
- **Previous period.** The same length immediately before: `[date_from − N, date_from)`.
- **Bucket.** `day` if N ≤ 31, `week` (ISO, Monday start) if N ≤ 183, otherwise `month`. Bucket keys are local dates (the first day of the bucket). Every bucket in the window is emitted, including empty ones.

### Scope

`scope = None` means unrestricted: the caller is a superuser or has `profile == 'ADMINISTRATOR'`. Otherwise `scope = {dashboard_id where effective level == MANAGE}`. The scope filters executions, dashboards rows, unused rows and the errors endpoint. Member counts are not scoped.

### Group filter (FR-005)

There is at most one of:
- `unit=<code>`: runs by users whose current unit is `code` or one of its descendants;
- `team=<code>`, or `team=__none__` for "No team": runs attributed to that team (research R8).

The filter narrows the headline, the timeline and the dashboards table. The adoption section is **not** narrowed by its own filter; the response marks the selected node, and the UI highlights it.

### Unit node (research R7)

```
UnitNode {
  code, name,
  members:          int    # active users in the subtree
  direct_members:   int    # active users whose unit == code
  runs, users, success_rate,
  adoption_rate:    float | null   # users / members (null if members == 0)
  children:         UnitNode[]     # a node is omitted only when its whole subtree has
                                   # members == 0 AND no runs (history is never hidden)
}
```

### Project row (follow-up, FR-014b)

```
ProjectRow {
  code | "__none__", name, team, team_name,
  members:       int | null    # the owning team's members; null for "No project"
  runs, users, success_rate,
  adoption_rate: float | null  # null for "No project"
}
```

A run counts in each **active** project owned by a team it counts in (Team row rule below), when the run's local date is within `start_date`/`end_date` (open ends allowed); otherwise in `__none__`.

### Team row (research R8)

```
TeamRow {
  code | "__none__", name,
  members:       int | null    # null for "No team"
  runs, users, success_rate,
  adoption_rate: float | null  # null for "No team"
}
```

### Dashboard row

```
DashboardRow {
  id, name, type, source, status,         # current status (may be ARCHIVED/RETIRED)
  runs, attempts, users, success_rate,
  median_ms, last_run_at,                 # last_run_at: newest run-class record in the period, or null
  unused: bool                            # true = Published + active, in scope, 0 runs in the period
}
```

A dashboard with only attempts in the period (no runs) is listed with `runs = 0`, `unused = false`.

## Validation rules (→ 400)

- `date_from` / `date_to` missing, malformed, inverted, more than 24 months apart, or in the future beyond tomorrow.
- `unit` and `team` given together. An unknown `unit` or `team` code.
- `limit` on the errors endpoint outside 1–50.

## State transitions

None. The feature is read-only (FR-003).
