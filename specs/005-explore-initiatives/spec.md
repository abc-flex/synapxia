# Feature Specification: Explore Initiatives, Propose Initiative & Initiative Notifications

**Feature Branch**: `005-explore-initiatives`

**Created**: 2026-09-24

**Status**: Draft

**Input**: User description: "La historia de usuario de Explore Initiatives es similar a Explore Category, pero en lugar de listar una de las categorías de los Assets, lista las [iniciativas], y se deben tener en cuenta las siguientes consideraciones: Se deben mantener los filtros de buscar mis favoritos y privilegios, considerando que el de privilegios debe tener solo las opciones de: Public, Shared with me, My role, My team, My unit, My projects; con un funcionamiento similar a como lo hacen en Explore Category. Las tarjetas que muestran las iniciativas pueden mantener todos los elementos que tienen las tarjetas de los activos en Explore Category, exceptuando la versión del activo; sin embargo, quiero que los muestres en una forma visual diferente dado que típicamente son menos iniciativas que activos en una categoría (podrían ser en la línea completa o mostrando cada iniciativa de otra forma que visualmente sea atractivo). Debe mantener la opción de '+ Proponer'. Para el Propose Initiative se deben implementar solo tres pestañas: 1- Core Fields con el mismo comportamiento que en Propose an asset, incluido el campo reviewer; botones 'Back to initiatives' y 'Diagnosis questions >'. 2- Diagnosis Questions, basada en la tabla Diagnostics para guardar las respuestas del proponente a las preguntas de la tabla Criterias; botones 'Back to initiatives', 'Request diagnosis' y 'Related Assets >'. 3- Related Assets con el mismo comportamiento que en Propose an asset pero basada en la tabla Asset_Inits; botones 'Back to initiatives' y 'Request diagnosis'. Cuando una iniciativa es propuesta se debe presentar la respectiva notificación; la ventana pop-up de la campana se debe dividir en dos: notificaciones de los activos y notificaciones de las iniciativas, con comportamiento similar pero con las equivalencias en estados de iniciativas y tipos de colaboraciones, basadas en la tabla collaborations. Las notificaciones de las iniciativas también deben aparecer en el Account Menu, sección MY WORKSPACE, en la opción My Initiative Requests, justo debajo de My Asset Requests, con un comportamiento similar."

Covers user stories **HU-IN04 Explore Initiatives**, **HU-IN05 Propose Initiative**, **HU-IN13 Initiative Notifications** and **HU-IN14 My Initiative Requests**, **HU-IN06 Initiative Detail**, **HU-IN15 Diagnosis of the Initiative**, **HU-IN16 Modify Initiative** and **HU-IN17 User Acknowledgment of Initiative Notification**, plus the Propose Initiative behaviour of the tab stories **HU-IN07 – HU-IN09** (see `docs/user-stories/05-inits.md`). Together they close the full propose → diagnose → modify → acknowledge loop for initiatives.

## Problem Context

Initiatives are the platform's AI-adoption opportunities. Initiative Management (spec 004) now lets owners curate the initiatives they are responsible for, but it has no way for anyone to *start* one. An initiative only enters the system by being proposed and diagnosed. Today there is no way to propose one, no place where the wider community can browse the portfolio, and no signal telling a reviewer that a diagnosis is waiting for them.

The AI Library already solved each of these problems for assets:

- **Explore Category** is a card gallery of the assets a person can see, with favorites and privilege filters and a "+ Propose" entry point.
- **Propose an asset** is a stepped wizard (Core Fields → … → Related), ending in "Propose for review". It assigns a reviewer and records the proposal.
- The **notification bell** lists what is waiting on the user, and **My Asset Requests** is the durable record of everything they have taken part in.

Users expect the same experience for initiatives, with these differences:

1. **Fewer items, richer cards.** A person typically sees far fewer initiatives than assets in one category, so the gallery should give each initiative more room and a visually distinct presentation, rather than reusing the dense asset grid.
2. **Diagnosis replaces characterization.** The proposer answers every diagnosis criterion on its own scale, and the reviewer later answers the same criteria.
3. **Collaborations replace actions.** Initiative workflow activity is recorded as collaborations. They have their own types and status equivalences (see Key Entities).

## Clarifications

### Session 2026-09-24

- Q: Which initiative statuses does the Explore gallery show? → A: Accepted, In Progress and Delivered. This is the living portfolio: everything past a positive diagnosis and not yet archived. Proposals still in diagnosis (Activated, Feedback) and Rejected or Archived initiatives are not shown. Their participants follow them from My Initiative Requests.
- Q: Are the Diagnosis, Modify and Acknowledgment pages part of this feature? → A: Yes. This feature delivers the full loop, as the asset side did, so every notification is actionable end to end.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Propose an initiative and request its diagnosis (Priority: P1)

As a collaborator, I want to propose a new initiative in three steps (describe it, answer the diagnosis questions, optionally link related assets) and request its diagnosis from a reviewer, so that my idea enters the evaluation workflow.

**Why this priority**: No initiative can exist without being proposed. Every other story in this feature (the gallery's content, the notifications, the requests list) depends on proposals being recorded.

**Independent Test**: As a non-admin user, open Propose Initiative, fill in Core Fields, answer every diagnosis question, optionally add a related asset, and press "Request diagnosis". Confirm that the initiative now exists in Activated status, with your answers, links, a reviewer assignment and management access for you and the reviewer.

**Acceptance Scenarios**:

1. **Given** a user opens Propose Initiative, **When** the page loads, **Then** exactly three tabs are shown in this order: Core Fields, Diagnosis Questions, Related Assets. Core Fields is active.
2. **Given** the Core Fields tab is active, **When** the user looks at the bottom of the form, **Then** two buttons are shown: "Back to initiatives" and "Diagnosis questions >".
3. **Given** the Core Fields tab has a required field empty, **When** the user presses "Diagnosis questions >", **Then** the wizard stays on Core Fields and marks each missing required field inline.
4. **Given** the Diagnosis Questions tab is active, **When** the user looks at the bottom, **Then** three buttons are shown: "Back to initiatives", "Request diagnosis" and "Related Assets >".
5. **Given** the Diagnosis Questions tab, **When** it renders, **Then** every active diagnosis criterion appears as a question. Each question offers only the answer options of that criterion's own scale, in the user's language, and has an optional rationale field.
6. **Given** at least one criterion is unanswered, **When** the user presses "Request diagnosis", **Then** nothing is submitted, and each unanswered question is marked inline.
7. **Given** the Related Assets tab is active, **When** the user looks at the bottom, **Then** two buttons are shown: "Back to initiatives" and "Request diagnosis".
8. **Given** the Related Assets tab, **When** the user picks a target asset and a relation type, adds an optional rationale and presses "Add relation", **Then** the relation is staged in a list below the form and can be removed before submitting. Nothing is saved until the proposal is submitted.
9. **Given** the user tries to stage the same asset with the same relation type twice, **When** they press "Add relation", **Then** the duplicate is refused. The same asset may be staged once per distinct relation type.
10. **Given** all required Core Fields are valid and every criterion is answered, **When** the user presses "Request diagnosis" (on either step that offers it), **Then** the initiative is recorded in one all-or-nothing operation:
    - the initiative is saved with status Activated;
    - one diagnosis answer is saved per criterion, as the proposer's answer;
    - each staged related-asset link is saved;
    - a completed Activation collaboration is recorded for the proposer;
    - a pending Diagnosis collaboration is recorded for the reviewer;
    - management access is granted to both the proposer and the reviewer.
11. **Given** the proposal succeeded, **When** the result is shown, **Then** a blocking confirmation dialog explains that the initiative was sent for diagnosis and where to follow it (My Initiative Requests). Only after the user acknowledges it are they returned to Explore Initiatives.
12. **Given** the proposal failed, **When** the result is shown, **Then** the same kind of blocking dialog explains the failure, and the user stays on the wizard with their entries intact.
13. **Given** any step, **When** the user presses "Back to initiatives", **Then** they return to Explore Initiatives. Nothing has been saved.

---

### User Story 2 - Choose the reviewer exactly as in Propose an asset (Priority: P1)

As a proposer, I want the Core Fields tab to offer a reviewer field that behaves exactly as in Propose an asset, so that the right person diagnoses my initiative and I cannot review my own proposal.

**Why this priority**: A proposal without a valid reviewer produces an assignment nobody can act on, so the workflow stalls at its first step.

**Independent Test**: Open Propose Initiative first as a Reviewer-profile user, then as an Administrator. Compare the reviewer lists, then submit without picking a reviewer.

**Acceptance Scenarios**:

1. **Given** a user opens Core Fields, **When** they open the reviewer field, **Then** it lists the users eligible to review, using the same rule as Propose an asset (Administrator, Administrative or Reviewer profile, or superuser).
2. **Given** the proposer is not an Administrator, Administrative or superuser, **When** the reviewer list is shown, **Then** the proposer does not appear in it. A direct attempt to name themselves as reviewer is also refused when the proposal is submitted.
3. **Given** the proposer leaves the reviewer empty, **When** they submit, **Then** a reviewer is chosen automatically by the same rule Propose an asset uses, and the proposer is never auto-assigned to review their own proposal.

---

### User Story 3 - Browse the initiative portfolio (Priority: P1)

As a collaborator, I want to browse the initiatives I have access to in an attractive gallery, filter it by favorites and by how each initiative is shared with me, and search it, so that I can see where the organization is investing.

**Why this priority**: This is the entry point of the whole module for most users, and the place the "+ Propose" action lives.

**Independent Test**: Sign in as a collaborator with grants reaching some initiatives through different scopes (public, user, team). Open Explore Initiatives and confirm that each privilege option shows exactly the initiatives shared through that scope, and that the favorites toggle narrows the list.

**Acceptance Scenarios**:

1. **Given** a user opens Explore Initiatives from the sidebar, **When** the page loads, **Then** they see a header with the option's name and icon, a search box, a "★ My favorites" toggle, a privileges filter, a "+ Propose" button and the initiatives gallery.
2. **Given** the privileges filter, **When** the user opens it, **Then** it offers exactly these six options in this order: Public, Shared with me, My role, My team, My unit, My projects. It has no "all" option and defaults to Public, as in Explore Category.
3. **Given** a privilege option is selected, **When** the gallery updates, **Then** only initiatives shared with the user through that scope remain.
4. **Given** the favorites toggle is on, **When** the gallery updates, **Then** only initiatives the user has marked as favorite remain. Toggling a card's star updates the filtered gallery immediately, without a reload.
5. **Given** the user types in search, **When** the gallery updates, **Then** only initiatives whose name, description or tags match remain.
6. **Given** each initiative card, **When** it renders, **Then** it shows every element an Explore Category asset card shows except the version: name, how long ago it was created, status, description, tags, favorite star, vote tally and a discussion count. It also shows the initiative's type, priority and expected impact.
7. **Given** a typical set of a few to a few dozen initiatives, **When** the gallery renders, **Then** it uses a layout clearly different from the asset card grid: each initiative gets a wider, more prominent presentation (for example, a full-width row per initiative) that remains readable on phones.
8. **Given** no initiative is reachable through the selected filters, **When** the gallery renders, **Then** an explanatory empty state is shown, and the "+ Propose" button stays available.
9. **Given** the user presses "+ Propose", **When** the page changes, **Then** Propose Initiative opens.
10. **Given** the user votes positive or negative on a card, **When** the vote is registered, **Then** the tally updates. Pressing the same vote again withdraws it, and each user holds at most one active vote per initiative.
11. **Given** the user clicks a card, **When** it opens, **Then** the initiative's read-mostly detail view (Initiative Detail) is shown. Core fields, diagnosis answers, related assets and history are read-only there, the discussion is interactive, and permissions are not shown.

---

### User Story 4 - See what is waiting on me, split between assets and initiatives (Priority: P2)

As a reviewer or proposer, I want the notification bell to separate asset notifications from initiative notifications, so that I can tell at a glance which kind of work is waiting on me.

**Why this priority**: Without it, a reviewer never learns that a diagnosis was assigned to them, and proposals stall silently. It depends on proposals existing (P1).

**Independent Test**: Propose an initiative naming reviewer R. Sign in as R and open the bell. The initiative's diagnosis request should appear under the initiatives section, and the asset section should be unchanged.

**Acceptance Scenarios**:

1. **Given** the user opens the bell, **When** the panel shows, **Then** it is divided into two sections, Assets and Initiatives. Each section shows its own count, and the badge on the bell shows the total of both.
2. **Given** a Diagnosis collaboration is pending for the user, **When** they open the Initiatives section, **Then** it shows one entry for that initiative, with the initiative name, what is expected ("Diagnosis requested") and how long ago.
3. **Given** the user has several collaborations on the same initiative, **When** the section renders, **Then** it shows only one entry per initiative, reflecting its latest collaboration.
4. **Given** an item is waiting on somebody else (for example, a proposal whose diagnosis the reviewer has not made yet), **When** the proposer opens the bell, **Then** it does not appear there. It appears only in My Initiative Requests.
5. **Given** the Initiatives section, **When** it renders, **Then** it lists only pending Diagnosis, Modification, Acceptance and Rejection collaborations directed at the user. No entry has a dismiss control; an entry leaves the list only when it is resolved.
6. **Given** the user clicks an initiative entry, **When** it opens, **Then** it routes to the page for that collaboration type (see FR-031).
7. **Given** the user has no initiative notifications, **When** they open the Initiatives section, **Then** an empty message is shown, with a link to My Initiative Requests.
8. **Given** the asset section, **When** the bell is split, **Then** the asset notifications behave exactly as before.

---

### User Story 5 - Keep a durable record of my initiative requests (Priority: P2)

As a proposer or reviewer, I want a My Initiative Requests page in the Account Menu, just below My Asset Requests, so that I can find every initiative I took part in, open or closed, without depending on a transient notification.

**Why this priority**: The bell shows only what is waiting on the user. A proposer whose initiative is waiting on the reviewer needs this page to follow it.

**Independent Test**: As the proposer of an initiative whose diagnosis is still pending, open My Initiative Requests. The initiative should appear once in the Pending view, marked as waiting on somebody else.

**Acceptance Scenarios**:

1. **Given** the user opens the Account Menu, **When** the My Workspace section shows, **Then** "My Initiative Requests" appears directly below "My Asset Requests".
2. **Given** the user opens My Initiative Requests, **When** the page loads, **Then** it lists every initiative the user took part in (those they proposed and those with collaborations directed at them), with exactly one entry per initiative.
3. **Given** the page, **When** it renders, **Then** it is split into two views, Pending and Handled, with the same wording and behaviour as My Asset Requests.
4. **Given** an in-motion entry, **When** it renders, **Then** it states whose action is awaited: the user's own, or somebody else's (naming the stage, for example "Waiting for diagnosis").
5. **Given** an entry awaiting the user, **When** it renders, **Then** it offers the button for the corresponding action, matching the bell's routing.
6. **Given** a proposal whose initiative was accepted but whose Acceptance notice the proposer has not acknowledged yet, **When** the page renders, **Then** the entry is still in the Pending view, awaiting the user, and is not shown as closed.
7. **Given** the user resolves an item in one surface (bell or requests page), **When** they return to the other, **Then** both reflect the change without a manual reload. The same live-refresh rules as the asset surfaces apply.

---

### User Story 6 - Diagnose a proposed initiative (Priority: P2)

As the assigned reviewer, I want to open a proposed initiative, see the proposer's answers, score each criterion myself, and accept it, reject it or request changes, so that only viable initiatives proceed.

**Why this priority**: Without a diagnosis, every proposal stays Activated forever and the portfolio never grows. It depends on proposals (P1) and the notification that routes the reviewer here (P2).

**Independent Test**: As reviewer R of an Activated initiative, open it from the bell. Score every criterion, choose "Request changes" with a message, and confirm the outcome: the status is Feedback, R's Diagnosis is handled, and the proposer has a pending Modification carrying the message.

**Acceptance Scenarios**:

1. **Given** R has a pending Diagnosis on an Activated initiative, **When** R opens it from the bell or from My Initiative Requests, **Then** the page shows the initiative's core fields, its related assets, and for each criterion the proposer's answer and rationale beside an input for R's own answer. Opening the page records nothing.
2. **Given** the diagnosis page, **When** R chooses Accept, Reject or Request changes, **Then** the decision is refused until R has answered every criterion. A message is required for Reject and Request changes and optional for Accept.
3. **Given** a valid decision, **When** R submits it, **Then** one all-or-nothing operation:
   - saves R's answer per criterion;
   - records R's Diagnosis collaboration as handled;
   - sets the initiative's status to Accepted, Rejected or Feedback;
   - records the initiative's resulting score;
   - records a pending Acceptance, Rejection or Modification collaboration for the proposer, carrying R's message.
4. **Given** the decision was saved, **When** the result is shown, **Then** R is taken to My Initiative Requests, where the initiative now appears as handled by them (or waiting on the proposer, after Request changes).
5. **Given** a user who is not the initiative's assigned reviewer, or an initiative that is not Activated, **When** someone tries to submit a diagnosis, **Then** it is refused, and nothing changes.

---

### User Story 7 - Modify and resubmit after a change request (Priority: P2)

As the proposer, I want to see the reviewer's feedback, edit my initiative and my diagnosis answers, and resubmit it to the same reviewer, so that the diagnosis cycle can continue.

**Why this priority**: "Request changes" is a dead end without it.

**Independent Test**: As the proposer of an initiative in Feedback, open it from the bell. Change the description and one answer, then resubmit. Confirm that the status is Activated again, your Modification is handled, and the original reviewer has a new pending Diagnosis.

**Acceptance Scenarios**:

1. **Given** the proposer has a pending Modification, **When** they open it, **Then** the page shows the reviewer's feedback (read-only) and the initiative's Core Fields and Diagnosis Questions (the proposer's own answers), prefilled and editable. Opening the page records nothing.
2. **Given** the modify page, **When** the proposer resubmits with valid fields and every criterion answered, **Then** one all-or-nothing operation:
   - updates the initiative and the proposer's answers in place;
   - records the proposer's Modification collaboration as handled;
   - returns the initiative to Activated;
   - records a new pending Diagnosis collaboration for the same reviewer who requested the changes.
3. **Given** a user who is not the proposer, or an initiative not in Feedback, **When** someone tries to resubmit, **Then** it is refused, and nothing changes.
4. **Given** the cycle, **When** the reviewer requests changes again, **Then** the loop repeats, with no limit on the number of rounds.

---

### User Story 8 - Acknowledge the outcome of my initiative (Priority: P3)

As the proposer, I want to see whether my initiative was accepted or rejected, with the reviewer's message, and explicitly acknowledge it, so that I learn the result and clear the notice.

**Why this priority**: It closes the loop for the proposer. Without it, Acceptance and Rejection notices would stay pending forever, but the initiative's outcome itself is already recorded.

**Independent Test**: As the proposer of a just-accepted initiative, open the Acceptance notice from the bell and press Acknowledge. The notice should leave the bell, and the initiative should move to the Handled view of My Initiative Requests.

**Acceptance Scenarios**:

1. **Given** the proposer has a pending Acceptance or Rejection notice, **When** they open it, **Then** an outcome card shows the initiative name, the outcome (accepted with a positive treatment, rejected with a negative one), the reviewer's message and when it happened. Opening it records nothing.
2. **Given** the outcome card, **When** the proposer presses Acknowledge, **Then** the notice is recorded as handled, and it disappears from the bell. The initiative moves to the Handled view of My Initiative Requests.
3. **Given** the outcome card, **When** the proposer leaves without acknowledging, **Then** the notice stays pending in both surfaces.
4. **Given** a user who is not the notice's recipient, **When** they try to acknowledge it, **Then** it is refused.

---

### Edge Cases

- **No active criteria.** If no diagnosis criterion is active, the Diagnosis Questions tab explains that there is nothing to answer, and "Request diagnosis" is allowed without answers.
- **No eligible reviewer.** If no eligible reviewer exists other than the (non-admin) proposer, the submission is refused with an explanatory message, and no partial records are left behind.
- **Asset not visible to the proposer.** The Related Assets target list offers only assets the proposer can see. A submission naming an invisible or inactive asset is refused.
- **Double submission.** Pressing "Request diagnosis" twice quickly creates only one initiative.
- **Partial failure.** If any part of the proposal fails (answers, links, collaborations, grants), nothing is saved.
- **Session expiry mid-wizard.** The user is sent to sign in. Unsaved wizard entries are lost, as in Propose an asset.
- **Initiative leaves scope.** If a grant is revoked while the gallery is open, the next load no longer shows that initiative. Opening its detail by a stale link is refused.
- **Superuser.** A superuser sees every initiative in the gallery, as the asset side does.
- **Mixed pending work.** A user with both asset and initiative items waiting sees both sections populated, and the badge counts both.
- **Network hiccup while refreshing.** A failed refresh keeps the last known lists instead of blanking them, as the asset surfaces do.
- **Language switch.** Criterion questions and scale answers follow the selected language (English/Spanish). Items without a translation fall back to English.

## Requirements *(mandatory)*

### Functional Requirements

**Explore Initiatives (HU-IN04)**

- **FR-001**: The system MUST provide an Explore Initiatives page, reached from the existing "Explore Initiatives" sidebar option, available to every profile that holds that option.
- **FR-002**: The gallery MUST list only initiatives the user can access through a live grant (a superuser sees all) and whose status is Accepted, In Progress or Delivered. Activated, Feedback, Rejected and Archived initiatives MUST NOT appear in the gallery.
- **FR-003**: The page MUST offer a privileges filter with exactly six options: Public, Shared with me, My role, My team, My unit, My projects. The filter MUST have no "all" option, MUST default to Public, and MUST show only initiatives shared with the user through the selected scope, matching Explore Category's behaviour.
- **FR-004**: The page MUST offer a "★ My favorites" toggle and a text search, both combining with the privileges filter.
- **FR-005**: Users MUST be able to mark and unmark an initiative as a favorite from its card. Holding view access to an initiative is enough to do so.
- **FR-006**: Each card MUST show: name, relative creation time, status, description, tags, favorite star, vote tally and discussion count, plus type, priority and expected impact. It MUST NOT show a version.
- **FR-007**: The gallery MUST use a presentation visibly distinct from the asset card grid that gives each initiative more space (for example, one full-width row per initiative). It MUST stay usable on phone-width screens.
- **FR-008**: Users MUST be able to cast a positive or negative vote on an initiative, withdraw it, or change it. The system MUST keep at most one active vote per user and initiative.
- **FR-009**: The page MUST provide a "+ Propose" button that opens Propose Initiative.
- **FR-010**: Clicking a card MUST open a read-mostly Initiative Detail view (HU-IN06). Core fields, diagnosis answers, related assets and history MUST be read-only. The discussion MUST be interactive (comment, ask, answer, delete one's own). Permissions MUST NOT be shown.

**Propose Initiative (HU-IN05, HU-IN07–HU-IN09)**

- **FR-011**: Propose Initiative MUST be a stepped wizard with exactly three tabs, in this order: Core Fields, Diagnosis Questions, Related Assets.
- **FR-012**: Core Fields MUST collect the same initiative fields as Initiative Management's Core Fields: name (required), description, type, expected impact (required), priority (required), reference, tags and detail. It MUST also include a reviewer field that behaves as in Propose an asset (FR-018 – FR-020). The status field MUST NOT be offered, because a proposal always starts as Activated.
- **FR-013**: The Core Fields footer MUST show "Back to initiatives" and "Diagnosis questions >". The latter MUST validate Core Fields before advancing.
- **FR-014**: Diagnosis Questions MUST present one question per active criterion. Each question offers only the options of that criterion's own scale, plus an optional rationale. Every criterion MUST be answered before submitting.
- **FR-015**: The Diagnosis Questions footer MUST show "Back to initiatives", "Request diagnosis" and "Related Assets >".
- **FR-016**: Related Assets MUST behave as the Related Assets step of Propose an asset: pick a target asset and a relation type, add an optional rationale, stage the link, remove staged links, and refuse a duplicate asset + type pair. Links MUST be saved as initiative-to-asset relations only on submission.
- **FR-017**: The Related Assets footer MUST show "Back to initiatives" and "Request diagnosis", mirroring the last step of Propose an asset.
- **FR-018**: The reviewer list MUST contain the users with an Administrator, Administrative or Reviewer profile, plus superusers.
- **FR-019**: A proposer who is not an Administrator, Administrative or superuser MUST NOT appear in their own reviewer list. The system MUST also refuse a submission naming them as reviewer.
- **FR-020**: If no reviewer is chosen, the system MUST pick one automatically by the same rule as Propose an asset, never the non-admin proposer.
- **FR-021**: On "Request diagnosis", the system MUST record the following in a single all-or-nothing operation:
  - the initiative, with status Activated;
  - one diagnosis answer per criterion, as the proposer's answer, with its rationale;
  - every staged related-asset link;
  - a completed Activation collaboration by the proposer;
  - a pending Diagnosis collaboration for the reviewer;
  - management access for the proposer and for the reviewer, open-ended from now.
- **FR-022**: The authoritative checks MUST run on the server, whatever the form allowed: required fields, a complete set of answers, answers within each criterion's scale, reviewer eligibility and self-review exclusion, and asset visibility. A violation MUST be refused with a clear message, and nothing MUST be saved.
- **FR-023**: After submission, the system MUST show a blocking outcome dialog, for success and for failure, that closes only when the user acknowledges it. On success, the user MUST then return to Explore Initiatives.
- **FR-024**: "Back to initiatives" MUST return to Explore Initiatives from any step without saving anything.

**Initiative notifications (HU-IN13)**

- **FR-025**: The notification bell's panel MUST be divided into two sections, Assets and Initiatives, each with its own count. The bell's badge MUST show the total of both sections.
- **FR-026**: The Assets section MUST keep the current asset notification behaviour unchanged.
- **FR-027**: The Initiatives section MUST list, for the current user, only initiatives whose latest collaboration directed at them is pending and of type Diagnosis, Modification, Acceptance or Rejection. It MUST show one entry per initiative.
- **FR-028**: Initiative notifications MUST have no dismiss control. An entry MUST leave the list only when its collaboration is resolved: by a decision, by a resubmission, or by an explicit acknowledgment for Acceptance and Rejection.
- **FR-029**: Opening a notification MUST record nothing. Viewing is not deciding or acknowledging.
- **FR-030**: Each entry MUST show the initiative name, a type-specific description of what is expected, and a relative time. The section MUST link to My Initiative Requests.
- **FR-031**: Clicking an entry MUST route by type: Diagnosis → Diagnosis of the Initiative (HU-IN15); Modification → Modify Initiative (HU-IN16); Acceptance or Rejection → Acknowledgment (HU-IN17). All three pages are delivered by this feature (FR-040 – FR-051).

**My Initiative Requests (HU-IN14)**

- **FR-032**: The Account Menu's My Workspace section MUST contain "My Initiative Requests" directly below "My Asset Requests".
- **FR-033**: My Initiative Requests MUST list every initiative the user took part in (initiatives they proposed and those with collaborations directed at them), with exactly one entry per initiative, split into Pending and Handled views.
- **FR-034**: Each in-motion entry MUST state whose action is awaited (the user's or somebody else's) and the stage. Whether the user owes something MUST be determined before the initiative's status is considered, so that an unacknowledged outcome never reads as closed.
- **FR-035**: Entries awaiting the user MUST offer the action button matching the bell's routing (FR-031).
- **FR-036**: The bell's Initiatives section MUST always be a strict subset of My Initiative Requests: only the entries awaiting the user.
- **FR-037**: The bell and My Initiative Requests MUST refresh with the same rules as the asset surfaces: immediately after a same-tab change, when the tab becomes visible again, and periodically while it is visible. A failed refresh MUST keep the last known list.

**Diagnosis of the Initiative (HU-IN15)**

- **FR-040**: The system MUST provide a diagnosis page for a pending Diagnosis collaboration. It MUST show the initiative's core fields and related assets, and for each criterion the proposer's answer and rationale beside an input for the reviewer's own answer (limited to that criterion's scale).
- **FR-041**: Opening the diagnosis page MUST record nothing.
- **FR-042**: The reviewer MUST be able to Accept, Reject or Request changes. All criteria MUST be answered first. A message MUST be required for Reject and Request changes, and is optional for Accept.
- **FR-043**: A diagnosis decision MUST, in one all-or-nothing operation:
  - save the reviewer's answer per criterion;
  - record the reviewer's Diagnosis collaboration as handled;
  - set the initiative's status to Accepted, Rejected or Feedback;
  - compute and store the initiative's score from the diagnosis;
  - record a pending Acceptance, Rejection or Modification collaboration for the proposer, carrying the reviewer's message.
- **FR-044**: A diagnosis MUST be refused unless the caller holds a pending Diagnosis on that initiative, is still an eligible reviewer, and the initiative is Activated. The last check guards against double submission.

**Modify Initiative (HU-IN16)**

- **FR-045**: The system MUST provide a modify page for a pending Modification collaboration. It MUST show the reviewer's feedback read-only, and the initiative's core fields and the proposer's diagnosis answers prefilled and editable.
- **FR-046**: Opening the modify page MUST record nothing.
- **FR-047**: A resubmission MUST, in one all-or-nothing operation:
  - update the initiative and the proposer's answers in place;
  - record the proposer's Modification collaboration as handled;
  - return the initiative to Activated;
  - record a new pending Diagnosis collaboration for the reviewer who requested the changes.
- **FR-048**: A resubmission MUST be refused unless the caller is the initiative's proposer, holds a pending Modification on it, and the initiative is in Feedback. The number of rounds MUST NOT be limited.

**User Acknowledgment (HU-IN17)**

- **FR-049**: The system MUST provide a read-only outcome card for a pending Acceptance or Rejection notice, with the initiative name, the outcome, the reviewer's message and the time.
- **FR-050**: Opening the outcome card MUST record nothing. Only the explicit Acknowledge action MUST record the notice as handled.
- **FR-051**: Only the notice's recipient MUST be able to acknowledge it.

**Cross-cutting**

- **FR-052**: Every user-facing string MUST exist in English and Spanish.
- **FR-053**: Every initiative workflow record MUST be attributed to the signed-in user as recorded by the server, never to an identity supplied by the client.

### Key Entities

- **Initiative**: an AI-adoption opportunity. Has a name, description, type, expected impact, priority, reference, tags, detail, status and score. A proposal starts as Activated.
- **Diagnosis Criterion**: a shared evaluation question with its own answer scale (for example, 1–3 with bilingual labels). The set of active criteria defines the Diagnosis Questions tab.
- **Diagnosis Answer**: one per initiative and criterion. Holds the proposer's answer and rationale (captured at proposal) and, later, the reviewer's answer.
- **Initiative–Asset Link**: relates an initiative to a library asset through a relation type, with an optional rationale. The same pair may be linked once per relation type.
- **Collaboration**: an activity record on an initiative, with a type, a workflow status (Pending or Handled), an actor, and optional message content. It plays the role that actions play for assets. Equivalences with the asset workflow:

  | Asset side (actions) | Initiative side (collaborations) |
  |---|---|
  | Proposal (handled) | Activation (handled) |
  | Review (pending → handled) | Diagnosis (pending → handled) |
  | Modification | Modification |
  | Publication notice | Acceptance notice |
  | Rejection notice | Rejection notice |
  | Asset status Proposed / Feedback / Published / Rejected | Initiative status Activated / Feedback / Accepted / Rejected |

  Vote, Comment, Question and Answer are community collaborations. Kickoff, Delivery and Archiving are completed log records written by Initiative Management and raise no notice.
- **Initiative Grant**: view or manage access to an initiative for a user, role, team, unit, project or everyone, valid from a start time until revoked. Visibility in the gallery and the privileges filter both derive from it.
- **Favorite Initiative**: a user's mark on an initiative they follow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can propose an initiative (all three steps, all criteria answered) in under 5 minutes, without help.
- **SC-002**: 100% of successful proposals leave a complete, consistent record: the initiative, one answer per criterion, the proposer's Activation, the reviewer's pending Diagnosis and both grants. 0% of failed proposals leave any partial record.
- **SC-003**: The assigned reviewer sees the new diagnosis request in the bell's Initiatives section within one refresh cycle (at most 60 seconds) of the proposal, without reloading the page.
- **SC-004**: For every user, each initiative they took part in appears exactly once in My Initiative Requests, and every entry in the bell's Initiatives section is also present there.
- **SC-005**: In the gallery, each privilege option shows exactly the initiatives shared with the user through that scope. This is verified for all six options with a user whose grants cover each scope.
- **SC-006**: Asset notifications and My Asset Requests behave identically before and after the bell is split, with no regressions in their existing checks.
- **SC-007**: Each initiative in the gallery is identifiable and actionable (open, favorite, vote) at phone width (about 390 px) without horizontal scrolling.
- **SC-008**: An initiative can travel the whole loop — propose → request changes → resubmit → accept → acknowledge — driven only by the bell and My Initiative Requests, with each participant seeing exactly one actionable entry at each step and none after the final acknowledgment.

## Assumptions

- **Reuse of Explore Category behaviour.** Search, favorites, the privileges filter (default Public, one scope at a time), voting and the discussion are behaviourally identical to their asset counterparts. Only the card presentation differs.
- **Card click opens Initiative Detail (HU-IN06).** "Similar to Explore Category" implies clicking a card opens its detail, as on the asset side. The tab behaviour follows the documented Initiative Detail matrix.
- **Related Assets in Propose.** The user's request adds Related Assets to the Propose wizard, which the earlier tab matrix marked as "not applicable". The user's request takes precedence, and the matrix doc will be updated.
- **All criteria are mandatory.** Each diagnosis answer requires a proposer answer, and the documented story says every criterion is scored, so all active criteria must be answered before requesting diagnosis. Rationale is optional.
- **Delivery raises no notice.** The earlier notification story listed Delivery among notifiable types, but spec 004 records Delivery (with Kickoff and Archiving) as a completed log entry with no notice, by the user's decision. Delivery is therefore excluded from notifications.
- **Who sees My Initiative Requests.** Every signed-in user sees it, like My Asset Requests (the current header passes that item with no profile restriction; an older note claiming it was gated is out of date, see research R14). Collaborators can propose initiatives and must be able to follow their proposals.
- **Reviewer eligibility.** Reviewer eligibility and auto-assignment reuse the asset rule unchanged, with no initiative-specific reviewer profile.
- **Where proposals go.** A proposal has no category to return to, so "Back to initiatives" and the post-proposal redirect both go to Explore Initiatives.
- **Grant scoping.** Grants use the same scope matching, validity window and revoke-not-delete semantics as asset grants, through the shared permission engine established in spec 004.
- **Data changes.** No new tables are expected. All the entities above already exist. Only seed or label additions (for example, bilingual labels for new notification texts) may be needed.
