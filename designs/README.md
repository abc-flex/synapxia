# Design mockups → Figma

Static HTML mockups of the SynapxIA asset modals (responsive UI refresh). They render
from the same Tailwind component markup used in the app, so a Figma import matches
production closely.

## Files

| File | What it shows |
|------|---------------|
| `create-edit-modal.html` | Asset **create** + **edit** modals (desktop 680px) and the **mobile 375px** variant, side by side |
| `asset-detail-tabs.html` | Asset detail/edit modal with the three tabs: **Caracterización**, **Activos relacionados**, **Permisos** |

> Tailwind is pulled from the Play CDN (`cdn.tailwindcss.com`), so opening the files
> needs an internet connection. They are self-contained otherwise — no build step.

## Preview locally

Just open either file in a browser (double-click, or `open designs/create-edit-modal.html`).
In `asset-detail-tabs.html` the tabs are clickable to switch panels.

## Import into Figma

There is **no native "open HTML" in Figma** — use one of these.

### Option A — html.to.design plugin (recommended, gives editable frames)

1. In Figma: **Menu → Plugins → Manage plugins…**, search **"html.to.design"**, install it.
2. Run it: **Plugins → html.to.design**.
3. Choose the **Code / HTML** (or **Paste code**) tab.
4. Open one of the `.html` files in a text editor, copy **all** of it, paste into the plugin, and **Import**.
   - It also accepts a public **URL** — if you push this branch and enable GitHub Pages
     (or use any static host), paste the file's URL instead.
5. The plugin generates a frame tree with real layers (text, inputs, buttons) you can edit.
6. Repeat for the second file. Rename the top frames so they read clearly, e.g.
   `Asset / Create (desktop)`, `Asset / Edit (mobile 375)`, `Asset / Detail — tabs`.

> Free tier allows a limited number of imports per day — two files fits comfortably.

### Option B — paste as SVG (no plugin, but flattened)

Use only if you can't install a plugin. Render the page in a browser, capture the node as
SVG (e.g. browser devtools or an "export to SVG" extension), copy the SVG markup, then in
Figma press **Cmd/Ctrl+V** on the canvas — Figma converts pasted SVG into vector layers.
Text stays editable but layout auto-layout is lost (it's flat vectors).

### Option C — screenshot (fastest, not editable)

Open the file, screenshot each card (`Cmd+Shift+4` / `Win+Shift+S`), and drag the PNG
into Figma as a reference image.

## Design tokens used

- **Primary:** indigo-600 `#4F46E5` (buttons, active tab, focus ring indigo-200 `#C7D2FE`)
- **Surfaces:** white cards on gray-100 `#F3F4F6`; borders gray-200 `#E5E7EB`
- **Text:** gray-900 `#111827` headings · gray-700 `#374151` labels · gray-500 `#6B7280` hints
- **Status badges:** emerald-50/700 (MANAGE), sky-50/700 (PUBLIC), indigo-50/700 (VIEW / counts)
- **Radius:** `rounded-lg` (8px) inputs · `rounded-2xl` (16px) modal · `rounded-full` badges
- **Modal widths:** 680px (create/edit), 900px max (detail), 375px (mobile)
