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

See [../PLAN.md](../PLAN.md) and [../STEPS.md](../STEPS.md) for the full project plan.

### Phase 2 modules

| Module | Role |
|--------|------|
| `app/config.py` | Pydantic `Settings` + `get_settings()` |
| `app/logging.py` | structlog |
| `app/errors.py` | `api_error()` → JSON `{"error":{code,message,...}}` |
| `app/db/supabase_client.py` | `supabase` (anon) + `supabase_admin` (service role) |
| `app/dependencies.py` | `get_current_user`, `require_super_admin`, `require_business_admin`, `get_optional_user` |

Tests load [`.env.test`](.env.test) first (see `tests/conftest.py`).

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
