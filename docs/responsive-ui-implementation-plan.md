# Responsive UI Refresh — Implementation Plan

**Branch:** `feat/responsive-ui-refresh` · **Scope:** refine the current look + full mobile
responsiveness (no rebrand). Commits follow **Conventional Commits**.

**Design references**
- Private Figma file (your Drafts): `https://www.figma.com/design/3f8xvADR47P17b25QTnvau`
  — frames: Desktop app shell + Asset table, Mobile cards, Mobile drawer. *(CrudModal +
  Dashboard frames pending Figma free-plan quota reset.)*
- Local HTML preview (not deployed): [`design/responsive-preview.html`](../design/responsive-preview.html)
  — covers **all** surfaces incl. CrudModal + Dashboard.

The HTML preview is the source of truth for the visual target; this doc maps it onto the
existing Astro/Tailwind code.

---

## Design language (refined, current identity kept)

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `indigo-600` (#4F46E5), soft `indigo-50`, ink `indigo-700` | buttons, active nav, accents |
| Neutrals | `slate-50/100/200/500/900/950` | bg, borders, text, dark mode |
| Success | `green-50` / `green-700` | "En uso" status chips |
| Radius | `rounded-lg` (controls), `rounded-2xl` (cards/modals) | |
| Type | Inter 400/500/600/700 | |
| Touch target | ≥ 44px on mobile | hamburger, pagination, row actions |
| Breakpoints | Tailwind default — `sm 640` (card view), `lg 1024` (sidebar/drawer) | no config change |

---

## Workstream A — Mobile navigation drawer

Files: `ui/src/components/core/sidebar/SideBar.astro`, `ui/src/layouts/BaseLayout.astro`,
`ui/src/styles/globals.css`.

1. `<aside>` becomes an off-canvas flex column by default, static at `lg` (see Figma "Drawer
   open" / preview §2): `hidden … lg:static lg:flex` →
   `flex w-[290px] max-w-[85vw] -translate-x-full … transition-transform … lg:static lg:translate-x-0 lg:transition-none`.
2. Add `data-sidebar-backdrop` div in `BaseLayout` (sibling of `<SideBar/>`):
   `fixed inset-0 z-[9998] hidden bg-black/40 lg:hidden`.
3. `globals.css` `@media (max-width:1023px)`: `.sidebar-open .sidebar{transform:translateX(0)}`,
   `.sidebar-collapsed .sidebar{width:290px}` (neutralize desktop 90px on phones),
   `.sidebar-open [data-sidebar-backdrop]{display:block}`, `body.sidebar-open{overflow:hidden}`.
4. Rewrite the `BaseLayout` toggle IIFE: hamburger → desktop toggles+persists
   `sidebar-collapsed`; mobile toggles ephemeral `sidebar-open`. Close on backdrop click,
   nav-link tap (delegate on `<aside>`, match `a[href]`), `Escape`, and `matchMedia` →
   desktop. Do **not** persist `sidebar-open`.

## Workstream B — Responsive DataTable (table → cards)

Files: `ui/src/components/table/DataTable.astro`, `ui/src/styles/globals.css`.
**No changes to `advancedTable.ts`** — the card view is pure CSS so pagination/search/filter
(which toggle `.hidden`/`.hidden-by-filter` on `<tr>`) keep working.

1. Frontmatter: import `t`, `getLocale`; `const locale = getLocale(Astro)`.
2. Each `<td>` gets `data-label={t(locale, col.label)}` (drives the card label via CSS).
3. `globals.css` `@media (max-width:639px)` (see preview §2 card list):
   - visually-hide `thead` with the clip technique — **keep it in the DOM** (`getColumnIndex()`
     reads `thead th[data-column-key]`);
   - `display:block` on `.datatable-dense`, `tbody`, and `tbody tr:not(.hidden)` — the
     `:not(.hidden)` is **critical** so paged/filtered rows stay hidden;
   - card per row (border, `rounded-xl`, `.dark` variant); each `td` a flex row with
     `td::before{content:attr(data-label)}`;
   - `td.actions-cell` → right-aligned action row, no label, ~44px buttons.
4. Toolbar fixes: filter `<select>` `w-100` (**invalid**) → `w-full sm:w-auto sm:min-w-[10rem]`;
   search `w-56` → `w-full sm:w-56`; add `flex-wrap` to toolbar groups; per-page select drop
   `ml-3`, add `w-full sm:w-auto`; pagination prev/next `h-8 w-8` → `h-11 w-11 sm:h-8 sm:w-8`.

## Workstream C — Layout & content padding

File: `ui/src/layouts/BaseLayout.astro`.
- `<main class="flex-1">` + wrapper `mx-auto w-full max-w-screen-2xl p-4 sm:p-6 lg:p-8`.
- Fixes the **no-op** `max-w-(--breakpoint-2xl)` (Tailwind-v4 syntax in a v3 repo) and the
  `md:p-0` that stripped mobile padding.
- Normalize `ui/src/pages/lib/assets.astro` wrapper (and any page repeating
  `max-w-(--breakpoint-2xl)`) to avoid double-padding.

## Workstream D — Header & touch targets

File: `ui/src/components/core/header/Header.astro` (+ `ThemeSwitcher.astro`).
- Hamburger `h-10 w-10 lg:h-11 lg:w-11` → `h-11 w-11`; action group `gap-4` → `gap-2 sm:gap-4`;
  theme/lang/bell/avatar ≥ 44px tap area (preview §1/§2 header).

## Workstream E — CrudModal responsive form

File: `ui/src/components/forms/CrudModal.astro` (see preview §3).
- `<dialog>`: add `max-w-[calc(100vw-2rem)] max-h-[calc(100dvh-2rem)]`.
- `<form>`: `flex max-h-[calc(100dvh-2rem)] w-full flex-col`; field container
  `flex-1 overflow-y-auto` (header/footer pinned, body scrolls).
- Field rows: `flex items-start gap-4` → `flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-4`;
  label `w-32 pt-2` → `sm:w-32 sm:pt-2` (stacks on mobile). Checkbox spacer `hidden sm:block sm:w-32`.

## Workstream F — Dashboard

File: `ui/src/pages/dashboard.astro` (uses `Layout`, see preview §4).
- KPI cards `grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-4`.
- Panels: `grid grid-cols-1 lg:grid-cols-3 gap-4` (chart `lg:col-span-2`, recent list).
- Cards `rounded-2xl border bg-white dark:bg-slate-900 p-4/5`. Ensure full-width stacking < `lg`.

## Workstream G — Shared UI component polish (consistency pass)

Codify the refined tokens so future pages inherit them:
- Promote repeated control styles to `@layer components` in `globals.css`
  (`.btn-primary`, `.btn-ghost`, `.input`, `.select`, `.chip`, `.chip-status`, `.card`) and
  refactor `DataTable`/`CrudModal` to use them — reduces ad-hoc class strings and keeps the
  look uniform. (Reuse-first per Constitution; no new components, just style primitives.)
- Status chips: map list-item codes (e.g. `6-IN_USE`) → semantic colors via a small helper.

---

## Constitution / repo guardrails
- Reuse `DataTable`, `CrudModal`, `Toast` — no parallel components.
- Any new visible string → **both** `en.json` and `es.json` (e.g. mobile "Filtros", "Nuevo Activo").
- UI-only change → manual verification per Constitution III.
- Add one `memory/CHANGELOG.md` rollup entry (date + HH:MM).

## Verification
1. `cd ui && npx tsc --noEmit` · `cd ui && bun run build` (catches invalid Tailwind classes).
2. `make dev` → `:4321`, devtools device toolbar at **320 / 375 / 414 / 768 / 1024 px**.
3. Checks: drawer open/close (backdrop, Esc, nav tap, resize, stale-localStorage = 290px);
   table → cards < 640 with working pagination (page 2 hides page-1 cards) + filters + search;
   modal stacks + scrolls; header targets ≥ 44px; dashboard reflows; `/dashboard` (Layout) intact.

## Suggested commit sequence (Conventional Commits)
1. `docs(ui): add responsive design preview + implementation plan` *(this commit)*
2. `feat(ui): mobile navigation drawer with backdrop + scroll lock`
3. `feat(ui): responsive card-view DataTable + toolbar fixes`
4. `fix(ui): content max-width/padding for mobile (Tailwind v3 class fix)`
5. `feat(ui): responsive CrudModal form + header touch targets`
6. `feat(ui): responsive dashboard grid`
7. `refactor(ui): shared control style primitives in globals.css`
