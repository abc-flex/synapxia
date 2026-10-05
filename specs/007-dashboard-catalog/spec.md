# Feature Specification: Dashboard Catalog (with Execute and Favorite)

**Feature Branch**: `007-dashboard-catalog`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "quiero que trabajemos en la historia de usuario de Dashboard Catalog que incluye Execute, y Favorite. Dashboard Catalog debe considerar un filtro de privilegios similar al de la opción /lib/explore y a la de /inits/explore (con las mismas opciones de: Public, Shared with me, My role, Me team, My unit y My projects); También debe considerar el cajón de búsqueda y el filtro de favoritos similar al de estas dos opciones. Por su parte la opción de ejecución debe mostrarle al usuario una ventana para que ingrese los parámetros según las especificaciones de cada parámetro para que posteriormente use el botón de ejecutar y hacer la invocación de la respectiva herramienta o reporte (La ejecución del reporte se debe rastrear para registrar toda la información pertinente en la tabla de Executions)."

## Context

Covers user stories **HU-AN04 Dashboard Catalog**, **HU-AN05 – Execute** and the consumption half of **HU-AN06 – Favorite** (see `docs/user-stories/06-ana.md`). **HU-AN07 Usage Metrics** is out of scope; it will read the execution records this feature starts writing.

What already exists (SpecKit 006, Dashboard Management):

- Analysts register dashboards and reports, internal pages or embedded BI (Power BI, Looker Studio, Tableau, …), with a lifecycle Draft → Published → Archived/Retired.
- Each dashboard declares parameters (name, label, data type, required flag, default value, optional list of allowed values, optional grant binding). A parameter's **value source** is derived: bound to a grant, picked from a list, or typed by the viewer. Lists, viewer input, and a grant-bound parameter the viewer did not reach through the bound grant are asked for in a **parameters window before the run**. SpecKit 006 explicitly left that window to this feature.
- Dashboards are shared through grants (View / Manage) to a user, role, team, unit, project or everyone.
- Favorites are already stored and can be set from Dashboard Management. The Catalog shows the same favorites.

What this feature adds: the place where every user finds the dashboards shared with them, runs one with the right parameter values, and leaves a trace of each run.

## Clarifications

### Session 2026-10-04

- Q: How is the dashboard invoked? → A: Internal Page dashboards open inside the platform; every external BI source opens in a new browser tab (option C).
- Q: Is a parameters window closed without executing recorded? → A: Yes, as an execution with status Cancelled (option A).
- Q: How does an Internal Page dashboard open "inside the platform"? → A: In a large, closable viewer window over the catalog, showing the dashboard's name, the values used and an "open full page" link.
- Q: Besides search, favorites and privileges, does the catalog get its own type and source filters? → A: No. The search box also matches type and source; no separate selectors.
- Q: What visual layout does the catalog use? → A: A card grid like Explore Category, each card with an icon by source, name, type, description, tags, star and Execute button.
- Q: How long may an Internal Page take to load in the viewer before it is recorded as Timeout? → A: 30 seconds.
- Q: What values prefill the parameters window? → A: The parameter defaults, plus a "use my last values" button. The last values are derived from the payload of the user's most recent Success execution of that dashboard; no separate storage.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse the dashboards shared with me (Priority: P1)

As any user, I want to browse the published dashboards I am allowed to see, filter them by how they are shared with me, search them and narrow them to my favorites, so that I can find the right analytics quickly.

**Why this priority**: Without the catalog there is no entry point for consumers. Everything else (running, favoriting) happens from it.

**Independent Test**: Sign in as a collaborator whose grants reach some published dashboards through different scopes (public, user, team) and one draft dashboard. Open Dashboard Catalog and confirm each privilege option shows exactly the dashboards shared through that scope, the draft never appears, and search and favorites narrow the list.

**Acceptance Scenarios**:

1. **Given** a user opens Dashboard Catalog from the sidebar, **When** the page loads, **Then** they see a header with the option's name and icon, a search box, a "★ My favorites" toggle, a privileges filter and the dashboards gallery.
2. **Given** the privileges filter, **When** the user opens it, **Then** it offers exactly these six options in this order: Public, Shared with me, My role, My team, My unit, My projects. It has no "all" option and defaults to Public, as in Explore Category and Explore Initiatives.
3. **Given** a privilege option is selected, **When** the gallery updates, **Then** only dashboards shared with the user through that scope remain.
4. **Given** the favorites toggle is on, **When** the gallery updates, **Then** only dashboards the user marked as favorite remain.
5. **Given** the user types in search, **When** the gallery updates, **Then** only dashboards whose name, description, tags, type or source match remain.
6. **Given** a dashboard is Draft, Archived or Retired, or the user holds no live grant to it, **When** the catalog loads, **Then** it does not appear, whatever filter is selected.
7. **Given** the gallery, **When** it renders, **Then** dashboards are laid out as a card grid like Explore Category, and each card shows an icon that identifies its source, the name, type, source, description, tags, how long ago it was created, a favorite star and an **Execute** button.
8. **Given** the user clicks a card outside its buttons, **When** the detail opens, **Then** it shows the full description, the detail text, the list of parameters it accepts (label, data type, required) and the same Execute button and star.
9. **Given** no dashboard matches the current filters, **When** the gallery updates, **Then** an empty-state message says so.

---

### User Story 2 - Run a dashboard with parameter values (Priority: P1)

As any user, I want to enter the parameter values a dashboard needs in a window, then press Execute and get the dashboard or report opened with those values, so that I see the analytics for my case.

**Why this priority**: Running the dashboard is the reason the catalog exists; browsing alone delivers little value.

**Independent Test**: Sign in as a user who reaches a published dashboard with one list parameter, one required date parameter with a default, one optional number parameter and one parameter bound to the team grant the user came through. Press Execute, confirm the window shows the right controls and the bound value fixed, fill it in, run it, and confirm the dashboard opens with those values and one execution record is written.

**Acceptance Scenarios**:

1. **Given** a user presses Execute on a dashboard that has parameters to ask for, **When** the parameters window opens, **Then** it shows one field per parameter, labelled with the parameter's label, marking required ones, prefilled with the default value when there is one.
2. **Given** the user has run this dashboard successfully before, **When** the window opens, **Then** fields still start from the defaults, and a "use my last values" button fills them from their most recent successful run (grant-bound values excluded; values no longer valid fall back to the default).
3. **Given** a parameter with a list of allowed values, **When** the window renders, **Then** the field is a selector over that list's values, labelled in the current interface language.
4. **Given** a parameter entered by the viewer, **When** the window renders, **Then** the control fits its data type: text for String, numeric for Number, yes/no for Boolean, date picker for Date.
5. **Given** a grant-bound parameter and the user reached the dashboard through that bound grant, **When** the window renders, **Then** the value is the grant's recipient (e.g. team ANALYTICS), shown read-only and not editable.
6. **Given** a grant-bound parameter and the user reached the dashboard only through other grants, **When** the window renders, **Then** the value is asked for from the parameter's list if it has one, otherwise by free input, as for an unbound parameter.
7. **Given** a required field is empty or a value does not fit its data type (or is not in its list), **When** the user presses Execute, **Then** the run does not start and the field shows an inline error.
8. **Given** all values are valid, **When** the user presses Execute, **Then** the dashboard or report is invoked with those values and the window closes.
9. **Given** a dashboard has no parameters to ask for (none at all, or all are bound to the user's grant), **When** the user presses Execute, **Then** it runs straight away without showing the window.
10. **Given** the server re-checks the request, **When** a value is invalid, a required value is missing, or a bound value was tampered with, **Then** the run is refused with an explanatory message. The server never trusts a bound value sent by the browser.
11. **Given** the dashboard's source is Internal Page, **When** the invocation happens, **Then** it opens in a large viewer window over the catalog with the parameter values applied. The viewer shows the dashboard's name, the values used and an "open full page" link, and can be closed to return to the catalog where the user left it. Its loading is observed, so duration, Timeout and Cancelled apply; closing the viewer before the page finishes loading counts as Cancelled.
12. **Given** the dashboard's source is an external BI platform (Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Custom Iframe), **When** the invocation happens, **Then** it opens in a new browser tab at its location with the parameter values applied; the run counts as invoked once the tab is opened.
13. **Given** the browser blocks the new tab, **When** the invocation fails to open it, **Then** the user sees a message with a link to open it manually, and the run is recorded as Failed with that reason.

---

### User Story 3 - Every run is recorded (Priority: P1)

As the organization, I want each run to be recorded with who ran what, when, with which values, and how it ended, so that usage stays traceable and Usage Metrics can be built on it.

**Why this priority**: The user made traceability an explicit requirement, and HU-AN07 depends on it. A run that leaves no record is a defect.

**Independent Test**: Run dashboards successfully, with an invalid value rejected by the server, and on a dashboard the user lost access to; then inspect the execution records and confirm each attempt produced exactly one record with the expected status, values and timing.

**Acceptance Scenarios**:

1. **Given** a run is invoked successfully, **When** it completes, **Then** one execution record is stored with the dashboard, the user, the time, the parameter values used, status Success and the duration.
2. **Given** the user who runs it comes from the session, **When** the record is written, **Then** the user is never taken from the request body.
3. **Given** a user tries to run a dashboard they no longer hold a live grant to, or one that is no longer Published, **When** the server checks it, **Then** the run is refused and one record with status Unauthorized is stored.
4. **Given** the server rejects the values or the invocation fails, **When** the attempt ends, **Then** one record with status Failed and an error message is stored.
5. **Given** an Internal Page dashboard does not finish loading within 30 seconds, **When** the limit passes, **Then** the record is stored with status Timeout and the viewer tells the user the dashboard did not respond, keeping the "open full page" link. External BI tabs are never marked Timeout, because their loading cannot be observed.
6. **Given** the user closes the parameters window without pressing Execute, **When** it closes, **Then** one record with status Cancelled is stored, with the values present in the window at that moment and no error message. The same applies when the user closes the viewer before an Internal Page dashboard finishes loading.
7. **Given** the stored values, **When** the record is read later, **Then** for each parameter they show its name, the value used and where the value came from (grant, list, viewer input or default).

---

### User Story 4 - Favorite a dashboard from the catalog (Priority: P2)

As any user, I want to mark the dashboards I use most as favorites from the catalog, so that they are one click away.

**Why this priority**: It improves repeated use but the catalog and runs deliver value without it. Storage already exists.

**Independent Test**: Star a dashboard in the catalog, turn on "★ My favorites", confirm it is listed; open Dashboard Management (as an analyst) and confirm it is starred there too; unstar it with the toggle on and confirm it leaves the list without a reload.

**Acceptance Scenarios**:

1. **Given** a dashboard card or detail, **When** the user clicks the star, **Then** the dashboard is marked as favorite and the star fills.
2. **Given** the favorites toggle is on, **When** the user unstars a dashboard, **Then** it disappears from the gallery immediately, without a reload.
3. **Given** a favorite set in Dashboard Management, **When** the same user opens the catalog, **Then** it shows as favorite, and vice versa.
4. **Given** a user who only holds view access and the catalog privilege without edit rights, **When** they star a dashboard, **Then** it works: favoriting is consumption, not editing.

---

### Edge Cases

- A dashboard reaches the user through several grants (e.g. public and team). It appears once; each privilege option it matches shows it. If one of those grants is the bound grant of a parameter, the bound value applies.
- A parameter is bound to a grant that has since been revoked. The binding no longer applies; the parameter is asked for like an unbound one (list or input).
- A parameter's list has no values in the current language: values fall back to English, as everywhere else.
- A parameter's list is empty or inactive and the parameter is required: the window explains the dashboard cannot be run and no run starts; the attempt is recorded as Failed.
- The dashboard is archived or its grant revoked while the user has the window open: the server refuses on Execute and records Unauthorized.
- An Internal Page finishes loading after its run was already recorded as Timeout: the record stays Timeout (records are append-only) and the page is shown.
- "Use my last values" when the dashboard's parameters changed since that run: removed parameters are ignored, values no longer valid fall back to the default, new parameters keep their default.
- The user double-clicks Execute: only one run is started and one record written.
- A Boolean parameter that is not required and has no default: "not set" is a valid choice, distinct from "no".
- Dashboard detail text is long or contains markdown: it renders readably in the detail.
- Phone width (about 390 px): cards, filters and the parameters window remain usable without horizontal scrolling.
- The interface language changes while the catalog is open: list values in cards and the window follow it.

## Requirements *(mandatory)*

### Functional Requirements

**Catalog**

- **FR-001**: The system MUST provide a Dashboard Catalog page reachable from the Analytics sidebar option "Dashboard Catalog", available to every profile holding that option, whether or not it has edit rights.
- **FR-002**: The catalog MUST list only dashboards that are Published, active, and reached by at least one live grant of the user (View or Manage). Superusers see every published dashboard.
- **FR-003**: The catalog MUST offer a privileges filter with exactly six options — Public, Shared with me, My role, My team, My unit, My projects — with no "all" option, defaulting to Public, showing only dashboards shared with the user through the selected scope, matching Explore Category and Explore Initiatives.
- **FR-004**: The catalog MUST offer a "★ My favorites" toggle and a text search over name, description, tags, type and source, both combining with the privileges filter. The catalog MUST NOT add separate type or source selectors; HU-AN04's "filterable by type, source and tags" is met by the search box, which matches type and source in both interface languages.
- **FR-005**: Dashboards MUST be laid out as a card grid like Explore Category. Each card MUST show an icon identifying its source, name, type, source, description, tags, relative creation time, a favorite star and an Execute button. Clicking elsewhere on the card MUST open a read-only detail with the full description, the detail text and the parameter list (label, data type, required).
- **FR-006**: Visibility filtering MUST happen on the server before pagination, so a user never receives dashboards they cannot see.

**Execute**

- **FR-007**: Pressing Execute MUST open a parameters window listing every parameter whose value the user has to supply, unless there is none, in which case the run starts directly.
- **FR-008**: The window MUST render each parameter by its value source: a selector over the list's values (in the interface language) for list parameters; a control matching the data type (String, Number, Boolean, Date) for viewer input; a read-only value for a parameter bound to a grant the user reached the dashboard through.
- **FR-009**: Fields MUST be prefilled with the parameter's default value when it has one, and required fields MUST be marked.
- **FR-009a**: When the user has at least one Success execution of the dashboard, the window MUST offer a "use my last values" button. It fills the fields from the payload of the user's most recent Success execution of that dashboard, with these rules: grant-bound values are never taken from it (they are recomputed); a stored parameter that no longer exists is ignored; a stored value that no longer fits the parameter's data type or list falls back to the default; a parameter added since that run keeps its default. Without a previous Success execution, the button is not shown.
- **FR-010**: The window MUST validate before running: required values present, each value fits its data type, list values belong to the list. Invalid fields show inline errors and the run does not start.
- **FR-011**: The server MUST re-validate every run: live grant, Published status, required values, data types, list membership. It MUST compute grant-bound values itself and ignore any bound value sent by the client.
- **FR-012**: On a valid run the system MUST invoke the dashboard with the parameter values: an Internal Page opens in a closable viewer window over the catalog (name, values used, "open full page" link); every external BI source opens in a new browser tab. If the browser blocks the tab, the user gets a link to open it manually.
- **FR-013**: Executing MUST require only view access to the dashboard and the catalog privilege; edit rights are not needed.
- **FR-014**: A run MUST be started at most once per press of Execute (no duplicate runs from double clicks).

**Execution record**

- **FR-015**: Every run attempt — including a parameters window closed without executing — MUST produce exactly one execution record with: dashboard, user (from the session), timestamp, payload, status, duration and, when it did not succeed, an error message.
- **FR-016**: The payload MUST record, per parameter, its name, the value used and its source (grant, list, viewer input, default).
- **FR-017**: Status MUST be one of the existing execution statuses: Success (invoked), Failed (rejected values or invocation error), Unauthorized (no live grant or not Published), Timeout (an Internal Page that does not finish loading within 30 seconds), Cancelled (parameters window closed without executing, or the viewer closed before the Internal Page finished loading).
- **FR-018**: Execution records MUST be append-only: never edited or deleted from the application.

**Favorite**

- **FR-019**: Users MUST be able to mark and unmark a dashboard as favorite from its card and its detail, holding only view access.
- **FR-020**: Catalog favorites MUST be the same favorites shown in Dashboard Management.
- **FR-021**: With the favorites toggle on, unmarking a favorite MUST remove it from the gallery immediately, without a reload.

**General**

- **FR-022**: Every user-facing text MUST exist in English and Spanish and follow the language switcher, including list values.
- **FR-023**: The catalog and the parameters window MUST be usable at phone width without horizontal scrolling.

### Key Entities

- **Dashboard**: a registered dashboard or report (name, description, type, source, location, status, tags, detail). Only Published ones reach the catalog.
- **Parameter**: an input a dashboard accepts (name, label, data type, required, default, optional list, optional grant binding). Its value source — grant, list or viewer input — decides how the window asks for it.
- **Dashboard Grant**: view or manage access for a user, role, team, unit, project or everyone, live from when it is given until revoked. Visibility, the privileges filter and grant-bound values all derive from it.
- **Execution**: one run attempt — who, which dashboard, when, with which values and their sources, outcome status, duration, error message.
- **Favorite Dashboard**: a user's mark on a dashboard, shared between the catalog and Dashboard Management.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the six privilege options, the catalog shows exactly the published dashboards shared with the user through that scope, verified with a user whose grants cover each scope; no draft, archived, retired or ungranted dashboard ever appears.
- **SC-002**: A user can go from opening the catalog to a running dashboard with parameters filled in under 1 minute when defaults cover most fields.
- **SC-003**: 100% of run attempts, including abandoned parameters windows, produce exactly one execution record with the correct user, dashboard, values, value sources and status.
- **SC-004**: No run starts with a missing required value, a value of the wrong type, a value outside its list, or a tampered grant-bound value — verified for each case.
- **SC-005**: Users with view-only access and no edit rights can browse, favorite and execute; verified as a collaborator.
- **SC-006**: A favorite set in either the catalog or Dashboard Management shows in the other on the next load.
- **SC-007**: Search and filter changes update the gallery in under 1 second for catalogs of up to 200 dashboards.

## Assumptions

- **Published only.** The catalog shows Published dashboards; Archived and Retired are hidden, consistent with the lifecycle defined in SpecKit 006 ("status decides whether a dashboard shows up in the Catalog").
- **Same filter behaviour as the Explore pages.** Search, favorites and the privileges filter (default Public, one scope at a time, no "all") behave exactly as in Explore Category and Explore Initiatives. HU-AN04's "filterable by type, source and tags" is covered by the search box matching those fields; no separate type/source dropdowns are added.
- **No votes, discussion or history on dashboards.** The analytics module has no such substrate and the user did not ask for it.
- **Who can browse and run.** Every profile holding the Dashboard Catalog option (today Administrator, Administrative, Collaborator, Reviewer). Collaborator and Reviewer hold it without edit rights; executing and favoriting are consumption, so they are not gated on edit rights.
- **Grant binding rule** is the one defined in SpecKit 006: the binding applies only when the user reaches the dashboard through the bound grant; otherwise the value is asked for (list if any, else free input).
- **What "Success" means.** The platform cannot observe whether an external BI tool rendered its data correctly. For an external source, Success means the run passed every check and its tab was opened. For an Internal Page, it means the page finished loading.
- **Duration** is measured from pressing Execute to the Internal Page finishing loading, or to the external tab being opened. For a Cancelled record it is the time the window (or the loading page) stayed open.
- **Parameter values are passed to the dashboard's location** in the form the location accepts (query parameters on its address); per-vendor embed APIs and authentication tokens for BI platforms are out of scope.
- **The user's own execution history and usage dashboards** are out of scope; HU-AN07 Usage Metrics will read the records.
- **No new tables are expected**: dashboards, parameters, grants, favorites and executions already exist, and the execution statuses are seeded.
