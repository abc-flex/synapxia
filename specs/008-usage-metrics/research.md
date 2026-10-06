# Research: Usage Metrics (SpecKit 008)

Phase 0 decisions. The spec has no open `[NEEDS CLARIFICATION]` markers; these entries settle the technical unknowns that the Technical Context raised.

## R1 — Where the aggregation runs: one bounded query, aggregated in Python

**Decision.** The service loads the executions of the requested window (current period plus the preceding period of equal length) with a projected query: `id, dashboard, user_id, executed_at, status, duration_ms`, no payload and no error message. It filters on `executed_at` and on the caller's dashboard scope in SQL, and streams the result (`yield_per`). One Python pass then builds every figure: headline, buckets, per-dashboard rows, unit tree and teams.

**Rationale.**
- Several figures are not portable SQL:
  - medians (`percentile_cont` does not exist in SQLite);
  - local-day buckets (`date_trunc` + `AT TIME ZONE` are Postgres-only);
  - the hybrid team attribution, which is a per-run lookup against validity windows.
- The test suite runs on SQLite (`api/tests/conftest.py`), and Constitution III asks for automated tests of new contracts. Python aggregation keeps all of it testable.
- Volume: 100 000 rows of six scalar columns is about 10 MB of tuples, which psycopg2 fetches in roughly 0.3–0.6 s. One pass with dictionaries is of the same order. The SC-003 budget (3 s for up to 100 000 records) has headroom.
- Error messages for one dashboard are only needed when a row is expanded. They come from a separate endpoint (R6) with a SQL `GROUP BY error_message`, which is portable.

**Alternatives considered.**
- *SQL `GROUP BY` per section* (5–6 queries). Faster at very high volume, but it needs Postgres-only functions, which would mean Postgres-only tests or a dialect switch.
- *A materialized daily summary table.* New DDL plus a refresh mechanism, and the serverless API has no background jobs. Out of proportion for the expected volume.

**Guard.** The custom range is capped at 24 months (FR-004). If the 100 000-record benchmark (quickstart §4) shows the budget at risk, the documented fallback is to move only the per-day counts into SQL behind a dialect check. That would be a plan amendment, not a silent change.

## R2 — Indexes on `executions`

**Decision.** Add `ix_executions_executed_at (executed_at)` and `ix_executions_dashboard_executed_at (dashboard, executed_at)`. Both go in `db/sql/61-ana-ddl.sql` (fresh volumes) and in `specs/008-usage-metrics/provisioned-db.sql` as `CREATE INDEX IF NOT EXISTS`, to run once on provisioned DBs (local and Neon).

**Rationale.** SpecKit 007 deferred the indexes to this feature ("HU-AN07 will add the indexes its aggregates need"). Every usage query is a range on `executed_at`, and scoped users add `dashboard IN (…)`. The change is additive and the rollback is `DROP INDEX`.

**Alternatives.** No index, which means a sequential scan that grows with history. A partial index on non-NULL status is rejected, because Incomplete rows must be counted.

## R3 — Organization time zone

**Decision.** Add a setting `APP_TIMEZONE` (default `America/Bogota`) in `api/app/core/config.py`. Period dates are interpreted in that zone: `from` is 00:00 local and `to` runs up to the end of that day. Buckets are local days, ISO weeks starting Monday, or calendar months. Conversion uses `zoneinfo` (verified working in the API container).

**Rationale.** Colombia has no DST, but naming the zone, rather than hard-coding −05:00, keeps the rule correct if the setting changes. Without it a run at 20:00 local would land on the next UTC day.

**Alternatives.** Use the browser's zone. Rejected: two managers in different zones would see different figures for the same period.

## R4 — Access scope (FR-002)

**Decision.** There are two gates.
- **Outer gate.** The route is gated on `require_privilege("ANA", "USAGE")` (read).
- **Inner scope.** It is resolved once per request in `usage_service.scope_for(session, user)`:
  - superuser, or `user.profile == "ADMINISTRATOR"`: unrestricted (`None`);
  - anyone else: the set of dashboard ids where `permissions_service.accessible_dashboards(session, user)` gives `MANAGE`. That is the shared engine, so it covers every scope type plus validity, and stays revoke-aware. An empty set returns empty figures, not an error.

The scope filters executions in SQL (`dashboard IN scope`), and it also filters the "unused" list and the dashboards table. Adoption denominators (members) stay organization-wide: they count people, not dashboards.

**Rationale.** This is the user's choice (clarification Q1 = C), and it reuses the existing per-resource engine (Constitution I and its established pattern). The Administrator is identified by profile code through a dedicated constant `ORG_WIDE_PROFILES = ("ADMINISTRATOR",)` in `usage_service`. `app/internal/reviewers.ADMIN_PROFILES` is deliberately **not** reused, because it also includes ADMINISTRATIVE, which this feature must scope.

**Alternatives.** A new privilege option such as `ANA/USAGE_ALL`. Rejected, because it would be seed and privilege churn for a rule that is fixed per profile.

## R5 — Run vs attempt, rates and durations (FR-006, FR-007a, FR-008)

**Decision.** A single classification table drives everything:

| Status | Class | Runs | Success-rate denominator | Duration |
|--------|-------|------|--------------------------|----------|
| `SUCCESS` | run | ✔ | ✔ (numerator too) | ✔ when present |
| `FAILED` | run | ✔ | ✔ | ✘ |
| `TIMEOUT` | run | ✔ | ✔ | ✘ |
| `NULL` | run (Incomplete) | ✔ | ✘ | ✘ |
| `CANCELLED` | attempt (abandoned) | ✘ | ✘ | ✘ |
| `UNAUTHORIZED` | attempt (refused) | ✘ | ✘ | ✘ |

- Success rate is `null` (shown as "n/a") when the denominator is 0.
- The median is computed with `statistics.median` over the Success durations. The average is rounded to whole milliseconds.
- Distinct users, distinct dashboards, dashboard ranking, adoption and the unit and team run counts all use **runs** only.
- The chart stacks every class.
- A status value outside the list, such as legacy data, is classed as a run and reported under its raw code in the breakdown, so it never disappears silently.

## R6 — API shape: one metrics document plus one lazy errors endpoint

**Decision.** There are two endpoints, both under `insights/routes/usage.py`:
1. `GET /api/usage/metrics?date_from&date_to[&unit|&team]` returns one document: period info, headline (current and previous period), timeline buckets, dashboards table (used plus unused rows), unit tree and team rows.
2. `GET /api/usage/dashboards/{id}/errors?date_from&date_to[&unit|&team]&limit=10` returns the most frequent error messages for that dashboard in the period, inside the caller's scope (404 if the dashboard is outside it).

**Rationale.**
- One pass over the rows feeds every section, so splitting `metrics` would re-read the same rows several times.
- The page always needs all sections together.
- Errors are optional per row and are the only part that touches `error_message` text.

**Pagination (Constitution II).** The `metrics` document is not a list endpoint: its row counts are bounded by entities (dashboards, units, teams), not by executions. The errors endpoint takes a bounded `limit` (1–50, default 10). No individual execution is ever returned (FR-015).

**Alternatives.** Five section endpoints: more round-trips and repeated scans. A generic "query builder" endpoint: over-engineered for one page.

## R7 — Unit hierarchy (clarification: tree with roll-up)

**Decision.**
- Load all active `business_units` (fewer than 100) and build `parent → children`.
- Each run is counted once in the user's own unit, then added to every ancestor. Distinct-user sets are rolled up the same way, as set unions.
- Members per unit are active users whose unit is in the subtree.
- Units whose whole subtree has zero members are omitted. Direct members of a parent unit appear in its "(direct)" figures, so a parent's totals reconcile with its children.
- The response is a nested tree. The UI expands top-level units one level by default.
- A cycle in `parent` (bad data) is broken by a visited-set guard and logged.

## R8 — Team attribution, hybrid (clarification Q2 = C)

**Decision.**
- Load the active assignments (`is_active`, team not null) of the users who have runs in the window, plus every active assignment for the member counts. That is one query.
- For a run at `t`, the teams are those with `valid_from ≤ t < coalesce(valid_to, ∞)`.
- If there are none, the user's current teams are used: assignments valid now.
- If there are still none, the run goes to "No team".
- Team members are active users with an active assignment to the team that is valid at any time in `[from, to]` or now.
- A run may count in several teams, and the UI states that team totals can exceed the overall total.

The `team=` filter uses the same attribution, so a run belongs to team X under the filter exactly when it would count in X's row.

## R9 — Period comparison (FR-007)

**Decision.** The previous period is `[from − N days, from)`, where N is the inclusive length of the selected range in days. The change is reported as `(current − previous) / previous`, as a ratio with the UI formatting it. It is `null` when previous is 0 or the figure is undefined, and the UI then shows a neutral mark. Durations and success rate compare as plain differences: points for the rate, milliseconds for durations.

## R10 — Chart rendering

**Decision.** Use a hand-built SVG stacked-bar chart inside the Svelte island (`UsageTimeline.svelte`). There is no new dependency.
- Colors are CSS variables with light and dark values.
- There is a legend with text labels (FR-018: never color alone).
- Each bucket gets a tooltip with the per-outcome counts.
- On narrow screens the bar width shrinks, and above about 60 buckets the x-labels thin out. The bucket rule (R3) keeps the count at 53 or fewer for 12 months.
- Load the `dataviz` skill before writing the chart.

**Alternatives.** ECharts via CDN, as in `TreeChart.astro`. Rejected, because it adds a 1 MB global script for one stacked bar chart, makes dark mode harder, and does not fit the Svelte `mount()` convention.

## R11 — Exports (clarification Q3 = B)

**Decision.** Exports are client-side, from the data already loaded:
- **CSV**: UTF-8 with BOM, so Excel opens accents correctly, comma separated, RFC 4180 quoting. It reuses the escaping approach of `components/table/advancedTable.ts` `toCSV`, extracted to a small shared helper in `lib/` rather than copied.
- **Excel**: a real `.xlsx` built by a small in-repo writer, `ui/src/lib/xlsx.ts`. It produces one sheet with inline strings and numeric cells, zipped with STORE (no compression) and CRC-32. That is about 120 lines and no dependency.

The file name carries the table, the period and the filter, for example `usage-dashboards_2026-09-06_2026-10-05_unit-ENG.xlsx`. The first row is a header and the rows match the visible table, after search and the "show unused" toggle. Unit rows are flattened with their full path (`Corporate › Engineering › Backend`).

**Alternatives.**
- SheetJS: about 400 KB and its licensing changed.
- An HTML or SpreadsheetML file renamed `.xls`: Excel warns about a format mismatch.
- Server-side `openpyxl`: a new API dependency and a second contract per table.

## R12 — UI structure

**Decision.**
- `ui/src/pages/ana/usage.astro` is a thin SSR shell, with `BaseLayout`, a breadcrumb, the option name and icon via `getOption("ANA", "USAGE")`, and a mount point.
- `ui/src/components/svelte/UsageMetrics.svelte` is mounted manually with `mount()`, per the Svelte 5 convention. It owns the period selector, the filter chip, the headline tiles, the timeline, the dashboards table and the adoption tabs.
- Data is fetched client-side from `lib/usageMetrics.ts`, because the period changes interactively and an SSR snapshot would immediately go stale.
- Labels for statuses, types and sources come from `list_items` through `lib/listLang.ts` (`toListOptions` / `listLabel` under `langTick`), following the language switcher (FR-016).
- Everything is responsive: tiles wrap, and tables scroll inside their own container (FR-017).

## R13 — Synthetic data (FR-019)

**Decision.** `synthetic-usage.sql` writes **only** to `executions` (user follow-up, 2026-10-06; an earlier version also created people, dashboards, grants and assignments, and was withdrawn).
- Runs are spread over the existing active Published dashboards and the existing active users. Each row carries `"synthetic": true` in its payload, and `synthetic-usage-remove.sql` deletes exactly those rows.
- It is deterministic, and removal restores the exact prior counts.
- Seeded team assignments start on the provisioning day, so the team figures exercise R8's fallback to current teams.
- felipe.cardenas holds MANAGE on seeded dashboards 1 and 4 (4 is inactive), which exercises R4's narrowed scope.
- No seeded dashboard is an Internal Page, so the data contains no Timeout; the unit tree is narrow because nearly every seeded user is in Engineering.
- For the SC-003 benchmark, `-v scale=21` multiplies the daily counts (about 100 000 rows). The plain script cannot be stacked, because every load first removes the previous one.

## R14 — Tests

pytest, on SQLite like the existing suites:
- **Access.** No `ANA/USAGE` gets 403. COLLABORATOR gets 403. ADMINISTRATOR and superuser see everything. ADMINISTRATIVE sees only MANAGE dashboards; a revoked grant drops out; VIEW-only is not enough.
- **Classification and rates.** Each status is checked against the R5 table. A zero denominator gives null. The median is correct.
- **Buckets.** Day, week and month thresholds; local-time boundaries (a 20:00 local run on the 31st stays in its own month); empty buckets come back as zeros.
- **Unit tree.** Roll-up across three levels, direct members, empty subtrees omitted, adoption rate.
- **Teams.** Historical assignment, fallback to current, "No team", multi-team double count, the `team` filter matches row attribution.
- **Comparison.** The previous-period window and `null` changes.
- **Errors endpoint.** Top-N ordering, scope 404, `limit` bounds.
- **Validation.** Bad or inverted dates and ranges over 24 months give 400. `unit` and `team` together give 400.
- **No leak.** No response contains `payload` or `user_id` keys (FR-015, SC-005).
