# Feature Specification: Collab Projects CRUD with Team Filter

**Feature Branch**: `001-collab-projects`  
**Created**: 2026-03-25  
**Status**: Draft  
**Input**: User description: "Implementa la historia de usuario de projects dentro del módulo de collab, debe ser similar a la historia de usuario de options del módulo admin pero en lugar de tener un filtro por module que lo tenga por team"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - List and Filter Projects by Team (Priority: P1)

As a collaboration team member, I want to view all projects in a table and filter them by team so that I can quickly find the projects that belong to a specific team.

**Why this priority**: Viewing and filtering is the primary read operation and the most frequently used action. It mirrors the options list with module filter and provides the core value of this feature — navigating projects organized by team.

**Independent Test**: Can be fully tested by navigating to the projects page, seeing all active projects in a table, selecting a team from the filter dropdown, and confirming only that team's projects are shown.

**Acceptance Scenarios**:

1. **Given** the user navigates to the projects page, **When** the page loads, **Then** a table displays all active projects with columns: code, name, team, status, start date, end date — ordered by team and then by name.
2. **Given** the projects table is displayed, **When** the user selects a team from the filter dropdown, **Then** only projects belonging to that team are shown in the table.
3. **Given** the user has filtered by a team, **When** the user clears the filter (selects blank option), **Then** all active projects are shown again.
4. **Given** there are no projects for a selected team, **When** the user filters by that team, **Then** the table shows an empty state with no error.

---

### User Story 2 - Create a New Project (Priority: P1)

As a collaboration team member, I want to create a new project associated with a team so that I can register and track new initiatives within the organization.

**Why this priority**: Creating projects is the fundamental write operation. Without it, there is no data to list or manage. It is equally critical as listing.

**Independent Test**: Can be fully tested by clicking the create button, filling in the form fields (code, name, team, status, etc.), submitting, and verifying the new project appears in the projects table.

**Acceptance Scenarios**:

1. **Given** the user is on the projects page, **When** the user clicks the create button, **Then** a modal form opens with fields: code, name, description, team (dropdown populated from teams list), status (dropdown with project status options), repo URL, start date, end date.
2. **Given** the create form is open, **When** the user fills all required fields (code, name, status) and submits, **Then** the project is created and appears in the table.
3. **Given** the create form is open, **When** the user submits with an existing project code, **Then** a conflict error is shown and the project is not created.
4. **Given** the create form is open, **When** the user selects a team from the dropdown, **Then** the team value must correspond to an existing team.
5. **Given** the create form is open, **When** the user leaves required fields empty and submits, **Then** validation errors are displayed and the form is not submitted.

---

### User Story 3 - Edit an Existing Project (Priority: P2)

As a collaboration team member, I want to edit an existing project's details so that I can keep project information up to date as it evolves.

**Why this priority**: Editing ensures data accuracy over time. It depends on having projects to edit (US1/US2) but is essential for ongoing project management.

**Independent Test**: Can be fully tested by clicking edit on a project row, modifying fields, submitting, and verifying the changes are reflected in the table.

**Acceptance Scenarios**:

1. **Given** a project exists in the table, **When** the user clicks the edit action on that row, **Then** an edit modal opens pre-populated with the project's current data.
2. **Given** the edit form is open, **When** the user changes the name and status and submits, **Then** the project is updated and the table reflects the changes.
3. **Given** the edit form is open, **When** the user changes the team to another valid team, **Then** the update succeeds and the project now belongs to the new team.
4. **Given** the edit form is open, **When** the user clears a required field and submits, **Then** validation prevents the update.

---

### User Story 4 - Delete a Project (Priority: P2)

As a collaboration team member, I want to deactivate a project so that obsolete or cancelled projects no longer appear in the active list.

**Why this priority**: Deletion (logical deactivation) is needed to keep the project list clean, but is less frequent than creating or editing.

**Independent Test**: Can be fully tested by clicking delete on a project row, confirming the action, and verifying the project no longer appears in the active projects table.

**Acceptance Scenarios**:

1. **Given** a project exists in the table, **When** the user clicks the delete action on that row, **Then** a confirmation dialog/modal appears asking the user to confirm deletion.
2. **Given** the delete confirmation is shown, **When** the user confirms, **Then** the project is logically deactivated (is_active set to false) and disappears from the active list.
3. **Given** the delete confirmation is shown, **When** the user cancels, **Then** no changes are made and the project remains in the list.

---

### User Story 5 - Navigate to Projects from Teams (Priority: P3)

As a collaboration team member, I want a detail/link action on the teams page that navigates to the projects page filtered by that team so that I can quickly see all projects for a specific team.

**Why this priority**: This master-detail navigation pattern improves workflow efficiency but is a convenience feature on top of the core CRUD and filter functionality.

**Independent Test**: Can be fully tested by clicking the detail action on a team row, verifying that the projects page opens with the team filter pre-selected.

**Acceptance Scenarios**:

1. **Given** the user is on the teams page, **When** the user clicks a "detail" or "projects" action on a team row, **Then** the browser navigates to the projects page with the team filter pre-applied for that team.
2. **Given** the user arrives at projects via a team detail link, **When** the page loads, **Then** only projects belonging to that team are shown and the filter dropdown reflects the selected team.
3. **Given** the user is on the filtered projects page from a team link, **When** the user clears the filter, **Then** all active projects are shown.

---

### Edge Cases

- What happens when a project is created without selecting a team? The team field is optional, so the project is created with a null team and appears when no filter is applied but not under any specific team filter.
- How does the system handle deleting a team that still has projects assigned to it? The projects retain their team reference; the system does not cascade-delete. Projects with a deleted (inactive) team remain visible but their team may show as inactive.
- What happens when two users create a project with the same code simultaneously? The first succeeds; the second receives a conflict error (409).
- How does the system handle filtering when a team code passed via URL parameter does not exist? The filter dropdown shows no match; the table displays no filtered results. No error is thrown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a projects page under the Collaboration section accessible via the application navigation.
- **FR-002**: System MUST display all active projects (is_active=true) in a data table with columns: code, name, team, status, start_date, end_date.
- **FR-003**: System MUST provide a team filter dropdown populated from the list of active teams, allowing users to filter the projects table by team.
- **FR-004**: System MUST allow users to create new projects via a modal form with fields: code (required, text), name (required, text), description (optional, textarea), team (optional, select from teams), status (required, select from project status list), repo_url (optional, text), start_date (optional, date), end_date (optional, date).
- **FR-005**: System MUST validate that the project code is unique when creating a new project and display a conflict error if it already exists.
- **FR-006**: System MUST validate that the selected team exists when creating or updating a project with a team value.
- **FR-007**: System MUST allow users to edit existing projects via a modal form pre-populated with current values. Only changed fields are sent for update.
- **FR-008**: System MUST allow users to logically delete a project (set is_active to false) with a confirmation prompt. Deleted projects no longer appear in the active list.
- **FR-009**: System MUST display toast notifications for successful create, update, and delete operations, as well as for errors.
- **FR-010**: System MUST support a master-detail navigation from the teams page to the projects page, pre-filtering by the selected team.
- **FR-011**: System MUST order the projects list by team and then by name by default.
- **FR-012**: System MUST support pagination parameters (skip and limit) for the projects list endpoint.

### Compatibility & Deployment Requirements

- **CR-001**: The existing projects API endpoints (GET/POST/PUT/DELETE on `/api/projects`) already exist in the backend. The UI MUST consume these existing endpoints without backend modifications, unless the current endpoints lack team-based filtering query parameters — in which case the backend MUST be extended to support an optional `team` query parameter on the list endpoint.
- **CR-002**: No new database schema changes are required. The `projects` table already exists with the `team` foreign key to `teams`. No migration is needed.
- **CR-003**: No new environment variables are required. The feature uses the existing API base URL and authentication configuration.

### Security & Performance Requirements

- **SPR-001**: All projects endpoints MUST require a valid JWT Bearer token. The existing authentication middleware already covers `/api/projects` routes. No new roles or scopes are introduced — all authenticated users can manage projects.
- **SPR-002**: No secrets or sensitive data are involved in the projects entity. No special handling beyond the existing transport encryption is needed.
- **SPR-003**: The projects list endpoint MUST support pagination (skip/limit) with a default limit of 100 records. The team filter SHOULD be applied server-side when the optional `team` query parameter is provided, or client-side via the DataTable column filter to match the options pattern.

### Key Entities

- **Project**: Represents a work initiative within the collaboration module. Key attributes: code (unique identifier), name, description, team (which team owns it), status (lifecycle state from PROJECT_STATUS list: PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED), repo URL, start/end dates, active flag. Belongs to a Team.
- **Team**: An existing entity representing a collaboration group. Key attributes: code (unique identifier), name, description, lead (user). A team has zero or many projects.
- **Project Status**: A set of predefined status values sourced from the PROJECT_STATUS list: PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED. Used to track the lifecycle of a project.

## Assumptions

- The projects backend API already exists with full CRUD (POST, GET, GET by code, PUT, DELETE on `/api/projects`). This feature primarily adds the UI page that consumes it.
- The team filter will be implemented client-side following the same DataTable `columnFilter` pattern used by the options page with modules, unless the backend already supports a `team` query parameter for server-side filtering.
- The project status dropdown options will be sourced from the existing `PROJECT_STATUS` list in the `list_items` table (values: PLANNED, IN_PROGRESS, ON_HOLD, COMPLETED).
- The breadcrumb navigation will follow the existing pattern: Collaboration > Projects.
- The projects page will follow the same UI patterns (CrudModal, DataTable, Toast) used by the admin/options page and the collab/teams page.
- The detail action on the teams page (currently linking to assignments) will either be changed to link to projects, or a second detail action will be added for projects.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view, create, edit, and delete projects from the projects page within the same interaction patterns established by the options page (under 30 seconds per operation).
- **SC-002**: Users can filter the projects table by team in a single click, reducing visual clutter to only relevant projects.
- **SC-003**: Users can navigate from a team on the teams page to its associated projects in one click, with the filter pre-applied.
- **SC-004**: 100% of CRUD operations on projects produce visible feedback (success toast or error message) within 2 seconds of submission.
- **SC-005**: The projects page loads and displays all active projects within 3 seconds under normal conditions (up to 200 projects).
