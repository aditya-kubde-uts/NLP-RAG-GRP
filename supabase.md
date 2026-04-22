# Supabase Setup Guide for This Project (Beginner Friendly)

This guide explains, step by step, how to:

1. Create a new Supabase project.
2. Find all required keys and connection values.
3. Connect Supabase to this repository.
4. Apply this project's database schema.
5. Verify everything works.

If you are completely new to Supabase, follow the steps in order.

---

## 1) What This Project Needs From Supabase

This project uses Supabase for:

- Auth (users and JWT)
- Postgres database
- pgvector extension for embeddings
- Storage bucket (`uploads`)
- Row Level Security (RLS) policies

All schema definitions are already versioned in SQL migration files under:

- `supabase/migrations/`

---

## 2) Prerequisites

Before starting, make sure you have:

- A Supabase account: https://supabase.com
- Access to this repository on your machine
- Python + `uv` installed (for backend)
- Node.js + `pnpm` installed (for frontend)

Optional but useful:

- Supabase CLI (`npx supabase ...` can be used without global install)

---

## 3) Create a Supabase Project

1. Go to https://supabase.com and sign in.
2. Create or choose an Organization.
3. Click **New project**.
4. Fill project details:
   - **Name**: anything (example: `rag-factory-dev`)
   - **Database password**: create a strong password and save it safely
   - **Region**: choose closest to you
5. Click **Create new project** and wait until setup completes.

Important:

- Do not lose the database password you set here.
- You will need this password for `DATABASE_URL`.

---

## 4) Get Required Supabase Values (Keys + URLs)

Open your Supabase dashboard for the new project.

### A. Get project URL and API keys

Path in dashboard:

- **Project Settings -> API**

Copy these values:

- **Project URL** -> used as:
  - `SUPABASE_URL` (backend)
  - `VITE_SUPABASE_URL` (frontend)
- **anon public key** -> used as:
  - `SUPABASE_ANON_KEY` (backend)
  - `VITE_SUPABASE_ANON_KEY` (frontend)
- **service_role key** -> used as:
  - `SUPABASE_SERVICE_ROLE_KEY` (backend only)

Security rule:

- Never put `SUPABASE_SERVICE_ROLE_KEY` in frontend code or frontend `.env`.

### B. Get database connection string

Path in dashboard:

- **Connect -> Transaction pooler** (recommended)

Copy the connection string in Postgres URI format.

Use this format:

`postgresql://postgres.<project-ref>:<db-password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`

Notes:

- Username should usually be `postgres.<project-ref>` for pooler.
- Port is usually `6543` for transaction pooler.
- If your password has special characters, URL-encode them.

This value becomes:

- `DATABASE_URL` (backend)

---

## 5) Configure Backend Environment

From repository root:

```powershell
cd backend
copy .env.example .env
```

Open `backend/.env` and fill at least these Supabase values:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`

You should also fill Azure OpenAI values in the same file for full app features.

---

## 6) Apply Database Schema (Migrations)

This project already contains migration SQL files in timestamp order under `supabase/migrations/`.

Choose one method.

### Method A (Recommended on Windows): Python migration runner

From `backend/`:

```powershell
uv sync
uv run python scripts/apply_migrations.py
```

Why this is recommended:

- It handles common hostname/network issues (especially IPv6-related cases on Windows).

### Method B: Supabase CLI

From repository root:

```powershell
npx supabase login
npx supabase link --project-ref <your-project-ref>
npx supabase db push
```

### Method C: Supabase Dashboard SQL Editor (manual)

- Open **SQL Editor**.
- Run each file in `supabase/migrations/` in filename order.

---

## 7) Configure Frontend Environment

From repository root:

```powershell
cd frontend
copy .env.example .env
```

Open `frontend/.env` and set:

- `VITE_SUPABASE_URL` = same as backend `SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY` = same as backend `SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL` = `http://localhost:8000` (default local backend)

---

## 8) Run the App Locally

### Start backend

From `backend/`:

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Start frontend

From `frontend/` in a new terminal:

```powershell
pnpm install
pnpm dev
```

Default URLs:

- Backend docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/api/health
- Frontend app: http://localhost:5173

---

## 9) Create First User and Grant Super Admin

After migrations:

1. In Supabase dashboard, go to **Authentication -> Users**.
2. Create a user (email/password).
3. Open **SQL Editor** and run:

```sql
UPDATE public.user_profiles
SET is_super_admin = TRUE
WHERE email = 'you@example.com';
```

Use the same email as the created auth user.

---

## 10) Quick Verification Checklist

Run these checks:

1. Backend health is up:
   - `GET /api/health` returns success.
2. DB health is up:
   - `GET /api/health/db` returns success.
3. In Supabase Table Editor, confirm tables exist:
   - `businesses`
   - `business_members`
   - `knowledge_chunks`
   - `conversations`
   - `chat_messages`
   - `alerts`
   - `response_cache`
   - `user_profiles`
4. Storage bucket `uploads` exists.

---

## 11) Common Errors and Fixes

### Error: Database timeout or cannot connect

- Use transaction pooler URI (port 6543) instead of direct host.
- Re-check `DATABASE_URL` format.

### Error: password authentication failed

- Database password is wrong in `DATABASE_URL`.
- Reset DB password in Supabase project settings and update `.env`.

### Error: Frontend auth/network fails

- `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` might be wrong.
- `VITE_API_BASE_URL` may point to wrong backend URL.

### Error: Backend returns 503 on `/api/health/db`

- Backend can run, but DB credentials/network are wrong.
- Verify `DATABASE_URL` and rerun migrations.

---

## 12) Security Notes (Do Not Skip)

- Keep `backend/.env` and `frontend/.env` out of git.
- Never expose `SUPABASE_SERVICE_ROLE_KEY` to browser/client.
- Rotate keys immediately if accidentally leaked.

---

## 13) Minimal Value Mapping (Cheat Sheet)

- Supabase Project URL -> `SUPABASE_URL`, `VITE_SUPABASE_URL`
- Supabase anon key -> `SUPABASE_ANON_KEY`, `VITE_SUPABASE_ANON_KEY`
- Supabase service_role key -> `SUPABASE_SERVICE_ROLE_KEY` (backend only)
- Supabase Postgres URI (pooler) -> `DATABASE_URL`

---

If you follow this file from top to bottom, you can set up a fresh Supabase project and connect it to this repository without prior Supabase experience.
