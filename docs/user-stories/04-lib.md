# AI Library — User Stories

> Module `LIB` · API domain [`api/app/lib`](../../api/app) · DB band 40s
> ([`41-lib-ddl.sql`](../../db/sql/41-lib-ddl.sql)) · Diagram [4-lib.png](../diagrams/4-lib.png)

The AI Library is the reusable asset repository: assets are **proposed → reviewed →
published**, then characterized, discussed, voted, related, permissioned and versioned. Two
surfaces share one data model and one set of tabs — **Asset Management** (governance, full
edit) and **Explore Category** (discovery, read-mostly).

| Code | Story | | Code | Story |
|------|-------|-|------|-------|
| HU-LI01 | Asset Management | | HU-LI13 | [Asset Tab] Versioning |
| HU-LI02 | – New Asset | | HU-LI14 | [Notifications] Asset Notifications |
| HU-LI03 | – Edit Asset (Include Versioning / Deprecation) | | HU-LI15 | [Account Menu] My Asset Requests |
| HU-LI03 | Explore Category (Include Favorite / Vote) | | HU-LI16 | – Review Asset Proposal |
| HU-LI04 | – Propose Asset | | HU-LI17 | – Modify Asset Proposal |
| HU-LI05 | – Asset Detail (Include Favorite / Vote) | | HU-LI18 | – Asset Request Detail |
| HU-LI06 | [Asset Tab] Core Fields | | HU-LI19 | [Explore Category] Prompt Gallery |
| HU-LI07 | [Asset Tab] Characteristics (Include Report Usage) | | HU-LI20 | [Explore Category] MCP Directory |
| HU-LI08 | [Asset Tab] Related Assets | | HU-LI21 | [Explore Category] Agent Repository |
| HU-LI09 | [Asset Tab] Related Inits | | HU-LI22 | [Explore Category] Agentic Flows |
| HU-LI10 | [Asset Tab] Permissions | | HU-LI23 | [Explore Category] Skill Catalog |
| HU-LI11 | [Asset Tab] Discussion | | HU-LI24 | [Explore Category] RAG Apps |
| HU-LI12 | [Asset Tab] History | | HU-LI25 | [Explore Category] Models |

> **Codes as on the board.** `Control H de U.xlsx` assigns `HU-LI03` twice — to *Edit Asset*
> and to *Explore Category*. Both are kept verbatim here; the two stories are distinguished by
> name.

> The contribution/review workflow runs on the `actions` table through `type` and
> `workflow_status` (`ASSIGNED` → `NOTIFIED` → `FINISHED`). Full matrix:
> [Asset Action Workflows](states-and-types.md#asset-action-workflows-actions-table).
> What each tab does per parent story:
> [Asset tab options](states-and-types.md#asset-tab-options-by-user-story).

---

## Asset Management

### HU-LI01 · Asset Management
> As an **asset owner**, I want to **manage the assets I am responsible for**, filtered by
> category, status, privileges and favorites, **so that** the catalog stays curated across the
> whole asset lifecycle.
- **Data:** `assets` — `id`, `name`, `description`, `category` (FK → `categories.code`),
  `reference`, `status` (→ `ASSET_STATUS`: Proposed, Feedback Provided, Published, Rejected,
  Deprecated), `tags` (JSONB), `detail`, `current_version`. The list is scoped to the assets
  the user can reach through `asset_permissions`; rows the user can only *view* hide the edit
  actions.
- **UI:** [`lib/assets.astro`](../../ui/src/pages/lib/assets.astro)

### HU-LI02 · – New Asset
> As an **asset owner**, I want to **create an asset directly**, filling every tab before
> saving, **so that** an asset that needs no review can be registered in one pass.
- **Behavior:** all tabs are staged in the modal and persisted together on save — core fields,
  characteristics, related assets, related inits and permissions (Discussion / History /
  Versioning do not apply yet). The creator is granted `MANAGE` on the new asset.
- **Data:** `assets` + `characterizations` + `related_assets` + `asset_inits` +
  `asset_permissions`
- **UI:** create mode of [`AssetDetailModal.astro`](../../ui/src/components/lib/AssetDetailModal.astro)
  + [`AssetDetailTabs.svelte`](../../ui/src/components/svelte/AssetDetailTabs.svelte).
  Detail of **HU-LI01**.

### HU-LI03 · – Edit Asset (Include Versioning / Deprecation)
> As an **asset owner**, I want to **edit an asset one tab at a time**, **publish a new
> version** when its characteristics change, and **deprecate** it when it is superseded,
> **so that** improvements are tracked without losing history and obsolete assets are retired.
- **Behavior:** each tab saves **its own slice only**. Saving the **Characteristics** tab asks
  for a change type (Major / Minor / Patch), bumps `assets.current_version` accordingly,
  snapshots the characterizations under the new `version_label` and records a `VERSIONING`
  action. Core fields, related assets, related inits and permissions save in place with no
  version bump. Setting the status to *Deprecated* records a `DEPRECATION` action.
- **Data:** `assets`, `characterizations` (per `version_label`), `actions`
  (`VERSIONING` / `DEPRECATION`, `workflow_status = FINISHED`)
- **UI:** edit mode of [`AssetDetailModal.astro`](../../ui/src/components/lib/AssetDetailModal.astro).
  Detail of **HU-LI01**.

---

## Explore Category

### HU-LI03 · Explore Category (Include Favorite / Vote)
> As any **user**, I want to **browse the published assets of a category as a card gallery**,
> search and filter them, **favorite** the ones I care about and **vote** on them, **so that**
> I can discover and reuse what the organization already has.
- **Behavior:** one generic page driven by the option's own `code` / `name` / `icon`
  (`/lib/explore?code=<CATEGORY>`); every AI Library sidebar entry and every taxonomy leaf
  points here. Cards show icon, name, status, version, description, tags and the vote /
  discussion counters. The gallery is scoped by `asset_permissions`; a category with no assets
  yet shows a *coming soon* placeholder. A **Propose** call to action leads to **HU-LI04**.
- **Data:** `assets` (published, by category) + `favorite_assets` + `actions` of `type = VOTE`
  (one active vote per user and asset, `content` = `POSITIVE` / `NEGATIVE`)
- **UI:** [`lib/explore.astro`](../../ui/src/pages/lib/explore.astro),
  [`ExploreCard.astro`](../../ui/src/components/lib/ExploreCard.astro),
  [`gallery/CardGallery.astro`](../../ui/src/components/lib/gallery/CardGallery.astro)

### HU-LI04 · – Propose Asset
> As a **collaborator**, I want to **propose a new asset for a category and request a
> reviewer** **so that** it enters the review workflow before being published.
- **Behavior:** a wizard whose steps are the asset tabs — **Core Fields → Characteristics →
  Related Assets → Related Inits**, the last one submitting the proposal. The category is
  locked when the page is reached from a gallery; required characteristics (from
  `specifications.required`) must be filled. A proposer who is not an administrator cannot
  pick themselves as reviewer. On success an acknowledgement dialog reports the outcome before
  returning to the category.
- **Data:** one transaction inserts — an `assets` row (`status = PROPOSED`); one
  `characterizations` row per feature in the category's `specifications`; an `actions` row for
  the proposer (`type = PROPOSAL`, `workflow_status = FINISHED`); an `actions` row for the
  chosen reviewer (`type = REVIEW`, `workflow_status = ASSIGNED`); and `asset_permissions`
  rows (`access_level = MANAGE`, open validity) for the proposer and the reviewer.
- **UI:** [`lib/propose.astro`](../../ui/src/pages/lib/propose.astro). Detail of **HU-LI03
  Explore Category**.

### HU-LI05 · – Asset Detail (Include Favorite / Vote)
> As any **user**, I want to **open an asset's full detail** from the gallery — description,
> characteristics, relations, discussion, history and versions — and **favorite** or **vote**
> on it from there, **so that** I can judge whether to reuse it.
- **Behavior:** read-mostly modal. Core fields and characteristics are unified in a single
  **Detail** tab; Related Assets, Related Inits, History and Versions are read-only; Discussion
  stays fully interactive; Permissions is not shown.
- **Data:** read view over `assets` + `characterizations` (current version) + relations +
  `actions`; writes only `favorite_assets` and `actions` of `type = VOTE`.
- **UI:** [`ExploreDetailModal.astro`](../../ui/src/components/lib/ExploreDetailModal.astro)
  over [`gallery/CatalogDetailModal.astro`](../../ui/src/components/lib/gallery/CatalogDetailModal.astro).
  Detail of **HU-LI03 Explore Category**.

---

## Asset tabs

The same eight tabs back every asset surface; what each one *does* depends on the parent story
(New Asset / Edit Asset / Propose Asset / Asset Detail) — see the
[asset tab matrix](states-and-types.md#asset-tab-options-by-user-story).

### HU-LI06 · [Asset Tab] Core Fields
> As a **contributor**, I want to **fill an asset's core identity** — name, category, status,
> description, repository reference, tags and detail — **so that** it is identifiable and
> findable.
- **Data:** `assets` — `name`, `category`, `status`, `description`, `reference`, `tags`,
  `detail`
- **Options:** New Asset → *Save* · Edit Asset → *Save core fields* · Propose Asset →
  *Characteristics ›* · Asset Detail → unified in the *Detail* tab

### HU-LI07 · [Asset Tab] Characteristics (Include Report Usage)
> As a **contributor**, I want to **fill the features the asset's category declares** — each
> with a value and an optional detail note — and, as a **consumer**, **copy a characteristic's
> content** so that its **usage is reported** and the most-used assets can be identified.
- **Data:** `characterizations` — PK `(asset, version_label, feature)`, `value` (the payload),
  `detail` (optional elaboration). The form is built from `specifications` for the asset's
  category: `required` blocks the save, `copyable` renders the value in a copy box, `sort_order`
  fixes the order, `default_value` pre-fills it. Copying a value inserts an `actions` row of
  `type = USAGE`.
- **Options:** New Asset → *Save* · Edit Asset → *Save new version* (see **HU-LI13**) ·
  Propose Asset → *Related assets ›* · Asset Detail → read-only, inside the *Detail* tab

### HU-LI08 · [Asset Tab] Related Assets
> As a **contributor**, I want to **link an asset to other assets** (depends on, extends,
> similar to, …) with a rationale **so that** users can navigate between connected assets.
- **Data:** `related_assets` — PK `(source, target, type)`, `type` (→ `RELATION_TYPE`),
  `rationale`. Shown in both directions and de-duplicated.
- **Options:** New Asset → *Save* · Edit Asset → *Save related assets* · Propose Asset →
  *Related inits ›* · Asset Detail → read-only

### HU-LI09 · [Asset Tab] Related Inits
> As a **contributor**, I want to **link an asset to the initiatives it supports or came from**
> **so that** the library and the initiative portfolio stay connected.
- **Data:** `asset_inits` — PK `(asset, init, type)`, `type` (→ `RELATION_TYPE`), `rationale`;
  target initiatives come from `initiatives`.
- **Options:** New Asset → *Save* · Edit Asset → *Save related inits* · Propose Asset →
  *Request asset review* (final step) · Asset Detail → read-only

### HU-LI10 · [Asset Tab] Permissions
> As an **asset owner**, I want to **grant view or manage access to users, roles, projects,
> teams, units or everyone**, for a validity window, **so that** visibility and editing are
> controlled per audience.
- **Data:** `asset_permissions` — `asset`, `target_type` (→ `TARGET_TYPE`), `target_code`,
  `access_level` (→ `ACCESS_LEVEL`: View / Manage), `valid_from`, `valid_to`. A grant is
  **revoked**, never deleted: revoking stamps `valid_to`. A grant is live while
  `valid_to IS NULL OR valid_to > now()`.
- **Options:** New Asset → *Save* · Edit Asset → *Save permissions* · Propose Asset → not
  applicable · Asset Detail → not applicable

### HU-LI11 · [Asset Tab] Discussion
> As a **community member**, I want to **comment on an asset and ask or answer questions about
> it** **so that** knowledge about the asset stays attached to the asset.
- **Data:** `actions` of `type = COMMENT` / `QUESTION` / `ANSWER`; answers are threaded to
  their question through `parent`.
- **Options:** New Asset → not applicable · Edit Asset → read-only (participation belongs to
  the Explore surface) · Propose Asset → not applicable · Asset Detail → fully interactive
- **UI:** [`Foro.svelte`](../../ui/src/components/svelte/Foro.svelte)

### HU-LI12 · [Asset Tab] History
> As any **user**, I want to **see an asset's activity timeline** — proposal, review,
> publication, votes, comments, usage, versioning, deprecation — **so that** I understand how
> it evolved.
- **Data:** read-only view over `actions` for the asset, newest first, with the acting user.
- **Options:** read-only wherever it is shown (Edit Asset, Asset Detail); not applicable while
  creating or proposing.
- **UI:** [`gallery/HistoryTimeline.astro`](../../ui/src/components/lib/gallery/HistoryTimeline.astro)

### HU-LI13 · [Asset Tab] Versioning
> As any **user**, I want to **see every version of an asset** — date, author, change type and
> the characteristics as they were — **so that** I can compare generations and understand what
> changed.
- **Data:** read-only view over `characterizations` grouped by `version_label` (one entry per
  label, including the initial `1.0.0`), enriched with the matching `VERSIONING` actions and
  flagged against `assets.current_version`.
- **Options:** read-only wherever it is shown (Edit Asset, Asset Detail); the *write* side —
  bumping the version — lives in **HU-LI03 Edit Asset**.
- **UI:** [`gallery/VersionsTimeline.astro`](../../ui/src/components/lib/gallery/VersionsTimeline.astro)

---

## Review workflow

These stories implement the contribution/review loop on `actions`. See the
[workflow matrix](states-and-types.md#asset-action-workflows-actions-table).

### HU-LI14 · [Notifications] Asset Notifications
> As an **assignee** (reviewer or proposer), I want a **notification bell listing the workflow
> actions waiting on me** **so that** I know what needs my attention.
- **Behavior:** lists the user's `actions` grouped by asset whose **latest** `workflow_status`
  is `ASSIGNED` (bold) or `NOTIFIED` (not bold), for `type` in `REVIEW` / `MODIFICATION` /
  `PUBLICATION` / `REJECTION`. Opening one routes to **HU-LI16 Review Asset Proposal**
  (`REVIEW`), **HU-LI17 Modify Asset Proposal** (`MODIFICATION`) or **HU-LI18 Asset Request
  Detail** (`PUBLICATION` / `REJECTION`). Dismissing is offered only for the informational
  outcomes (`PUBLICATION` / `REJECTION`) and inserts that action with
  `workflow_status = FINISHED`; `REVIEW` and `MODIFICATION` cannot be dismissed, since that
  would silently drop the assignment.
- **Data:** `actions` (`type`, `workflow_status`, `content`)
- **UI:** [`NotificationBell.svelte`](../../ui/src/components/svelte/NotificationBell.svelte)

### HU-LI15 · [Account Menu] My Asset Requests
> As a **reviewer or proposer**, I want a **durable list of my asset requests** — open and
> already resolved — **so that** I can find my pending work without depending on a transient
> notification.
- **Behavior:** lists the user's `actions` grouped by asset with status `ASSIGNED` (bold),
  `NOTIFIED` (plain) or `FINISHED` (muted), for `type` in `REVIEW` / `MODIFICATION` /
  `PUBLICATION` / `REJECTION`. Every `FINISHED` action — and every `PUBLICATION` / `REJECTION`
  — opens **HU-LI18 Asset Request Detail**; the rest open **HU-LI16** (`REVIEW`) or **HU-LI17**
  (`MODIFICATION`). Reached from the account menu's *My Workspace* section.
- **Data:** `actions` (`type`, `workflow_status`)
- **UI:** [`lib/my_asset_requests.astro`](../../ui/src/pages/lib/my_asset_requests.astro)

### HU-LI16 · – Review Asset Proposal
> As a **reviewer**, I want to **review a proposed asset and approve it, reject it or request
> changes** **so that** only vetted assets are published.
- **Behavior:** on open, an `ASSIGNED` action is un-bolded in the notifications and re-inserted
  as `NOTIFIED`. On decision, one transaction inserts the `REVIEW` action as `FINISHED`, sets
  the asset `status` to `PUBLISHED` / `REJECTED` / `FEEDBACK`, and inserts an action for the
  **proposer** of `type` `PUBLICATION` / `REJECTION` / `MODIFICATION` with
  `workflow_status = ASSIGNED` and the feedback in `content`. Feedback is mandatory when
  rejecting or requesting changes.
- **Data:** `actions`, `assets.status`
- **UI:** [`lib/review.astro`](../../ui/src/pages/lib/review.astro),
  [`ReviewAction.svelte`](../../ui/src/components/svelte/ReviewAction.svelte).
  Detail of **HU-LI15**.

### HU-LI17 · – Modify Asset Proposal
> As a **proposer**, I want to **apply the changes a reviewer asked for and resubmit** **so
> that** the review cycle can continue.
- **Behavior:** on open, an `ASSIGNED` action is un-bolded and re-inserted as `NOTIFIED`. On
  save, one transaction updates the asset and its characterizations in place, inserts the
  `MODIFICATION` action as `FINISHED`, flips the asset back to `PROPOSED`, and re-arms the
  **same reviewer** with a new `REVIEW` action as `ASSIGNED`. The category is fixed (it decides
  the characteristic set); the cycle is not capped.
- **Data:** `actions`, `assets`, `characterizations`
- **UI:** [`lib/modify.astro`](../../ui/src/pages/lib/modify.astro),
  [`ModifyAction.svelte`](../../ui/src/components/svelte/ModifyAction.svelte).
  Detail of **HU-LI15**.

### HU-LI18 · – Asset Request Detail
> As a **proposer**, I want to **see the outcome of my proposal** — published or rejected, with
> the reviewer's message — **so that** I learn the result and can clear the notification.
- **Behavior:** read-only outcome card (approval vs rejection styling, asset name, message,
  timestamp). On open, an `ASSIGNED` action is un-bolded and re-inserted as `NOTIFIED`;
  dismissing inserts it as `FINISHED`.
- **Data:** `actions`, `assets`
- **UI:** [`lib/show-action.astro`](../../ui/src/pages/lib/show-action.astro),
  [`ShowAction.svelte`](../../ui/src/components/svelte/ShowAction.svelte).
  Detail of **HU-LI15**.

---

## Category galleries

Each of these is **HU-LI03 Explore Category** bound to one taxonomy category — same page, same
cards, same detail modal, same tabs; only `?code=` changes. Adding a category is a seed change
(`options` + `categories` + `specifications`), not a new page.

| Code | Story | Category | Entry point |
|------|-------|----------|-------------|
| HU-LI19 | [Explore Category] Prompt Gallery | `PROMPTS` | `/lib/explore?code=PROMPTS` |
| HU-LI20 | [Explore Category] MCP Directory | `MCPS` | `/lib/explore?code=MCPS` |
| HU-LI21 | [Explore Category] Agent Repository | `AGENTS` | `/lib/explore?code=AGENTS` |
| HU-LI22 | [Explore Category] Agentic Flows | `FLOWS` | `/lib/explore?code=FLOWS` |
| HU-LI23 | [Explore Category] Skill Catalog | `SKILLS` | `/lib/explore?code=SKILLS` |
| HU-LI24 | [Explore Category] RAG Apps | `RAG_APPS` | `/lib/explore?code=RAG_APPS` |
| HU-LI25 | [Explore Category] Models | `MODELS` | `/lib/explore?code=MODELS` |

> As a **contributor**, I want **one gallery per asset family** — reusable prompts, MCP
> servers, agents, agentic flows, skills, RAG applications and models — **so that** I can
> discover, reuse and propose assets within the family I work in.
