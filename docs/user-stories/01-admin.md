# Administration — User Stories

> Module `ADMIN` · API domain [`api/app/admin`](../../api/app) · DB band 10s
> ([`11-admin-ddl.sql`](../../db/sql/11-admin-ddl.sql)) · Diagram [1-admin.png](../diagrams/1-admin.png)

Administration centralizes everything needed to operate SynapxIA: the organization's units,
profiles and privileges, users, configurable lists, and the modules/options that drive
navigation. It also owns the **application shell** — login, landing page, menu, search,
theme, language, account menu and support.

| Code | Story | | Code | Story |
|------|-------|-|------|-------|
| HU-AD01 | Business Units | | HU-AD10 | Landing Page |
| HU-AD02 | Profiles | | HU-AD11 | Load Menu (Include "Hide Menu") |
| HU-AD03 | – Privileges | | HU-AD12 | Search |
| HU-AD04 | Users | | HU-AD13 | Dark Mode (Include "Light Mode") |
| HU-AD05 | Lists | | HU-AD14 | Language Selector |
| HU-AD06 | – List Items | | HU-AD15 | Account Menu (With "My Workspace" Options) |
| HU-AD07 | Modules | | HU-AD16 | – Account Settings (Include "Change Password") |
| HU-AD08 | Options | | HU-AD17 | – Support (Include "Contact us" / "Report a Bug") |
| HU-AD09 | Login (Include "Forgot Password") | | HU-AD18 | – Sign Out |

---

## Configuration

### HU-AD01 · Business Units
> As an **administrator**, I want to **define the organization's units in a hierarchy**
> (division, area, department, business unit) **so that** users, processes and metrics can be
> attributed to the right part of the organization.
- **Data:** `business_units` — `code`, `name`, `description`, `type` (→ `BIZ_UNIT_TYPE`),
  `parent` (self-FK)
- **UI:** [`admin/business_units.astro`](../../ui/src/pages/admin/business_units.astro)

### HU-AD02 · Profiles
> As an **administrator**, I want to **manage access profiles** **so that** I can group the
> privileges that decide what each kind of user sees and edits.
- **Data:** `profiles` — `code`, `name`, `description`, `icon`. Seeded: `ADMINISTRATOR`,
  `ADMINISTRATIVE`, `COLLABORATOR`, `REVIEWER`.
- **UI:** [`admin/profiles.astro`](../../ui/src/pages/admin/profiles.astro)

### HU-AD03 · – Privileges
> As an **administrator**, I want to **grant a profile access to specific module options**
> with a view/edit flag **so that** the privilege matrix enforces role-based access control.
- **Data:** `privileges` — PK `(profile, module, option)`, `can_edit`. Detail of **HU-AD02**;
  the option list refreshes with the selected module.
- **UI:** [`admin/privileges.astro`](../../ui/src/pages/admin/privileges.astro)

### HU-AD04 · Users
> As an **administrator**, I want to **create and maintain user accounts** (profile, business
> unit, activation) **so that** people can authenticate and operate with the right permissions.
- **Data:** `users` — `id`, `username`, `email`, `password_hash`, `first_name`, `last_name`,
  `profile` (FK), `unit` (FK), `is_superuser`, `is_verified`, `is_active`, `last_login_at`
- **UI:** [`admin/users.astro`](../../ui/src/pages/admin/users.astro)

### HU-AD05 · Lists
> As an **administrator**, I want to **define configurable lists** (lists of values, scales,
> features, criteria) **so that** enumerations across modules are centrally managed instead of
> hard-coded.
- **Data:** `lists` — `code`, `name`, `module`, `type` (→ `LIST_TYPE`: `LIST_OF_VALUES`,
  `SCALE`, `FEATURE`, `CRITERIA`)
- **UI:** [`admin/lists.astro`](../../ui/src/pages/admin/lists.astro)

### HU-AD06 · – List Items
> As an **administrator**, I want to **manage the items of a list per language** **so that**
> every list of values is bilingual (en/es) and ordered for the UI.
- **Data:** `list_items` — PK `(list, lang, value)`, `label`, `sort_order`. Detail of
  **HU-AD05**; every form that loads a list filters by `lang`.
- **UI:** [`admin/list_items.astro`](../../ui/src/pages/admin/list_items.astro)

### HU-AD07 · Modules
> As an **administrator**, I want to **register the platform modules** (icon, order,
> visibility) **so that** they drive the primary navigation and scope lists, options and
> privileges.
- **Data:** `modules` — `code`, `name`, `description`, `sort_order`, `icon`. Seeded: the 7
  modules of this catalog.
- **UI:** [`admin/modules.astro`](../../ui/src/pages/admin/modules.astro)

### HU-AD08 · Options
> As an **administrator**, I want to **define the navigable options of each module** (forms,
> content pages, reports, card galleries) **so that** they populate the sidebar and become the
> targets of the privilege matrix.
- **Data:** `options` — PK `(module, code)`, `name`, `path`, `type` (→ `OPTION_TYPE`), `icon`,
  `sort_order`
- **UI:** [`admin/options.astro`](../../ui/src/pages/admin/options.astro)

---

## Application shell

### HU-AD09 · Login (Include "Forgot Password")
> As a **user**, I want to **sign in with my credentials** and **recover a forgotten
> password** **so that** I can reach the platform securely.
- **Data:** `users` (`password_hash`, `is_active`, `last_login_at`), `refresh_tokens`
- **UI:** [`login.astro`](../../ui/src/pages/login.astro) ·
  [`middleware.ts`](../../ui/src/middleware.ts) guards every private route
- **Behavior:** JWT Bearer + bcrypt; repeated failed attempts are rate-limited. After login
  the user lands on the first `LIB` option their profile is privileged for.

### HU-AD10 · Landing Page
> As a **visitor**, I want a **public landing page** presenting SynapxIA **so that** I
> understand the product before signing in.
- **UI:** [`index.astro`](../../ui/src/pages/index.astro) ·
  [`landing/LandingBody.astro`](../../ui/src/components/landing/LandingBody.astro)

### HU-AD11 · Load Menu (Include "Hide Menu")
> As a **signed-in user**, I want the **sidebar to show only the modules and options my
> profile is privileged for**, expandable per module and collapsible as a whole, **so that**
> navigation reflects my permissions and I can reclaim screen space.
- **Data:** `modules` + `options` + `privileges` for the current user's `profile`, ordered by
  `sort_order`.
- **UI:** [`sidebar/SideBar.astro`](../../ui/src/components/core/sidebar/SideBar.astro),
  [`SideBarMenuItem.astro`](../../ui/src/components/core/sidebar/SideBarMenuItem.astro),
  [`lib/navigation.ts`](../../ui/src/lib/navigation.ts)

### HU-AD12 · Search
> As a **signed-in user**, I want to **search the platform's modules and options from the
> header** (⌘K / Ctrl+K) **so that** I can jump anywhere without walking the menu.
- **Behavior:** ranks navigation entries by text relevance, boosts the `LIB` module, and
  learns from the user's own recency/usage (kept client-side). Each result shows a
  `Home › Module` breadcrumb and navigates to `options.path`.
- **UI:** [`header/SearchBar.astro`](../../ui/src/components/core/header/SearchBar.astro),
  [`SearchPalette.svelte`](../../ui/src/components/svelte/SearchPalette.svelte),
  [`lib/searchIndex.ts`](../../ui/src/lib/searchIndex.ts)

### HU-AD13 · Dark Mode (Include "Light Mode")
> As a **signed-in user**, I want to **switch between dark and light themes** **so that** the
> interface is comfortable in my working environment.
- **UI:** [`header/ThemeSwitcher.astro`](../../ui/src/components/core/header/ThemeSwitcher.astro)
  (also offered inside the account menu); the choice persists per browser.

### HU-AD14 · Language Selector
> As a **signed-in user**, I want to **switch the interface language (en / es)** **so that** I
> work in my own language.
- **Data:** UI strings in [`i18n/en.json`](../../ui/src/i18n/en.json) /
  [`es.json`](../../ui/src/i18n/es.json); catalog labels from `list_items.lang`.
- **UI:** [`header/LanguageSwitcher.astro`](../../ui/src/components/core/header/LanguageSwitcher.astro)

### HU-AD15 · Account Menu (With "My Workspace" Options)
> As a **signed-in user**, I want an **account menu** with who I am, my theme/language
> switches, my personal queues and the way out **so that** everything about *me* is in one
> place.
- **Behavior:** the **My Workspace** section lists the personal request queues —
  *My Asset Requests* ([HU-LI15](04-lib.md#hu-li15--account-menu-my-asset-requests)) and
  *My Initiative Requests* ([HU-IN14](05-inits.md#hu-in14--account-menu-my-initiative-requests)) —
  filtered by profile, so entries the user cannot act on are hidden.
- **UI:** [`header/AccountMenu.astro`](../../ui/src/components/core/header/AccountMenu.astro)

### HU-AD16 · – Account Settings (Include "Change Password")
> As a **signed-in user**, I want to **see and edit my account data and change my password**
> **so that** my profile stays current and my credentials stay mine.
- **Data:** `users` — editable `first_name`, `last_name`, `email`, `username`; `profile` and
  `unit` stay read-only (administrator-managed); a password change rewrites `password_hash`.
- **UI:** [`profile.astro`](../../ui/src/pages/profile.astro). Detail of **HU-AD15**.

### HU-AD17 · – Support (Include "Contact us" / "Report a Bug")
> As a **signed-in user**, I want to **contact the team and report a bug with a screenshot I
> can annotate** **so that** problems are reported with enough context to reproduce them.
- **Data:** `bug_reports` — `user_id`, `description`, `page_url`, `user_agent`, `screenshot`
  (annotated capture), `attachments` (extra images), `status` (`OPEN` / `RESOLVED`)
- **UI:** [`support.astro`](../../ui/src/pages/support.astro),
  [`BugReporter.svelte`](../../ui/src/components/svelte/BugReporter.svelte),
  [`BugReportWidget.astro`](../../ui/src/components/core/BugReportWidget.astro) (floating
  shortcut, enabled from the support page). Detail of **HU-AD15**.

### HU-AD18 · – Sign Out
> As a **signed-in user**, I want to **sign out** **so that** my session is closed on a shared
> device.
- **Behavior:** clears the session cookie and client-side state, revokes the refresh token and
  returns to **HU-AD09 Login**.
- **UI:** account menu action → [`lib/auth.ts`](../../ui/src/lib/auth.ts). Detail of **HU-AD15**.
