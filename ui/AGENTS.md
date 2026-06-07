# AGENTS.md — UI

**Read the root [`AGENTS.md`](../AGENTS.md) first** for the full conventions and the
binding Constitution rules. This file covers what is specific to the frontend.

## Stack

Astro 4 + Tailwind CSS + Flowbite + `simple-datatables`, run with **Bun**. Port 4321.
The UI consumes the API contracts in `ui/src/types/api.ts`.

## Structure

```
ui/src/
  types/api.ts        # TypeScript API contracts
  lib/{entity}.ts     # CRUD service wrappers around lib/api.ts
  pages/{module}/     # Astro pages (admin/, collab/, ...)
  components/         # shared: DataTable, CrudModal, Toast, ...
  i18n/{en,es}.json   # translations
```

## Commands

```bash
make logs-ui     # tail UI logs
make exec-ui     # bash into the UI container
bun install      # install deps (inside ui/)
bun run dev      # astro dev --host 0.0.0.0
bun run build    # production build
```

App: http://localhost:4321.

## Adding a CRUD entity (the established pattern)

1. Add `Entity`, `EntityCreate`, `EntityUpdate` interfaces to `src/types/api.ts`.
2. Add `src/lib/{entity}.ts` with CRUD wrappers (mirror an existing one, e.g.
   `lib/projects.ts`).
3. Add `src/pages/{module}/{entity}.astro`, mirroring a close existing page (e.g.
   `admin/options.astro`); reuse `DataTable`, `CrudModal`, `Toast`.
4. Add i18n keys to **both** `src/i18n/en.json` and `src/i18n/es.json`.

## Rules that bite here

- Keep types in sync with backend models; don't rely on removed/renamed API keys.
- Every user-facing string is translated in both `en.json` and `es.json`.
- UI-only copy/layout changes may be verified manually; anything touching API contracts
  follows the backend testing rules in [`AGENTS.md`](../AGENTS.md).
