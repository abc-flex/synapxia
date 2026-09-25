# UI Contracts: Explore Initiatives, Propose Initiative & Initiative Notifications

**Branch**: `005-explore-initiatives` | **Phase**: 1 | **Date**: 2026-09-24

## Routes

| Route | Page | Purpose |
|---|---|---|
| `/inits/explore` | `ui/src/pages/inits/explore.astro` | Gallery (FR-001 – FR-010). The target of the existing `INITS.EXPLORE` sidebar option, so no seed change is needed |
| `/inits/propose` | `ui/src/pages/inits/propose.astro` | Three-step wizard (FR-011 – FR-024) |
| `/inits/diagnose?collab={id}` | `ui/src/pages/inits/diagnose.astro` | Reviewer decision (FR-040 – FR-044) |
| `/inits/modify?collab={id}` | `ui/src/pages/inits/modify.astro` | Proposer resubmit (FR-045 – FR-048) |
| `/inits/show-collab?collab={id}` | `ui/src/pages/inits/show-collab.astro` | Outcome card + Acknowledge (FR-049 – FR-051) |
| `/inits/my_initiative_requests` | `ui/src/pages/inits/my_initiative_requests.astro` | Durable record (FR-032 – FR-037) |

All pages use `BaseLayout` and a Breadcrumb, and every string goes through i18n. The action pages resolve `?collab=` with `GET /api/collaborations/{id}`. They show a "not found" state when the row is missing or foreign, and a "no longer actionable" state when the thread is no longer PENDING or the status precondition fails. In either case the page offers a link back to My Initiative Requests.

## Explore gallery

- **`<CardGallery>`** is reused with:
  - `galleryId="inits-gallery"`, `layout="list"` (new opt-in prop);
  - `statuses={[]}` (status filter hidden), `privileges={PRIVILEGE_OPTIONS}` (the same six options and `asset_table.perm_filter_*` keys as `lib/explore.astro`, default PUBLIC);
  - `showFavorites`, `proposeHref="/inits/propose"`.
- **Empty state.** The gallery uses the key `inits_explore.empty`. The "+ Propose" CTA stays visible even when the gallery is empty.
- **`<InitiativeCard>`** (new, `components/inits/`):
  - Data attributes are compatible with `initCardGallery`: `data-card`, `data-id`, `data-search` (name + description + tags), `data-favorite`, `data-permissions`, `data-detail-modal="inits-view-modal"`.
  - **Layout.** A full-width row with a left accent bar coloured by status (ACCEPTED indigo, IN_PROGRESS amber, DELIVERED emerald).
  - **Header.** Name, status pill (`initiative_status.*` labels from the list), chips for type / priority / expected impact, and the relative time.
  - **Body.** A two-line clamped description and `#tags`.
  - **Footer.** The vote bar (`data-action="vote-up|vote-down"`), the discuss button (`data-action="discuss"` with the count), a related-assets count, and the favorite star (`data-action="favorite"`).
  - Below `sm` the card stacks vertically with no horizontal scroll (SC-007). No version pill is shown.
- **`initCardGallery`** is called with `idAttr: "initId"` and
  `services: { toggleFavorite: setInitiativeFavorite, vote: setInitiativeVote, tally: getInitiativeVoteTally }`.
- **`<InitiativeExploreModal modalId="inits-view-modal">`** mounts `InitiativeDetailView.svelte`:
  - **Tabs.** Core Fields (read-only), Diagnosis Questions (`DiagnosisTable` mode `view`), Related Assets (read-only list), Discussion (`Foro` with `api=initiativeForoApi`, `idAttr="initId"`, interactive), History (`mountHistory` with the initiative fetcher).
  - **Header.** Name, status, favorite and vote bar, kept in sync with the card.
  - **Not shown.** No Permissions tab, and no edit or save controls.

## Propose wizard (`/inits/propose`)

| Step | Tab key | Content | Footer (left → right) |
|---|---|---|---|
| 1 | `core` | name*, description, type, expected impact*, priority*, reference, tags, detail, reviewer | Back to initiatives · **Diagnosis questions >** |
| 2 | `diagnosis` | `DiagnosisTable` mode `propose`: one row per active criterion, a scale `<select>` (label in the current language) + a Show/Hide rationale switch | Back to initiatives · Request diagnosis · **Related Assets >** |
| 3 | `related` | Target asset (`/linkable-assets`) · relation type (`RELATION_TYPE`) · rationale · Add relation · staged list with Remove | Back to initiatives · **Request diagnosis** |

- **Buttons.** Bold marks the primary (submit) button.
  - The labels are `inits_propose.next_diagnosis`, `inits_propose.next_related` and `inits_propose.submit`.
  - The secondary "Request diagnosis" (`inits_propose.submit`) is shown only on `diagnosis`.
  - "Back to initiatives" is `inits_propose.back`, a ghost button that goes to `/inits/explore`.
- **Validation.** Missing required fields are marked with `setFieldInvalid` and a toast (`inits_propose.required` / `inits_propose.answers_required`), and the wizard activates the first invalid tab.
- **Staged relations.** A duplicate `(asset, type)` shows an inline error (`inits_propose.related_duplicate`).
- **Double submission.** An in-flight guard disables both submit buttons.
- **Outcome.** `showAckDialog` from `lib/ackDialog.ts` (extracted). Success shows `inits_propose.success`, which mentions My Initiative Requests; after "Got it" the user goes to `/inits/explore`. A failure shows the server message; after "Got it" the user stays with their entries intact.
- **Reviewer select.** Options are `label — role` (`reviewer_role.*`). The placeholder "Auto-assign" (`inits_propose.reviewer_auto`) means omitting `reviewer_id`.
- **Rationale toggle.** The Show/Hide switch is right-aligned and collapsed by default, following the established toggle style.

## DiagnosisTable (`components/svelte/DiagnosisTable.svelte`, extracted)

| Mode | Proposer column | Reviewer column | Score cards |
|---|---|---|---|
| `view` | read | read (only when status ∉ {ACTIVATED}) | both |
| `propose` | editable (scale select + rationale) | hidden | proposer only (live total) |
| `review` | read, with rationale | editable (scale select) | both (live reviewer total) |
| `modify` | editable (prefilled) | read (previous round, labelled "Previous review") | both |

- **Props.** `rows`, `mode`, `lang`, and an `onChange(answers)` callback.
- **Method.** An exported `validate()` returns the list of unanswered criteria.
- **Adoption.** `InitiativeDetailTabs.svelte` switches to `mode="view"`, so its rendering is unchanged.

## Diagnose page (`/inits/diagnose`)

- **Content.** The initiative's core fields and related assets (read-only), then `DiagnosisTable` mode `review`, then a feedback textarea.
- **Buttons.** Accept (emerald), Request changes (amber), Reject (red) and Back.
- **Validation.** Feedback is required for Reject and Request changes; every reviewer answer is required.
- **On success.** The page calls `notifyChanged()` and goes to `/inits/my_initiative_requests`.

## Modify page (`/inits/modify`)

- **Content.** The reviewer's feedback (read-only panel from `collab.content`), the editable core fields, and `DiagnosisTable` mode `modify`.
- **On Resubmit.** `notifyChanged()`, then `/inits/my_initiative_requests`.

## Show-collab page (`/inits/show-collab`)

- **Card.** An outcome card: ACCEPTANCE uses emerald with a check, REJECTION red with an ×. It shows the initiative name, the reviewer message and the relative time.
- **Buttons.** Acknowledge calls the acknowledge endpoint, then `notifyChanged()`, then `/inits/my_initiative_requests`. Back only navigates.

## Notification bell (split)

- **Tabs.** Assets and Initiatives, each with a count pill.
  - The badge dot shows when `feed.total + initFeed.total > 0`.
  - The bell opens on the first tab that has items.
- **Assets tab.** Unchanged from today.
- **Initiatives tab.**
  - Items show `init_name` and `inits_notifications.type.<TYPE> · relative time`, with at most 5 items and an "and N more" line.
  - Routing: DIAGNOSIS → `/inits/diagnose?collab=id`, MODIFICATION → `/inits/modify?collab=id`, ACCEPTANCE / REJECTION → `/inits/show-collab?collab=id`.
  - The empty state is `inits_notifications.empty`.
  - The footer links to `/inits/my_initiative_requests`.
- **No dismiss control** in either tab.

## My Initiative Requests

A structural twin of `MyAssetRequests.svelte`, `MyInitiativeRequests.svelte`:
- **Tabs.** Pending and Handled with counts.
- **Columns.** Initiative, Request (the pending type, or "Proposed by me" / "Diagnosed by me"), Status, Waiting on (Pending only: a "You" amber pill, or a "Someone else" gray pill with the stage), Updated, Action.
- **Actions.** "Got it" for SELF + ACCEPTANCE / REJECTION. "Open" for SELF DIAGNOSIS / MODIFICATION, using the bell's routing. No button for OTHER.
- **Refresh.** It subscribes to the shared `notificationsStore`.

## Account menu

`Header.astro` `workItems` becomes:
- `account_menu.my_asset_requests` → `/lib/my_asset_requests`
- `account_menu.my_initiative_requests` → `/inits/my_initiative_requests` (new, directly below, ungated)

`AccountMenu.astro` `ICONS` gains the matching icon entry.

## i18n (en + es, all new keys)

| Namespace | Keys |
|---|---|
| `inits_explore.*` | title, subtitle, empty, related_count, discuss |
| `inits_propose.*` | title, subtitle, tab_core, tab_diagnosis, tab_related, next_diagnosis, next_related, submit, back, reviewer, reviewer_auto, required, answers_required, related_duplicate, related_hint, success, failure, no_criteria |
| `inits_diagnosis.*` | proposer, reviewer, previous_review, rationale_show, rationale_hide, total, unanswered |
| `inits_diagnose.*` | title, feedback, feedback_required, accept, changes, reject, blocked, not_found |
| `inits_modify.*` | title, reviewer_feedback, resubmit, blocked, not_found |
| `inits_show_collab.*` | title_accepted, title_rejected, acknowledge, message |
| `inits_notifications.*` | tab_assets, tab_initiatives, empty, see_all, `type.{DIAGNOSIS,MODIFICATION,ACCEPTANCE,REJECTION}` |
| `my_initiative_requests.*` | title, subtitle, tab_pending, tab_handled, col_*, you, someone_else, stage.*, proposed_by_me, diagnosed_by_me, got_it, open, empty_* |
| `account_menu.*` | my_initiative_requests |
| `menu_options.*` | reuses the existing `explore` key ("Explore Initiatives") |
