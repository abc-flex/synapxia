# Tasks: Usage Metrics

**Input**: Design documents from `/specs/008-usage-metrics/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/usage-api.md](contracts/usage-api.md),
[quickstart.md](quickstart.md)

**Tests**: REQUIRED. Constitution Principle III makes automated tests mandatory for new contracts and permission rules, and research R14 lists what to cover. Each story writes its backend tests first and confirms they fail before implementing. The UI is verified manually through the quickstart.

**Organization**: tasks are grouped by the spec's user stories:

- US1: see overall usage for a period (P1)
- US2: see usage over time (P1)
- US3: see which dashboards are used and how well they work (P2)
- US4: see adoption by unit and team (P2)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4. Setup, Foundational and Polish tasks carry no story label.
- Paths are repository-relative: `api/`, `ui/`, `db/`, `specs/`.

## Conventions every task follows

- **Backend**: copy the style of `api/app/insights/routes/catalog.py` and `internal/catalog_service.py`.
  - Module RBAC is `Depends(require_privilege("ANA", "USAGE", can_edit=False))`.
  - Business logic lives in `api/app/insights/internal/usage_service.py`, never in routes.
  - `ValueError` maps to 400.
  - Every request logs one structured line: period, scope size, rows read, elapsed ms.
  - **Never** return `user_id`, `payload` or an execution row (FR-015).
  - Run classification, rate and duration rules come from **one** table in `usage_service` (research R5); never re-derive them per section.
- **Tests**: run on SQLite via `api/tests/conftest.py`.
  - Reuse `api/tests/ana_helpers.py` (`seed_privileges`, `mk_dashboard`, `mk_grant`, `seed_ana_lists`) and `api/tests/catalog_helpers.py` (`mk_execution`).
  - Add builders in `api/tests/usage_helpers.py`.
  - Run with `docker compose exec -T api uv run pytest -q <path>`.
- **UI**:
  - Svelte 5 islands are mounted with `mount()` from a bundled `<script>` importing through `@/`. Template comments are `<!-- -->`.
  - Seed `$state` from props via `untrack`.
  - List values go through `ui/src/lib/listLang.ts`: keep raw items and read `toListOptions` / `listLabel` under `langTick`. Never write `textContent` into Svelte-owned DOM.
  - Every string goes in both `ui/src/i18n/en.json` and `es.json` under `usage_metrics.*`.
  - Colors are tokens with light and dark values. Layout works at 390 px with no page-level horizontal scroll; wide tables scroll inside their own container.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: DB indexes, the time-zone setting and development data.

- [X] T001 Add the two indexes `ix_executions_executed_at (executed_at)` and `ix_executions_dashboard_executed_at (dashboard, executed_at)` at the end of the executions section in `db/sql/61-ana-ddl.sql` (same statements as `specs/008-usage-metrics/provisioned-db.sql`), then apply `specs/008-usage-metrics/provisioned-db.sql` to the local DB and confirm with `\di ix_executions*`
- [X] T002 [P] Add the `APP_TIMEZONE: str = "America/Bogota"` setting (env-overridable) to `api/app/core/config.py` and document it in `.env.template` next to the other API settings
- [X] T003 [P] Add an optional `scale` psql variable to `specs/008-usage-metrics/synthetic-usage.sql`: `\if :{?scale} \else \set scale 1 \endif`, multiply the daily count `n` by `:scale`, and update the header comment with `-v scale=21` for the SC-003 benchmark. Re-run the script with and without `-v scale=2` and confirm the counts scale and the remove script still restores the baseline

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared contract, scope, period math, run classification, page shell and test builders every story builds on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Tests (write first, confirm they fail)

- [X] T004 Create test builders in `api/tests/usage_helpers.py`:
  - `mk_unit(session, code, parent=None)`;
  - `mk_user(session, id, unit, profile="COLLABORATOR", active=True, superuser=False)`;
  - `mk_team(session, code)`;
  - `mk_assignment(session, user_id, team, valid_from, valid_to=None, active=True)` (role defaults to an existing seeded-style code it also creates);
  - `run(session, dashboard, user_id, status, at_local, duration_ms=None, error=None)`, a wrapper over `catalog_helpers.mk_execution` that converts a local `America/Bogota` datetime to UTC;
  - `seed_usage(session)`: privileges `ANA/USAGE` for ADMINISTRATOR and ADMINISTRATIVE, plus `seed_ana_lists`.
- [X] T005 [P] Write `api/tests/test_ana_usage_access.py`:
  - 401 without a token;
  - 403 for a COLLABORATOR without `ANA/USAGE`;
  - 200 for ADMINISTRATOR and superuser with `scope.restricted == false`;
  - ADMINISTRATIVE sees only dashboards with a live MANAGE grant (USER, ROLE, TEAM and UNIT scopes). A VIEW-only grant is excluded, a revoked grant (`valid_to` in the past) is excluded, and no MANAGE at all gives empty figures with `restricted == true, dashboards == 0`.
  - Validation 400s: missing or malformed dates, inverted range, more than 731 days, `date_to` beyond tomorrow, `unit` together with `team`, unknown `unit` or `team` code.
  - No-leak: recursively assert that no key named `user_id`, `payload` or `error_message` appears in the `metrics` response.

### Implementation

- [X] T006 Add the response models to `api/app/insights/internal/models.py`, as plain `SQLModel` (non-table) classes following data-model.md and contracts/usage-api.md:
  - `UsagePeriod`, `UsageScope`, `UsageFilter`, `UsageFigures` (runs, attempts, users, dashboards, success_rate, median_ms, avg_ms, incomplete, outcomes dict), `UsageChange`, `UsageSummary`;
  - `UsageBucket`, `UsageDashboardRow`, `UsageUnitNode` (self-referencing `children`), `UsageTeamRow`, `UsageMetrics`;
  - `UsageErrorItem`, `UsageErrors`.
- [X] T007 Create `api/app/insights/internal/usage_service.py` with the shared core:
  - `ORG_WIDE_PROFILES = ("ADMINISTRATOR",)`.
  - `OUTCOME_CLASS` table and `classify(status) -> (outcome_key, is_run)` per research R5, with unknown codes treated as runs under their raw key.
  - `parse_period(date_from, date_to) -> Period`: validation per data-model, raising `ValueError`. Computes the local window converted to naive UTC with `zoneinfo.ZoneInfo(settings.APP_TIMEZONE)`, the previous window, the inclusive length N, and `bucket` (day ≤ 31, week ≤ 183, else month).
  - `scope_for(session, user) -> Optional[set[int]]`: `None` for superuser or `ORG_WIDE_PROFILES`; otherwise the ids whose level is MANAGE in `permissions_service.accessible_dashboards`.
  - `load_rows(session, start_utc, end_utc, scope)`: one projected `select(Execution.id, .dashboard, .user_id, .executed_at, .status, .duration_ms)` on the combined current and previous window, filtered by scope (`IN`; an empty scope short-circuits to `[]`), with `execution_options(yield_per=5000)`.
  - `figures(rows) -> UsageFigures` and `change(cur, prev) -> UsageChange` (research R9).
  - `build_metrics(session, user, period, unit=None, team=None) -> UsageMetrics`: fills `period`, `scope`, `filter` and `summary` for now (later stories add `timeline`, `dashboards`, `units` and `teams`), and logs the structured line.
- [X] T008 Create `api/app/insights/routes/usage.py` with `router = APIRouter(prefix="/api/usage", tags=["usage"])` and `GET /metrics` (query `date_from`, `date_to`, optional `unit`, `team`). It calls `usage_service.build_metrics` and maps `ValueError` to 400. Register it in `api/app/main.py` next to the other insights routers.
- [X] T009 [P] Add the TypeScript types `UsageMetrics`, `UsagePeriod`, `UsageFigures`, `UsageChange`, `UsageSummary`, `UsageBucket`, `UsageDashboardRow`, `UsageUnitNode`, `UsageTeamRow`, `UsageErrors` and `UsageErrorItem` to `ui/src/types/api.ts`, mirroring contracts/usage-api.md
- [X] T010 [P] Create `ui/src/lib/usageMetrics.ts`:
  - `getUsageMetrics({dateFrom, dateTo, unit?, team?})`;
  - `getDashboardErrors(id, {dateFrom, dateTo, unit?, team?, limit?})`, both over `lib/api.ts`;
  - `presetRange(preset: "7d"|"30d"|"90d"|"12m", today)`, which returns local `YYYY-MM-DD` dates (12m = today − 364 days).
- [X] T011 Create the page shell `ui/src/pages/ana/usage.astro`:
  - copy the header part of `ui/src/pages/ana/catalog.astro`: `BaseLayout`, `Breadcrumb`, the option name and icon via `getOption("ANA", "USAGE")`, and `Toast`;
  - add a `<div data-usage-root>` mount point and a bundled `<script>` that mounts `UsageMetrics.svelte` with `mount()`.
- [X] T012 Create the island root `ui/src/components/svelte/UsageMetrics.svelte`:
  - period selector: presets 7d, 30d (default), 90d and 12m, plus a custom start/end date pair with an inline error for inverted or over-24-month ranges;
  - a loading state, an error state that keeps the last good data, and a fetch through `getUsageMetrics` on every change;
  - a scope note when `scope.restricted` ("Limited to the N dashboards you manage");
  - placeholder slots for the four sections;
  - loads the `EXECUTION_STATUS`, `DASHBOARD_TYPE`, `SOURCE_TYPE` and `DASHBOARD_STATUS` list items once, for labels.
- [X] T013 [P] Add the base i18n keys under `usage_metrics.*` to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`: title, period presets, custom range labels and errors, loading/error/empty texts, the scope note, and the "No team" label.

**Checkpoint**: T005 passes. `/ana/usage` renders for `admin` with the period selector working against the endpoint.

---

## Phase 3: User Story 1 — See overall usage for a period (Priority: P1) 🎯 MVP

**Goal**: headline figures for the chosen period with change against the previous period (FR-006, FR-007, FR-007a, FR-008, FR-009).

**Independent Test**: with a known set of executions across every status, users and dates, open the page as `admin`, pick a period, and each tile matches a hand count (quickstart §3.2).

### Tests (write first, confirm they fail)

- [X] T014 [P] [US1] Write `api/tests/test_ana_usage_metrics.py` (summary part):
  - Each status is classified per research R5. Runs exclude CANCELLED and UNAUTHORIZED, while attempts count them.
  - The success rate is `SUCCESS/(SUCCESS+FAILED+TIMEOUT)`; it is `null` when only Cancelled or Incomplete records exist; Incomplete never enters it.
  - The median and average use only SUCCESS records with a duration; the median works for both odd and even counts.
  - Users and dashboards are distinct over runs only.
  - The previous window is computed per research R9: change ratios for counts, a points difference for the rate, a ms difference for durations, and `null` when previous is 0.
  - A run at 23:30 local on `date_to` is inside the period; one at 00:10 local the next day is outside.
  - Empty period: every count is 0 and the rate and durations are `null`.

### Implementation

- [X] T015 [US1] Complete `figures()`, `change()` and the summary assembly in `api/app/insights/internal/usage_service.py`. Split `load_rows` output into current and previous by `executed_at`, and compute `outcomes` per key including `INCOMPLETE`. Make T014 pass.
- [X] T016 [P] [US1] Create the headline tiles in `ui/src/components/svelte/UsageMetrics.svelte`:
  - tiles for Runs, Abandoned or refused attempts, Distinct users, Distinct dashboards, Success rate, Median duration (with the average as secondary text) and Incomplete;
  - each tile shows its change with an up, down or neutral mark and a tooltip naming the previous period's dates;
  - durations are formatted as `1.2 s` / `850 ms` and the rate as a percentage;
  - an empty state when the period has no records (FR acceptance US1-6);
  - the tiles wrap on narrow screens.
- [X] T017 [P] [US1] Add the tile labels, change tooltips and empty-state text under `usage_metrics.summary.*` to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`

**Checkpoint**: US1 is fully functional. The MVP can be demonstrated with the synthetic data.

---

## Phase 4: User Story 2 — See usage over time (Priority: P1)

**Goal**: a stacked outcome chart per day, week or month, with empty buckets shown as zero (FR-010).

**Independent Test**: with records spread over several weeks, choose 90 days. There is one bar per ISO week, and its stacked counts match a hand count (quickstart §3.3).

### Tests (write first, confirm they fail)

- [X] T018 [P] [US2] Extend `api/tests/test_ana_usage_metrics.py` (timeline part):
  - bucket thresholds: 31 days gives `day`, 32 gives `week`, 183 gives `week`, 184 gives `month`;
  - weekly buckets start on Monday, so the first bucket is partial and its `start` is the period's first day;
  - monthly buckets follow calendar months;
  - local-time placement: a 20:00 local run on the 31st stays in that month;
  - every bucket in the window is present, oldest first, empty ones all zero;
  - the outcomes per bucket sum to runs plus attempts.

### Implementation

- [X] T019 [US2] Add `timeline()` to `api/app/insights/internal/usage_service.py`: generate every bucket for the current window in local dates, then assign each current row by its local date. Include it in `build_metrics`. Make T018 pass.
- [X] T020 [US2] Load the `dataviz` skill, then create `ui/src/components/svelte/UsageTimeline.svelte`:
  - a responsive SVG stacked-bar chart with stack order Success, Failed, Timeout, Incomplete, then Cancelled and Unauthorized set apart (hatched or desaturated) as abandoned or refused attempts;
  - color tokens for light and dark;
  - a legend with translated outcome labels from `EXECUTION_STATUS` (plus `usage_metrics.outcome.incomplete`);
  - y-axis ticks;
  - x-labels that thin out when crowded;
  - a hover and tap tooltip listing the bucket's dates and counts per outcome;
  - `role="img"` with an accessible summary.

  Mount it from `UsageMetrics.svelte`.
- [X] T021 [P] [US2] Add the chart title, legend labels, tooltip texts and the "attempts" grouping label under `usage_metrics.timeline.*` to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`

**Checkpoint**: US1 and US2 both work. The 12-month view shows growth and the holiday dip with the synthetic data.

---

## Phase 5: User Story 3 — See which dashboards are used and how well they work (Priority: P2)

**Goal**: the ranked dashboards table with unused rows, lazy top errors and CSV/Excel export (FR-011, FR-012, FR-014a).

**Independent Test**: with several dashboards, the table lists each one run in the period with correct figures, sorts by every numeric column, "show unused" adds Published zero-run dashboards in scope, and expanding a row lists its top errors (quickstart §3.4, §3.7).

### Tests (write first, confirm they fail)

- [X] T022 [P] [US3] Write `api/tests/test_ana_usage_dashboards.py`:
  - Rows carry name, type, source and **current** status: an Archived or Retired dashboard with history is still listed.
  - Runs, attempts, users, rate and median are per dashboard; `last_run_at` is the newest run-class record.
  - Ordering is runs desc.
  - A dashboard with only attempts gets `runs = 0, unused = false`.
  - Unused rows are Published + active + in scope with zero records; Draft and inactive dashboards are never unused rows.
  - Scope filters the rows for ADMINISTRATIVE.
  - Errors endpoint:
    - top-N ordering by count, then message;
    - `statuses` per message;
    - `total_with_error`;
    - `limit` bounds 1–50 (400 outside);
    - 404 for a dashboard outside scope and for a nonexistent one, with the same body.

### Implementation

- [X] T023 [US3] Add `dashboard_rows()` to `api/app/insights/internal/usage_service.py`: aggregate current rows per dashboard, then fetch labels with one `select(Dashboard)` over the used ids plus the Published, active, in-scope unused ids. Include it in `build_metrics`.
- [X] T024 [US3] Add `dashboard_errors(session, user, dashboard_id, period, unit, team, limit)` to `api/app/insights/internal/usage_service.py`:
  - check scope (raise a not-found error when out of scope);
  - one `GROUP BY error_message, status` query over the period with a non-empty `error_message`, merged into `items` with `statuses`;
  - apply the `unit` / `team` filter once US4 lands. Leave a single hook `_user_filter(...)` returning `None` for now.

  Then add `GET /dashboards/{dashboard_id}/errors` to `api/app/insights/routes/usage.py` (`limit: int = Query(10, ge=1, le=50)`, not-found → 404). Make T022 pass.
- [X] T025 [P] [US3] Create `ui/src/lib/tableExport.ts` by **extracting** `toCSV` and `downloadFile` from `ui/src/components/table/advancedTable.ts`, keeping the same output, and make `advancedTable.ts` import them. Add:
  - `toCSV(rows, columns, {bom: true})` with RFC 4180 quoting and a UTF-8 BOM option;
  - `exportFileName(table, period, filter)`, e.g. `usage-dashboards_2026-09-06_2026-10-05_unit-ENG`.

  Verify an existing DataTable export (for example `/admin/options`) produces an identical CSV.
- [X] T026 [P] [US3] Create `ui/src/lib/xlsx.ts`: `toXlsx(sheetName, header: string[], rows: (string|number|null)[][]): Blob`, a minimal Office Open XML workbook. It has one worksheet with inline strings and numeric cells, the parts `[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/_rels/workbook.xml.rels` and `xl/worksheets/sheet1.xml`, and is zipped with STORE using a table-driven CRC-32. XML-escape cell text and cap the sheet name at 31 characters. Verify the file opens in Excel / LibreOffice without warnings and that accents survive.
- [X] T027 [US3] Create `ui/src/components/svelte/UsageDashboardsTable.svelte`:
  - columns: name, type, source, status (labels via `listLang`), runs, attempts, users, success rate, median duration and last run;
  - click-to-sort on numeric columns (default runs desc), a search box over name, type and source in both languages, and a "show unused" toggle;
  - expandable rows that lazily call `getDashboardErrors` and show message, count and statuses, with loading and empty states;
  - an Export menu (CSV, Excel) that exports exactly the visible rows and columns via `tableExport.ts` / `xlsx.ts`;
  - horizontal scroll inside its own container.

  Mount it from `UsageMetrics.svelte`.
- [X] T028 [P] [US3] Add the column headers, search placeholder, unused toggle, errors panel texts and export menu labels under `usage_metrics.dashboards.*` and `usage_metrics.export.*` to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`

**Checkpoint**: US1–US3 work. Exports of the dashboards table open correctly in Excel.

---

## Phase 6: User Story 4 — See adoption by unit and team (Priority: P2)

**Goal**: the unit tree with roll-up, team rows with hybrid attribution, adoption counts and rates, a row-click filter that narrows the other sections, and export (FR-005, FR-013, FR-014, FR-014a).

**Independent Test**: with users in a three-level unit tree and three teams (one user in two teams, one with only a historical assignment, one with none), every unit and team row matches a hand count, and selecting a row narrows the headline, chart and dashboards table (quickstart §3.5–3.6).

### Tests (write first, confirm they fail)

- [X] T029 [P] [US4] Write `api/tests/test_ana_usage_groups.py`:
  - **Unit tree.** A three-level tree rolls up runs and distinct users as a set union, so a user with runs on two dashboards counts once. `members` and `direct_members` are correct, and inactive users are not members. A subtree with zero members is omitted. A parent's figures equal its direct members' plus its children's. `adoption_rate = users/members`, `null` when members is 0. A cycle in `parent` does not hang and is logged.
  - **Teams.** A run inside an assignment's validity counts in that team. A run before any valid assignment falls back to the user's current team. A user with no assignment at all goes to `__none__`. A user in two teams at run time counts in both. Team `members` are users with an active assignment valid during the period or now. `__none__` has `members` and `adoption_rate` null.
  - **Filter.** `unit=ENG` narrows summary, timeline and dashboards to users in ENG's subtree; `team=X` narrows to runs attributed to X, the same rule as the team rows; `team=__none__` works. The `units` and `teams` sections are not narrowed by the filter. The errors endpoint honours the filter.
  - **Scope interaction.** For ADMINISTRATIVE, unit and team runs only count in-scope dashboards, while members stay organization-wide.

### Implementation

- [X] T030 [US4] Add the group loaders to `api/app/insights/internal/usage_service.py`:
  - one query for active `BusinessUnit` rows into a `children` map, with a visited-set cycle guard;
  - one query for active users (`id`, `unit`) for membership and run attribution;
  - one query for active `Assignment` rows with a team (`user_id`, `team`, `valid_from`, `valid_to`);
  - one query for `Team` names.

  Keep this to four constant queries per request.
- [X] T031 [US4] Add `teams_for_run(user_id, executed_at)` to `api/app/insights/internal/usage_service.py`. It implements the hybrid rule of research R8 (valid at `executed_at`, else currently valid, else `__none__`), compares in naive UTC, and memoises current teams per user.
- [X] T032 [US4] Add `unit_tree()` and `team_rows()` to `api/app/insights/internal/usage_service.py` per data-model.md. Then implement the `unit` / `team` filter: resolve unit codes to their subtree once, filter the current and previous rows by user or by `teams_for_run`, and apply it before `figures`, `timeline` and `dashboard_rows`, but **not** before `unit_tree` / `team_rows`. Wire `_user_filter` into `dashboard_errors`. Include `units` and `teams` in `build_metrics`. Make T029 pass.
- [X] T033 [US4] Create `ui/src/components/svelte/UsageAdoption.svelte`:
  - two tabs, By unit and By team;
  - the unit tab is an expandable tree (top-level expanded one level) with members, users who ran, adoption rate as a percentage with a small bar, runs and success rate;
  - the team tab is a table with the same columns, a "No team" row showing the count only, and a note that team totals can exceed the overall total;
  - clicking a row sets the filter in `UsageMetrics.svelte`, which re-fetches and shows a clearable chip "Unit: X" / "Team: X", and the selected row is highlighted;
  - an Export menu per tab (CSV, Excel) via `tableExport.ts` / `xlsx.ts`, with unit rows flattened to their full path (`Corporate › Engineering › Backend`).

  Mount it from `UsageMetrics.svelte`.
- [X] T034 [P] [US4] Add the tab names, column headers, the multi-team note, the filter chip text and the No team label under `usage_metrics.adoption.*` to `ui/src/i18n/en.json` and `ui/src/i18n/es.json`

**Checkpoint**: all four stories work independently and together.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T035 Run the full backend suite `docker compose exec -T api uv run pytest -q` and `make test`. The baseline is 715 passed / 0 failed plus the new suites, with no regressions.
- [X] T036 [P] Run `cd ui && bun run build` and `bunx astro check`. The build must be clean, and the check may only add the known "Svelte file is not a module" error once per new Svelte import.
- [X] T037 Run the SC-003 benchmark from `specs/008-usage-metrics/quickstart.md` §5:
  - reload with `-v scale=21` (about 100 000 rows);
  - time `GET /api/usage/metrics` over 12 months and record the elapsed time from the structured log line;
  - if it takes 3 s or more, stop and apply the research R1 fallback as a plan amendment rather than a silent change;
  - reload at scale 1 afterwards.
- [ ] T038 Walk through `specs/008-usage-metrics/quickstart.md` §3–§4 as `admin`, `felipe.cardenas` and `adriana.velez`:
  - **Status (2026-10-06):** partially verified, not done. Everything checkable without a browser passed:
    - API figures equal an independent SQL hand count as `admin` and as `felipe.cardenas`;
    - `adriana.velez` gets 403, and out-of-scope errors get 404;
    - `/ana/usage` SSR returns 200;
    - the dev server serves the new island;
    - the `.xlsx` output passes zip/CRC and XML checks.

    **Still pending: a manual click-through in a browser** (no Playwright in this environment). Cover period presets, chart hover, table view, sorting, unused toggle, errors panel, row filter chip, exports opened in Excel, Español, dark mode and 390 px.
  - including Español, dark mode and 390 px width;
  - export files opened in Excel;
  - note anything not click-tested.
- [X] T039 [P] Check i18n parity: every `usage_metrics.*` key exists in both `ui/src/i18n/en.json` and `es.json` (a script diffing the key sets) and no hard-coded user-facing string remains in the new Svelte files
- [X] T040 [P] Update `docs/user-stories/06-ana.md` HU-AN07 with a **Status: ✅ implemented (SpecKit 008)** paragraph covering scope rules, run definition, unit tree, hybrid teams, exports, and the synthetic-data and index scripts
- [X] T041 Update `memory/MEMORY.md`:
  - a decisions-log row for SpecKit 008 covering the Python aggregation and its rationale, `ORG_WIDE_PROFILES` vs MANAGE scope, run vs attempt, hybrid teams, `APP_TIMEZONE`, the in-repo `.xlsx` writer, the extracted `lib/tableExport.ts`, the indexes, `provisioned-db.sql`, and the synthetic scripts;
  - in Feature status, a new shipped row, `insights` → "✅ done", and the HU-AN07 pending note removed;
  - the backend-tests baseline count.
- [X] T042 Add one rollup entry at the top of `memory/CHANGELOG.md` (`## YYYY-MM-DD HH:MM — …`, time from `date '+%Y-%m-%d %H:%M'`) covering the whole 008 change set, listing files affected

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none. T001 should precede the benchmark (T037). T003 is needed only by T037.
- **Foundational (Phase 2)**: T004 → T005 (tests) → T006 → T007 → T008. The UI tasks T009 and T010 can run in parallel with the backend; T011 → T012 need T009 and T010. **Blocks every story.**
- **US1 (Phase 3)**: after Phase 2.
- **US2 (Phase 4)**: after Phase 2. Its UI mounts inside the same root as US1 (T012), so independent of US1's code apart from sharing that file.
- **US3 (Phase 5)**: after Phase 2. Provides `tableExport.ts` and `xlsx.ts`, which US4 reuses.
- **US4 (Phase 6)**: after Phase 2. Its export reuses T025 and T026 from US3, and its filter extends `dashboard_errors` from US3 (T024). Run US4 after US3, or implement T025/T026 first if they are staffed in parallel.
- **Polish (Phase 7)**: after all stories.

### Within each story

Tests fail first, then service, then route, then UI, then i18n. `usage_service.py` is one file, so its tasks within and across stories are sequential (no [P]).

### Parallel opportunities

- Setup: T002 ∥ T003.
- Foundational: T005 can be written ∥ T009, T010 and T013.
- US1: T014 ∥ T016 ∥ T017 (the UI can be built against the contract while the service is written).
- US2: T018 ∥ T021; T020 after T019 only for live data (it can be built against a fixture).
- US3: T022 ∥ T025 ∥ T026 ∥ T028.
- US4: T029 ∥ T034.
- Polish: T036 ∥ T039 ∥ T040.

## Parallel Example: User Story 3

```text
Task: "T022 [P] [US3] Write api/tests/test_ana_usage_dashboards.py"
Task: "T025 [P] [US3] Extract toCSV/downloadFile into ui/src/lib/tableExport.ts"
Task: "T026 [P] [US3] Create the .xlsx writer in ui/src/lib/xlsx.ts"
Task: "T028 [P] [US3] Add usage_metrics.dashboards.* / export.* i18n keys"
# then sequentially: T023 → T024 (usage_service.py + routes) → T027 (table island)
```

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup (T001–T003), then Phase 2 Foundational (T004–T013).
2. Phase 3 US1 (T014–T017).
3. **Stop and validate**: quickstart §3.2 with the synthetic data, as `admin` and as `felipe.cardenas`.

### Incremental delivery

1. US1, the headline: answers "is it used, and is it working?"
2. US2, the timeline: trends and the holiday dip.
3. US3, the dashboards table and export: what to promote, fix or retire.
4. US4, unit and team adoption, filter and export: where to train or promote.

Each increment is demoable on its own with the synthetic data loaded.

## Notes

- `usage_service.py` is the single owner of the classification, period and scope rules. Never re-implement them in the UI or in another service.
- Synthetic data is development-only. Never add it to `db/sql/`.
- Provisioned DBs (local, Neon) need `provisioned-db.sql` run once for the indexes.
- Commit per completed phase. Keep one CHANGELOG rollup entry for the whole branch (T042).
