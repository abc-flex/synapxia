# Feature Specification: Dashboard Management

**Feature Branch**: `006-dashboard-management`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "quiero que trabajemos en la historia de usuario de Dashboard Management que incluye Parameters y Permission"

**Amended** 2026-10-02 at the user's request, with three changes:
- Favorites are added, the same as in Asset Management and Initiative Management.
- The Permissions tab no longer shows or asks for validity dates; they are handled internally.
- The Parameters tab's form is compacted so the declared parameters stay in view.

Covers user stories **HU-AN01 Dashboard Management**, **HU-AN02 – Parameters** and **HU-AN03 – Permission** (see `docs/user-stories/06-ana.md`). It also covers the management-side half of **HU-AN06 Favorite**: marking a dashboard as a favorite from this screen and filtering by it. The other consumption stories, **HU-AN04 Dashboard Catalog**, **HU-AN05 Execute** and **HU-AN07 Usage Metrics**, are out of scope and will be specified separately. When the Catalog is built, it reuses the same favorites.

## Problem Context

The organization's analytics live in many places: internal pages, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset and ad-hoc embedded iframes. Nobody has one governed place that says which dashboards exist, what each one is for, which inputs it expects, and who is allowed to open it. The platform already stores this information as data (three dashboards, their parameters and their access grants are seeded) but there is no screen where analysts can register a new dashboard or keep an existing one accurate.

The platform has already solved the equivalent problem twice: **Asset Management** (AI Library) and **Initiative Management**. Both offer a filterable list of the records a person can access and an edit dialog organised in tabs, each tab saving its own slice. Analysts expect the same experience. Dashboards differ from assets and initiatives in three ways that shape this feature:

1. **They are created by hand.** Unlike initiatives, an analyst registers a dashboard directly. There is no propose/review workflow.
2. **They declare inputs.** Each dashboard carries a list of parameters (name, label, data type, required flag, default value, allowed values, context binding) that the future Catalog/Execute stories will use to filter it and bind it to the viewer's context at run time.
3. **Their audience is sensitive.** Analytics often expose figures that only some people should see. Access is granted per dashboard to users, roles, projects, teams, units or everyone, exactly as for assets and initiatives. As there, the system manages a grant's validity: the grant starts when it is given and ends when it is revoked.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register and maintain dashboards (Priority: P1)

As an analyst, I want a list of the dashboards I have access to, filterable by type, source, status, tags and my access level and searchable by name, and I want to register a new dashboard or edit the core fields of an existing one, so that the organization has one governed place to publish its analytics.

**Why this priority**: Everything else in this feature hangs off a dashboard record. On its own, this story already gives the organization its first governed inventory of analytics.

**Independent Test**: Sign in as an analyst who manages some dashboards and only views others. Open Dashboard Management and confirm that exactly the accessible dashboards appear and each filter narrows the list. Create a dashboard, then confirm it appears in the list and that its creator can manage it. Edit its core fields, save, and confirm the changes persisted.

**Acceptance Scenarios**:

1. **Given** a user holds manage or view access to some dashboards and none to others, **When** they open Dashboard Management, **Then** only the dashboards they can access are listed, with the columns name, type, source, status, tags and actions (in that order). The actions include a favorite star on every row.
2. **Given** the list is open, **When** the user filters by one or more of type, source, status, privileges (how the dashboard is shared with them) or "my favorites", **Then** only dashboards matching every selected filter remain, and the visible count reflects the filtered set.
3. **Given** the list is open, **When** the user types part of a dashboard's name in search, **Then** matching dashboards remain and the rest are hidden.
4. **Given** a user with permission to manage dashboards, **When** they choose "New Dashboard", fill in name, type, source, source location and (optionally) description, tags and detail, and save, **Then** the dashboard is created in Draft status and the creator automatically holds manage access to it.
5. **Given** a user manages a dashboard, **When** they open it, **Then** an edit dialog opens with three tabs in this order: Core Fields, Parameters, Permissions; Core Fields is shown first.
6. **Given** the Core Fields tab is open, **When** the user edits name, description, type, source, source location, tags or detail and saves, **Then** only those fields are persisted, and the other tabs' pending edits are neither saved nor discarded.
7. **Given** a required field (name, type, source, source location) is empty or the source location is not valid for the chosen source, **When** the user tries to save, **Then** the save is blocked and the field is flagged.
8. **Given** a user has view-only access to a dashboard, **When** it appears in the list, **Then** its row offers no edit or remove affordance, and opening it shows every tab read-only.
9. **Given** a user manages a dashboard, **When** they remove it and confirm, **Then** it disappears from the list but the record (and its parameters and grants) is retained.
10. **Given** a user has no access to any dashboard, **When** they open Dashboard Management, **Then** they see an explanatory empty state, plus the "New Dashboard" action if they are allowed to create.
11. **Given** a platform superuser opens Dashboard Management, **When** the list loads, **Then** every active dashboard is listed, regardless of grants.
12. **Given** a user can access a dashboard (manage or view), **When** they click its star in the list, **Then** it is saved immediately as one of their favorites (or removed from them), and an active "my favorites" filter updates at once, without reloading.
13. **Given** a dashboard's dialog is open, **When** the user clicks the star in its header, **Then** the favorite is saved immediately, and the list's star and "my favorites" filter reflect it when the dialog closes.
14. **Given** a dashboard is one user's favorite, **When** another user opens the list, **Then** it is not marked as their favorite: favorites are personal.

---

### User Story 2 - Control a dashboard's lifecycle status (Priority: P1)

As an analyst, I want to move a dashboard through its lifecycle (Draft, Published, Archived, Retired) so that only finished dashboards are offered to consumers and obsolete ones stop being offered without losing their record.

**Why this priority**: Status is what will later decide whether a dashboard shows up in the Catalog. Without a controlled lifecycle, half-built or obsolete dashboards would reach consumers.

**Independent Test**: Create a dashboard, which starts in Draft. Move it through every allowed transition and confirm each is accepted. Then attempt every disallowed transition, both in the dialog and directly against the system, and confirm each is refused and nothing changes.

**Acceptance Scenarios**:

1. **Given** a dashboard is being created, **When** the Core Fields tab is shown, **Then** the status is Draft and cannot be changed until the dashboard exists.
2. **Given** a dashboard in a given status, **When** the owner opens its Core Fields tab, **Then** the status control offers only the current status and the statuses allowed from it: Draft → Published; Published → Archived or Retired; Archived → Published or Retired. Retired is final.
3. **Given** a status change outside the allowed set is requested, through the dialog or directly against the system, **When** it is processed, **Then** it is refused with a clear message and nothing is changed.
4. **Given** a dashboard is Retired, **When** the owner opens it, **Then** the status control is locked with a short explanation that the dashboard is closed; Core Fields, Parameters and Permissions remain readable.
5. **Given** a dashboard is moved to Published, **When** it has a required parameter with no default value and no grant binding, **Then** the change is still allowed (the viewer supplies the value at run time through the parameters window of the Execute story).
6. **Given** a Retired dashboard, **When** any status change is requested, **Then** it is refused.

---

### User Story 3 - Declare a dashboard's parameters (Priority: P2)

As an analyst, I want to declare the parameters a dashboard accepts (name, label, data type, required flag, default value, an optional list of allowed values and a context binding) so that it can be filtered and bound to the viewer's context at run time.

**Why this priority**: Parameters are only consumed by the future Execute story, but they must be declared and correct before that story can deliver value. They depend on Story 1's editing surface.

**Independent Test**: Open a dashboard the user manages, go to the Parameters tab, add a parameter of each data type, mark one required with a default, give one a list of allowed values, edit one, remove one, and save. Reopen and confirm the tab shows exactly the saved set and that no other tab changed.

**Acceptance Scenarios**:

1. **Given** the Parameters tab is open, **When** the dashboard has parameters, **Then** they are listed with name, label, data type, required flag, default value, allowed-values list and context binding.
2. **Given** the Parameters tab is open, **When** the user adds a parameter with a name, a label and a data type (String, Number, Boolean or Date), plus optionally a required flag, a default value, an allowed-values list and a context binding, and saves, **Then** the parameter is stored for that dashboard.
3. **Given** a parameter name already used by an active parameter of the same dashboard, **When** the user tries to add it again, **Then** the addition is refused with a clear message.
4. **Given** a parameter whose name was used before and then removed, **When** the user adds a parameter with that name again, **Then** the removed parameter is restored with the new values rather than duplicated.
5. **Given** a default value is entered, **When** it does not match the parameter's data type (e.g. text for a Number, an invalid date for a Date), or is not one of the allowed values when a list is chosen, **Then** the save is blocked and the field is flagged.
6. **Given** the user chooses an allowed-values list, **When** they pick a default, **Then** the default is chosen from that list's values (in the current language) rather than typed freely.
7. **Given** an existing parameter, **When** the user edits its label, data type, required flag, default, allowed-values list or context binding and saves, **Then** the changes persist; the parameter name itself cannot be renamed (remove and re-add instead).
8. **Given** an existing parameter, **When** the user removes it and saves, **Then** it no longer appears in the tab, but the record is retained.
9. **Given** the user edits a parameter, **When** they choose how its value is obtained at run time, **Then** they choose exactly one of three sources: **bound to a grant** (the value is fixed to the recipient of one of the dashboard's grants), **from a list** (the viewer picks one of the allowed-values list's values), or **entered by the viewer** (free input validated against the data type). The editor makes the active source explicit.
10. **Given** a parameter is bound to a grant, **When** the tab is shown, **Then** the binding is displayed in plain language, e.g. "Bound to the grant for team ANALYTICS: value fixed to ANALYTICS for viewers who reach the dashboard through it".
11. **Given** the user binds a parameter to a grant, **When** they pick the grant, **Then** only the same dashboard's live grants to a user, role, project, team or unit are offered (a public grant has no recipient value to bind).
12. **Given** a dashboard with declared parameters is open on the Parameters tab, **When** the tab is shown at the dialog's normal size, **Then** the add/edit form is compact enough that part of the declared parameters list is visible below it without scrolling.

---

### User Story 4 - Grant and revoke access to a dashboard (Priority: P2)

As a dashboard owner, I want to grant view or manage access to users, roles, projects, teams, units or everyone, and to revoke it, so that sensitive analytics reach only their intended audience.

**Why this priority**: Access control is what makes the inventory safe to open to consumers later. It reuses the experience users already know from Asset Management and Initiative Management.

**Independent Test**: Open a dashboard the user manages, grant view access to another user and manage access to a team, and save. Sign in as each recipient and confirm the dashboard appears in their list with the right access level. Revoke one grant and confirm the recipient loses access while the grant stays recorded as ended.

**Acceptance Scenarios**:

1. **Given** the Permissions tab is open, **When** the dashboard has grants, **Then** its live grants are listed with recipient type, recipient and access level (View or Manage), exactly as in Asset Management and Initiative Management. Revoked grants are not listed, and no dates are shown.
2. **Given** the Permissions tab is open, **When** the user grants View or Manage to a user, role, project, team, unit or everyone and saves, **Then** the grant is stored and takes effect immediately. The tab asks for no dates, because the system manages a grant's validity.
3. **Given** a live grant, **When** the user revokes it and saves, **Then** the grant is kept as a record ending now rather than deleted, and the recipient loses the access it gave.
4. **Given** an identical live grant (same recipient and access level) already exists, **When** the user adds it again, **Then** it is refused with a clear message; a revoked one does not block re-granting.
5. **Given** a user holds both a view grant and a manage grant that reach them, **When** their access is resolved, **Then** manage wins.
6. **Given** a grant is used as a parameter's context binding, **When** the user revokes it, **Then** they are warned that the binding will stop applying, and the parameter keeps working without it.
7. **Given** the owner revokes their own manage access, **When** they save, **Then** they are warned first that they will lose edit access, and the dashboard may drop out of their list afterwards.

---

### Edge Cases

- **Dashboard whose status, type or source value is not in the known lists** (e.g. legacy data): it still lists and opens; the unknown value is shown as-is and the status control is locked.
- **Source location for an Internal Page**: it is a path inside the platform, not an external web address; every other source requires a secure (https) web address.
- **Many dashboards or many parameters**: the list stays responsive and does not silently truncate.
- **Allowed-values list later deactivated or emptied by an administrator**: existing parameters keep showing the list by code; the default stays as stored.
- **Parameter data type changed after a default was set**: the default is re-validated against the new type before saving.
- **Grant with a future start or an end date set outside this screen** (seed data, direct API use): it is listed like any live grant and only takes effect inside its window. The tab neither shows nor edits the dates.
- **Two owners edit the same tab concurrently**: the last save wins for core fields. For parameters and grants, each addition or removal is evaluated against the current state, so a duplicate is refused.
- **Removed dashboard**: no longer listed. Its parameters and grants are retained but have no effect.
- **Language switch**: type, source, status, parameter data type, recipient type and access level labels follow the header language switcher.

## Requirements *(mandatory)*

### Functional Requirements

**List (Dashboard Management)**

- **FR-001**: The system MUST provide a Dashboard Management screen, reachable from the existing "Dashboard Management" navigation option, listing the active dashboards the current user can access.
- **FR-002**: A user MUST only see dashboards on which they hold a currently valid view or manage grant, either directly or through their role, project, team, unit or a public grant; superusers MUST see all active dashboards.
- **FR-003**: The list MUST show, per dashboard, the columns name, type, source, status, tags and actions, in that order.
- **FR-004**: The list MUST support filtering by type, source, status, privileges and favorites, and searching by name; filters combine. The privileges filter MUST work as in Asset Management: All privileges, Shared with me, My role, My team, My unit, My projects and Public.
- **FR-004a**: The actions column MUST include a favorite star on every listed dashboard (manage or view access), and the dialog header MUST show the same star. Toggling either MUST save the current user's favorite immediately, as in Asset Management and Initiative Management. Favorites are personal, are kept as records (removing one is logical), and require view access to the dashboard.
- **FR-005**: Edit and remove affordances MUST only be offered on dashboards the user can manage; view-only dashboards MUST open read-only.
- **FR-006**: Removing a dashboard MUST be a logical removal (the record is retained and hidden), available only to users who manage it, after confirmation.
- **FR-007**: The list MUST NOT silently truncate when the number of dashboards exceeds a single page.

**Core Fields**

- **FR-008**: Users holding the Dashboard Management privilege with edit rights MUST be able to create a dashboard with name (required, at most 100 characters), description (optional, at most 500), type (required, from the dashboard type list), source (required, from the source type list), source location (required), tags (optional, free list) and detail (optional, long text).
- **FR-009**: A new dashboard MUST start in Draft status, and its creator MUST automatically receive a manage grant on it.
- **FR-010**: The source location MUST be validated against the chosen source: an internal platform path for Internal Page, a secure (https) web address for every other source.
- **FR-011**: Saving the Core Fields tab MUST persist only core fields.

**Status lifecycle**

- **FR-012**: Status changes MUST be limited to the allowed transitions (see User Story 2, scenario 2), enforced by the system and not only by the screen. Disallowed changes are refused with a clear message and change nothing.
- **FR-013**: The status control MUST offer only the current status and the statuses allowed from it, and MUST be locked with an explanation when no transition is allowed.

**Parameters**

- **FR-014**: Users who manage a dashboard MUST be able to add, edit and remove its parameters from a Parameters tab; saving that tab MUST persist only parameters.
- **FR-015**: Each parameter MUST have a name unique within its dashboard (required, at most 100 characters, not renamable), a label (required, at most 100), a data type (required: String, Number, Boolean or Date), a required flag (default off), and optionally a default value, an allowed-values list chosen from the platform's administered lists, and a context binding.
- **FR-016**: A default value MUST be valid for the parameter's data type and, when an allowed-values list is chosen, MUST be one of that list's values.
- **FR-017**: Removing a parameter MUST be a logical removal; re-adding a removed name MUST restore it with the new values.
- **FR-018**: Each parameter MUST declare how its value is obtained at run time, as exactly one of: (a) **grant binding**: the context binding references one of the same dashboard's grants to a user, role, project, team or unit, and the value is that grant's recipient; (b) **list**: there is no context binding, an allowed-values list is set, and the viewer picks a value from it; (c) **viewer input**: there is neither a binding nor a list, and the viewer enters a value valid for the data type.
- **FR-018a**: For sources (b) and (c), and for a grant-bound parameter when the viewer's access does not come through the bound grant, the value MUST be requested from the viewer in a parameters window before the dashboard runs, prefilled with the default when there is one. That window and the run itself belong to the Execute story (HU-AN05, out of scope). This feature declares, validates and displays the source.

**Permissions**

- **FR-019**: Users who manage a dashboard MUST be able to grant View or Manage access to a user, role, project, team, unit or everyone from a Permissions tab; saving that tab MUST persist only grants. The tab MUST look and behave like the Permissions tabs of Asset Management and Initiative Management: recipient type, recipient and access level, with no validity dates shown or asked for. A grant given here starts immediately and has no end until it is revoked.
- **FR-020**: Revoking a grant MUST end it now and keep it as a record. Grants are never deleted.
- **FR-021**: Access resolution MUST honour each grant's (internally managed) validity window and recipient scope, MUST let Manage win over View, and MUST behave identically to asset and initiative permissions.
- **FR-022**: Every write to a dashboard (core fields, status, parameters, grants, removal) MUST require a live manage grant (or superuser), checked by the system and not only hidden in the screen.

**General**

- **FR-023**: Every user-facing label and message MUST be available in English and Spanish, and list values MUST follow the header language switcher.
- **FR-024**: Unsaved edits in a tab MUST prompt for confirmation before the dialog is closed.

### Key Entities

- **Dashboard**: a governed analytics artifact. It has a name, description, type (Dashboard, Report, Scorecard, KPI View, Analytical View), source (Internal Page, Power BI, Looker Studio, Tableau, Qlik Sense, Metabase, Superset, Custom Iframe), source location, lifecycle status (Draft, Published, Archived, Retired), tags and a long-form detail. It is logically removable.
- **Parameter**: an input a dashboard accepts, identified by its name within the dashboard. It has a label, data type (String, Number, Boolean, Date), required flag, optional default and a value source: bound to one of the dashboard's grants (context binding), picked from an allowed-values list (an administered platform list), or entered by the viewer. It is logically removable.
- **Dashboard Permission (grant)**: an access grant on one dashboard to a recipient (user, role, project, team, unit or everyone), at View or Manage level. Its validity (a start and an optional end) is managed by the system: it starts when given and ends when revoked. It is never deleted.
- **Favorite dashboard**: a user's personal mark on a dashboard they can access, kept per (user, dashboard). Removing it is logical, and marking it again restores it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An analyst can register a new dashboard with its core fields in under 2 minutes.
- **SC-002**: An analyst can declare a dashboard with 4 parameters in under 3 minutes.
- **SC-003**: 100% of the seeded dashboards, parameters and grants are visible and editable by their managers from the new screen, with no data correction needed.
- **SC-004**: 0 dashboards are visible to a user without a live grant, and 0 write attempts by a user without manage access succeed, verified by automated tests across every recipient type.
- **SC-005**: 100% of disallowed status transitions and invalid parameter defaults are refused, whether attempted from the screen or directly.
- **SC-006**: The list opens and filters without noticeable delay with 500 dashboards.

## Assumptions

- **Analyst = holder of the Dashboard Management privilege with edit rights.** Today that is the Administrator and Administrative profiles. Collaborator and Reviewer hold only the Catalog privilege and therefore do not reach this screen.
- **The list is grant-scoped, as in Asset Management and Initiative Management.** Holding the privilege opens the screen; per-dashboard grants decide which dashboards appear. Because a creator receives manage access automatically, a new dashboard never becomes invisible to the person who made it.
- **No activity history or discussion on this screen.** Dashboards have no activity log in the data model; a History tab may be added later.
- **Favorites are stored in the analytics module's own favorites table** (`favorite_dashboards`). It is the counterpart of the favorites tables of Asset Management (`favorites`) and Initiative Management (`favorite_inits`), which can only hold assets and initiatives respectively. The future Catalog (HU-AN04/HU-AN06) shows the same favorites.
- **No preview or embedding in this feature.** Opening or running the dashboard (and recording executions) belongs to HU-AN05 Execute.
- **Source location is stored, not probed.** The system validates its format but does not check that the external dashboard is reachable.
- **The permission behaviour is shared**: it reuses the same rules as asset and initiative grants (internally managed validity, revoke-not-delete, Manage beats View, same recipient types), so users see one consistent model.
- **A grant binding applies only to viewers who reach the dashboard through the bound grant.** A viewer who reaches it through another grant (e.g. a public one) is asked for the value in the parameters window: from the allowed-values list if the parameter has one, otherwise by free input. A bound parameter may therefore also carry a list for that fallback; that is the analyst's choice.
- **Seed data**: the seeded dashboards' parameters have no context binding yet, and the analytics lists (type, source, status, parameter type) are English-only. Spanish labels are expected to be added as part of this feature, consistent with the system-wide list-language rule.
