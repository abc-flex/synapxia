# Feature Specification: Process Landscape Views (Value Chain + Process Map)

**Feature Branch**: `010-process-landscape-views`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Value Chain (HU-PR05) and Process Map (HU-PR06), specified jointly as two complementary read-only views of the Processes domain. The Value Chain is the macro view (what creates value), the Process Map the navigable view (how it connects). Clicking a process in the value chain opens the map focused on it, and the map can lead back to the chain; both can open the process's details. Both views share one bounded read of the process landscape. P1 Value Chain, P2 Process Map."

## Context

Covers user stories **HU-PR05 Value Chain** and **HU-PR06 Process Map** (see `docs/user-stories/07-proc.md`):

> As a **manager**, I want to **see the processes arranged as a value chain**, primary activities across the flow and support activities underneath, **so that** I understand how operations create value end to end — and where AI could help.

> As a **manager**, I want to **see a process map** — the hierarchy of processes and the relations between them — **so that** the landscape is navigable visually.

What already exists (Process Management, SpecKit 009):

- **Processes** with a permanent code, name, description, type (Primary or Support), optional parent (processes nest, the hierarchy is acyclic), business unit, owner, status (Draft, Review, Published, Deprecated), tags and an active flag. The seed holds the nine value-chain activities (five Primary, four Support) and their sub-processes, all Published.
- **Process relations** typed with the BPMN-oriented Process Relation Type list: Precedes (sequence flow), Triggers (event start), Calls (call activity), Feeds Into (data association), Interacts With (message flow, undirected), Supports and Governs (association). Rules already enforced: Supports only from a Support process to a Primary one; Precedes only between processes of the same type. The seed chains the primary activities with Precedes (Inbound Logistics → Operations → Outbound Logistics → Marketing & Sales → Service) and links each support activity to a primary one with Supports.
- **Process–asset** and **process–initiative** links (typed, with a rationale).
- The sidebar already has the options **Value Chain** (`/proc/value_chain`) and **Process Map** (`/proc/process_map`). Administrator and Administrative hold both with edit rights; Collaborator and Reviewer hold both **read-only**, and hold no Process Management privilege.

What this feature adds: the two read-only views, a shared read-only process detail panel, and navigation between the views. Neither view creates, edits or removes anything.

## Clarifications

### Session 2026-10-24

- Q: Which statuses do the views show? → A: Every active process except Deprecated (Draft, Review and Published), with the status marked visually on each block and node so drafts are not mistaken for the official landscape (option C). The rule applies to both views and to the counts.
- Q: How deep does the Value Chain go? → A: Top-level processes, each expandable one level to list its direct sub-processes with their own counts (option B). Deeper levels are not listed in the chain; their links count in their level-one ancestor, and the full depth is explored in the Process Map.
- Q: How is "where AI could help" surfaced? → A: Counts, plus highlighting the processes with no linked assets and no linked initiatives, plus an *Only opportunities* switch that dims every other process (option C).

### Session 2026-10-25 (changes after the first implementation)

- **Value Chain compact.** The whole chain fits one screen: smaller blocks sharing the width, no star or "AI opportunity" badge. An opportunity is told by its color alone, explained by a legend next to the *Only opportunities* switch, which stays.
- **Detail panel layout** (both views). A small title with the process name and an arrow button that closes the panel, then the properties. Outgoing relations, Incoming relations, Linked assets and Linked initiatives are tabs, and only the tab body scrolls so the panel stays compact. The action buttons sit at the bottom.
- **Process Map legend** can be shown or hidden with a button next to +, − and Fit.
- **Process Map drill-down replaces nested expansion.** A process's "+" no longer stacks its sub-processes inside it: it replaces the diagram with that process's internal diagram, drawn BPMN-style (its sub-processes ordered by their sequence flows, start and end events, and the outside processes they relate to). A Back button and a breadcrumb return to the main diagram.
- **Second review (same day).**
  - The panel was drawn under the application's top bar, which hid its title and close arrow. It now sits above the bar, with roomier spacing.
  - The seed gains relations between sub-processes, so every activity's internal diagram has a flow with a start and an end. Each activity has its own Precedes chain, plus a few Feeds Into, Triggers, Supports, Governs and Interacts With links inside and across activities, all within the compatibility rules (`db/sql/72-proc-insert.sql`).
  - In the Value Chain, the support bands are taller, the counts use the sidebar's AI Library and Initiatives (rocket) icons, and the Margin chevron spans the primary and the support activities, as in Porter's diagram.
- **Third review (same day).**
  - **Internal diagrams looked empty because of a bug.** A focus left on the drilled process faded every connector of its internal diagram to 10%. Focus now dims only when the focused process is drawn at the current level, and opening a level clears it.
  - Both pages have a one-row toolbar with shorter texts. The Process Map legend is a narrow panel docked on the right, opened by a larger "Legend" button under +, − and Fit; it separates the start and end events and adds the opportunity and outside-process marks.
  - The panel title shows the code before the name and closes with an "x". Its buttons are shorter and stay on one line.
  - The Value Chain shows the code more prominently than the name, with sub-processes as "code name". "Margin" is one size larger and centered on the chevron's colored area.
- **Fourth review (same day).**
  - In the Process Map, the "Legends" button (plural) sits beside +, − and Fit at the same height and type size, and the Primary and Support lane titles are larger, bolder and colored.
  - The request for expand/collapse-all plus an *Only opportunities* that sees expanded processes was applied to the **Value Chain**, the view that has both expansion and that switch. An *Expand all / Collapse all* button opens every block. With *Only opportunities* on:
    - a block that is not an opportunity but has opportunity sub-processes stays lit with an amber ring while collapsed;
    - once expanded, it dims only its own header, so its opportunity sub-processes stand out;
    - blocks with no opportunity anywhere are dimmed whole.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the value chain (Priority: P1)

A manager opens **Value Chain** and sees the organization's processes laid out as a Porter value chain: the primary activities as a row of blocks ordered along the flow, ending in the "value" (margin) marker, and the support activities as horizontal bands spanning underneath (or above) them. Each block shows the process name, its code and how many library assets and initiatives are linked to it, so the manager sees at a glance which parts of the operation already have AI support and which do not.

**Why this priority**: it is the headline view of the module ("identify stages where AI can create impact") and delivers value on its own, without the map.

**Independent Test**: as a Collaborator (read-only on Value Chain), open `/proc/value_chain` and see the five primary activities in the order Inbound Logistics → Operations → Outbound Logistics → Marketing & Sales → Service and the four support activities as bands; Operations shows its asset count (including those of its sub-process Software Development) and Technology Development shows its initiative count.

**Acceptance Scenarios**:

1. **Given** the seeded processes, **When** the user opens Value Chain, **Then** the primary activities appear as one row ordered along their Precedes chain, and the support activities appear as bands in a separate area, with names in the stored language and type labels in the current language.
2. **Given** primary processes connected by Precedes, **When** the chain is drawn, **Then** each process appears after every process that precedes it; primary processes not connected by Precedes appear after the connected ones, in code order.
3. **Given** a process block, **When** the user looks at it, **Then** it shows the number of distinct active assets and the number of distinct active initiatives linked to it or to any of its active sub-processes.
4. **Given** a process (top-level or sub-process) with neither assets nor initiatives, rolled up, **When** the chain is drawn, **Then** it is highlighted as an AI opportunity by its color, explained by a legend (no badge); **When** the user turns on *Only opportunities*, **Then** every other process is dimmed (still visible, so the chain keeps its shape), and turning it off restores the normal view.
5. **Given** a top-level block, **When** the user expands it, **Then** its direct active sub-processes are listed inside it with their own rolled-up counts; deeper levels are not listed, and collapsing hides the list again. Blocks open collapsed.
6. **Given** a process in Draft or Review, **When** the chain is drawn, **Then** its block shows its status with a distinct marker; Published blocks carry no marker and Deprecated processes are not shown.
7. **Given** the chain, **When** the user filters by business unit, **Then** only processes of that unit (and the ancestors needed to place them) are shown, and the counts recompute over what is shown.
8. **Given** a block or a listed sub-process, **When** the user selects it, **Then** the read-only process detail panel opens (User Story 3), with a *Show in Process Map* action.
9. **Given** a user without the Value Chain privilege, **When** they open `/proc/value_chain`, **Then** access is refused as for any other module option.

---

### User Story 2 - Navigate the process map (Priority: P2)

A manager opens **Process Map** and sees the process landscape as a diagram: each top-level process is a node, and the relations between processes are drawn as connectors whose style follows their BPMN meaning. The "+" marker of a process opens its internal diagram in place of the main one (BPMN style: sub-processes in sequence-flow order, start and end events, outside processes in a lane below), with Back to return. The manager can filter which relation types are drawn, show or hide the legend, search a process, and focus on one process to see its direct neighborhood.

**Why this priority**: it is the detailed, navigable complement of the value chain; useful once the chain shows where to look.

**Independent Test**: as a Reviewer (read-only on Process Map), open `/proc/process_map`, see the nine activities with the Precedes connectors between primaries and the Supports connectors from support to primary, open Operations' internal diagram with its "+" and come back with Back, hide the Supports type with the relation filter, then focus on Operations and see only it, its parent/children and its direct relations highlighted.

**Acceptance Scenarios**:

1. **Given** the seeded landscape, **When** the user opens Process Map, **Then** every shown process appears as a node labeled with its name and code (with the Draft/Review marker of FR-002 when applicable), nodes are visually grouped by type (Primary / Support) in two lanes, and only top-level processes are drawn; a process with sub-processes carries BPMN's collapsed sub-process "+" marker.
2. **Given** a process with sub-processes, **When** the user clicks its "+", **Then** the diagram is replaced by that process's internal diagram: a pool named after it with its active sub-processes laid out along their Precedes relations (start event before the first, end event after the last; sub-processes outside any flow on a row of their own), every other relation among them, and the outside processes they relate to in a lane underneath. Sub-processes with their own sub-processes carry the "+" too. **When** the user clicks Back (or a level in the breadcrumb), **Then** the previous level is shown, up to the main diagram.
3. **Given** relations between processes, **When** the map is drawn, **Then** each relation appears as a connector from source to target styled by type, following its BPMN counterpart: Precedes as a solid arrow (sequence flow), Triggers as an arrow starting at an event marker, Calls as a bold-bordered arrow (call activity), Feeds Into as a dotted arrow (data association), Interacts With as a dashed connector without arrowheads (message flow, undirected), Supports and Governs as dotted association lines with different end markers. A legend lists every type in the current language.
4. **Given** a relation whose source or target is a sub-process not drawn at the current level, **When** the map is drawn, **Then** the connector is drawn to its nearest drawn ancestor, and several such connectors between the same two nodes with the same type are drawn once with a count.
5. **Given** the relation filter, **When** the user unchecks a relation type, **Then** its connectors disappear and no box moves. **Given** the legend button next to +, − and Fit, **When** the user clicks it, **Then** the legend and filter panel is shown or hidden (remembered on that browser).
6. **Given** the search box, **When** the user types part of a code or name and picks a result, **Then** the map opens the level where that process is drawn and focuses on it.
7. **Given** a focused process, **When** the map is drawn, **Then** the process, its parent, its children and every process directly related to it (incoming and outgoing) are highlighted and the rest is dimmed; clearing focus restores the full view.
8. **Given** a node, **When** the user selects it, **Then** the read-only process detail panel opens (User Story 3), with a *Show in Value Chain* action.
9. **Given** a user without the Process Map privilege, **When** they open `/proc/process_map`, **Then** access is refused.

---

### User Story 3 - Move between the views and read a process's details (Priority: P2)

From either view, the manager opens a read-only detail panel for a process: its core fields, its incoming and outgoing process relations, and its linked assets and initiatives. From the panel they jump to the other view focused on that process, and, if they also manage processes, open it in Process Management.

**Why this priority**: it is what makes the two views complementary instead of two separate pictures; it depends on at least one of the views existing.

**Independent Test**: in Value Chain select Operations, read in the panel that it is preceded by Inbound Logistics, precedes Outbound Logistics and is supported by Technology Development and Human Resource Management, then click *Show in Process Map* and land on the map focused on Operations; from there click *Show in Value Chain* and land on the chain with Operations highlighted.

**Acceptance Scenarios**:

1. **Given** a process selected in either view, **When** the panel opens, **Then** it starts with a small title (the process name and code) and an arrow button that closes it, then shows type, status, parent, business unit, owner, description and tags, labels in the current language; Outgoing relations, Incoming relations, Linked assets and Linked initiatives are tabs whose body alone scrolls, and the action buttons sit at the bottom.
2. **Given** the panel, **When** the user reads the relations section, **Then** it lists outgoing and incoming relations separately, each with the other process, the relation type in the current language and the rationale; Interacts With appears once, without direction.
3. **Given** the panel, **When** the user reads the assets and initiatives sections, **Then** each link shows the asset (name, category) or initiative (name), the relation type and the rationale, and the section states how many come from sub-processes.
4. **Given** the panel opened from Value Chain, **When** the user clicks *Show in Process Map*, **Then** the map opens focused on that process; **Given** the panel opened from Process Map, *Show in Value Chain* opens the chain with that process (or the top-level process containing it) highlighted.
5. **Given** a link to the other view, **When** the user does not hold that view's privilege, **Then** the action is not offered.
6. **Given** a user who also holds Process Management, **When** the panel is open, **Then** an *Open in Process Management* action opens that process's edit dialog; users without that privilege do not see the action.
7. **Given** a focused view, **When** the user copies its address and opens it later, **Then** the same view opens focused on the same process.

---

### Edge Cases

- **No processes to show** (empty inventory, or a filter that excludes everything): each view shows an empty-state message instead of an empty diagram.
- **Precedes cycle among primary processes** (allowed by Process Management, since BPMN flows may loop back): the chain still draws every primary process once; the processes in the cycle are placed in code order at the point where the cycle is entered, and the panel lists the full relations.
- **A primary process with no Precedes links**: placed after the connected chain, in code order (see Acceptance Scenario 1.2).
- **Sub-processes of a type different from their parent** (e.g. a Support sub-process under a Primary parent): in the value chain they appear under their parent; in the map they keep their own type styling.
- **Processes removed logically**: never shown in either view, and their links are not counted; a relation to a removed process is not drawn.
- **Links to removed assets or initiatives**: not counted and not listed in the panel.
- **A process whose parent is not shown** (e.g. a Deprecated parent, or one excluded by the unit filter): it is attached to the nearest shown ancestor, or shown at top level if none is shown.
- **Large landscapes**: the views stay usable with several hundred processes and relations (see SC-003); the map draws one level at a time so each picture stays readable.
- **A focus address pointing to a process that no longer exists or is not shown**: the view opens unfocused with a short message.
- Both views are read-only: no create, edit, move or remove action is offered on the diagrams themselves.

## Requirements *(mandatory)*

### Functional Requirements

**Shared landscape**

- **FR-001**: Both views MUST read the same process landscape: the shown processes (code, name, type, parent, business unit, owner, status), the active relations between them, and per process the distinct counts of active linked assets and active linked initiatives, own and rolled up over its active sub-processes. The landscape MUST be obtained in a single bounded read per view load, not one request per process.
- **FR-002**: The processes shown MUST be the active processes in Draft, Review or Published; Deprecated processes MUST NOT be shown or counted. Draft and Review processes MUST carry a visible status marker in both views. The same rule MUST apply to both views, to the counts and to the detail panel's relation lists.
- **FR-003**: Both views MUST offer a business-unit filter; the Process Map additionally offers the relation-type filter (FR-011) and search (FR-013).
- **FR-004**: Type, status and relation type labels MUST follow the language chosen in the header and switch with it, as every list value in the application does.

**Value Chain (HU-PR05)**

- **FR-005**: The Value Chain MUST place primary processes in one ordered row and support processes in a separate band area, as in Porter's value chain, with a value/margin marker at the end of the primary row.
- **FR-006**: The order of primary processes MUST be derived from the Precedes relations among them: a process appears after every process that precedes it; processes not connected by Precedes follow the connected ones in code order; cycles are broken as described in Edge Cases. Support bands are ordered by code. The order is computed, not stored, so maintaining Precedes links in Process Management is how the chain is reordered.
- **FR-007**: Each block and listed sub-process MUST show name, code, its status marker (FR-002), the asset count and the initiative count of FR-001 (rolled up), and MUST be highlighted as an AI opportunity when both counts are zero, by color alone, explained by a legend. An *Only opportunities* switch MUST dim every process that is not an opportunity without removing it from the layout. The chain MUST fit one screen (blocks share the width) with the seeded landscape.
- **FR-008**: The Value Chain MUST show top-level processes, each expandable one level to list its direct active sub-processes; deeper levels MUST NOT be listed in the chain, and their links count in their level-one ancestor's roll-up.
- **FR-009**: Selecting a block MUST open the shared detail panel (FR-014).

**Process Map (HU-PR06)**

- **FR-010**: The Process Map MUST draw one level at a time: the main diagram (top-level processes in a Primary and a Support lane) or the internal diagram of one process (Acceptance Scenario 2.2), reached through BPMN's collapsed sub-process "+" marker and left through Back or the breadcrumb. The drilled process is part of the address.
- **FR-011**: The Process Map MUST draw every active relation between the processes of the current level as a connector from source to target, styled per relation type after its BPMN counterpart (Acceptance Scenario 2.3), with a legend that can be shown or hidden, and MUST let the user show or hide each relation type without moving any box. Interacts With MUST be drawn undirected. Hierarchy is never drawn as a relation.
- **FR-012**: Connectors whose ends are sub-processes not drawn at the current level MUST be redirected to the nearest drawn ancestor and merged per (visible source, visible target, type), showing how many relations they stand for; connectors that end up from a node to itself after merging MUST NOT be drawn.
- **FR-013**: The Process Map MUST offer search by code or name; choosing a result opens the level where it is drawn and focuses it. Focusing a process MUST highlight it, its parent, its children and its directly related processes (both directions) and dim the rest, until focus is cleared.

**Detail panel and navigation**

- **FR-014**: Both views MUST share one read-only process detail panel showing the core fields, outgoing and incoming relations (Interacts With once, undirected), linked assets and linked initiatives with relation type and rationale, distinguishing links of the process itself from those of its sub-processes. Each linked asset MUST link to its read-only detail in Explore for its category (`/lib/explore?code=<category>&asset=<id>`), and each linked initiative to its detail in Explore Initiatives (`/inits/explore?initiative=<id>`). When Explore Initiatives does not list that initiative (not accepted yet, or not shared with the caller), the page MUST say so instead of opening nothing. Layout: a small title with an arrow that closes the panel, the properties, the four lists as tabs whose body alone scrolls, and the actions at the bottom.
- **FR-015**: The panel MUST offer *Show in Process Map* (from the chain) and *Show in Value Chain* (from the map) when the user holds the target view's privilege, opening the other view focused on that process (or, in the chain, its top-level process).
- **FR-016**: The panel MUST offer *Open in Process Management* only to users holding the Process Management privilege; it opens that process's existing edit dialog.
- **FR-017**: A view's focus (selected process), filters and the *Only opportunities* switch MUST be reflected in its address, so that copying the address reproduces the same view.

**Access**

- **FR-018**: Opening the Value Chain and reading its landscape MUST require the Value Chain privilege; the Process Map MUST require the Process Map privilege. Read access is enough for everything in this feature; neither view needs edit rights. Holding either view's privilege MUST be enough to read the landscape and the detail panel, without the Process Management privilege. Current grants are kept: Administrator and Administrative hold both views, Collaborator and Reviewer hold both read-only.
- **FR-019**: The views MUST NOT offer, and their reads MUST NOT allow, any create, edit or remove operation.
- **FR-020**: All user-facing text MUST exist in English and Spanish.

### Key Entities

- **Process landscape**: the read model shared by both views — the shown processes with their hierarchy, the active relations among them and, per process, the own and rolled-up counts of linked assets and initiatives. Derived from existing data; nothing new is stored.
- **Value chain arrangement**: the computed placement of processes — primary row order (from Precedes), support bands, depth — derived from the landscape, never stored.
- **Map view state**: which parents are expanded, which relation types are shown, the focused process and the filters; held by the viewer and reflected in the address, not stored on the server.
- Referenced, not owned: **Process**, **Process relation** and **Process relation type**, **Process–asset link**, **Process–initiative link**, **Business unit**, **User** (owner), **Asset**, **Initiative** (all from Process Management and the existing modules).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager opening the Value Chain can name, within 30 seconds and without guidance, the primary activity that comes first, the one that comes last, and which activities have no linked assets or initiatives; with *Only opportunities* on, they can list every opportunity sub-process of a top-level activity in one more interaction (expanding it).
- **SC-002**: From any process in the Value Chain, the user reaches the same process focused in the Process Map (and back) in at most 2 interactions.
- **SC-003**: With the seeded landscape each view is fully drawn within 2 seconds of opening; with 300 processes and 600 relations it is drawn within 4 seconds and stays responsive to expand, filter and focus actions (each under 1 second).
- **SC-004**: The counts shown in both views and in the panel equal an independent count of active links over the shown processes, for 100% of processes (verified against the seed).
- **SC-005**: 100% of the relation types in the Process Relation Type list are drawn with a distinct style that matches the legend, and every relation shown in the panel for a process is drawn on the map when its type is enabled and its ends are visible.
- **SC-006**: Users holding only a view privilege (Collaborator, Reviewer) can use that view and its panel end to end, and every attempt to reach a view or a write operation they lack is refused.

## Assumptions

- **Order from Precedes, not a new column.** Process Management already restricts Precedes to processes of the same type, and the seed chains the five primary activities with it, so the chain order is derived from data the owners already maintain; no sort column is added. Support bands have no flow order and are sorted by code.
- **Counts roll up.** A block or node counts the distinct assets and initiatives linked to it and to its active sub-processes, because links are mostly seeded on sub-processes (e.g. Software Development under Operations); the panel distinguishes own links from sub-process links.
- **Which relations each view draws.** The Value Chain draws structure only: the primary row order (from Precedes) and the support bands; it does not draw relation connectors, since Supports links are implied by the band layout and the detailed connections belong to the map. The Process Map draws every relation type.
- **Access by view privilege.** The views and their landscape read are gated by their own options (`Value Chain`, `Process Map`), which Collaborator and Reviewer already hold read-only; reading the landscape therefore does not require Process Management. The detail panel shows asset and initiative names and categories without requiring library or initiative privileges, as Process Management's pickers already do.
- **Read-only views.** All maintenance stays in Process Management; the views only read and link to it.
- **No new stored data and no schema change.** Expanded parents, enabled relation types and focus are viewer state kept in the address (and optionally remembered in the browser), not on the server.
- **Export** (image or file) of either view is out of scope.
- **Process names and descriptions** are shown as stored (they are not translated); only list values follow the language switch.
- **The diagrams are for viewing**, not a BPMN modeller: no dragging nodes to change data, no saved layouts. Node positions are computed automatically each time.
