# Feature Specification: Process Management

**Feature Branch**: `009-process-management`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "la historia de usuario de Process Management teniendo en cuenta las siguientes consideraciones: al momento de agregar un nuevo proceso o editar uno existente, el orden de las pestañas debe ser Related processes, Related assets y Related inits; Related assets es similar a la pestaña Related assets de la opción Asset detail de la historia de Asset Management, pero con las respectivas tablas equivalentes; Related inits es similar a la pestaña Related inits de la opción Asset detail de la historia de Asset Management, pero con las respectivas tablas equivalentes; Related processes debe conservar el mismo estilo y funcionalidad de Related assets y Related inits."

## Context

Covers user stories **HU-PR01 Process Management** and its details **HU-PR02 Related Processes**, **HU-PR03 Related Assets** and **HU-PR04 Related Inits** (see `docs/user-stories/07-proc.md`):

> As a **process owner**, I want to **register and maintain the organization's processes** — typed as primary or support, optionally nested, owned by a person and a business unit — **so that** there is a single inventory of how the organization operates.

What already exists:

- **Process data**: a process has a unique code, a name, a description, a type (Primary or Support, Porter's value chain), an optional parent process (processes nest), an optional business unit, an owner (a user), a reference, a status (Draft, Review, Published, Deprecated), tags and a free-text detail. The seed holds the nine value-chain activities plus their sub-processes, all Published.
- **Process links**: a process can be linked to other processes (with a relation type such as *Depends On* or *Used By*, and a rationale), to library assets (with a rationale) and to initiatives (with a rationale). The seed already holds some links of each kind.
- **Asset Management** (`/lib/assets`): the reference experience. Its edit dialog has a **Related Assets** tab and a **Related Inits** tab. Each tab shows the current links as a list (target, relation type, rationale), lets the user add a link by picking a target, a relation type and an optional rationale, and remove a link. In create mode every tab is staged and saved together with the new record; in edit mode each tab saves only its own slice ("Save related assets", "Save related inits"), with a pending-changes indicator on the tab.
- The sidebar already has the option **Process Management** (`/proc/processes`) in the Processes module, granted today to the Administrator and Administrative profiles with edit rights. Collaborator and Reviewer hold no Process Management privilege.
- There is no server-side support for processes yet: this feature is the first one in the Processes module.

What this feature adds: a Process Management page with a list of processes and a create/edit dialog whose tabs, in order, are **Core Fields → Related processes → Related assets → Related inits**. The three Related tabs look and behave like Asset Management's Related Assets / Related Inits tabs, over the process link tables.

## Clarifications

### Session 2026-10-23

- Q: The process–asset and process–initiative links have no relation type, while Asset Management's tabs ask for one. Keep them without a type, or add one? → A: Add a relation type to both, so the three Related tabs match Asset Management exactly: the same pair may be linked once per relation type (option B). Because the product has not reached production, the table definitions are changed **in place in the existing SQL files** (no separate migration); the seeded links receive a relation type in the same files.
- Q: Which status moves are allowed? → A: A fixed lifecycle (option B): Draft → Review → Published → Deprecated, plus Review → Draft to send a process back. Every other move is refused by the server, and the form offers only the moves allowed from the current status.
- Q: Should process relations use the shared relation type list, a subset of it, or a dedicated list, given that they will build the Value Chain and the Process Map? → A: A dedicated list, **Process Relation Type**, used only by process-to-process links, extended beyond the four proposed types so that each type maps to a BPMN connecting object and the Value Chain and Process Map can be drawn in BPMN notation: Precedes, Triggers, Calls, Feeds Into, Interacts With, Supports, Governs (see FR-013a). Process–asset and process–initiative links keep the shared relation type list. The seeded process relations are rewritten in place: Depends On becomes Precedes with the direction reversed (INBL → OPER → OUTL → MKTS → SERV) and Used By becomes Supports.
- Q: Must the relation type be compatible with the process types (Primary/Support) of the two processes? → A: Two server-enforced rules, the rest free (option B): **Supports** only from a Support process to a Primary process, and **Precedes** only between processes of the same type (Primary–Primary or Support–Support). The target picker offers only compatible processes for the chosen relation type.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse and maintain the process inventory (Priority: P1)

A process owner opens Process Management and sees every active process in a table: code, name, type, parent, business unit, owner, status and tags. They search and filter the list (by type, status, business unit), open a process to edit its core fields, create a new process, and remove one that is no longer needed.

**Why this priority**: without the inventory there is nothing to relate; it is the minimum viable slice and already gives the organization a single place to keep its processes.

**Independent Test**: as an Administrative user, create a process "OPER-QA" (type Primary, parent "OPER", unit, owner; it lands in Draft), find it in the list through search and the type filter, change its name and move it to Review, then remove it and confirm it disappears from the list while its record is retained.

**Acceptance Scenarios**:

1. **Given** the seeded processes, **When** the user opens Process Management, **Then** the table lists every active process with its code, name, type, parent, business unit, owner, status and tags, labels in the current language.
2. **Given** the list, **When** the user filters by type *Support*, **Then** only support processes are shown; **When** they also filter by status, both filters apply.
3. **Given** the user clicks *New Process*, **When** they fill code, name, type and owner and save, **Then** the process is created in **Draft** and appears in the list; the status is not selectable at creation.
4. **Given** a code that already exists, **When** the user saves a new process with it, **Then** the save is refused with a clear "code already in use" message and nothing is created.
5. **Given** an existing process, **When** the user edits its core fields and saves the Core Fields tab, **Then** only those fields change; its links are untouched.
6. **Given** an existing process, **When** the user tries to set its parent to itself or to one of its own descendants, **Then** the save is refused with a clear message.
7. **Given** a process with no active child processes, **When** the user removes it, **Then** it leaves the list and the record is kept (logical removal).
8. **Given** a process that still has active child processes, **When** the user tries to remove it, **Then** the removal is refused and the message says the children must be moved or removed first.
9. **Given** a process in Review, **When** the user opens the status control, **Then** it offers only Review (unchanged), Published and Draft; **Given** a Published process, it offers only Published and Deprecated; **Given** a Deprecated process, the status is shown read-only.
10. **Given** a status move outside the lifecycle (e.g. Published → Draft) is submitted, **When** the server receives it, **Then** it is refused with a validation message and the status is unchanged.

---

### User Story 2 - Relate a process to other processes (Priority: P1)

From the process dialog's **Related processes** tab (the first tab after Core Fields), the owner links the process to other processes, choosing the target process, a relation type and an optional rationale, and removes links that no longer apply. The tab looks and behaves exactly like Asset Management's Related Assets tab.

**Why this priority**: dependencies between processes are the core of the process landscape and feed the later Value Chain and Process Map views.

**Independent Test**: edit process "OUTL", open Related processes, see its existing link to "MKTS" (*Precedes*), add a link to "SERV" (*Interacts With*, with a rationale), remove nothing else, click *Save related processes*, reopen the dialog and see both links.

**Acceptance Scenarios**:

1. **Given** a process with existing process links, **When** the user opens Related processes, **Then** each link shows the target process (code and name), the relation type in the current language and the rationale.
2. **Given** the tab, **When** the user picks a target and a relation type and adds the link, **Then** it appears in the list as a pending change and the tab shows the pending-changes indicator.
3. **Given** the target or relation type is missing, **When** the user tries to add, **Then** an inline message asks for both and nothing is added.
4. **Given** the same target with the same relation type is already listed, **When** the user adds it again, **Then** an inline message says it is already related with that type; the same target with a **different** type is allowed.
5. **Given** the target list, **When** the user opens it, **Then** the process being edited is not offered (a process cannot be related to itself).
6. **Given** pending changes in Related processes, **When** the user clicks *Save related processes*, **Then** only process links are saved, the other tabs' pending changes are kept unsaved, and the indicator clears.
7. **Given** a link that was removed earlier, **When** the user adds the same target and type again and saves, **Then** the link is restored rather than duplicated.
8. **Given** a Support process and relation type *Supports*, **When** the user opens the target picker, **Then** only Primary processes are offered; **Given** *Precedes*, only processes of the same type are offered; **Given** a Primary process, *Supports* links to any target are refused with a message naming the rule.
9. **Given** a target already picked, **When** the user switches to a relation type it is not compatible with, **Then** an inline message explains the rule and the link cannot be added until target or type changes.

---

### User Story 3 - Relate a process to library assets (Priority: P2)

From the **Related assets** tab, the owner links the process to the AI and digital assets that support it, with an optional rationale, and removes links. The tab is the equivalent of Asset Management's Related Assets tab, over the process–asset links.

**Why this priority**: it connects the process inventory with the AI library, which is the module's purpose, but processes are already useful without it.

**Independent Test**: edit process "OPER-DEVELOP", open Related assets, see its seeded asset links, add another published asset with a rationale, click *Save related assets*, reopen and see it.

**Acceptance Scenarios**:

1. **Given** a process with asset links, **When** the user opens Related assets, **Then** each link shows the asset name and its category, the relation type in the current language and the rationale.
2. **Given** the tab, **When** the user picks an asset and a relation type and adds the link, **Then** it appears as a pending change; the same asset with the same type already listed shows an inline "already related with that relation type" message, while a different type is allowed; a missing asset or type shows an inline message asking for both.
3. **Given** pending changes, **When** the user clicks *Save related assets*, **Then** only asset links are saved.
4. **Given** the asset picker, **When** it opens, **Then** it offers active assets only.

---

### User Story 4 - Relate a process to initiatives (Priority: P2)

From the **Related inits** tab, the owner links the process to the initiatives that affect it, with an optional rationale, and removes links. The tab is the equivalent of Asset Management's Related Inits tab, over the process–initiative links.

**Why this priority**: ties improvement opportunities to the processes they change; valuable but independent of the inventory itself.

**Independent Test**: edit process "TECH-AIPLATF", open Related inits, see its seeded initiative link, add another initiative with a rationale, click *Save related inits*, reopen and see it.

**Acceptance Scenarios**:

1. **Given** a process with initiative links, **When** the user opens Related inits, **Then** each link shows the initiative name, the relation type in the current language and the rationale.
2. **Given** the tab, **When** the user picks an initiative and a relation type and adds the link, **Then** it appears as a pending change; the same initiative with the same type already listed shows an inline "already related with that relation type" message, while a different type is allowed; a missing initiative or type shows an inline message asking for both.
3. **Given** pending changes, **When** the user clicks *Save related inits*, **Then** only initiative links are saved.

---

### User Story 5 - Create a process with its links in one pass (Priority: P3)

When creating a new process, the user fills Core Fields and can also stage links in Related processes, Related assets and Related inits before saving; one *Save* creates the process and all staged links together.

**Why this priority**: convenience that mirrors Asset Management's create mode; links can always be added afterwards in edit mode.

**Independent Test**: click *New Process*, fill Core Fields, stage one link in each Related tab, save once, reopen the new process and see all three links.

**Acceptance Scenarios**:

1. **Given** the create dialog, **When** the user looks at the tabs, **Then** they are, in order, Core Fields, Related processes, Related assets, Related inits.
2. **Given** staged links in several tabs, **When** the user saves, **Then** the process and every staged link are created together; if the process cannot be created (e.g. duplicate code), no link is created either.
3. **Given** required core fields are empty, **When** the user saves from any tab, **Then** the save is refused and the Core Fields tab shows which fields are missing.

---

### Edge Cases

- A target process, asset or initiative that was removed (logically) after being linked: the link still shows in the list, marked as inactive, and can be removed; it is not offered when adding.
- Relating A → B and B → A is allowed for directed types (they are different links), and cycles are allowed (a BPMN flow may loop back). Only the **parent** hierarchy must stay acyclic.
- *Interacts With* is undirected: if A Interacts With B exists, adding B Interacts With A is refused as a duplicate, and the link shows in both processes' Related processes tab.
- Changing a process's type (Primary ↔ Support) when it has active *Supports* or *Precedes* links that would become incompatible is refused, with a message listing those links; the user removes or changes them first.
- Hierarchy is never expressed as a relation: there is no "Part Of"/"Contains" process relation type, because the parent field is the decomposition (a BPMN collapsed sub-process).
- Closing the dialog with unsaved changes in any tab asks for confirmation before discarding, as in Asset Management.
- A process code is its permanent identifier: it cannot be changed after creation (it is shown read-only in edit mode).
- Two people editing the same process: the last save of each tab wins for that tab's slice; no locking.
- A user without the Process Management privilege who opens `/proc/processes` or calls its operations is refused (not authorized), as with every other module option.
- A user who holds the privilege with read access only sees the list and can open a process in read-only mode, without New, Save or Remove actions.

## Requirements *(mandatory)*

### Functional Requirements

**Process inventory**

- **FR-001**: The system MUST list active processes with code, name, type, parent, business unit, owner, status and tags, with bounded pagination, search by code/name/description, and filters by type, status and business unit.
- **FR-002**: Type and status MUST display in the language chosen in the header and switch with it, like every other list value in the application.
- **FR-003**: Users with edit rights on Process Management MUST be able to create a process with: code (required, unique, at most 50 characters), name (required, at most 100), description (optional, at most 500), type (required, Primary or Support), parent (optional, an active process), business unit (optional, an active unit), owner (required, an active user; defaults to the creator), reference (optional), tags (optional list) and detail (optional). A new process always starts in **Draft**; any other status submitted at creation MUST be refused as a validation error.
- **FR-004**: A duplicate code MUST be refused as a conflict; invalid type, status, parent, unit or owner values MUST be refused as validation errors with a message naming the field.
- **FR-005**: The code MUST NOT be editable after creation.
- **FR-006**: The parent hierarchy MUST stay acyclic: a process cannot be its own parent or the parent of one of its ancestors.
- **FR-007**: Removing a process MUST be logical (the record is kept and leaves every list and picker) and MUST be refused while the process has active child processes.
- **FR-008**: Status changes MUST follow a fixed lifecycle enforced by the server: Draft → Review, Review → Published, Review → Draft, Published → Deprecated. Deprecated is final. Any other move MUST be refused as a validation error. The form MUST offer only the current status and the moves allowed from it, as provided by the server, so the rule is defined in one place.

**Dialog and tabs**

- **FR-009**: The create/edit dialog MUST show its tabs in this order: **Core Fields, Related processes, Related assets, Related inits**.
- **FR-010**: In create mode, all tabs MUST be staged and saved together by a single *Save*, all-or-nothing.
- **FR-011**: In edit mode, each tab MUST save only its own slice: *Save* (Core Fields), *Save related processes*, *Save related assets*, *Save related inits*. Each tab MUST show a pending-changes indicator while it has unsaved changes.
- **FR-012**: The three Related tabs MUST share the look and interaction of Asset Management's Related Assets / Related Inits tabs: a list of current links (target, relation type, rationale, remove action), and an add row with a target picker, a relation type picker, an optional rationale and an *Add* button, with inline messages for missing fields and duplicates.

**Links**

- **FR-013**: Related processes MUST link a source process to a target process with a relation type from the dedicated **Process Relation Type** list (FR-013a) and an optional rationale. The same pair may be linked once per relation type; a process cannot be related to itself. The shared relation type list MUST NOT be accepted for process-to-process links.
- **FR-013a**: The Process Relation Type list MUST contain these values, in English and Spanish, each with a fixed meaning (source → target) and its BPMN counterpart, so that the Value Chain and Process Map can render them in BPMN notation:

  | Value | Label (en / es) | Meaning (source → target) | BPMN counterpart |
  |-------|-----------------|---------------------------|------------------|
  | PRECEDES | Precedes / Precede a | The target starts when the source ends; orders the flow (e.g. the primary chain). | Sequence flow |
  | TRIGGERS | Triggers / Dispara | An event raised by the source starts the target. | Event (message/signal) start |
  | CALLS | Calls / Invoca a | The source invokes the target as a reusable process. | Call activity |
  | FEEDS_INTO | Feeds Into / Alimenta a | An output of the source is an input of the target. | Data association (data object) |
  | INTERACTS_WITH | Interacts With / Interactúa con | The two exchange information without a flow order; undirected. | Message flow (between pools) |
  | SUPPORTS | Supports / Apoya a | The source enables the target (typically a support activity for a primary one). | Association |
  | GOVERNS | Governs / Regula a | The source sets rules or controls for the target. | Association (annotation) |

- **FR-013b**: The server MUST enforce type compatibility so the Value Chain stays coherent: **Supports** is accepted only from a Support process to a Primary process, and **Precedes** only between two processes of the same type. Triggers, Calls, Feeds Into, Interacts With and Governs accept any combination. An incompatible link MUST be refused as a validation error naming the rule; the target picker MUST offer only processes compatible with the selected relation type.
- **FR-014**: Related assets and Related inits MUST link a process to an active asset / initiative with a relation type (from the same shared list) and an optional rationale. The same pair may be linked once per relation type. The process–asset and process–initiative link definitions gain the relation type as part of their identity, changed in place in the existing SQL definition and seed files (pre-production; no separate migration), and every seeded link receives a relation type.
- **FR-015**: Removing a link MUST be logical (kept, no longer shown as active); adding an identical link again MUST restore it instead of creating a duplicate.
- **FR-016**: Target pickers MUST offer only active records, exclude the current process (Related processes) and show enough to identify the target (code and name for processes; name and category for assets; name for initiatives).
- **FR-017**: Links MUST be read and written only through the owning process: managing a process's links requires edit rights on Process Management.

**Access**

- **FR-018**: Every Process Management operation MUST require an authenticated user holding the Process Management privilege; writes require its edit right. Administrator and Administrative profiles keep the access they hold today; Collaborator and Reviewer remain without access.
- **FR-019**: All user-facing text MUST exist in English and Spanish.

### Key Entities

- **Process**: a unit of how the organization operates. Identified by a permanent code; has name, description, type (Primary / Support), optional parent process, optional business unit, owner, reference, status, tags, detail and an active flag.
- **Process relation**: a link from one process to another with a process relation type and rationale; unique per (source, target, type), directed except for *Interacts With*.
- **Process relation type**: a dedicated list of the seven BPMN-oriented relation types of FR-013a, separate from the shared relation type list.
- **Process–asset link**: a link from a process to a library asset with a relation type and rationale; unique per (process, asset, type).
- **Process–initiative link**: a link from a process to an initiative with a relation type and rationale; unique per (process, initiative, type).
- Referenced, not owned: **Business unit**, **User** (owner), **Asset**, **Initiative**, shared **Relation type** list, **Process type** and **Process status** lists.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A process owner can create a process with one link of each kind in under 3 minutes, in a single save.
- **SC-002**: Adding or removing a link in any Related tab and saving takes no more than 3 interactions after opening the tab.
- **SC-003**: A user who already knows Asset Management's Related tabs completes the same task in the three process Related tabs on first attempt without guidance (identical controls, labels and messages pattern).
- **SC-004**: 100% of invalid operations (duplicate code, parent cycle, self relation, duplicate link, incompatible Supports/Precedes link, type change that breaks existing links, removal with children, status move outside the lifecycle, non-Draft status at creation, missing privilege) are refused with a message that tells the user what to fix, and leave data unchanged.
- **SC-005**: The full seeded inventory (all value-chain activities and sub-processes) loads in the list and is searchable in under 2 seconds.
- **SC-006**: Saving one Related tab never changes data belonging to another tab (verified for every tab combination).

## Assumptions

- **Core Fields is the first tab.** The requested order (Related processes, Related assets, Related inits) applies to the link tabs, which follow a Core Fields tab holding the process's own data, as in Asset Management.
- **Access is by module privilege only.** There is no per-process permission table; the owner is informational and does not grant or restrict access. A per-process grant model, Discussion, History and Permissions tabs are out of scope.
- **Links are shown from the process being edited (outgoing).** The Related processes tab lists links whose source is the current process, like Asset Management's edit tab; the only exception is *Interacts With*, which is undirected and shows in both processes. Showing incoming links read-only is left to the Process Map story.
- **Value Chain (HU-PR05) and Process Map (HU-PR06) are out of scope**; this feature only provides the data and maintenance they will read.
- Process–asset and process–initiative links use the relation type list Asset Management already uses (Depends On, Related To, Similar To, Used By, …); process-to-process links use the dedicated Process Relation Type list. Both show in the current language.
- This feature defines and maintains the BPMN-oriented relations; drawing them (Value Chain, Process Map) belongs to HU-PR05/HU-PR06.
- Owners are chosen among active users; the creator is the default owner.
- No status-change history is recorded (there is no activity log for processes).
- Seeded processes stay Published as they are; the lifecycle governs changes made through Process Management, not seed data.
- The seeded process–asset and process–initiative links receive the relation type *Related To* unless a more specific type is evident from their rationale. Databases already provisioned must be recreated (`make rebuild`) or have the equivalent change applied by hand once; no migration script is produced, per the user's decision.
- Reading assets and initiatives in the pickers does not require Asset Management or Initiative Management privileges; the picker only exposes names needed to identify the target.
