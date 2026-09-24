# Feature Specification: Initiative Management

**Feature Branch**: `004-initiative-management`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description (status transitions later amended by the user — see Assumptions): "La historia de usuario de Initiative Management es similar a Asset Management pero con las siguientes consideraciones: No se necesita implementar la opción de New Initiative pues las iniciativas no se crean manualmente, solo se proponen. En lugar de actions se usa collaborations para registrar las actividades que se realizan sobre las iniciativas. El estado solo se puede actualizar de Acceptance a Delivery o Archiving y de Delivery a Archiving; los demás estados se dan a través del flujo de proponer y revisar las iniciativas. Las pestañas que se necesitan en el detalle de la iniciativa son: Core Fields, Diagnosis Questions, Related Assets, Permissions, Discussion y History; todas similares a las pestañas del detalle de los Assets, menos la de Related Assets que se basa en la tabla de Asset_Inits y la de Diagnosis Questions que se basa en la tabla de Diagnostics para guardar las respuestas a las preguntas que aparecen en la tabla de Criterias tanto de quien la crea como de quien la revisa."

Covers user stories **HU-IN02 Initiative Management** and **HU-IN03 Edit Initiative (Include Delivery / Archiving)**, plus the Edit Initiative behaviour of the tab stories **HU-IN07 – HU-IN12** (see `docs/user-stories/05-inits.md`).

## Problem Context

Initiatives are the platform's AI-adoption opportunities. They already exist as data — with a status, a diagnosis scored against shared criteria, links to library assets, access grants and an activity log — but there is no screen where the people responsible for them can see and curate them. Initiative owners today cannot answer "which initiatives am I responsible for, and where is each one?", cannot record that an accepted initiative was delivered, and cannot retire one that is no longer relevant.

The AI Library already solved the equivalent problem for assets with **Asset Management**: a filterable list of the assets a person can access, and an edit dialog organised in tabs, each saving its own slice. Initiative owners expect the same experience. Initiatives differ in three ways that shape this feature:

1. **They are never created by hand.** An initiative only enters the system by being proposed and then diagnosed by a reviewer. The management screen therefore offers no "New Initiative" entry point.
2. **Their lifecycle is mostly driven by the diagnosis workflow.** Only the post-acceptance moves — starting work (In Progress), delivering and archiving — belong to the owner. Every other status is the result of proposing, diagnosing and modifying.
3. **Their evaluation is a scored diagnosis, not a set of characteristics.** Each initiative carries one answer per diagnosis criterion from its proposer and, once diagnosed, one from its reviewer, side by side.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See and filter the initiatives I am responsible for (Priority: P1)

As an initiative owner, I want a list of the initiatives I have access to — filterable by status, type, priority, expected impact, my access level and favorites, and searchable by name — so that I can see the state of the portfolio I curate at a glance.

**Why this priority**: Everything else in this feature starts from this list. On its own it already answers the core question ("what am I responsible for and where does each one stand?") that no screen answers today.

**Independent Test**: Sign in as a user who holds access to some initiatives but not others; open Initiative Management and confirm that exactly the accessible initiatives appear, that each filter narrows the list correctly, and that no option to create an initiative is offered.

**Acceptance Scenarios**:

1. **Given** a user holds manage or view access to some initiatives and none to others, **When** they open Initiative Management, **Then** only the initiatives they can access are listed, with the columns name, type, priority, status, tags and actions (in that order); the actions include a favorite star.
2. **Given** the list is open, **When** the user filters by one or more of status, type, priority, privileges (how the initiative is shared with them) or "my favorites", **Then** only initiatives matching every selected filter remain, and the visible count reflects the filtered set.
3. **Given** the list is open, **When** the user types part of an initiative's name in search, **Then** matching initiatives remain and the rest are hidden.
4. **Given** any user opens Initiative Management, **When** they look for a way to add an initiative, **Then** none is offered — no "New" button, no empty-state call to create one.
5. **Given** a user has view-only access to an initiative, **When** it appears in the list, **Then** its row offers no edit or remove affordance.
6. **Given** a user has no access to any initiative, **When** they open Initiative Management, **Then** they see an explanatory empty state rather than an error or blank area.
7. **Given** a platform superuser opens Initiative Management, **When** the list loads, **Then** every active initiative is listed, regardless of grants.

---

### User Story 2 - Edit an initiative one tab at a time (Priority: P1)

As an initiative owner, I want to open an initiative in a tabbed detail dialog — Core Fields, Diagnosis Questions, Related Assets, Permissions, Discussion and History — and save each editable tab on its own, so that I can keep the initiative accurate without touching parts I did not mean to change.

**Why this priority**: The list without an editing surface is a read-only report. Editing core fields, linked assets and access is the day-to-day curation work the owner needs, and the tabbed, save-per-tab convention is what users already know from Asset Management.

**Independent Test**: Open an initiative the user manages; change a core field and save; add a related asset and save; grant access to another user and save; confirm each save only changed its own slice, and that Diagnosis Questions, Discussion and History cannot be modified from here.

**Acceptance Scenarios**:

1. **Given** a user manages an initiative, **When** they open it from the list, **Then** a dialog titled for editing opens with six tabs in this order: Core Fields, Diagnosis Questions, Related Assets, Permissions, Discussion, History; Core Fields is shown first.
2. **Given** the Core Fields tab is open, **When** the user edits name, description, type, expected impact, priority, reference, tags or detail and saves, **Then** only those fields are persisted, and the other tabs' pending edits are neither saved nor discarded.
3. **Given** the Core Fields tab is open, **When** the user leaves a required field (name, expected impact, priority) empty and tries to save, **Then** the save is blocked and the field is flagged.
4. **Given** the Related Assets tab is open, **When** the user adds a link to a library asset with a relation type and optional rationale, or removes an existing link, and saves, **Then** only the initiative's asset links change; the same link is visible from that asset's "Related Inits" tab in Asset Management.
5. **Given** the Permissions tab is open, **When** the user grants view or manage access to a user, role, project, team, unit or everyone, with an optional validity window, or revokes an existing grant, and saves, **Then** only the initiative's grants change, and a revoked grant is kept as a record ending now rather than deleted.
6. **Given** the Diagnosis Questions tab is open, **When** the user views it, **Then** the criteria are shown as a table with the proposer's answers and the reviewer's answers in visually distinct columns (or an indication that the reviewer has not answered yet), an overall score for the proposer and another for the reviewer, and each criterion's rationale hidden until the user reveals it; none of it can be edited.
7. **Given** the Discussion tab is open, **When** the user views it, **Then** the comments, questions and answers on the initiative are shown, and the user can post a comment or a question, answer a question, and delete their own entries, as in Asset Management.
8. **Given** the History tab is open, **When** the user views it, **Then** the initiative's activity is listed newest first with the acting person, including activation, diagnosis, modifications, acceptance or rejection, delivery, archiving, votes, comments, questions and answers.
9. **Given** the user switches to Diagnosis Questions, Discussion or History, **When** that tab is shown, **Then** the dialog's save action is hidden (Discussion saves each post on its own).
10. **Given** the user has unsaved edits in a tab, **When** they try to close the dialog, **Then** they are asked to confirm discarding them.

---

### User Story 3 - Record delivery and archive initiatives (Priority: P2)

As an initiative owner, I want to mark an accepted initiative In Progress when work starts, move it to Delivered when its work is done, and to Archived when it is no longer relevant — and have each move recorded in the initiative's history — so that the portfolio reflects reality after the diagnosis workflow has finished.

**Why this priority**: These are the only status changes the owner is allowed to make by hand, and without them accepted initiatives stay "accepted" forever. It depends on Story 2's editing surface, hence P2.

**Independent Test**: Take an accepted initiative, move it to In Progress, then Delivered, then Archived; confirm every move is accepted and appears in History. Repeat skipping steps (Accepted→Delivered, Accepted→Archived, In Progress→Archived). Then try every other status change (from any status) and confirm each is refused, both in the dialog and if attempted directly.

**Acceptance Scenarios**:

1. **Given** an initiative is Accepted, **When** the owner opens its Core Fields tab, **Then** the status control offers only Accepted (unchanged), In Progress, Delivered and Archived.
2. **Given** an initiative is In Progress, **When** the owner opens its Core Fields tab, **Then** the status control offers only In Progress (unchanged), Delivered and Archived.
3. **Given** an initiative is Delivered, **When** the owner opens its Core Fields tab, **Then** the status control offers only Delivered (unchanged) and Archived.
4. **Given** an initiative is in any other status (Activated, Feedback Provided, Rejected, Archived), **When** the owner opens its Core Fields tab, **Then** the status control is locked and a short explanation states that this status is set by the propose/diagnose workflow (or, for Archived, that the initiative is closed).
5. **Given** an Accepted initiative, **When** the owner saves it as In Progress, **Then** the status changes and an activity recording the start of work, attributed to the owner, is recorded and shown in History as a new "Kickoff" activity type.
6. **Given** an Accepted or In Progress initiative, **When** the owner saves it as Delivered, **Then** the status changes and a Delivery activity attributed to the owner is recorded and shown in History.
7. **Given** an Accepted, In Progress or Delivered initiative, **When** the owner saves it as Archived, **Then** the status changes and an Archiving activity attributed to the owner is recorded and shown in History.
8. **Given** any status change outside the allowed set (Accepted → In Progress / Delivered / Archived; In Progress → Delivered / Archived; Delivered → Archived) is requested — through the dialog or directly against the system — **When** it is processed, **Then** it is refused with a clear message and nothing is changed or recorded.
9. **Given** the owner edits other core fields without changing the status, **When** they save, **Then** no status-change activity is recorded.
10. **Given** an initiative is delivered or archived, **When** the change is saved, **Then** the activity is recorded as already completed and no pending notice is raised for the proposer or anyone else — the change is visible in History only (same as deprecation in Asset Management).

---

### Edge Cases

- **Initiative whose status value does not match the known list** (e.g. legacy seed values): it still lists and opens; its status control is locked, like any status outside the owner-editable set.
- **Initiative with no diagnosis answers yet**: the Diagnosis Questions tab lists every criterion with "not answered" rather than an empty panel.
- **Proposer answered but the reviewer has not diagnosed yet**: the reviewer column shows "pending diagnosis" for each criterion.
- **Criterion added after an initiative was diagnosed**: it is listed with no answers, not hidden.
- **Criterion deactivated after being answered**: existing answers for it remain visible so the diagnosis is not silently rewritten.
- **Two owners change the status concurrently** (one delivers, one archives): the second request is evaluated against the status as it stands then, and refused if the move is no longer allowed.
- **Linking an asset the owner cannot see**: the asset picker only offers assets the owner can access; an existing link to an asset they cannot see is still shown by name so the link is not invisible.
- **Several links to the same asset**: allowed, one per relation type (e.g. an asset both USED_BY and CONTAINS the initiative); each is shown and removed on its own.
- **Duplicate asset link** (same asset AND same relation type already linked): refused with a clear message; a previously removed identical link is restored rather than duplicated.
- **Owner revokes their own manage access**: allowed, but they are warned first that they will lose edit access; the initiative may drop out of their list after saving.
- **Grant scheduled to start in the future**: shown in Permissions as a grant not yet in effect, not as revoked.
- **Archived initiative**: remains visible in the list (filterable), all tabs readable; Core Fields, Related Assets and Permissions stay editable, but the status stays locked.
- **Many initiatives**: the list stays responsive and does not silently truncate.

## Requirements *(mandatory)*

### Functional Requirements

**List (Initiative Management)**

- **FR-001**: The system MUST provide an Initiative Management screen, reachable from the existing "Initiative Management" navigation option, listing the active initiatives the current user can access.
- **FR-002**: A user MUST only see initiatives on which they hold a currently valid view or manage grant — directly, or through their role, project, team, unit, or a public grant; superusers MUST see all active initiatives.
- **FR-003**: The list MUST show, per initiative, the columns name, type, priority, status, tags and actions, in that order; expected impact, score and the user's access level are NOT shown.
- **FR-004**: The list MUST support filtering by status, type, priority, privileges and favorites, and searching by name; filters combine. The privileges filter works exactly like Asset Management's: options All privileges, Shared with me (a grant to the user), My role, My team, My unit, My projects and Public, each matching initiatives where a live grant of that scope reaches the user.
- **FR-004a**: The actions column MUST include a favorite star on every listed initiative (manage or view access); toggling it saves the current user's favorite immediately and is reflected by the favorites filter.
- **FR-005**: The screen MUST NOT offer any way to create an initiative.
- **FR-006**: Edit and remove affordances MUST only be offered on initiatives the user can manage; view-only initiatives MUST open read-only.
- **FR-007**: Removing an initiative MUST be a logical removal (the record is retained and hidden), available only to users who manage it, after confirmation.

**Detail dialog**

- **FR-008**: Opening an initiative MUST show a dialog with the tabs Core Fields, Diagnosis Questions, Related Assets, Permissions, Discussion and History, in that order.
- **FR-009**: Each editable tab (Core Fields, Related Assets, Permissions) MUST save only its own slice, with a save action labelled for that tab; saving one tab MUST NOT persist or discard another tab's pending edits.
- **FR-010**: Diagnosis Questions and History MUST be read-only in this dialog; Discussion is interactive but saves each post on its own. The dialog's save action MUST be hidden while any of these three tabs is shown.
- **FR-011**: The dialog MUST warn before discarding unsaved edits on close.

**Core Fields**

- **FR-012**: Core Fields MUST allow editing name, description, type, expected impact, priority, reference, tags, detail and status (status subject to FR-017 – FR-021); name, expected impact and priority are required.
- **FR-013**: Type, expected impact, priority and status MUST be chosen from the platform's configured value lists, shown in the user's language.

**Diagnosis Questions**

- **FR-014**: Diagnosis Questions MUST list every diagnosis criterion (active ones, plus any inactive one the initiative already has answers for) as rows of a table showing the criterion's question and description, the proposer's answer and the reviewer's answer, with the two answer columns visually distinguishable at a glance. Each criterion's rationale MUST be hidden by default and revealed on demand with the same Show / Hide switch used for characteristic details in Asset Management.
- **FR-015**: Each answer MUST be shown by its label from that criterion's own scale (not just the numeric value), in the user's language; missing answers MUST be shown as "not answered" / "pending diagnosis".
- **FR-016**: The tab MUST show an overall score for the proposer and another for the reviewer — each the sum of that party's answers — indicating how many criteria each has answered, and "pending diagnosis" for the reviewer when they have not answered any.

**Status transitions**

- **FR-017**: The only status changes a user may make from Initiative Management are: Accepted → In Progress / Delivered / Archived; In Progress → Delivered / Archived; Delivered → Archived. Every other change MUST be refused.
- **FR-018**: The refusal MUST be enforced by the system itself, not only by the dialog, for every path that can change an initiative's status outside the propose/diagnose/modify workflow.
- **FR-019**: The status control MUST offer only the statuses reachable from the current one (plus the current one), and MUST be locked with an explanation when no move is available.
- **FR-020**: Each allowed status change MUST be recorded as an initiative activity attributed to the acting user — Kickoff for → In Progress, Delivery for → Delivered, Archiving for → Archived — in the same operation as the status change, so that neither can happen without the other.
- **FR-020a**: Status-change activities (Kickoff, Delivery, Archiving) MUST be recorded as already completed; they MUST NOT create pending notices or assignments for anyone.
- **FR-021**: Saving core fields without a status change MUST NOT record any status-change activity.
- **FR-022**: Only users who manage the initiative (or superusers) MAY change its status or any other editable slice.

**Related Assets**

- **FR-023**: Related Assets MUST list the library assets linked to the initiative, each with its relation type and rationale, and allow adding and removing links; links are the same records shown from the asset side ("Related Inits").
- **FR-024**: Adding a link MUST require an asset and a relation type from the configured relation types. The same asset MAY be linked more than once with different relation types; a link is identified by (asset, relation type). A duplicate (same asset and type) MUST be refused, and a previously removed identical link MUST be restored instead of duplicated. Removal MUST be logical and affect only that (asset, type) link.
- **FR-024a**: The same rule applies on the asset side (Asset Management → Edit Asset): its Related Assets tab MAY hold several links to the same target asset and its Related Inits tab several links to the same initiative, one per relation type. Both tabs, and the Propose wizard, MUST identify a link by (target, relation type).

**Permissions**

- **FR-025**: Permissions MUST list the initiative's grants (target type, target, access level, validity window) and allow adding and revoking them, following the same model as asset permissions: a grant is revoked by ending its validity now, never deleted, and a grant not yet in effect is not treated as revoked.
- **FR-026**: A user with view-only access MUST NOT be able to add, change or revoke grants.

**Discussion & History**

- **FR-027**: Discussion MUST show the initiative's comments, questions and answers (answers under their question) and let the user post comments and questions, answer questions and delete their own entries, as in Asset Management. Posts are attributed to the signed-in user (never to a user named in the request); only the author (or a superuser) may delete an entry.
- **FR-028**: History MUST show all of the initiative's activity newest first, with the acting user, date and a localized description of each activity, including status-change activities recorded by FR-020.

**General**

- **FR-029**: All initiative activity (delivery, archiving and any activity read by Discussion and History) MUST be recorded in and read from the initiatives' own collaboration record — not the asset activity record.
- **FR-030**: Every user-facing text MUST be available in English and Spanish.

### Key Entities

- **Initiative**: an AI-adoption opportunity. Name, description, type, expected impact, priority, reference, tags, detail, status, overall score, active flag.
- **Diagnosis criterion**: a shared evaluation question, each with its own scale of labelled answers (1–3 today).
- **Diagnosis answer**: for one initiative and one criterion — the proposer's answer, the reviewer's answer (once diagnosed) and a rationale.
- **Collaboration (initiative activity)**: something a person did on an initiative — activation, diagnosis, modification, acceptance, rejection, delivery, archiving, vote, comment, question or answer — with actor, time, optional message, optional parent (for answers) and a pending/handled workflow state for workflow items.
- **Initiative–asset link**: a typed, optionally explained relationship between an initiative and a library asset, shared with the asset side.
- **Initiative grant**: view or manage access to an initiative for a user, role, project, team, unit or everyone, within a validity window.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An initiative owner can find a given initiative they are responsible for, using search or filters, in under 30 seconds.
- **SC-002**: 100% of initiatives listed to a user are ones they hold a valid grant on (or the user is a superuser); 0 initiatives without a grant are shown.
- **SC-003**: 100% of status changes outside the six allowed transitions (FR-017) are refused, whichever way they are attempted.
- **SC-004**: 100% of in-progress, delivery and archiving changes appear in the initiative's History, attributed to the person who made them; 0 status changes exist without their activity record.
- **SC-005**: Saving a tab changes only that tab's data in 100% of cases (verified per tab).
- **SC-006**: An owner can record the delivery of an accepted initiative in under 1 minute from opening Initiative Management.
- **SC-007**: A reader can compare the proposer's and reviewer's answer for every criterion of a diagnosed initiative on a single screen, without leaving the dialog.

## Assumptions

- **Status names.** The user's "Acceptance", "Delivery" and "Archiving" refer to the statuses Accepted, Delivered and Archived plus In Progress (recorded by the collaboration types Kickoff — new — Delivery and Archiving). **Amended by the user (2026-09-23):** the allowed transitions are Accepted → In Progress / Delivered / Archived, In Progress → Delivered / Archived, and Delivered → Archived. This supersedes the older docs' "any → Archived" row: Activated, Feedback Provided and Rejected initiatives cannot be archived from here.
- **Diagnosis answers are read-only in Initiative Management.** The proposer's answers are written when proposing and the reviewer's when diagnosing (both out of scope here), matching the Edit Initiative column of the initiative tab matrix. Letting owners edit scores here would bypass the diagnosis.
- **Discussion is interactive here**, as in Asset Management's edit dialog (user decision, 2026-09-23). Posting requires the edit-level Initiative Management privilege (or an edit-level Explore Initiatives privilege) plus access to the initiative.
- **Access model** mirrors Asset Management: per-initiative grants (view/manage, validity window, revoke-not-delete); an initiative with no grant reaching the user is hidden. Access to the screen itself requires the existing "Initiative Management" privilege (today held by administrator and administrative profiles).
- **Favorites**: the star in the list's actions column writes the existing initiative-favorites record for the current user (user decision, 2026-09-23); anyone who can see the initiative may favorite it.
- **Seed data alignment.** Current seed initiatives carry status values outside the configured list (e.g. "3-ENGAGING"); the product is unreleased, so the seed will be realigned to the configured statuses as part of this work rather than migrated.
- **Out of scope**: proposing an initiative (HU-IN05), diagnosing it (HU-IN15), modifying it after feedback (HU-IN16), acknowledging outcomes (HU-IN17), initiative notifications and "My Initiative Requests" (HU-IN13/14), Explore Initiatives and its detail view (HU-IN04/06), votes, and editing criteria (HU-IN01, already shipped). Until proposing exists, initiatives come only from seed data.
- **Dependencies**: reuses the existing Asset Management dialog conventions (tab-scoped saves, read-only tab behaviour, discard confirmation), the shared value lists, and the existing relation-type and permission target-type lists.
- **New collaboration type "Kickoff".** The configured collaboration types have no entry for starting work, so one is added — code `KICKOFF`, labels "Kickoff" / "Arranque" — to record Accepted → In Progress. Added to the seed directly (unreleased product, no migration).

## Clarifications

### Session 2026-09-23

- Q: Which status transitions may the owner make from Initiative Management? → A: Accepted → In Progress / Delivered / Archived; In Progress → Delivered / Archived; Delivered → Archived.
- Q: Does delivery (or archiving) raise a pending notice for the proposer? → A: No. Both are recorded as completed activities only, visible in History (Option A).
- Q: How is the move to In Progress recorded? → A: With a new collaboration type, recorded as completed (Option A); name chosen by the user: `KICKOFF` ("Kickoff" / "Arranque").
- Q (2026-09-23, after implementation): May an initiative and an asset (and two assets) be linked more than once? → A: Yes — one link per relation type, in both Edit Initiative and Edit Asset. That is why the primary keys of `asset_inits` and `related_assets` include `type`. Supersedes the plan's earlier "one link per pair" reading.
- Q (2026-09-23, review of the first implementation): list columns, favorites, diagnosis layout and discussion → A: columns name, type, priority, status, tags, actions (no expected impact, score or access); a favorite star in actions; Diagnosis Questions as a table distinguishing proposer vs reviewer answers, rationale behind a Show/Hide switch, an overall score for each party; Discussion interactive like Edit Asset.
- Q (2026-09-23, review): which list filters? → A: drop the access-level and expected-impact filters; add a privileges filter identical in behaviour to Asset Management's (All privileges, Shared with me, My role, My team, My unit, My projects, Public).
