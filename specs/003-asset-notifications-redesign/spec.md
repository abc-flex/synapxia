# Feature Specification: Asset Notification Scheme Redesign

**Feature Branch**: `003-asset-notifications-redesign`

**Created**: 2026-09-16

**Status**: Draft

**Input**: User description: "Rediseño del esquema de notificaciones de assets: colapsar el ciclo de vida de workflow_status de tres estados (ASSIGNED/NOTIFIED/FINISHED) a dos (PENDING/HANDLED, etiquetados Pendiente/Atendido) en lib e inits; convertir la campana en un feed de pendientes con enlace a My Asset Requests, y esa página en la cola durable con pestañas Pendientes/Atendidas cubriendo los cuatro tipos (REVIEW, MODIFICATION, PUBLICATION, REJECTION); y agregar un mecanismo de refresco porque hoy la campana y su lista quedan obsoletas tras una revisión o modificación. El sistema no está liberado: se editan los seeds SQL directamente, sin migración."

## Problem Context

Today the platform surfaces asset workflow assignments in two places that show **the same rows**: the header notification bell and the "My Asset Requests" page. Both list the caller's open assignments, both link to the same action screens, and neither shows anything the other does not. Users perceive this as a duplicated list with no added value.

Three further defects compound it:

1. **Requests disappear with no history.** Once an assignment is resolved it vanishes from both surfaces. A user cannot review what they were asked to do in the past, or confirm the outcome of a request they participated in.
2. **Lists go stale.** After a reviewer decides, neither the bell nor the requests page reflects the change until the user manually reloads. A user can act on information that is minutes or hours out of date, and in the worst case act twice on the same item.
3. **Ambiguous vocabulary.** The assignment lifecycle carries three states, one of which records only that the user looked at the item. This mixes *read state* with *work state*: a user who opened an item but did nothing appears to be in a different state from one who never opened it, even though both still owe the same action. The same conflation forces an inconsistent rule where informational notices can be cleared but actionable ones cannot.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find all my asset work in one place (Priority: P1)

As a reviewer or proposer, I want a single page that lists every asset I have taken part in — the requests waiting on me, the assets I proposed that are still making their way through the workflow, and everything already closed — so that I always know what I owe, what I am waiting on, and how past work ended.

**Why this priority**: This is the foundation of the whole scheme. Until a durable, complete page exists, nothing else can be safely narrowed: the notification indicator is currently the only route to some request kinds, so trimming it first would strand work. It also delivers value on its own — even with today's indicator untouched, a complete page with history is a net gain.

**Independent Test**: Can be fully tested by opening the page as a user who has a mix of requests waiting on them, assets they proposed that are still under review, and closed items, then confirming each appears in the right view with the correct indication of whose action is awaited.

**Acceptance Scenarios**:

1. **Given** a user has requests waiting on them of more than one kind (a review to decide, changes to resubmit, an outcome notice to acknowledge), **When** they open the page, **Then** all of them are listed together under "Pending", each identifying the asset, the kind of request, and that the user's own action is awaited.
2. **Given** a user proposed an asset that is still awaiting someone else's review, **When** they open the page, **Then** that asset appears under "Pending", marked as awaiting another person rather than the user.
3. **Given** a user has closed items — assets published, rejected, or requests they already resolved — **When** they switch to the "Handled" view, **Then** those are listed, newest first, with the asset and how it ended.
4. **Given** an entry is waiting on the user, **When** they choose it from the list, **Then** they are taken to the screen where it is acted on.
5. **Given** a user has never proposed an asset nor received a request, **When** they open the page, **Then** both views show an explanatory empty state rather than an error or a blank area.
6. **Given** a user resolves an entry waiting on them, **When** they return to the page, **Then** it no longer appears under "Pending" and does appear under "Handled".
7. **Given** a user proposed an asset that was later published and the user has acknowledged the outcome, **When** they open the page, **Then** that asset appears exactly once — not once as a proposal and again as an outcome notice.

---

### User Story 2 - Be alerted to outstanding work without a second list to scan (Priority: P1)

As any user, I want the header notification indicator to tell me only what still needs my attention, and to hand me off to the full page when I want the whole picture, so that I am not reading the same list in two places.

**Why this priority**: This is the change that removes the perceived duplication — the complaint that motivated the work. It depends on User Story 1 being in place first, because narrowing the indicator is only safe once every request kind has a durable home.

**Independent Test**: Can be fully tested by giving a user several outstanding requests, confirming the indicator reflects only outstanding ones, confirming a resolved request is absent, and confirming the panel offers a route to the full page.

**Acceptance Scenarios**:

1. **Given** a user has entries awaiting their action, **When** they open the notification panel, **Then** only those are listed — nothing already handled appears.
2. **Given** a user proposed an asset that is awaiting someone else's review, **When** they open the notification panel, **Then** that asset is absent, because nothing is being asked of them.
3. **Given** a user has nothing awaiting their action, **When** they look at the header, **Then** no attention signal is shown and the panel explains there is nothing pending.
4. **Given** the notification panel is open, **When** the user chooses the route to the full page, **Then** they arrive at it.
5. **Given** a user has more entries awaiting them than the panel displays at once, **When** they open the panel, **Then** the most recent are shown along with an indication that more exist and a route to see them all.
6. **Given** a user has an entry that requires action, **When** they view the panel, **Then** no control is offered that would clear the item without resolving it.

---

### User Story 3 - Never act on a stale list (Priority: P1)

As any user, I want the notification indicator and the requests page to reflect the current state of my work without me having to reload the page, so that I never act on something already dealt with and never miss something that just arrived.

**Why this priority**: This is the defect reported from live use. It is separable from stories 1 and 2 — the refresh behaviour can be built and demonstrated against the existing lists — but without it the redesign inherits the same staleness it was meant to fix.

**Independent Test**: Can be fully tested by resolving a request in one session and confirming that (a) the same session's indicator and page update with no manual reload, and (b) a second session belonging to the affected user reflects the change shortly after, also with no manual reload.

**Acceptance Scenarios**:

1. **Given** a user resolves a request, **When** they land back on any screen showing the indicator or the page, **Then** both reflect the resolution without the user reloading anything.
2. **Given** a user has a session open and idle, **When** another user's action creates a request for them, **Then** the indicator reflects it within a short, bounded delay without a reload.
3. **Given** a user has left the tab and comes back to it after a period away, **When** the tab regains focus, **Then** the indicator and any visible listing reflect current state.
4. **Given** a user navigates back to a previously visited screen using the browser's back control, **When** that screen appears, **Then** the indicator and page shown are current, not the state captured when the screen was first visited.
5. **Given** the system is briefly unreachable, **When** a refresh attempt fails, **Then** the last known list remains visible rather than being emptied, and no blocking error is forced on the user.
6. **Given** a user's tab is hidden or in the background, **When** time passes, **Then** the system does not keep asking for updates on behalf of that tab.

---

### User Story 4 - Understand at a glance whether something is pending or done (Priority: P2)

As any user, I want one consistent pair of states used everywhere a workflow step is shown — the requests page, the asset activity history, and the asset stage indicator — so that I never have to interpret a third, intermediate state whose meaning is unclear.

**Why this priority**: Valuable for clarity, and it removes the root cause behind the inconsistent clearing rules. The scheme functions without it, so it is the last slice to land.

**Independent Test**: Can be fully tested by inspecting every surface that displays a workflow step and confirming only two state labels ever appear, in both supported languages.

**Acceptance Scenarios**:

1. **Given** any surface that displays a workflow step's state, **When** it is rendered, **Then** the state shown is one of exactly two — "Pending" or "Handled" (Spanish: "Pendiente" / "Atendido").
2. **Given** an asset's activity history, **When** a user reads it, **Then** it contains no entry whose only content is that someone looked at a notification.
3. **Given** the language is switched between the two supported languages, **When** any state label is displayed, **Then** it is translated consistently on every surface.

---

### Edge Cases

- **A request resolved elsewhere while a user is looking at it.** A reviewer opens a review from a list rendered a minute ago, but the asset has since moved on. The action screen must explain that the item is no longer actionable rather than allowing a second decision or failing obscurely.
- **A user opens an actionable request and walks away without deciding.** The request must remain pending and reachable from both the indicator and the page — opening something is not resolving it.
- **A user never acknowledges an outcome notice.** The entry stays pending and the attention signal stays lit indefinitely. This is an accepted consequence of requiring explicit acknowledgement; it is mitigated by making acknowledgement a single action available directly from the listing.
- **A user who is both proposer and reviewer of the same asset.** Permitted today for administrative profiles. The page must still show one entry for that asset, reflecting whichever involvement most recently changed, and must not double-count it in the attention signal.
- **An asset the user proposed that is rejected.** It moves to the closed view once the user acknowledges the rejection — not at the moment of rejection, since the notice is still awaiting them.
- **A proposal that stalls.** An asset proposed long ago and never reviewed stays in the in-motion view, marked as awaiting another person, rather than silently disappearing.
- **Two sessions of the same user, one resolving.** The other session must converge on the new state within the bounded refresh delay, without the user reloading.
- **A user with a long history.** The "Handled" view must stay usable as history grows; it must not attempt to render an unbounded list in one go.
- **A request whose asset was subsequently deleted or deactivated.** The page must still render the row without failing, identifying the asset as best it can.
- **A request addressed to a user who cannot act on the asset.** The page lists it; the action screen enforces the rule and explains it rather than failing silently.
- **Refresh while the user is mid-interaction.** A background refresh must not discard text the user is typing or reset the view they have selected.
- **Two requests raised in the same minute.** They must present in a stable, predictable order rather than shuffling between refreshes.

## Requirements *(mandatory)*

### Functional Requirements

**Workflow state model**

- **FR-001**: The system MUST represent every workflow step with exactly two states: one meaning the step still awaits someone's action, and one meaning it no longer does.
- **FR-002**: The system MUST NOT record, expose, or display any state whose only meaning is that a user has viewed an item.
- **FR-003**: Opening an item MUST NOT change its recorded workflow state; only resolving it may.
- **FR-004**: The system MUST apply the same two-state vocabulary to asset workflow steps and to initiative workflow steps.
- **FR-005**: The system MUST keep recording a step's resolution as a new event rather than by altering the record of the original assignment, so the activity history stays complete.

**The requests page**

- **FR-006**: Users MUST be able to see, on a single page, every asset they have taken part in — both requests directed at them across all four kinds (a review to perform, changes to make, a publication outcome, a rejection outcome) and assets they proposed that are still moving through the workflow.
- **FR-006a**: Each entry MUST indicate whose action is currently awaited — the user's own, or another person's — so a user can tell at a glance what they owe from what they are merely waiting on.
- **FR-006b**: The page MUST show at most one entry per asset per user, reflecting the most recent state of that user's involvement. An asset the user proposed and whose outcome they later acknowledged MUST NOT appear as two separate entries.
- **FR-007**: The page MUST separate entries still in motion from entries that are closed, into two distinct, switchable views.
- **FR-008**: Each entry MUST identify the asset it concerns, the kind of involvement, its current state, and when it last changed.
- **FR-009**: Each entry awaiting the user's own action MUST offer a direct route to the screen where it is acted on.
- **FR-010**: Closed entries MUST be retained and stay visible in the closed view; resolving an entry MUST NOT erase it from the user's record.
- **FR-010a**: An informational outcome — a publication or rejection notice, where the user has nothing to do but take note — MUST become handled only when the user explicitly acknowledges it. Opening it MUST NOT be treated as acknowledgement.
- **FR-010b**: Acknowledging an outcome MUST be possible in a single action, offered both on the outcome screen and directly from the page listing, so that clearing a notice never requires navigating away.
- **FR-011**: Each view MUST present a clear empty state when it has no entries.
- **FR-012**: The closed view MUST stay responsive as a user's history grows, retrieving entries in bounded pages rather than all at once.

**The notification indicator**

- **FR-013**: The notification indicator MUST reflect only entries awaiting the user's own action. Closed entries, and entries waiting on someone else, MUST NOT appear in it — the indicator is a strict subset of the page, never a copy of it.
- **FR-014**: The indicator MUST show no attention signal when nothing awaits the user's own action.
- **FR-015**: The notification panel MUST offer a route to the full page.
- **FR-016**: The notification panel MUST limit how many entries it displays at once and indicate when more exist.
- **FR-017**: The system MUST NOT offer any control that removes an outstanding request from the user's view without resolving it.
- **FR-018**: Selecting an entry in the panel MUST take the user to the screen where that request is acted on.

**Staying current**

- **FR-019**: After a user resolves a request, the indicator and any visible listing in that same session MUST reflect the new state without the user reloading.
- **FR-020**: An open session MUST converge on the current state within a bounded delay when the change originated elsewhere — from another user or another session.
- **FR-021**: The system MUST refresh when a session regains the user's attention, including when a screen is restored by the browser's back or forward controls.
- **FR-022**: The system MUST NOT keep asking for updates on behalf of a session that is not visible to the user.
- **FR-023**: A failed refresh MUST leave the last known state visible and MUST NOT present the user with an empty list or a blocking error.
- **FR-024**: A refresh MUST NOT disturb in-progress user input or the user's current view selection.

**Consistency across surfaces**

- **FR-025**: Every surface displaying a workflow state — the requests page, the asset activity history, and the asset stage indicator — MUST use the same two-state vocabulary.
- **FR-026**: Every state label and every new user-facing string MUST be available in both supported languages.
- **FR-027**: The system MUST retire any page or menu entry made redundant by the unified requests page, so no second, partial list of the same requests stays reachable.

### Key Entities

- **Asset Request**: A unit of work directed at one user concerning one asset. Has a kind (review, modification, publication outcome, rejection outcome), an asset, a recipient, a moment it was raised, and a state (pending or handled). Its life is recorded as a sequence of events rather than as a mutable row.
- **Participation**: A user's involvement with one asset — as its proposer, as a reviewer, or as the recipient of an outcome. This is the unit the page lists, collapsing all of a user's requests and proposals for a given asset into a single entry.
- **Workflow State**: The two-valued vocabulary — pending or handled — shared by asset requests and initiative workflow steps.
- **Awaited Party**: For an entry still in motion, whether the next action belongs to the user or to someone else. Distinguishes what a user owes from what they are waiting on, and determines whether the entry reaches the attention signal.
- **Notification Feed**: The subset of a user's participations whose next action is the user's own, surfaced for attention.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can reach the screen for any entry awaiting their action in at most two interactions from any authenticated screen.
- **SC-002**: 100% of a user's asset involvement — every request across all four kinds, plus every asset they proposed, open and closed alike — is findable from a single page.
- **SC-003**: Zero entries awaiting a user's action can be made unreachable by any user action short of resolving them.
- **SC-003a**: Every entry in the in-motion view states whose action is awaited, so a user can separate what they owe from what they are waiting on without opening anything.
- **SC-003b**: No asset appears more than once per user on the page, regardless of how many workflow events that user accumulated on it.
- **SC-004**: After a user resolves a request, the state shown to that user is correct with no manual reload, on every surface that displays it.
- **SC-005**: When a change originates outside the user's session, the session shows current state within 90 seconds of the user having the tab in view.
- **SC-006**: Exactly two workflow state labels appear anywhere in the product, in both supported languages — no surface shows a third.
- **SC-007**: No more than one reachable list presents the same set of outstanding requests, eliminating the duplicate-list complaint that motivated this work.
- **SC-008**: A session not visible to the user issues no update requests.
- **SC-009**: A user returning to a screen through browser history sees current state, not the state captured when that screen was first loaded.

## Assumptions

- **The system has not been released.** There is no production data to preserve, so the change is applied by editing seed data directly and rebuilding. No data migration path, rollback script, or backward-compatible transition period is required.
- **Removing the view-marking and clear operations, and the read-state field, from the published interface is acceptable.** This is an incompatible change to an established contract, permitted here only because the product is unreleased and the bundled front end is its sole consumer. It is recorded explicitly rather than assumed silently.
- **Real-time push is out of scope.** The deployment target does not sustain long-lived connections, so "staying current" means converging within a bounded delay, not instantaneously. Up to about a minute for changes originating elsewhere is acceptable.
- **"New since I last looked" is cosmetic and per-device.** Any emphasis distinguishing recently-arrived items from older ones is a presentation concern held locally in the user's browser. It carries no authority, is not shared between devices, and never determines whether an item is pending.
- **Steps recorded as already complete keep the handled state.** Some recorded events — a proposal being made, a version created, a deprecation — never have a pending phase and are recorded directly as handled. Leaving them stateless was considered and rejected as wider scope than this feature warrants.
- **The page is scoped to the user's own involvement.** It answers "what did I ask for and what was asked of me", covering requests directed at the user and assets the user proposed. It does not extend to assets the user merely voted on, commented on or asked a question about.
- **Requiring explicit acknowledgement is an accepted trade-off.** A user who ignores outcome notices will keep a lit attention signal indefinitely. This was chosen deliberately over auto-clearing on open, so that no outcome can pass unregistered; the cost is mitigated by making acknowledgement a one-click action directly in the listing.
- **An entry waiting on someone else still counts as in motion.** "Pending" describes the request, not an obligation on the viewer — which is why every entry states whose turn it is.
- **Existing permission rules are unchanged.** This feature alters what is listed and when it refreshes; it does not widen or narrow who may act on an asset.
- **Existing action screens are reused.** Review, modify and outcome screens keep their current behaviour apart from where they return the user afterwards, and the removal of the view-marking step.

## Out of Scope

- Real-time push delivery (server-sent events, websockets) or any always-on connection.
- Email or other out-of-product notification channels.
- Notifications for anything other than asset and initiative workflow steps — votes, comments and questions are unaffected.
- Per-user notification preferences, muting, or digest scheduling.
- Any change to who is eligible to review, propose or modify an asset.
