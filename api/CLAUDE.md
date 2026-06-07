# CLAUDE.md — API

Companion to [`AGENTS.md`](AGENTS.md) (rules) and the root [`../AGENTS.md`](../AGENTS.md)
(Constitution + repo-wide conventions). This file is the **actionable map** of the API
service: every module, every route surface, every code pattern an AI agent needs to extend
or debug the backend.

> **Rule of thumb:** rules live in [`AGENTS.md`](AGENTS.md). Concrete code paths,
> module inventories, and patterns live here.

---

## Stack

| Item | Value |
|------|-------|
| Language | Python ≥3.12 |
| Framework | FastAPI (Starlette/ASGI) |
| ORM | SQLModel (SQLAlchemy 2.x + Pydantic v2) |
| DB driver | psycopg2-binary |
| Auth | Custom JWT (HS256) + passlib/bcrypt — `fastapi-users` installed but not used directly |
| Package manager | `uv` (locks via `uv.lock`, pinned mirror in `requirements.txt`) |
| Container port | 8000 (mapped from container 80) |
| ASGI server | `uvicorn` (dev), `Mangum` wrapper (Vercel serverless) |
| OpenAPI | `/docs` (Swagger UI), `/redoc` |

Entry point: `app/main.py`. Vercel handler: `index.py` (Mangum adapter).

---

## Directory map (`api/app/`)

```
api/
├── app/
│   ├── main.py                  # FastAPI app, CORS, router registration, startup events
│   ├── internal/                # Cross-domain plumbing — reuse, never duplicate
│   │   └── dependencies.py      # get_db_session, engine, DATABASE_URL config
│   ├── auth/                    # JWT + password hashing + /me + register/login
│   │   ├── routes.py            # /api/auth/login, /register, /me, /change-password
│   │   └── schemas.py           # UserRead, UserCreate, UserUpdate (shared with admin)
│   ├── admin/                   # Governance: users, profiles, units, modules, options, privileges, lists
│   │   ├── internal/
│   │   │   └── models.py        # SQLModel tables + Create/Update schemas
│   │   └── routes/
│   │       ├── health.py        # GET /health (DB ping)
│   │       ├── users.py         # /api/users  (+ /select, /profile/{code})
│   │       ├── profiles.py      # /api/profiles
│   │       ├── modules.py       # /api/modules
│   │       ├── options.py       # /api/options (composite key: module+code)
│   │       ├── privileges.py    # /api/privileges (composite key: profile+module+option)
│   │       ├── business_units.py
│   │       ├── lists.py
│   │       ├── list_items.py
│   │       └── item_translations.py
│   ├── taxo/                    # Asset taxonomy: categories (hierarchical), features
│   │   ├── internal/models.py
│   │   └── routes/
│   │       ├── categories.py
│   │       └── features.py
│   ├── collab/                  # Teams, roles, assignments, projects, dimensions, metrics
│   │   ├── internal/models.py
│   │   └── routes/
│   │       ├── teams.py
│   │       ├── roles.py
│   │       ├── assignments.py   # temporal: valid_from/valid_to
│   │       ├── projects.py
│   │       ├── dimensions.py
│   │       └── metrics.py
│   ├── lib/                     # Asset library: assets, characterizations, favorites, actions, relations
│   │   ├── internal/models.py
│   │   └── routes/
│   │       ├── assets.py        # JSON-typed `tags` and `details` columns
│   │       ├── characterizations.py
│   │       ├── favorites.py
│   │       ├── actions.py
│   │       └── asset_relations.py
│   ├── genai/                   # ⚠️ STUB — domain placeholder, no implementation
│   ├── inits/                   # ⚠️ STUB
│   ├── insights/                # ⚠️ STUB
│   └── workflows/               # ⚠️ STUB
├── pyproject.toml               # uv-managed deps; no [tool.X] lint sections yet
├── requirements.txt             # Pip mirror for Vercel build
├── index.py                     # `handler = Mangum(app, lifespan="off")` for Vercel
├── vercel.json                  # Vercel build + routes config
├── hash_password.py             # One-off bcrypt utility (CLI)
└── AUTH.md                      # Auth deep-dive (referenced by AGENTS.md)
```

**Domain pattern:** every domain has `routes/` (FastAPI routers) and `internal/` (data
access + models). Never put cross-domain plumbing inside a domain — that belongs in
`app/internal/`.

---

## Routes inventory

All routes are prefixed `/api/`. Health check at `/health`. OpenAPI at `/docs`.

### Auth (`/api/auth`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/login` | OAuth2PasswordRequestForm → JWT + user info |
| POST | `/api/auth/register` | Create user (validates uniqueness on username + email) |
| GET  | `/api/auth/me` | Current user from `Authorization: Bearer …` |
| POST | `/api/auth/change-password` | Verify old, hash new, update |
| POST | `/api/auth/logout` | Stateless (client clears token) |

### Health
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | psycopg2 ping → `{status: healthy, database: connected}` or 503 |

### Admin — `/api/{users,profiles,modules,options,privileges,business_units,lists,list_items,item_translations}`
Each resource implements the **canonical CRUD pattern**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/{resource}/` | List active rows (`skip`, `limit` bounded) |
| GET | `/api/{resource}/select` | Lightweight `{value, label}` for dropdowns |
| GET | `/api/{resource}/{key}` | Single row by key (or composite key path) |
| POST | `/api/{resource}/` | Create — 409 on unique conflict |
| PUT | `/api/{resource}/{key}` | Partial update via `*Update` schema (all Optional) |
| DELETE | `/api/{resource}/{key}` | Logical delete (`is_active=False`, row retained) |

**Key shapes per resource:**
- `users` → `/{id}` (integer); also `/profile/{profile_code}` filter
- `profiles`, `modules`, `lists`, `business_units`, `categories`, `features`, `assets`,
  `teams`, `roles`, `projects`, `dimensions` → `/{code}` (string)
- `options` → `/{module_code}/{code}` (composite)
- `privileges` → `/{profile_code}/{module_code}/{option_code}` (triple composite); also
  `/profile/{profile_code}` filter
- `list_items` → `/{list_code}/{value}` (composite); also `/list/{list_code}` and
  `/list/{list_code}/with-translations`
- `item_translations` → `/list/{list_code}/value/{value}/{lang}` (triple); also
  `/list/{list_code}` and `/list/{list_code}/value/{value}` filters
- `assignments`, `metrics`, `actions` → `/{id}` (integer)
- `characterizations` → `/{code}/{feature_code}` (composite)
- `favorites` → `/{user_id}/{asset_code}` (composite)
- `asset_relations` → `/{source_code}/{target_code}` (composite)

### Taxonomy — `/api/{categories,features}`
- `categories` supports `parent` (self-FK; hierarchical tree, see admin seed for the
  14-node `AI_ASSETS → CLASSIC_AI/GEN_AI → …` taxonomy).
- `features` supports a `type` field tied to the `FEAT_TYPE` list.

### Collab — `/api/{teams,roles,assignments,projects,dimensions,metrics}`
- `assignments` carries `valid_from` / `valid_to` (temporal validity for user×team×role).
- `metrics` records `value` against a `dimension` for an `assignment` at a `measured_at`
  timestamp (master-detail from `dimensions`).
- `teams` has optional `lead` (FK → users) and `chat_channel_url` / `kanban_board_url`.

### Lib — `/api/{assets,characterizations,favorites,actions,asset_relations}`
- `assets` have JSON-typed `tags` and `details` columns — pass arbitrary structured
  metadata. Status comes from the `ASSET_STATUS` list.
- `characterizations` are (asset × feature → value) triples — flexible per-asset
  metadata, gated by the taxonomy.

---

## Key code surfaces

### `app/main.py` — application bootstrap
- Instantiates `FastAPI(title="SynapxIA API", version="1.0.0", openapi_tags=[…])`.
- Adds `CORSMiddleware` reading `CORS_ORIGINS` env (comma-separated; defaults `*`).
- Registers routers from **auth → admin → taxo → lib → collab** in order. `genai`,
  `inits`, `insights`, `workflows` are TODO — when you implement one, import its router
  and `app.include_router(...)` here.
- Defines startup/shutdown event handlers (currently log-only — no DB pre-warm).
- `GET /` returns an index of available endpoint paths (cheap discovery).

### `app/internal/dependencies.py` — DB plumbing (single source of truth)
- **`get_db_session()`** — FastAPI `Depends` yielding a `Session`. Use this everywhere:
  ```python
  def list_users(db: Session = Depends(get_db_session)): ...
  ```
- **`engine`** — SQLAlchemy engine singleton; `pool_pre_ping=True` so dead connections
  in serverless Lambdas get recycled.
- **`DATABASE_URL`** resolution order:
  1. `POSTGRES_URL` env (Vercel/Neon auto-injects) — preferred in prod.
  2. Built from `DB_HOST`/`DB_SCHEMA`/`DB_USER`/`DB_PASSWORD`/`DB_PORT` — Docker Compose.
- `APP_ENV=development` enables SQL echo (verbose); production stays quiet.
- Never open raw `psycopg2.connect()` inside a route — use this module.

### `app/auth/routes.py` — JWT + password hashing
- `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")` — `hash_password()`
  and `verify_password()` helpers.
- JWT: HS256, `SECRET_KEY` env, 60-minute expiry (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` injects the bearer header.
- **Auth dependencies** to inject in protected routes:
  - `get_current_user(token: str = Depends(oauth2_scheme))` → User (401 if invalid).
  - `get_current_active_user(...)` → enforces `is_active=True` (403 otherwise).
  - `get_current_superuser(...)` → enforces `is_superuser=True` (403 otherwise).
- See [`AUTH.md`](AUTH.md) for the full token lifecycle.

### Model & schema pattern
For every entity, `app/{domain}/internal/models.py` declares three or four classes:

```python
# 1. Shared base (fields + constraints; no table)
class UserBase(SQLModel):
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=200, unique=True)
    profile: str = Field(foreign_key="profiles.code")
    is_active: bool = Field(default=True)

# 2. Table (DB row)
class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

# 3. Create schema (request body for POST)
class UserCreate(UserBase):
    password: str  # plaintext → hashed in route

# 4. Update schema (PATCH-style; everything Optional)
class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    profile: Optional[str] = None
    is_active: Optional[bool] = None
```

**Conventions to keep when adding entities:**
- Primary keys: `code: str` for human-readable codes (admin / taxo / collab); `id: int`
  for surrogate keys (users / assignments / metrics / actions).
- Composite keys: use `sa_column=Column('name', String, ForeignKey(...), primary_key=True)`.
  See `ListItem`, `Privilege`, `Option`, `Characterization` for examples.
- Timestamps: `created_at` defaults via `default_factory=datetime.utcnow`; `updated_at`
  set explicitly in the PUT handler before commit.
- Logical delete: `is_active: bool = Field(default=True)`. DELETE handlers must update,
  not `db.delete(...)`.
- JSON columns: `Field(sa_column=Column("column_name", JSON))`. See `Asset.tags`,
  `Asset.details`.
- Foreign keys reference the **table's `code` column** when possible (matches the seed
  data convention) — see `users.profile → profiles.code`.

### Route handler shape (canonical CRUD)
Mirror `app/admin/routes/users.py` when adding a new resource — it's the most complete
example (uniqueness checks, FK validation, password hashing on create):

```python
router = APIRouter(prefix="/api/users", tags=["admin: users"])

@router.get("/", response_model=List[User])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)):
    return db.exec(select(User).where(User.is_active == True).offset(skip).limit(limit)).all()

@router.post("/", response_model=User, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db_session)):
    # 1. FK existence checks
    if not db.get(Profile, data.profile):
        raise HTTPException(404, "Profile not found")
    # 2. Uniqueness pre-check (race-safe via IntegrityError below)
    if db.exec(select(User).where(User.username == data.username)).first():
        raise HTTPException(409, "Username already exists")
    # 3. Hash + persist
    payload = data.model_dump(exclude={"password"})
    user = User(**payload, hashed_password=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "User already exists")
    db.refresh(user)
    return user
```

**Status code policy (Constitution Principle II):**
- 200 — success (default)
- 201 — created
- 204 — deleted / no content
- 400 — request validation
- 401 — auth required (missing/invalid token) — emitted by auth deps
- 403 — forbidden (inactive user, missing superuser)
- 404 — resource not found
- 409 — unique conflict / illegal state transition

### Health endpoint
`app/admin/routes/health.py` opens a `psycopg2.connect(DATABASE_URL)` and runs
`SELECT 1`. Returns `{status: "healthy", database: "connected"}` or HTTP 503 with the
exception detail. Used by `make test`, `docker-compose healthcheck` is on the DB side.

---

## Configuration & environment

| Variable | Purpose | Default | Required in prod |
|----------|---------|---------|------------------|
| `POSTGRES_URL` | Full connection string (Vercel/Neon convention) | — | **Yes** (prod) |
| `DB_HOST` | DB hostname | `db` | No (Docker Compose) |
| `DB_SCHEMA` / `DB_USER` / `DB_PASSWORD` | DB credentials | `synapxia` | No (Docker Compose) |
| `DB_PORT` | DB port | `5432` | No |
| `SECRET_KEY` | JWT signing secret | dev-default + warning | **Yes** |
| `APP_ENV` | `development` or `production` | `development` | Sets SQL echo |
| `CORS_ORIGINS` | Comma-separated origins | `*` | **Yes** (prod) |

**No `.env` parsing inside the app** — environment is injected by Compose (`.env` file)
or Vercel project settings. Don't introduce `pydantic-settings` without aligning with
the Constitution (principle V — operability).

---

## Deployment (Vercel + Neon)

- **`index.py`** wraps the ASGI app with Mangum (`handler = Mangum(app, lifespan="off")`).
  `lifespan="off"` is required — serverless functions can't honor FastAPI startup/shutdown
  hooks.
- **`vercel.json`** declares a `@vercel/python` build of `index.py` with
  `maxLambdaSize: 15mb` and routes everything to it.
- **`requirements.txt`** is the pip-installable mirror of `pyproject.toml` deps — Vercel's
  Python builder uses pip, not `uv`. Keep both in sync when adding deps.
- DB connection uses `POSTGRES_URL` (Neon-injected); no other env vars needed in prod.
- Full guide: [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).

---

## Adding a new resource (step-by-step)

1. **Define models** in `app/{domain}/internal/models.py`:
   - `XxxBase` (shared fields), `Xxx` (table=True), `XxxCreate`, `XxxUpdate`.
2. **Create router** in `app/{domain}/routes/xxx.py` following the canonical CRUD pattern:
   - `list_xxx`, `get_xxx`, `create_xxx`, `update_xxx`, `delete_xxx`.
   - Add `/select` if the entity appears in a UI dropdown.
   - Always: skip/limit pagination, `is_active=True` filtering, logical delete.
3. **Register router** in `app/{domain}/routes/__init__.py` and `app/main.py`.
4. **Add DDL** in `db/sql/{NN}-{module}-ddl.sql` (additive only — Constitution V).
5. **Add seed data** in `db/sql/{NN}-{module}-insert.sql` if needed.
6. **Add tests** for any contract / auth / migration change (Constitution III).
7. **UI side:** add `ui/src/types/api.ts` types → `ui/src/lib/{entity}.ts` service →
   `ui/src/pages/{module}/{entity}.astro` page → i18n keys in en.json + es.json.

---

## Adding a new domain (rare)

The four stub domains (`genai`, `inits`, `insights`, `workflows`) ship empty so the
import surface stays stable. When promoting a stub to a real module:

1. Add SQL schema in `db/sql/{NN}-{module}-ddl.sql` + seeds in `{NN+1}-…-insert.sql`.
2. Replace `app/{domain}/internal/models.py` stub with real SQLModel tables.
3. Add `routes/{entity}.py` files following the canonical CRUD pattern.
4. Register routers in `app/{domain}/routes/__init__.py` and import-and-include in
   `app/main.py`.
5. Add a `specs/{NN}-{domain}-{feature}/` SpecKit folder with `spec.md` + `plan.md`
   (including the **Constitution Check** section). See `.specify/templates/`.
6. Update `memory/memory.md` with the new domain in established patterns.
7. Add CHANGELOG entry with `YYYY-MM-DD HH:MM` timestamp.

---

## Linting & testing

**Current state:** no enforced lint/format/type-check setup. `make lint` runs
`python -m py_compile` (syntax only) and `make format` runs `black` inside the API
container — neither is gated in CI.

**Target state (P1 follow-up from comparison plan):** add `[tool.ruff]`, `[tool.black]`,
`[tool.isort]`, `[tool.mypy]` sections to `pyproject.toml`; wire `make lint` /
`make fmt` / `make fmt-check` to fail on drift; gate in CI.

**Testing:** no `tests/` folder yet. When adding tests, use pytest with `httpx`'s
`AsyncClient` against the FastAPI app; spin up an isolated Postgres via testcontainers
(don't reuse the dev DB). Constitution III requires automated tests for
auth/contract/migration/permission changes.

---

## Debugging

```bash
# Tail logs
make logs-api

# Shell into the container
make exec-api

# Run the API directly (inside the container)
uv run fastapi dev app/main.py     # autoreload
uv run uvicorn app.main:app --host 0.0.0.0 --port 80

# Verify health + admin user from the host
make test

# DB introspection
make shell                         # psql synapxia/synapxia
\dt                                # list tables
\d users                           # describe table
SELECT * FROM users LIMIT 5;
```

**Common errors:**
- `psycopg.OperationalError: could not connect to server` → DB not ready. `make ps` to
  confirm; `docker-compose exec db pg_isready -U synapxia`.
- `401 Unauthorized` from `/api/*` → expired/missing JWT. Re-login in the UI.
- `403 Forbidden` on superuser endpoint → user.is_superuser is false. Check seed user.
- `409 Conflict` on POST → unique constraint (username/email/code already exists).
- `ImportError` after deps changed → rebuild the container (`make rebuild`) and ensure
  both `pyproject.toml` *and* `requirements.txt` were updated.

---

## Rules that bite here (recap from AGENTS.md)

- **Contract stability** — never remove/rename existing endpoints or request/response
  keys; versioned route + UI migration plan for breaking changes.
- **Pagination** — list endpoints take bounded `skip` / `limit`. Never return unbounded
  result sets.
- **Logical delete** — set `is_active=False`; never `db.delete(row)` in domain routes.
- **Status codes** — 409 unique conflict, 400 validation, 403 auth, 404 missing.
- **DB access** — managed sessions from `app/internal`; no raw psycopg2 connections in
  routes (health endpoint is the documented exception).
- **Auth** — JWT Bearer + bcrypt only, never plaintext; preserve `is_active` /
  `is_superuser` semantics.
- **Testing** — auth / contract / migration / permission changes REQUIRE automated tests.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/) — framework docs
- [SQLModel](https://sqlmodel.tiangolo.com/) — ORM (Pydantic v2 + SQLAlchemy 2)
- [Mangum](https://mangum.io/) — ASGI ↔ Lambda adapter (used by Vercel build)
- [Pydantic v2](https://docs.pydantic.dev/latest/) — validation engine under SQLModel
- Repo-wide: [`../AGENTS.md`](../AGENTS.md), [`../README.md`](../README.md),
  [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md), [`../memory/memory.md`](../memory/memory.md)
