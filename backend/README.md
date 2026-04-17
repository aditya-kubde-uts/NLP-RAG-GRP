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

API docs: <http://localhost:8000/docs>
Health check: <http://localhost:8000/api/health>

See [../PLAN.md](../PLAN.md) and [../STEPS.md](../STEPS.md) for the full project plan.

---

## Database migrations (Supabase / Phase 1)

Versioned SQL lives in [../supabase/migrations/](../supabase/migrations/). Apply them to your **hosted** Supabase project using **one** of:

1. **Python runner (recommended on Windows)** — resolves IPv6-only `db.*.supabase.co` hostnames by setting `hostaddr` for libpq:

   ```bash
   uv sync
   uv run python scripts/apply_migrations.py
   ```

   Requires `DATABASE_URL` in `.env` (direct connection URI). If you get **connection timeout**, your network may block outbound **5432** — use the Supabase **SQL Editor** (option 3) or a **Session pooler** URI (often IPv4) from the dashboard.

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
