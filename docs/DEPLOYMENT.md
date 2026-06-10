# Deploying SynapxIA on Vercel

SynapxIA deploys as **three Vercel resources** from this single monorepo:

| Resource | Type | Root dir | Notes |
|----------|------|----------|-------|
| Database | Neon Postgres (Vercel Storage) | — | serverless Postgres |
| API | Vercel Python serverless | `api/` | FastAPI via Mangum |
| UI | Vercel static (Astro) | `ui/` | built with Bun |

> Env var names are listed in [`../vercel.env.example`](../vercel.env.example).

---

## Step 1 — Create the Neon database (do this first)

1. Vercel dashboard → **Storage** → **Create Database** → **Postgres** (powered by Neon).
2. Name it `synapxia-db`, pick the region closest to your users.
3. Leave it for now — you'll connect it to the projects in steps 2 and 3.

## Step 2 — Create the API project

1. Vercel → **Add New** → **Project** → import `abc-flex/synapxia`.
2. **Root Directory:** `api/`
3. **Framework Preset:** Other.
4. **Build & Output:** leave empty — Vercel installs from `api/requirements.txt` and
   serves `api/index.py` (Mangum-wrapped FastAPI) per `api/vercel.json`.
5. **Storage tab:** connect the `synapxia-db` Neon database → `POSTGRES_URL` and siblings
   are auto-injected. (The app accepts `POSTGRES_URL` as an alias for the canonical
   `DATABASE_URL`, so no rename is required.)
6. **Settings → Environment Variables:** add
   - `SECRET_KEY` — a random 32+ char string
   - `CORS_ORIGINS` — your UI URL (e.g. `https://synapxia-ui.vercel.app`)
   - `APP_ENV` — `production`
7. Deploy. Verify: `https://<api>.vercel.app/api/health` → `200`.

## Step 3 — Run database migrations

From a machine with `psql` and the repo checked out:

```bash
# Copy POSTGRES_URL_NON_POOLING from Vercel → Storage → synapxia-db → .env.local tab
export DATABASE_URL="postgresql://...neon.tech/...?sslmode=require"
bash db/neon-migrate.sh
```

This creates all tables and seeds reference data + the `admin` user (`admin / Admin123!`).

## Step 4 — Create the UI project

1. Vercel → **Add New** → **Project** → import the same repo.
2. **Root Directory:** `ui/`
3. **Framework Preset:** Astro (config in `ui/vercel.json`: `bun install` / `bun run build` / `dist`).
4. **Settings → Environment Variables:** add
   - `PUBLIC_API_BASE_URL` — your API URL (e.g. `https://synapxia-api.vercel.app`)
   - `SITE_URL` — your UI URL (e.g. `https://synapxia-ui.vercel.app`)
5. Deploy.

## Step 5 — Wire CORS and verify end-to-end

1. Confirm the API's `CORS_ORIGINS` matches the deployed UI URL exactly (no trailing slash).
2. Open the UI, log in with `admin / Admin123!`.
3. Confirm pages load data (client-side fetch hits the API).

---

## How it works

- **API:** `api/index.py` exposes `handler = Mangum(app, lifespan="off")`. Vercel's
  `@vercel/python` runtime invokes that handler; `api/vercel.json` routes all paths to it.
- **DB connection:** resolved in `api/app/core/config.py` (`Settings.database_url`),
  precedence `DATABASE_URL` → `POSTGRES_URL` (alias) → composed from `DB_HOST` /
  `DB_USER` / `DB_PASSWORD` / `DB_SCHEMA` / `DB_PORT`. Both `app/internal/dependencies.py`
  (engines) and `migrations/env.py` (Alembic) read the same resolved value.
- **UI:** static Astro build. Pages call the API **client-side** after login; build-time
  fetches fail gracefully (return `[]`) so prerender succeeds without a live API.

## Local development is unchanged

`make dev` still runs all three services via Docker Compose using the `DB_*` env vars.
The Vercel config only adds new files; it does not change local behaviour.
