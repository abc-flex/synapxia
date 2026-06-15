# Administration — User Stories

> Module `ADMIN` · API domain [`api/app/admin`](../../api/app) · DB band 10s
> ([`11-admin-ddl.sql`](../../db/sql/11-admin-ddl.sql)) · Diagram [1-admin.png](../diagrams/1-admin.png)

Administration centralizes the support capabilities required to operate SynapxIA:
profiles, users, modules, privileges and the core configuration elements (business units,
lists) that enable secure and consistent platform management.

| Code | Story |
|------|-------|
| HU-AD01 | Business Units |
| HU-AD02 | Profiles |
| HU-AD03 | – Privileges |
| HU-AD04 | Users |
| HU-AD05 | Lists |
| HU-AD06 | – List Items |
| HU-AD07 | Modules |
| HU-AD08 | Options |

---

### HU-AD01 · Business Units
> As an **administrator**, I want to **define the organization's units in a hierarchy**
> (divisions, areas, departments, business units) **so that** users, processes and metrics
> can be attributed to the right part of the organization.
- **Data:** `business_units` — `code`, `name`, `type` (→ `BIZ_UNIT_TYPE`), `parent` (self-FK)
- **UI:** [`ui/src/pages/admin/business_units.astro`](../../ui/src/pages/admin/business_units.astro)

### HU-AD02 · Profiles
> As an **administrator**, I want to **manage access profiles** so that I can group the
> privileges that determine what each kind of user can see and edit.
- **Data:** `profiles` — `code`, `name`, `description`, `icon`. Seeded: `ADMINISTRATOR`,
  `ADMINISTRATIVE`, `COLLABORATOR`.
- **UI:** [`ui/src/pages/admin/profiles.astro`](../../ui/src/pages/admin/profiles.astro)

### HU-AD03 · – Privileges
> As an **administrator**, I want to **grant a profile access to specific module options**
> with a view/edit flag **so that** the privilege matrix enforces role-based access control.
- **Data:** `privileges` — PK `(profile, module, option)`, `can_edit`. Detail of **HU-AD02**.
- **UI:** [`ui/src/pages/admin/privileges.astro`](../../ui/src/pages/admin/privileges.astro)

### HU-AD04 · Users
> As an **administrator**, I want to **create and maintain user accounts** (with profile and
> business unit) **so that** people can authenticate and operate with the right permissions.
- **Data:** `users` — `id`, `username`, `email`, `password_hash`, `profile` (FK), `unit` (FK),
  `is_superuser`, `is_verified`, `is_active`, `last_login_at`
- **UI:** [`ui/src/pages/admin/users.astro`](../../ui/src/pages/admin/users.astro)

### HU-AD05 · Lists
> As an **administrator**, I want to **define configurable lists** (lists of values, scales,
> features, criteria) **so that** enumerations across modules are centrally managed instead
> of hard-coded.
- **Data:** `lists` — `code`, `name`, `module`, `type` (`LIST_OF_VALUES` / `SCALE` /
  `FEATURE` / `CRITERIA`)
- **UI:** [`ui/src/pages/admin/lists.astro`](../../ui/src/pages/admin/lists.astro)

### HU-AD06 · – List Items
> As an **administrator**, I want to **manage the items of a list in each language** so that
> every list of values is bilingual (en/es) and ordered for the UI.
- **Data:** `list_items` — PK `(list, lang, value)`, `label`, `sort_order`. Detail of **HU-AD05**.
  See also the **Item Translations** helper page.
- **UI:** [`ui/src/pages/admin/list_items.astro`](../../ui/src/pages/admin/list_items.astro),
  [`ui/src/pages/admin/item_translations.astro`](../../ui/src/pages/admin/item_translations.astro)

### HU-AD07 · Modules
> As an **administrator**, I want to **register the platform modules** (with icon and order)
> **so that** they drive the primary navigation and scope lists, options and privileges.
- **Data:** `modules` — `code`, `name`, `description`, `sort_order`, `icon`. Seeded: the 7
  modules in this catalog.
- **UI:** [`ui/src/pages/admin/modules.astro`](../../ui/src/pages/admin/modules.astro)

### HU-AD08 · Options
> As an **administrator**, I want to **define the navigable options of each module** (content
> pages, forms, reports) **so that** they populate the sidebar and become the targets of the
> privilege matrix.
- **Data:** `options` — PK `(module, code)`, `name`, `path`, `type` (→ `OPTION_TYPE`),
  `icon`, `sort_order`
- **UI:** [`ui/src/pages/admin/options.astro`](../../ui/src/pages/admin/options.astro)
