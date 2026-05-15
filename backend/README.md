# RAG Factory — Backend

FastAPI backend for the RAG Factory multi-tenant RAG platform.

## Quick Start

```bash
# From repo root
cd backend

# Install dependencies (creates .venv automatically)
uv sync

# Copy environment template and fill in real values
copy .env.example .env      # Windows
# cp .env.example .env      # Linux / macOS

# Run the dev server (auto-reload)
uv run uvicorn app.main:app --reload --port 8000

# Run tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

API docs: <http://localhost:8000/docs> · OpenAPI JSON: <http://localhost:8000/openapi.json>

Health checks:

- <http://localhost:8000/api/health> — process liveness
- <http://localhost:8000/api/health/db> — `SELECT 1` against `DATABASE_URL` (503 if DB unreachable)

### Phase 2 modules

| Module | Role |
|--------|------|
| `app/config.py` | Pydantic `Settings` + `get_settings()` |
| `app/logging.py` | structlog |
| `app/errors.py` | `api_error()` → JSON `{"error":{code,message,...}}` |
| `app/db/supabase_client.py` | `supabase` (anon) + `supabase_admin` (service role) |
| `app/dependencies.py` | `get_current_user`, `require_super_admin`, `require_business_admin`, `get_optional_user` |

Tests load [`.env.test`](.env.test) first (see `tests/conftest.py`).

### Phase 3–5 modules

| Module | Role |
|--------|------|
| `app/api/auth.py` | `POST /api/auth/{signup,login,logout}`, `GET /api/auth/me` |
| `app/api/super_admin.py` | Super-admin platform ops: list/create/update/deactivate businesses, stats, **invite Business Admin by email**, list/remove admins |
| `app/api/business_admin.py` | Business-admin tenant ops: `GET /api/business/{id}`, `PUT /api/business/{id}` (name/description/industry/settings — deep-merged) |
| `app/services/users.py` | `create_or_get_admin_user(email, password?, full_name?)` — provisions or finds a Supabase auth user via the admin API (`email_confirm=true`); returns one-time credentials on first create |
| `app/models/business.py` | `BusinessCreate` (with optional `admin_email/password/full_name`), `BusinessAdminInvite`, `BusinessAdminSummary`, `AdminCredentials`, `BusinessCreateResponse` |
| `app/core/*` | RAG engine: `llm_router`, `text_cleaner`, `pdf_parser`, `scraper`, `chunker`, `ingestor`, `searcher`, `rag_brain` (Azure OpenAI + pgvector + hybrid search + streaming) |

### Per-business-admin ownership model (Phase 4)

- **Super Admin** creates a business and optionally provides `admin_email` / `admin_password` / `admin_full_name`. The backend then:
  1. Calls `supabase_admin.auth.admin.create_user({... email_confirm: true})` (or looks up the existing user if the email already has an account).
  2. Inserts the `businesses` row with `owner_id = <admin user's id>` (NOT the super admin).
  3. Inserts a single `business_members` row with role `admin` for the assigned user.
  4. Returns `BusinessCreateResponse` with a one-time `admin` payload (email + password + `was_created` flag).
- **Invite-admin-by-email endpoints** allow the same flow on existing businesses:
  - `GET    /api/super-admin/businesses/{id}/admins` — list admins with `email`, `full_name`, `role`, `created_at`.
  - `POST   /api/super-admin/businesses/{id}/admins` — body `{ email, password?, full_name?, role? }` → returns `AdminCredentials`.
  - `DELETE /api/super-admin/businesses/{id}/members/{user_id}` — remove admin.
- **Business Admin** endpoints (`/api/business/{id}`) are gated by `require_business_admin` (super-admin bypass + `business_members` membership check). `is_active` is intentionally ignored here — only the super admin can soft-deactivate a business.
- Startup validation in `app/db/supabase_client.py` verifies that `SUPABASE_SERVICE_ROLE_KEY` is a real service-role JWT and that its `ref` matches the `SUPABASE_URL` project, refusing to boot on misconfiguration.

---

## Database migrations (Supabase / Phase 1)

Versioned SQL lives in [../supabase/migrations/](../supabase/migrations/). Apply them to your **hosted** Supabase project using **one** of:

1. **Python runner (recommended on Windows)** — resolves IPv6-only `db.*.supabase.co` hostnames by setting `hostaddr` for libpq:

   ```bash
   uv sync
   uv run python scripts/apply_migrations.py
   ```

   Requires `DATABASE_URL` in `.env`. If **direct** `db.<ref>.supabase.co:5432` times out, use the **Transaction pooler** from the dashboard (**Connect** → **Transaction pooler**): host like `aws-0-<region>.pooler.supabase.com`, port **6543**, user **`postgres.<project-ref>`** (not `postgres`), password = database password, `?sslmode=require`. Example:

   `postgresql://postgres.<ref>:PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require`

   (URL-encode special characters in the password.)

2. **Supabase CLI** — from repo root, after `supabase login` and `supabase link --project-ref <ref>`:

   ```bash
   npx supabase db push
   ```

3. **Dashboard** — **SQL** → **New query** → paste each file in `supabase/migrations/` in timestamp order → **Run**.

After migrations, create a user in **Authentication**, then grant super admin:

```sql
UPDATE public.user_profiles SET is_super_admin = TRUE WHERE email = 'you@example.com';
```

Optional live smoke test (requires reachable DB):

```bash
set RUN_LIVE_DB=1
uv run pytest tests/test_db_integration.py -m integration
```
