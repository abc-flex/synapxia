# Feature Specification: Collab Dimensions CRUD with Metrics Master-Detail

**Feature Branch**: `002-collab-dimensions-metrics`  
**Created**: 2026-04-03  
**Status**: Draft  
**Input**: User description: "construye la historia de usuario de dimensions dentro del módulo de collab, debe ser similar a la historia de usuario de roles del módulo admin pero en lugar de tener un maestro detalle a privileges que lo tenga a metrics"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List and Manage Dimensions (Priority: P1)

As a collaboration team member, I want to view all dimensions in a table and perform CRUD operations on them so that I can define and maintain the measurement dimensions used for analysis across teams and assignments.

**Why this priority**: Dimensions are the master catalog that backs the metrics detail. Without dimensions, there is nothing to measure. Viewing and managing dimensions is the core value of this feature and the prerequisite for all downstream metrics work.

**Independent Test**: Can be fully tested by navigating to the dimensions page, seeing all active dimensions in a table, and creating, editing, and deleting dimension records independently of the metrics page.

**Acceptance Scenarios**:

1. **Given** the user navigates to the dimensions page, **When** the page loads, **Then** a table displays all active dimensions with columns: code, name, scale, unit — ordered by name.
2. **Given** the dimensions table is displayed, **When** the user clicks the create button, **Then** a modal form opens with fields: code (required), name (required), description (optional), scale (optional, select from lists), unit (optional, select from DIMENSIONS_UNIT list).
3. **Given** the create form is filled with a unique code and required fields, **When** the user submits, **Then** the new dimension is saved and appears in the table.
4. **Given** the create form is open, **When** the user submits with a code that already exists, **Then** a conflict error is displayed and the dimension is not created.
5. **Given** a dimension exists in the table, **When** the user clicks the edit action, **Then** an edit modal opens pre-populated with the dimension's current values; the code field is read-only.
6. **Given** the edit form is open, **When** the user changes the name and submits, **Then** the dimension is updated and the table reflects the changes.
7. **Given** a dimension exists in the table, **When** the user clicks the delete action and confirms, **Then** the dimension is logically deactivated and no longer appears in the active list.
8. **Given** the delete confirmation is shown, **When** the user cancels, **Then** no changes are made and the dimension remains in the list.

---

### User Story 2 - Create a New Dimension (Priority: P1)

As a collaboration team member, I want to create a new measurement dimension so that I can later record metrics values against it for specific assignments.

**Why this priority**: Equally critical as listing — no new dimensions can be measured without this capability.

**Independent Test**: Can be fully tested by clicking create, filling in code, name, and optionally scale and unit, submitting, and verifying the new dimension appears in the table.

**Acceptance Scenarios**:

1. **Given** the user is on the dimensions page, **When** the user clicks the create button, **Then** a modal form opens with fields: code (required, text), name (required, text), description (optional, textarea), scale (optional, select from lists), unit (optional, select from DIMENSIONS_UNIT list items).
2. **Given** the create form is open, **When** the user fills all required fields and submits, **Then** the dimension is created and appears in the table.
3. **Given** the create form is open, **When** the user submits with an already-existing code, **Then** a conflict error is shown and the dimension is not created.
4. **Given** the create form is open, **When** the user leaves required fields (code, name) empty and submits, **Then** validation errors are displayed and the form is not submitted.

---

### User Story 3 - Edit an Existing Dimension (Priority: P2)

As a collaboration team member, I want to edit a dimension's details so that I can correct or update the name, description, scale, or unit as the measurement evolves.

**Why this priority**: Editing ensures the dimension catalog stays accurate. It depends on existing dimensions being created (US1/US2) but is critical for ongoing maintenance.

**Independent Test**: Can be fully tested by clicking edit on a dimension row, modifying fields, submitting, and verifying the table reflects the updated values.

**Acceptance Scenarios**:

1. **Given** a dimension exists in the table, **When** the user clicks the edit action on that row, **Then** an edit modal opens pre-populated with the dimension's current data (code is read-only).
2. **Given** the edit form is open, **When** the user changes the name or unit and submits, **Then** the dimension is updated and the table reflects the changes.
3. **Given** the edit form is open, **When** the user clears a required field (name) and submits, **Then** validation prevents the update.

---

### User Story 4 - Delete a Dimension (Priority: P2)

As a collaboration team member, I want to deactivate a dimension so that obsolete measurement dimensions no longer appear in the active list.

**Why this priority**: Logical deletion keeps the dimensions catalog clean. It is less frequent than creating or editing but necessary for lifecycle management.

**Independent Test**: Can be fully tested by clicking delete on a dimension row, confirming the action, and verifying the dimension no longer appears in the active dimensions table.

**Acceptance Scenarios**:

1. **Given** a dimension exists in the table, **When** the user clicks the delete action on that row, **Then** a confirmation dialog appears asking the user to confirm deactivation.
2. **Given** the delete confirmation is shown, **When** the user confirms, **Then** the dimension is logically deactivated (is_active set to false) and disappears from the active list.
3. **Given** the delete confirmation is shown, **When** the user cancels, **Then** no changes are made and the dimension remains in the list.

---

### User Story 5 - Navigate to Metrics from a Dimension (Priority: P2)

As a collaboration team member, I want a detail action on the dimensions page that navigates to the metrics page filtered by that dimension so that I can view and manage all measurement records for a specific dimension.

**Why this priority**: The master-detail navigation is the core value of the relationship between dimensions and metrics. It is the equivalent of how roles navigate to privileges in the admin module.

**Independent Test**: Can be fully tested by clicking the detail action on a dimension row, verifying that the metrics page opens with the dimension filter pre-applied and only shows metrics for that dimension.

**Acceptance Scenarios**:

1. **Given** the user is on the dimensions page, **When** the user clicks the detail action on a dimension row, **Then** the browser navigates to the metrics page with the dimension filter pre-applied for that dimension.
2. **Given** the user arrives at the metrics page via a dimension detail link, **When** the page loads, **Then** only metrics belonging to that dimension are shown and the filter reflects the selected dimension.
3. **Given** the user is on the filtered metrics page, **When** the user clears the filter, **Then** all active metrics are shown.
4. **Given** the user is on the metrics page arrived from the dimensions page, **When** the user clicks the back/master link, **Then** the browser navigates back to the dimensions page.

---

### User Story 6 - List and Filter Metrics by Dimension (Priority: P2)

As a collaboration team member, I want to view all metrics in a table and filter them by dimension so that I can analyze measurement values recorded for each dimension across assignments.

**Why this priority**: The metrics list is the detail side of the master-detail pattern. Users need to see metrics per dimension to understand measurement data.

**Independent Test**: Can be fully tested by navigating to the metrics page, viewing all active metrics, selecting a dimension from the filter dropdown, and verifying only metrics for that dimension are shown.

**Acceptance Scenarios**:

1. **Given** the user navigates to the metrics page, **When** the page loads, **Then** a table displays all active metrics with columns: dimension, assignment, value, measured_at — ordered by dimension and then by measured_at descending.
2. **Given** the metrics table is displayed, **When** the user selects a dimension from the filter dropdown, **Then** only metrics belonging to that dimension are shown.
3. **Given** the user has filtered by a dimension, **When** the user clears the filter, **Then** all active metrics are shown again.
4. **Given** there are no metrics for a selected dimension, **When** the user filters by that dimension, **Then** the table shows an empty state with no error.

---

### User Story 7 - Create a New Metric Record (Priority: P2)

As a collaboration team member, I want to create a new metric record associating a dimension value with an assignment so that I can track measurements over time for a specific person or team activity.

**Why this priority**: Creating metrics is the fundamental write operation for the detail side. Without it, there is no measurement data to analyze.

**Independent Test**: Can be fully tested by clicking create on the metrics page, filling in dimension, assignment, value, and measured_at, submitting, and verifying the new metric appears in the table.

**Acceptance Scenarios**:

1. **Given** the user is on the metrics page, **When** the user clicks the create button, **Then** a modal form opens with fields: dimension (required, select from active dimensions), assignment (required, select from assignments), value (required, select from list items of the relevant dimension's value list), observation (optional, textarea), measured_at (required, datetime picker).
2. **Given** the create form is filled with valid data, **When** the user submits, **Then** the metric is created and appears in the table.
3. **Given** the metrics page was opened from a dimension detail link, **When** the create form opens, **Then** the dimension field is pre-filled with the current filter dimension.
4. **Given** the create form is open, **When** the user selects a non-existent dimension or assignment, **Then** a validation error is shown and the record is not created.
5. **Given** the create form is open, **When** required fields are missing and the user submits, **Then** validation errors are displayed.

---

### User Story 8 - Edit and Delete Metric Records (Priority: P3)

As a collaboration team member, I want to edit or deactivate a metric record so that I can correct measurement errors or remove outdated entries.

**Why this priority**: Edit and delete are less frequent than creating metrics but necessary for data quality management.

**Independent Test**: Can be fully tested by clicking edit on a metric row, modifying the value or observation, submitting, and verifying the table reflects the change; and by clicking delete and confirming to verify the record disappears from the active list.

**Acceptance Scenarios**:

1. **Given** a metric exists in the table, **When** the user clicks the edit action, **Then** an edit modal opens pre-populated with the metric's current data.
2. **Given** the edit form is open, **When** the user changes the value or observation and submits, **Then** the metric is updated and the table reflects the changes.
3. **Given** a metric exists in the table, **When** the user clicks the delete action and confirms, **Then** the metric is logically deactivated and no longer appears in the active list.

---

### Edge Cases

- What happens when a dimension that has associated metrics is deactivated? The metrics retain their dimension reference; the system does not cascade-delete. Existing metrics remain in the metrics table but the dimension will no longer appear in the dimension filter dropdown (since only active dimensions are shown).
- What happens when two users create a dimension with the same code simultaneously? The first succeeds; the second receives a conflict error (409).
- What happens when the user navigates to the metrics page with a dimension query parameter that no longer exists (deactivated)? The filter dropdown shows no match; the table shows an empty state with no error thrown.
- What happens when the value options for a dimension depend on the dimension's scale list? The value field in the metrics form shows the list items associated with the selected dimension's value list. If no list is configured, an empty dropdown or text fallback is shown.
- What happens when trying to create a metric with an assignment that does not exist? The system returns a validation error and the metric is not created.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a dimensions page under the Collaboration section accessible via the application navigation.
- **FR-002**: System MUST display all active dimensions (is_active=true) in a data table with columns: code, name, scale, unit — ordered by name.
- **FR-003**: System MUST allow users to create a new dimension via a modal form with fields: code (required, unique text), name (required, text), description (optional, textarea), scale (optional, select from active lists), unit (optional, select from DIMENSIONS_UNIT list items).
- **FR-004**: System MUST validate that the dimension code is unique when creating and display a conflict error if it already exists.
- **FR-005**: System MUST allow users to edit an existing dimension via a modal form pre-populated with current values. The code field MUST be read-only in edit mode. Only changed fields are sent for update.
- **FR-006**: System MUST allow users to logically delete a dimension (set is_active to false) with a confirmation prompt. Deactivated dimensions no longer appear in the active list.
- **FR-007**: System MUST display a detail action on each dimension row that navigates to the metrics page with the dimension filter pre-applied.
- **FR-008**: System MUST display a metrics page under the Collaboration section accessible via navigation and via the dimension detail link.
- **FR-009**: System MUST display all active metrics (is_active=true) in a data table with columns: dimension, assignment, value, measured_at — ordered by dimension and measured_at descending.
- **FR-010**: System MUST provide a dimension filter dropdown on the metrics page, populated from the list of active dimensions, allowing users to filter the metrics table by dimension.
- **FR-011**: System MUST allow users to create a new metric record via a modal form with fields: dimension (required, select from active dimensions), assignment (required, select from active assignments), value (required, select from list items), observation (optional, textarea), measured_at (required, date/datetime).
- **FR-012**: System MUST validate that the selected dimension and assignment exist when creating or updating a metric.
- **FR-013**: System MUST allow users to edit an existing metric via a modal pre-populated with current values.
- **FR-014**: System MUST allow users to logically delete a metric (set is_active to false) with a confirmation prompt.
- **FR-015**: System MUST display a back link (masterPage) on the metrics page that navigates to the dimensions page.
- **FR-016**: System MUST display toast notifications for successful create, update, and delete operations and for errors.
- **FR-017**: System MUST support pagination parameters (skip and limit) for both dimensions and metrics list endpoints.
- **FR-018**: System MUST order the dimensions list by name and the metrics list by dimension and measured_at descending by default.

### Compatibility & Deployment Requirements

- **CR-001**: The existing dimensions and metrics API endpoints (GET/POST/PUT/DELETE on `/api/dimensions` and `/api/metrics`) already exist in the backend. The UI MUST consume these existing endpoints without backend modifications, unless the current endpoints lack dimension-based filtering query parameters — in which case the backend MUST be extended to support an optional `dimension` query parameter on the metrics list endpoint.
- **CR-002**: No new database schema changes are required. The `dimensions` and `metrics` tables already exist with the correct foreign key relationships. No migration is needed.
- **CR-003**: No new environment variables are required. The feature uses the existing API base URL and authentication configuration.

### Security & Performance Requirements

- **SPR-001**: All dimensions and metrics endpoints MUST require a valid JWT Bearer token. The existing authentication middleware covers these routes. Roles with `can_edit=TRUE` for the COLLAB/DIMENSIONS privilege can create, edit and delete dimensions and metrics; roles with `can_edit=FALSE` have read-only access.
- **SPR-002**: No secrets or sensitive data are involved in the dimensions or metrics entities beyond standard transport encryption already in place.
- **SPR-003**: The dimensions list endpoint MUST support pagination (skip/limit) with a default limit of 100 records. The metrics list endpoint MUST support pagination and the optional `dimension` query parameter for server-side filtering, or equivalent client-side column filtering consistent with the DataTable pattern.

### Key Entities

- **Dimension**: Represents a measurement axis used to evaluate assignments. Key attributes: code (unique identifier), name, description, scale (reference to a list that defines the rating/measurement scale), unit (a value from the DIMENSIONS_UNIT list), active flag. A dimension has zero or many metric records.
- **Metric**: Represents a single measurement event recorded for an assignment along a specific dimension. Key attributes: id (auto-generated), dimension (which dimension is measured), assignment (which assignment is being measured), value (selected from a list associated with the dimension's scale), observation (free text note), measured_at (when the measurement was taken), active flag.
- **Assignment**: An existing entity linking a user to a team with a role. Used as the subject being measured by a metric record.
- **List / List Item**: Existing reference tables used to populate the scale and unit fields of a dimension and the value field of a metric.

## Assumptions

- The dimensions backend API already exists with full CRUD (POST, GET, GET by code, PUT, DELETE on `/api/dimensions`). This feature primarily adds the UI page that consumes it.
- The metrics backend API already exists with full CRUD (POST, GET, GET by id, PUT, DELETE on `/api/metrics`). The UI page for metrics is new.
- The dimension filter for the metrics list will be implemented client-side following the DataTable `columnFilter` pattern unless the backend already supports a `dimension` query parameter for server-side filtering.
- The value field in the metrics form will be sourced from list items. If the dimension has a `scale` list code, the value dropdown will be populated from that list's items. If no scale is set, the value field falls back to a free-text input.
- The DIMENSIONS_UNIT list already exists in the `list_items` table with the code `DIMENSIONS_UNIT`.
- The assignments select field in the metrics form will be populated from the existing assignments select endpoint and display user + team information for readability.
- The back link on the metrics page will use the `masterPage="/collab/dimensions"` pattern consistent with how other detail pages reference their master.
- The detail action on the dimensions page (linking to the metrics page) follows the same pattern as the teams page detail action linking to assignments.
- The breadcrumb navigation follows the existing pattern: Collaboration > Dimensions (and Collaboration > Metrics for the detail page).
- The dimensions and metrics pages will follow the same UI patterns (CrudModal, DataTable, Toast) used by the admin/roles and admin/privileges pages respectively.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view, create, edit, and delete dimensions from the dimensions page within the same interaction patterns established by the admin/roles page (under 30 seconds per operation).
- **SC-002**: Users can navigate from a dimension on the dimensions page to its associated metrics in one click, with the dimension filter pre-applied.
- **SC-003**: Users can filter the metrics table by dimension in a single click, reducing the visible records to only those relevant to the selected dimension.
- **SC-004**: Users can record a new metric measurement (dimension + assignment + value) in under 60 seconds from opening the create form to seeing the success toast.
- **SC-005**: 100% of CRUD operations on dimensions and metrics produce visible feedback (success toast or error message) within 2 seconds of submission.
- **SC-006**: The dimensions page and metrics page each load and display all active records within 3 seconds under normal conditions (up to 200 records each).
