# CLAUDE.md — UI

Companion to [`AGENTS.md`](AGENTS.md) (rules) and the root [`../AGENTS.md`](../AGENTS.md)
(Constitution + repo-wide conventions). This file is the **actionable map** of the UI
service: every page, every reusable component, every code surface needed to add a CRUD
screen without rediscovering the patterns.

> **Rule of thumb:** rules live in [`AGENTS.md`](AGENTS.md). Concrete code paths,
> component inventories, and patterns live here.

---

## Stack

| Item | Value |
|------|-------|
| Framework | Astro 5 (SSR, `output: "server"`) + Vite 8 |
| Islands | Svelte 5 (manual `mount()`; raw `@sveltejs/vite-plugin-svelte`, not `@astrojs/svelte`) |
| Styling | Tailwind CSS 3 + Flowbite (Tailwind component lib, loaded via CDN) |
| Tables | `simple-datatables` (search, pagination, export) |
| Package manager | Bun |
| Container port | 4321 |
| Language | TypeScript (server-side `.astro` + client islands) |
| State | `localStorage` (no Redux/Zustand) |
| i18n | Custom JSON + runtime `data-i18n` patch |

**Svelte for heavy islands; vanilla by default.** Simple pages stay Astro + vanilla
`<script>`. For complex interactive surfaces use **Svelte 5** components in
`ui/src/components/svelte/`, compiled by the raw **`@sveltejs/vite-plugin-svelte`** (added to
`astro.config.mjs` `vite.plugins`) and **mounted manually** with Svelte's `mount()` from a
bundled `<script>` — e.g. `ui/src/pages/lib/show-action.astro` (page-level), or a component
shell that self-mounts by querying a `data-*-root` div (`components/core/header/NotificationMenu.astro`
→ `NotificationBell.svelte`; `components/lib/gallery/Foro.astro` → `Foro.svelte`, the asset
discussion HU-LI06). Do **not** use the `@astrojs/svelte` *integration* / `client:*` island
directives: the only version installable from our registry (`9.0.0`) mis-compiles its island
`astro-entry` whenever a Svelte island shares a page with vanilla `<script>`s (which every
`BaseLayout` page has). Manual `mount()` sidesteps that entirely and works on Vite 8. Svelte
islands reuse the existing `lib/*` services and read i18n via `translate()` (not `data-i18n`).
Template comments inside `.svelte` are `<!-- -->`, **not** JSX `{/* */}`. No React/Vue.

**Migrating a vanilla `mount*(cfg)` controller to Svelte:** move the render/state layer to
`components/svelte/X.svelte`, self-mount it from the controller's `.astro` shell (render
`<div data-x-root data-…>` + a bundled `<script>` that `mount()`s the island, reading its
config from the `data-` attrs), keep the shared `lib/*` services in place (trim the `.ts` to
just services + pure helpers), and delete the old `mount*` call from the caller. The island
re-hooks the same DOM triggers (e.g. `[data-modal-open]`) in `onMount`. See the foro migration
(`lib/foro.ts` 452→98 lines).

---

## Directory map (`ui/src/`)

```
ui/
├── astro.config.mjs            # Tailwind integration, @ alias, Vite polling
├── package.json                # bun scripts (dev/build/preview), Astro/Tailwind/Flowbite deps
├── vercel.json                 # Vercel static deploy (bun build → dist/)
├── tsconfig.json               # strict TS
├── public/
│   └── scripts/
│       └── dashboard.js        # Dashboard-specific JS  (crudClient moved to src/lib/)
└── src/
    ├── env.d.ts                # ImportMeta env types
    ├── layouts/
    │   ├── BaseLayout.astro    # AUTH layout: Header + Sidebar + slot
    │   └── Layout.astro        # MINIMAL layout: login / signup / full-screen pages
    ├── pages/                  # File-based routing
    │   ├── index.astro                 # Landing
    │   ├── dashboard.astro             # Authenticated dashboard (Layout, not BaseLayout)
    │   ├── login.astro
    │   ├── signup.astro
    │   ├── profile.astro
    │   ├── forms.astro                 # Form component showcase
    │   ├── admin/
    │   │   ├── users.astro             # User CRUD + profile/unit filters
    │   │   ├── profiles.astro
    │   │   ├── privileges.astro        # Composite-key CRUD (profile×module×option)
    │   │   ├── business_units.astro
    │   │   ├── modules.astro
    │   │   ├── options.astro           # Composite-key CRUD (module×code)
    │   │   ├── lists.astro
    │   │   ├── list_items.astro        # Composite-key CRUD (list×value)
    │   │   └── item_translations.astro # Triple composite (list×value×lang)
    │   ├── taxo/
    │   │   ├── categories.astro        # Hierarchical (parent self-FK)
    │   │   └── features.astro
    │   ├── lib/
    │   │   ├── assets.astro            # JSON tags/details
    │   │   └── characterizations.astro
    │   └── collab/
    │       ├── dashboard.astro
    │       ├── teams.astro
    │       ├── projects.astro
    │       ├── assignments.astro       # Temporal (valid_from/valid_to)
    │       ├── dimensions.astro
    │       └── metrics.astro
    ├── components/
    │   ├── core/                       # Layout + nav
    │   │   ├── header/
    │   │   │   ├── Header.astro        # Top bar
    │   │   │   ├── SearchBar.astro
    │   │   │   ├── ThemeSwitcher.astro
    │   │   │   ├── LanguageSwitcher.astro
    │   │   │   ├── AccountMenu.astro
    │   │   │   └── NotificationMenu.astro
    │   │   ├── sidebar/
    │   │   │   ├── SideBar.astro       # Modules → options nav
    │   │   │   └── SideBarMenuItem.astro
    │   │   └── Breadcrumb.astro
    │   ├── forms/
    │   │   ├── CrudModal.astro         # ⭐ Universal create/edit/delete modal
    │   │   ├── FormCard.astro
    │   │   ├── DefaultInputsCard.astro
    │   │   ├── SelectInputsCard.astro
    │   │   ├── CheckboxesCard.astro
    │   │   ├── RadiosCard.astro
    │   │   ├── TogglesCard.astro
    │   │   ├── TextareaCard.astro
    │   │   ├── InputGroupCard.astro
    │   │   ├── InputStatesCard.astro
    │   │   ├── FileInputCard.astro
    │   │   └── DropzoneCard.astro
    │   ├── table/
    │   │   ├── DataTable.astro         # ⭐ Orchestrator shell (props + bootstraps advancedTable)
    │   │   ├── advancedTable.ts        # simple-datatables init, export, filter logic
    │   │   └── parts/                  # DataTable sub-components (DOM-identical split)
    │   │       ├── DataTableToolbar.astro        # top bar: add/master/filters-toggle + filters + search/export
    │   │       ├── DataTableFilters.astro        # the 1–3 column-filter <select>s (single loop)
    │   │       ├── DataTableSearchExport.astro   # search input + export menu
    │   │       ├── DataTableHead.astro           # <thead>
    │   │       ├── DataTableBody.astro           # <tbody> rows (uses Cell + Actions)
    │   │       ├── DataTableCell.astro           # the `as`-dispatch cell renderer
    │   │       ├── DataTableActions.astro        # row action buttons (detail/expand/favorite/edit/delete)
    │   │       ├── DataTablePagination.astro     # footer (info, per-page, prev/next)
    │   │       └── DataTableEmpty.astro          # empty-state panel
    │   ├── Toast.astro                 # Top-right notifications
    │   └── ClientTranslations.astro    # Injects i18n dict into window for runtime patch
    ├── lib/                            # API service wrappers (one file per entity)
    │   ├── api.ts                      # ⭐ Fetch wrapper: GET/POST/PUT/DELETE + auth header
    │   ├── crudClient.js               # Modal ↔ form ↔ event bus glue (bundle via @/lib/crudClient)
    │   ├── datatable.ts                # Pure DataTable cell helpers (statusTone/formatDate/formatRelative/renderSubtitle)
    │   ├── auth.ts                     # login/register/logout/getCurrentUser + token storage
    │   ├── navigation.ts               # Builds sidebar from modules + options API
    │   ├── users.ts                    # Canonical example — copy when adding a new entity
    │   ├── profiles.ts
    │   ├── modules.ts
    │   ├── options.ts
    │   ├── privileges.ts
    │   ├── business_units.ts
    │   ├── lists.ts
    │   ├── list_items.ts
    │   ├── item_translations.ts
    │   ├── categories.ts
    │   ├── features.ts
    │   ├── assets.ts
    │   ├── teams.ts
    │   ├── roles.ts
    │   ├── projects.ts
    │   ├── dimensions.ts
    │   ├── metrics.ts
    │   ├── assignments.ts
    │   └── index.ts                    # Barrel re-exports
    ├── types/
    │   ├── api.ts                      # ⭐ Entity / EntityCreate / EntityUpdate interfaces
    │   ├── datatable.ts                # ColumnConfig / FilterOption / FilterConfig for DataTable
    │   ├── nav.ts                      # NavModule, NavOption
    │   └── category.ts
    ├── i18n/
    │   ├── en.json                     # ⭐ English dictionary (~390 keys)
    │   ├── es.json                     # ⭐ Spanish dictionary (mirror of en.json)
    │   └── index.ts
    ├── utils/
    │   ├── i18nClient.ts               # Runtime DOM patch via [data-i18n] attributes
    │   ├── clientLocale.ts
    │   └── getLocale.ts
    ├── styles/
    │   └── globals.css                 # Tailwind directives + theme vars
    └── data/                           # Static mock JSON (rarely used; prefer API)
```

⭐ marks the high-value surfaces you'll touch most often.

---

## Pages by module

### Admin — `/ui/src/pages/admin/`
| Page | Route | Notes |
|------|-------|-------|
| `users.astro` | `/admin/users` | Filters by profile + business unit; password set on create only |
| `profiles.astro` | `/admin/profiles` | Code-PK |
| `privileges.astro` | `/admin/privileges` | **Composite key**: profile × module × option |
| `business_units.astro` | `/admin/business_units` | Hierarchical via `parent` |
| `modules.astro` | `/admin/modules` | Drives the sidebar `primaryNav` |
| `options.astro` | `/admin/options` | **Composite key**: module × code; drives sidebar `itemsNav` |
| `lists.astro` | `/admin/lists` | Configurable enum catalog |
| `list_items.astro` | `/admin/list_items` | **Composite key**: list × value |
| `item_translations.astro` | `/admin/item_translations` | **Triple composite**: list × value × lang |

### Taxonomy — `/ui/src/pages/taxo/`
| Page | Route | Notes |
|------|-------|-------|
| `categories.astro` | `/taxo/categories` | Hierarchical (self-FK `parent`) |
| `features.astro` | `/taxo/features` | Type tied to FEAT_TYPE list |

### Lib — `/ui/src/pages/lib/`
| Page | Route | Notes |
|------|-------|-------|
| `assets.astro` | `/lib/assets` | JSON `tags` + `details` columns |
| `characterizations.astro` | `/lib/characterizations` | **Composite key**: asset × feature |

### Collab — `/ui/src/pages/collab/`
| Page | Route | Notes |
|------|-------|-------|
| `dashboard.astro` | `/collab/dashboard` | Module landing |
| `teams.astro` | `/collab/teams` | Optional `lead` (user FK) |
| `projects.astro` | `/collab/projects` | Status from list, optional `team` |
| `assignments.astro` | `/collab/assignments` | **Temporal**: valid_from / valid_to |
| `dimensions.astro` | `/collab/dimensions` | Master for metrics |
| `metrics.astro` | `/collab/metrics` | Master-detail from dimensions |

### Top-level
| Page | Route | Layout |
|------|-------|--------|
| `index.astro` | `/` | `Layout` (no auth) |
| `dashboard.astro` | `/dashboard` | `Layout` (full-screen, not sidebar) |
| `login.astro` | `/login` | `Layout` |
| `signup.astro` | `/signup` | `Layout` |
| `profile.astro` | `/profile` | `BaseLayout` |
| `forms.astro` | `/forms` | `BaseLayout` |

---

## Reusable components

### `DataTable.astro` (⭐ component #1)
Renders a `simple-datatables` table with search, pagination, export, row actions.

**Props:**
| Prop | Type | Purpose |
|------|------|---------|
| `tableId` | string | DOM id; used to wire up the modal triggers |
| `columns` | `{ key, label, visible?: boolean }[]` | `visible: false` keeps the column in form context but hides it |
| `data` | object[] | Pre-transformed rows (joins resolved server-side) |
| `entityName` | string | "User", "Team", etc. — drives i18n keys (`user_modal.*`) |
| `editModalId` / `deleteModalId` | string | Modal ids the row buttons trigger |
| `columnFilter` | string? | Single-column dropdown filter key |
| `filterOptions` | `{ value, label }[]?` | Options for `columnFilter` |
| `exportFormats` | `("csv"|"json"|"txt"|"sql")[]` | Default: all four |

**Per-row buttons emit:** `data-edit-id` / `data-delete-id` attributes; `crudClient.js`
binds these and opens the appropriate modal with `data-prefill` JSON.

### `CrudModal.astro` (⭐ component #2)
Universal create/edit/delete dialog. Renders form, validates, emits `crud-submit`.

**Props:**
| Prop | Type | Purpose |
|------|------|---------|
| `mode` | `"create" \| "edit" \| "delete"` | Affects field disabled-state + button label |
| `modalId` | string | DOM id (match `editModalId`/`deleteModalId` on DataTable) |
| `entityName` | string | "User", drives i18n keys |
| `entityI18key` | string? | Override default (lowercased entityName) |
| `fields` | `FormField[]` | Per-field config (see below) |
| `showTrigger` | boolean? | When `false`, modal is hidden until a row button opens it |

**FormField shape:**
```ts
{
  key: string,                                    // Maps to entity property
  label: string,                                  // i18n key (e.g. "user_modal.username")
  type?: "text" | "textarea" | "select" | "email" | "number" | "checkbox",
  required?: boolean,
  placeholder?: string,                           // i18n key for placeholder
  options?: { value: string, label: string, lang?: string }[],  // For type: "select"
  filterLang?: boolean,                           // Filter options to localStorage["lang"] client-side (options must carry `lang`, e.g. from getListItemsbyList)
  pk?: boolean,                                   // PK fields go readonly in edit mode
  disabled?: boolean
}
```

**Event:**
```js
document.addEventListener("crud-submit", async (e) => {
  const { mode, data, modalId } = e.detail;
  if (mode === "create") await createUser(data);
  // ...
});
```

### Layouts
- **`BaseLayout.astro`** — authenticated layout with header (search, theme, language,
  account, notifications) + sidebar (modules + options from `getNavigationData()`).
  Use for every page under `admin/`, `taxo/`, `lib/`, `collab/` (and `/profile`,
  `/forms`).
- **`Layout.astro`** — minimal HTML shell, no nav. Use for `/login`, `/signup`,
  `/index`, `/dashboard` (which is a standalone full-screen experience).
- **`@` alias** resolves to `ui/src/` via `fileURLToPath(new URL('./src', import.meta.url))`
  in `astro.config.mjs`. Use `import X from '@/lib/api'`, not `../../lib/api`.

### Notifications + i18n
- **`Toast.astro`** — call `window.showToast(message, type)` (type: error/info/success).
- **`ClientTranslations.astro`** — must be rendered once per layout. Injects the
  current locale's dictionary into `window.__I18N__` and triggers the runtime patch.

---

## API client (`ui/src/lib/api.ts`)

**Functions:**
```ts
apiGet<T>(route: string, init?: RequestInit): Promise<T>
apiPost<T, D>(route: string, data: D, init?: RequestInit): Promise<T>
apiPut<T, D>(route: string, data: D, init?: RequestInit): Promise<T>
apiDelete<T>(route: string, init?: RequestInit): Promise<T>
buildQueryString(params: Record<string, unknown>): string  // "?skip=0&limit=100"
```

**Behavior:**
- **Base URL** — `import.meta.env.PUBLIC_API_BASE_URL` (client) or `API_BASE_URL`
  (server during build). Defaults to `http://localhost:8000`.
- **Auth header** — auto-attaches `Authorization: Bearer ${getToken()}` from
  `localStorage`. No injection if token missing (anonymous endpoints).
- **Error handling** — non-2xx parses `{ detail }` from the body and throws an `Error`.
  Routes that 204 return `void`.
- **SSR safety** — list calls during `astro build` happen with no token + no API; the
  wrapper returns `[]` on connection failure so pre-render doesn't crash. Real data is
  fetched post-mount on the client.

**Adding a new service** (`ui/src/lib/{entity}.ts`):
```ts
import { apiGet, apiPost, apiPut, apiDelete, buildQueryString } from './api';
import type { Entity, EntityCreate, EntityUpdate } from '@/types/api';

export interface EntitySelectOption { value: string; label: string; }

export async function getEntities(skip = 0, limit = 100): Promise<Entity[]> {
  return apiGet<Entity[]>(`/api/entities${buildQueryString({ skip, limit })}`);
}
export async function getEntitiesSelect(): Promise<EntitySelectOption[]> {
  return apiGet<EntitySelectOption[]>(`/api/entities/select`);
}
export async function getEntity(key: string): Promise<Entity> {
  return apiGet<Entity>(`/api/entities/${key}`);
}
export async function createEntity(data: EntityCreate): Promise<Entity> {
  return apiPost<Entity>('/api/entities/', data);
}
export async function updateEntity(key: string, data: EntityUpdate): Promise<Entity> {
  return apiPut<Entity>(`/api/entities/${key}`, data);
}
export async function deleteEntity(key: string): Promise<void> {
  return apiDelete(`/api/entities/${key}`);
}
```

**Auth service** — `ui/src/lib/auth.ts`:
- `login(credentials) → LoginResponse` — POST OAuth2PasswordRequestForm
- `register(data) → UserRead`
- `getCurrentUser() → UserRead` — `/api/auth/me`
- `logout() → void` — clears token + user from `localStorage`
- `changePassword({ old_password, new_password })`
- Storage: `localStorage["auth_token"]`, `localStorage["auth_user"]` (JSON)

---

## Types (`ui/src/types/api.ts`)

**Pattern (Constitution-mandated):** three interfaces per entity.

```ts
// Read shape (from API responses)
export interface User {
  id: number;
  username: string;
  email: string;
  profile: string;
  unit: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

// Create request (plaintext password; backend hashes)
export interface UserCreate {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  profile: string;
  unit: string;
  is_active?: boolean;
}

// Update request (all Optional; PATCH-style)
export interface UserUpdate {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  profile?: string;
  unit?: string;
  is_active?: boolean;
}
```

Mirror the backend's `XxxBase` / `XxxCreate` / `XxxUpdate` SQLModel schemas. Add the
three interfaces in the same place — `types/api.ts` — keyed by entity. Don't fork into
per-entity files.

---

## i18n (`ui/src/i18n/`)

**Flow:** edit JSON → reference via `data-i18n` → runtime patch via `i18nClient.ts`.

### Structure (mirror of `en.json` and `es.json`)
```json
{
  "header":    { "search_placeholder": "Search...", "toggle_theme": "Theme", ... },
  "sidebar":   { "menu_title": "Menu" },
  "modules":   { "ADMIN": "Administration", "TAXO": "Asset Taxonomy", ... },
  "menu_options": { "users": "Users", "teams": "Teams", ... },
  "crud_modal":   { "add": "Add", "edit": "Edit", "delete": "Delete", ... },
  "data_table":   { "search": "Search", "export_csv": "Export CSV", ... },
  "user_modal": {
    "one_title": "User", "many_title": "Users", "add_new": "New User",
    "edit": "Edit User", "delete": "Delete User",
    "empty_message": "No Users found", "delete_confirmation": "Delete this User?",
    "username": "Username", "email": "Email", "profile": "Profile", ...
  }
  // ... one `{entity}_modal` block per entity
}
```

### Usage in markup
```astro
<h1 data-i18n="user_modal.many_title">user_modal.many_title</h1>
<input data-i18n-placeholder="user_modal.username_placeholder" placeholder="..." />
<button title="…" data-i18n-title="crud_modal.edit">…</button>
```

### Runtime patch
`utils/i18nClient.ts` runs on `DOMContentLoaded`, walks all `[data-i18n]`,
`[data-i18n-title]`, `[data-i18n-placeholder]` elements, and replaces text/title/
placeholder with the dictionary lookup. Locale is read from `localStorage["lang"]`
(default `en`).

### Adding new keys (Constitution mandate)
1. Add to `en.json` and `es.json` — **both files, same key, never one without the other**.
2. Reference in Astro markup via `data-i18n="path.to.key"`.
3. Verify in the browser by toggling the language switcher.

The pre-PR checklist enforces this — see root [`../AGENTS.md`](../AGENTS.md).

---

## Adding a new CRUD page (step-by-step)

Use `ui/src/pages/admin/users.astro` as the canonical reference; mirror its structure.

### 1. Define types in `ui/src/types/api.ts`
```ts
export interface MyEntity { code: string; name: string; is_active: boolean; created_at: string; }
export interface MyEntityCreate { code: string; name: string; is_active?: boolean; }
export interface MyEntityUpdate { name?: string; is_active?: boolean; }
```

### 2. Create the service in `ui/src/lib/my_entity.ts`
Copy the canonical pattern from `users.ts` — six functions (`get`, `getSelect`, `getById`,
`create`, `update`, `delete`).

### 3. Create the page `ui/src/pages/{module}/my_entity.astro`
```astro
---
import BaseLayout from '@/layouts/BaseLayout.astro';
import DataTable from '@/components/table/DataTable.astro';
import CrudModal from '@/components/forms/CrudModal.astro';
import { getMyEntities } from '@/lib/my_entity';

const data = await getMyEntities();
const columns = [
  { key: "code", label: "my_entity_modal.code" },
  { key: "name", label: "my_entity_modal.name" },
];
const fields = [
  { key: "code", label: "my_entity_modal.code", required: true, pk: true },
  { key: "name", label: "my_entity_modal.name", required: true },
];
---
<BaseLayout title="my_entity_modal.many_title">
  <DataTable
    tableId="my-entity"
    entityName="MyEntity"
    columns={columns}
    data={data}
    editModalId="my-entity-edit-modal"
    deleteModalId="my-entity-delete-modal"
  />
  <CrudModal mode="create" modalId="my-entity-create-modal" entityName="MyEntity" fields={fields} />
  <CrudModal mode="edit" modalId="my-entity-edit-modal" entityName="MyEntity" fields={fields} showTrigger={false} />
  <CrudModal mode="delete" modalId="my-entity-delete-modal" entityName="MyEntity" fields={fields} showTrigger={false} />
</BaseLayout>

<script>
  // ⚠️ Use a BUNDLED <script> (no `type="module"`) with `@/` imports so Astro
  // bundles + hashes them. NEVER `<script type="module">` importing absolute
  // `/src/lib/...` or `/scripts/...` paths — those 404 in the Vercel build and a
  // single failed import aborts the whole module (kills initCrudPage + submit).
  import { initCrudPage } from '@/lib/crudClient';
  import { createMyEntity, updateMyEntity, deleteMyEntity } from '@/lib/my_entity';

  // Row edit/delete buttons → modal prefill (reads the page's #my-entity-data JSON).
  initCrudPage({
    dataId: "my-entity-data",
    editModalId: "my-entity-edit-modal",
    deleteModalId: "my-entity-delete-modal",
  });

  document.addEventListener("crud-submit", async (e) => {
    const { mode, data } = (e as CustomEvent).detail;
    if (mode === "create") await createMyEntity(data);
    else if (mode === "edit") await updateMyEntity(data.code, data);
    else if (mode === "delete") await deleteMyEntity(data.code);
    window.location.reload();
  });
</script>
```

### 4. Add i18n keys to `en.json` AND `es.json`
```json
"my_entity_modal": {
  "one_title": "My Entity", "many_title": "My Entities",
  "add_new": "New", "edit": "Edit", "delete": "Delete",
  "code": "Code", "name": "Name",
  "empty_message": "No entries found",
  "delete_confirmation": "Delete this entry?"
}
```
Plus add the menu label in `menu_options` if it's a sidebar option.

### 5. Verify
- Page loads at `/{module}/my_entity`
- Create / edit / delete round-trip to the API
- Language switcher swaps every visible label

---

## Authentication state

**No middleware** — pages don't gate themselves yet. The pattern is:
- `BaseLayout.astro` assumes auth and reads `getCurrentUser()` for header display.
- `lib/api.ts` injects the JWT into every request.
- A 401 response → the page should redirect to `/login` (handled in `api.ts` error path).

`localStorage` keys:
| Key | Value |
|-----|-------|
| `auth_token` | JWT |
| `auth_user` | UserRead (JSON-serialized) |
| `lang` | `en` or `es` |
| `theme` | `light` or `dark` |
| `sidebar-collapsed` | `true` / `false` |

**Roadmap:** add `src/middleware.ts` to redirect unauthenticated users from gated routes.

---

## Configuration & environment

| Variable | Purpose | Default |
|----------|---------|---------|
| `PUBLIC_API_BASE_URL` | API origin (client-side fetch) | `http://localhost:8000` |
| `API_BASE_URL` | API origin (server-side build) | falls back to `PUBLIC_API_BASE_URL` |
| `SITE_URL` | Public Astro site URL | `http://localhost:4321` |

`PUBLIC_*` prefix is **required** for Astro to expose the var in the client bundle.

---

## Deployment (Vercel)

**`ui/vercel.json`:**
```json
{
  "framework": "astro",
  "buildCommand": "bun run build",
  "installCommand": "bun install",
  "outputDirectory": "dist",
  "devCommand": "bun run dev"
}
```

- Builds to `dist/` (static); Vercel serves over its CDN.
- Set `PUBLIC_API_BASE_URL` in Vercel project env vars before deploy.
- **Known gotcha:** static pages calling `localhost:8000` at build time fail on Vercel
  (`ECONNREFUSED`). The `api.ts` wrapper handles this by returning `[]` on fetch errors
  during build — list pages will hydrate client-side post-login. See
  [`../memory/memory.md`](../memory/memory.md) "Known issues" for the full ticket.

---

## Debugging

```bash
# Tail UI logs
make logs-ui

# Shell into the container
make exec-ui

# Local dev (outside Docker)
cd ui && bun install && bun run dev   # http://localhost:4321

# Type check (no autofix yet)
cd ui && npx tsc --noEmit

# Production build (mimics Vercel)
cd ui && bun run build && bun run preview
```

**Common errors:**
- **CORS error in browser** → API's `CORS_ORIGINS` doesn't include the UI origin.
- **401 on `/api/auth/me`** → token expired (60-minute lifetime). Logout + re-login.
- **`@/...` import not resolving** → check `astro.config.mjs` alias and `tsconfig.json`
  paths section.
- **i18n placeholder text shows instead of translation** → `ClientTranslations.astro`
  not rendered in the layout, or the key path is wrong.
- **DataTable empty / search broken** → simple-datatables CDN script didn't load
  (check Network tab). `BaseLayout` includes it.
- **Vercel build `ECONNREFUSED`** → see "Known gotcha" above; verify `api.ts` empty-list
  fallback is intact.

---

## Linting & testing

**Current state:** no ESLint, no Prettier, no test runner. TypeScript strict mode
catches static errors via `npx tsc --noEmit`.

**Target state (P1 follow-up):** add ESLint (Astro + TS plugin) + Prettier; integrate
into `make lint` and `make fmt`. UI testing via Playwright (after Constitution III is
formally extended to UI changes — currently UI is manual-verification per quickstart).

**Manual verification** is the current contract for UI changes: every spec's
`quickstart.md` lists the click-through to validate the feature.

---

## Rules that bite here (recap from AGENTS.md)

- **Three types per entity** — `Entity`, `EntityCreate`, `EntityUpdate` in
  `types/api.ts`. Don't fork into per-entity files.
- **One service per entity** — `lib/{entity}.ts` around `lib/api.ts`. Six functions
  matching the canonical CRUD shape.
- **Reuse components** — `DataTable`, `CrudModal`, `Toast`. Don't invent alternatives.
- **i18n in both files** — every visible string in both `en.json` and `es.json`,
  same key path.
- **Layouts** — `BaseLayout` for sidebar pages, `Layout` for full-screen / unauthenticated
  (login, signup, full dashboard).
- **`@` alias** — use `@/lib/api`, never relative `../../lib/api`.

---

## Resources

- [Astro Docs](https://docs.astro.build/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Flowbite components](https://flowbite.com/docs/components/)
- [simple-datatables](https://fiduswriter.github.io/simple-datatables/)
- Repo-wide: [`../AGENTS.md`](../AGENTS.md), [`../api/CLAUDE.md`](../api/CLAUDE.md),
  [`../memory/memory.md`](../memory/memory.md)
