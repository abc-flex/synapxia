# Feature Specification: Usage Metrics

**Feature Branch**: `008-usage-metrics`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "quiero que trabajemos en la historia de usuario de Usage Metrics"

## Context

Covers user story **HU-AN07 Usage Metrics** (see `docs/user-stories/06-ana.md`):

> As a **manager**, I want to **see how the analytics are actually used** — executions over time, success rate, duration, and adoption by unit and team — **so that** I can evaluate adoption, impact and return on investment.

What already exists:

- **Dashboard Management** (SpecKit 006): analysts register dashboards and reports, with a lifecycle Draft → Published → Archived/Retired, parameters and grants.
- **Dashboard Catalog with Execute** (SpecKit 007): every attempt to run a dashboard leaves one execution record — who, which dashboard, when, with which values, the outcome status, the duration and an error message when it did not succeed. Statuses are Success, Failed, Unauthorized, Timeout and Cancelled. A record with **no status yet** is a run whose browser closed before reporting its outcome; it is **incomplete**, not a success and not a failure.
- **People structure**: every user belongs to exactly one business unit, and may belong to zero, one or several teams through assignments that have a validity window.
- The sidebar already has the option **Usage Metrics** (`/ana/usage`) in the Analytics module, granted today to the Administrator and Administrative profiles.

## Clarifications

### Session 2026-10-05

- Q: Which executions does a manager see? → A: A superuser or an Administrator sees every execution in the organization; any other holder of the Usage Metrics privilege sees only executions of dashboards they hold a live Manage grant to (option C).
- Q: How is the success rate computed? → A: Success ÷ (Success + Failed + Timeout). Cancelled, Unauthorized and Incomplete are reported separately in the outcome breakdown and never enter the rate (option B).
- Q: How is adoption by unit and team measured? → A: Both the count of distinct users who ran at least one dashboard and the percentage of the group's active members that represents (option C).
- Q (user request): Is test data needed? → A: Yes. Realistic synthetic execution records must be provided so the page can be seen working with data that resembles real usage.
- Q (user follow-up, after implementation): May the synthetic data add people, dashboards, grants or assignments? → A: No. It writes **only** to the executions table, spread over the dashboards and users that already exist; every other table keeps its data.
- Q: How are business units grouped in the adoption view, given units form a tree (Corporate → departments → areas)? → A: Hierarchically: each unit rolls up its sub-units, shown as an expandable tree; filtering by a unit includes its sub-units (option B).
- Q: Which teams does a run count in: current teams or teams at the time of the run? → A: Hybrid: the teams whose assignment was valid when the run started; if the user had none then, their current active teams; if neither, "No team" (option C).
- Q: Can the figures be exported? → A: Yes: the dashboards table and the adoption table (unit and team) export to CSV/Excel, aggregates only, honouring the active period and filters; no PDF (option B).
- Q: What counts as a run in the totals? → A: Only real attempts: Success, Failed, Timeout and Incomplete. Cancelled and Unauthorized get their own figure ("abandoned or refused attempts") and stay in the stacked chart; distinct users, the dashboards ranking and adoption use the same run definition (option B).
- Q (user follow-up, 2026-10-06): Should adoption also break usage down by project? → A: Yes, a third view "By project" that works like the unit and team views. A project belongs to one team and people reach it through that team, so a run counts in the active projects of every team it counts in (FR-013), when its local date falls inside the project's dates; runs that reach no project go under "No project". Its members are the owning team's members. Selecting a project row filters the page like a unit or team.

What this feature adds: one read-only page where a manager sees how the dashboards are being used, over a chosen period, broken down by time, dashboard, unit and team. Nothing is written; it only reads the execution records.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See overall usage for a period (Priority: P1)

As a manager, I want to open Usage Metrics, pick a period and immediately see the headline figures — how many runs, how many distinct people, success rate and typical duration — so that I know at a glance whether the analytics are being used and working.

**Why this priority**: The headline figures answer the story's core question ("are the analytics actually used?") on their own; every other view is a breakdown of them.

**Independent Test**: With a known set of execution records across several statuses, users and dates, open the page as an administrator, choose a period, and confirm each headline figure matches a hand count over those records.

**Acceptance Scenarios**:

1. **Given** a manager opens Usage Metrics from the sidebar, **When** the page loads, **Then** they see a header with the option's name and icon, a period selector and a row of headline figures, with the default period applied.
2. **Given** the period selector, **When** the manager opens it, **Then** it offers quick ranges (last 7 days, last 30 days, last 90 days, last 12 months) and a custom start/end date range; the default is last 30 days.
3. **Given** a period is selected, **When** the figures update, **Then** they show: runs (Success, Failed, Timeout and Incomplete records — see FR-007a), abandoned or refused attempts (Cancelled + Unauthorized), distinct users who made at least one run, distinct dashboards run, success rate, and the median and average duration of successful runs.
4. **Given** each headline figure, **When** it renders, **Then** it also shows the change against the immediately preceding period of the same length (e.g. +12%), or a neutral mark when the previous period has no data.
5. **Given** records with no status yet (incomplete), **When** figures are computed, **Then** they are counted separately as "incomplete" and are never counted as successes or failures.
6. **Given** the period contains no execution records, **When** the page updates, **Then** an empty-state message says there is no usage in that period instead of showing zeroes as if they were meaningful.

---

### User Story 2 - See usage over time (Priority: P1)

As a manager, I want a chart of runs over time, split by outcome, so that I can see trends, adoption growth and periods of failures.

**Why this priority**: "Executions over time" is explicitly asked for in the story and is the main way to see adoption growing or fading.

**Independent Test**: With records spread across several weeks, choose a 90-day period and confirm the chart has one point per week whose stacked outcome counts match a hand count.

**Acceptance Scenarios**:

1. **Given** a period is selected, **When** the chart renders, **Then** it shows execution records per time bucket stacked by outcome (Success, Failed, Timeout, Incomplete, and — visually set apart as abandoned or refused — Cancelled, Unauthorized), with outcome labels in the interface language.
2. **Given** the period length, **When** buckets are chosen, **Then** they are days for periods up to 31 days, weeks up to 6 months and months beyond that.
3. **Given** a bucket with no runs, **When** the chart renders, **Then** that bucket shows as zero, not as a gap that hides inactivity.
4. **Given** the manager hovers or taps a bucket, **When** the detail shows, **Then** it lists the bucket's dates and the count per outcome.

---

### User Story 3 - See which dashboards are used and how well they work (Priority: P2)

As a manager, I want a table of dashboards ranked by use, with their success rate and duration, so that I can tell which analytics deliver value, which are ignored and which are failing.

**Why this priority**: Impact and return on investment are judged per dashboard; this view points to what to promote, fix or retire.

**Independent Test**: With records for several dashboards, confirm the table lists each dashboard run in the period with run count, distinct users, success rate, median duration and last run, and that sorting by each column orders correctly.

**Acceptance Scenarios**:

1. **Given** a period is selected, **When** the dashboards table renders, **Then** each dashboard run at least once in the period appears with: name, type, source, current status, runs, distinct users, success rate, median duration of successful runs and date of last run.
2. **Given** the table, **When** the manager sorts by any numeric column, **Then** rows reorder accordingly; the default order is runs, highest first.
3. **Given** the table, **When** the manager types in its search box, **Then** only dashboards whose name, type or source match remain.
4. **Given** Published dashboards that were never run in the period, **When** the manager turns on "show unused", **Then** they appear with zero runs, so idle analytics are visible.
5. **Given** a dashboard has failures, **When** the manager opens its row, **Then** they see its most frequent error messages in the period with how many times each occurred.
6. **Given** the dashboards table or the adoption table, **When** the manager exports it to CSV or Excel, **Then** the file holds exactly the rows the table shows for the active period and filters, with aggregates only.

---

### User Story 4 - See adoption by unit and team (Priority: P2)

As a manager, I want usage broken down by business unit and by team, so that I can see which parts of the organization have adopted the analytics and which have not.

**Why this priority**: Adoption by unit and team is explicitly asked for in the story and is what a manager uses to target training or promotion.

**Independent Test**: With users in two units and three teams (one user in two teams), confirm each unit and team row shows the expected runs and distinct users, and that the multi-team user's runs count in both of their teams.

**Acceptance Scenarios**:

1. **Given** a period is selected, **When** the adoption section renders, **Then** it offers two views, by unit (an expandable tree following the unit hierarchy) and by team, each listing runs, distinct users who ran something, success rate and an adoption rate (see FR-014).
2. **Given** a user belonged to several teams when a run started, **When** team figures are computed, **Then** the run counts in each of those teams; the section states that team totals can exceed the overall total.
3. **Given** a user had no team assignment valid when a run started, **When** team figures are computed, **Then** the run counts in the teams the user belongs to today; only if the user belongs to no team today either does it count under a "No team" row.
4. **Given** a unit or team has active members but no runs in the period, **When** the section renders, **Then** it still appears with zero runs and 0% adoption.
5. **Given** the manager selects a unit or team row, **When** the page updates, **Then** the headline figures, the chart and the dashboards table narrow to runs by that unit's members (including its sub-units) or that team's members, and a visible chip shows the active filter with a way to clear it.

---

### Edge Cases

- A run started just before the period's end and finished after it counts in the period where it **started**.
- A dashboard later Archived or Retired keeps its history; its runs still count and its current status is shown.
- A user later deactivated or moved to another unit: unit figures use the user's **current** unit (there is no unit history); team figures use the assignment valid when the run started, falling back to today's teams (see FR-013). A run made in team ALPHA before the user moved to BRAVO stays in ALPHA.
- A user assigned directly to a parent unit (e.g. Engineering) counts in that unit and its ancestors, not in any of its sub-units; the tree shows such direct members alongside the sub-unit rows.
- Records with no status (incomplete) never enter success rate or duration figures.
- Cancelled records include parameters windows closed without running; they are shown as abandoned attempts and count neither as runs nor against the success rate (see FR-006, FR-007a).
- A custom range whose end is before its start, or longer than 24 months, is refused with a message.
- Periods with very large volumes still load (see SC-003); the page never lists individual execution records.

## Requirements *(mandatory)*

### Functional Requirements

**Access**

- **FR-001**: The page MUST be reachable from the existing Usage Metrics option and require the Usage Metrics privilege (read level). Users without it MUST be refused, by the page and by the server.
- **FR-002**: A superuser or a user with the Administrator profile MUST see every execution in the organization. Any other holder of the Usage Metrics privilege MUST see only executions of dashboards they hold a live Manage grant to (through any scope: user, role, team, unit, project). This scope applies to every figure, the dashboards table (including "show unused") and the adoption section, and MUST be enforced by the server.
- **FR-003**: The page MUST be read-only: it never creates, edits or deletes execution records or anything else.

**Period and filters**

- **FR-004**: The manager MUST be able to choose the period with quick ranges (7, 30, 90 days, 12 months) or a custom start/end date, default last 30 days, at most 24 months. Dates are interpreted in the organization's local time zone.
- **FR-005**: Selecting a unit or team (User Story 4) MUST narrow every figure on the page to runs by that group's members (for a unit, members of the unit and all its sub-units), with a clearable filter chip.

**Figures**

- **FR-006**: Success rate MUST be Success ÷ (Success + Failed + Timeout). Cancelled, Unauthorized and Incomplete records MUST NOT enter the rate; they are shown in the outcome breakdown. When the denominator is zero, the rate shows as not applicable, not as 0%.
- **FR-007a**: A **run** MUST be an execution record whose status is Success, Failed, Timeout or none (Incomplete). Cancelled and Unauthorized records are **abandoned or refused attempts**: they MUST NOT count as runs anywhere (headline runs, distinct users, distinct dashboards, dashboards-table runs and users, adoption counts and rates, unit/team runs) and are reported in their own figure and in the outcome breakdown.
- **FR-007**: Headline figures MUST be: runs, abandoned or refused attempts, distinct users, distinct dashboards, success rate, median and average duration of successful runs, incomplete count; each with its change against the preceding period of equal length.
- **FR-008**: Duration figures MUST use only Success records that have a duration.
- **FR-009**: Records with no status MUST be reported as Incomplete and never counted as success or failure.
- **FR-010**: The over-time chart MUST show every execution record per bucket stacked by outcome, with Cancelled and Unauthorized visually distinguished as abandoned or refused attempts, with day/week/month buckets chosen by period length and empty buckets shown as zero.
- **FR-011**: The dashboards table MUST list each dashboard run in the period with name, type, source, current status, runs, distinct users, success rate, median success duration and last run; sortable, searchable, default order by runs; with a "show unused" toggle that adds Published dashboards with zero runs.
- **FR-012**: A dashboard row MUST expose its most frequent error messages in the period with their counts.
- **FR-013**: The adoption section MUST show by unit and by team. Units MUST follow the business-unit hierarchy as an expandable tree: each unit's figures roll up its own members and those of every sub-unit at any depth (top-level units expanded one level by default; units with no members in their whole subtree are omitted). Each row shows: runs, distinct users, success rate and adoption; a run counts in every team whose assignment to its user was active and valid at the moment the run started; when the user had no such assignment, it counts in the user's current active teams instead; when the user has neither, it goes under "No team".
- **FR-014**: Adoption MUST be shown as both the count of the group's distinct users who ran at least one dashboard in the period and the adoption rate: that count ÷ the group's active members (active users currently in the unit or any of its sub-units, or with an active assignment to the team valid at any time in the period or today). The "No team" row shows the count only.
- **FR-014b**: The adoption section MUST also offer a **By project** view with the same columns (plus the owning team). A run counts in each active project owned by a team the run counts in (FR-013), when the run's local date is within the project's start/end dates (open ends allowed); otherwise under "No project" (count only). Project members are the owning team's members (FR-014). Selecting a project narrows the page like a unit or team; unit, team and project filters are mutually exclusive.
- **FR-014a**: The dashboards table and the adoption table (unit and team views) MUST each offer an export to CSV and Excel. The file MUST contain exactly the rows and columns the table shows for the active period, unit/team filter and search (unit rows flattened with their full path, e.g. "Corporate › Engineering › Backend"), plus the period and active filter in its name or header. Exports contain aggregates only, never individual execution records (FR-015), and use the same access scope as the page (FR-002).

**Synthetic data**

- **FR-019**: The feature MUST ship realistic synthetic execution records that can be loaded into a development database, so the page can be demonstrated with data resembling real usage. They MUST:
  - cover the last 12 months, with adoption growing over time, fewer runs on weekends, a visible dip in holiday periods and runs concentrated in business hours;
  - write **only** to the executions table: no person, dashboard, grant, parameter or team assignment is created or changed;
  - spread over the existing active Published dashboards with uneven popularity;
  - come from the existing active users, with uneven activity (power users, occasional users, people who never run anything);
  - include the outcomes the existing dashboards can produce in plausible proportions (mostly Success; Failed, Cancelled, a few Incomplete; Unauthorized on dashboards not shared with everyone; Timeout only for Internal Page dashboards, so none while no such dashboard exists) with realistic durations and the error messages the catalog actually records;
  - carry a payload in the same shape the catalog writes (values, sources, mode), built from each dashboard's own parameters;
  - be removable in one step without touching records created by real use.

**General**

- **FR-015**: The page MUST never list individual execution records or the parameter values used; it shows aggregates only.
- **FR-016**: Every user-facing text MUST exist in English and Spanish and follow the language switcher, including list values (statuses, dashboard types, sources).
- **FR-017**: The page MUST be usable at phone width without horizontal page scrolling; wide tables may scroll inside their own container.
- **FR-018**: Charts MUST be readable in light and dark themes and MUST not rely on color alone to tell outcomes apart (labels or legend).

### Key Entities

- **Execution**: one attempt (a run, or an abandoned/refused attempt — FR-007a) — dashboard, user, start time, outcome status (or none = incomplete), duration, error message. The only source of every figure.
- **Dashboard**: name, type, source, current status. Used to label and group runs, and to list unused Published dashboards.
- **User**: the person who ran the dashboard; belongs to one business unit.
- **Business Unit**: organizational unit with an optional parent unit (a tree: business unit → departments → areas); groups users for adoption figures, rolled up from sub-units.
- **Team Assignment**: a user's membership in a team over a validity window; the assignment valid when a run started decides which teams it counts in, with the current assignment as fallback.
- **Team**: groups users for adoption figures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every figure on the page matches a hand count over a known set of execution records covering all statuses, incomplete records, several units, several teams and one multi-team user.
- **SC-002**: A manager can answer "how many people used the analytics last month, and which dashboard was used most?" within 30 seconds of opening the page.
- **SC-003**: The page shows its figures in under 3 seconds for a period containing up to 100,000 execution records.
- **SC-004**: Users without the Usage Metrics privilege cannot see any figure, verified as a collaborator.
- **SC-005**: No individual execution record or parameter value is ever exposed by the page.
- **SC-006**: An Administrative user with Manage on only some dashboards sees figures computed exclusively from those dashboards' executions, verified against a hand count; an Administrator sees the organization-wide figures.
- **SC-007**: With the synthetic data loaded, the headline figures, chart, dashboards table and team adoption show non-trivial content for both the default period and the 12-month period. Unit adoption shows whatever the existing users' units allow (today almost everyone is in Engineering).

## Assumptions

- **Who is a manager.** Whoever holds the Usage Metrics option: today Administrator (organization-wide view) and Administrative (view limited to dashboards they manage). No new profile is created; extending access is a seed change.
- **Run vs attempt.** Every execution record is an attempt; only Success, Failed, Timeout and Incomplete ones are runs (FR-007a). Cancelled (mostly parameters windows closed without running) and Unauthorized records would inflate usage, so they are counted apart.
- **Period by start time.** A run belongs to the period of its start timestamp.
- **Current unit, teams at run time with a fallback.** Users carry only their current unit, so unit figures use it. Team figures use the assignment valid when the run started, so reassignments do not rewrite history; when no assignment was valid then (seeded assignments start on the day the database was provisioned), the user's current teams are used, so past usage is not pushed into "No team".
- **Synthetic data is development data, not seed data.** It ships as a load script and a removal script run by hand (`specs/008-usage-metrics/synthetic-usage.sql` / `synthetic-usage-remove.sql`, like the test-grant scripts of SpecKit 004/006), never in the ordered migrations, so production never receives it. It writes about 4,700 executions (and nothing else), each tagged with a marker the removal script uses.
- **Duration** comes from the execution record (measured by the catalog, SpecKit 007); median is the primary duration figure because a few slow runs would distort the average.
- **No PDF export, scheduled reports or alerts** in this feature; table exports (FR-014a) are included. The others can be added later.
- **No new tables are expected**: every figure is an aggregation over existing executions, dashboards, users, business units and team assignments.
- **Out of scope**: usage of the asset library or initiatives, per-user activity reports, and editing any execution record.
