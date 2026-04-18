# RAG Factory — Plan & Task Tracker

> **Purpose.** Living execution tracker for the RAG Factory project. Use this file day-to-day; keep [STEPS.md](STEPS.md) as the detailed reference guide (SQL, code snippets, explanations).
>
> **How to use.** Tick boxes as you complete work. Do not move to the next phase until its **Definition of Done** is fully green.

---

## Status

**Overall:** `6 / 13` phases complete _(Phases 0–5 done; Phase 7 partially started — business-admin settings page landed alongside Phase 4's per-business-admin ownership work)_

| # | Phase | Status |
|---|---|---|
| 0 | Project Init & Env | [x] |
| 1 | Supabase Schema + RLS + pgvector | [x] |
| 2 | Backend Foundation | [x] |
| 3 | Authentication | [x] |
| 4 | Super Admin Dashboard + per-business admin provisioning | [x] |
| 5 | RAG Engine Core | [x] |
| 6 | Knowledge Base Management | [ ] |
| 7 | Business Admin Dashboard | [~] (settings page live; KB / alerts / analytics pending) |
| 8 | User Chat Portal | [ ] |
| 9 | Integration Testing & E2E | [ ] |
| 10 | Embeddable Widget | [ ] |
| 11 | UI Polish & A11y | [ ] |
| 12 | Documentation | [ ] |

### Legend

| Mark | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done |
| `[!]` | Blocked (add a note on the same line) |

---

## 1. Confirmed Decisions

- **Frontend language:** TypeScript (`.tsx`, strict mode)
- **UI kit:** shadcn/ui (installed via CLI) + Tailwind CSS v4
- **Testing:** automated + manual — pytest, Vitest, Playwright
- **Scope of this file:** companion to [STEPS.md](STEPS.md); STEPS.md remains unchanged
- **Deployment target:** local development only for now
- **Ownership model** (finalised during Phase 4):
  - **Super Admin** — the platform operator. Creates businesses, invites Business Admins, manages platform stats, can soft-deactivate any business. Identified by `user_profiles.is_super_admin = TRUE`.
  - **Business Admin** — assigned per business by the Super Admin with a **dedicated login (email + password)**. Owns a single tenant workspace at `/b/<slug>/admin`; manages business profile + settings (and in later phases KB, alerts, analytics). Identified by a `business_members` row with `role ∈ ('admin','super_admin')`. Cannot see other tenants.
  - **End user** — talks to a business's chatbot at `/b/<slug>`. Anonymous unless the business enables `user_login_required`.
  - Enforcement: backend service-role key writes go through `supabase_admin`; read-time protection is `require_super_admin` / `require_business_admin(business_id)` FastAPI dependencies. RLS on all tenant tables uses a `SECURITY DEFINER` `auth_is_super_admin()` helper to avoid recursion on `user_profiles`.

- **Tenant routing & API conventions** (binding decisions for Phases 6–8, locked during the Phase 4 follow-up audit):
  - **Backend URL prefix for all tenant-scoped admin APIs**: `/api/business/{business_id}/…`. Phase 6's knowledge base, Phase 7's alerts / analytics / chat logs / cache, and any future per-tenant endpoint all hang off this prefix so they can share `require_business_admin(business_id)` without another router. (STEPS.md originally proposed `/api/knowledge/{business_id}/…` — treat that as superseded.)
  - **Business detail endpoint stays unified**: `GET /api/business/{id}` and `PUT /api/business/{id}` (deep-merged settings) cover profile + all settings fields. **Do not** introduce a separate `PUT /api/business/{id}/settings` in Phase 7.
  - **`is_active` ownership**: only the super admin's `PUT /api/super-admin/businesses/{id}` and `DELETE` can change `is_active`. `/api/business/{id}` PUT strips it. Chat portal (Phase 8) is the only consumer that must additionally 404 when `is_active = FALSE`.
  - **Slug→business resolution**: `GET /api/business/by-slug/{slug}` (gated by super-admin OR membership) returns the same `BusinessResponse`. Frontend sub-pages use the shared `useBusinessBySlug(slug)` hook instead of deriving the id from `profile.businesses` — that lookup fails for super admins inspecting a tenant they don't belong to.
  - **Frontend workspace route**: `/b/:slug/admin` will become an outlet layout (`BusinessAdminLayout`) with nested children (`index` → settings, `knowledge`, `chat`, `alerts`, `analytics`). The current single-page dashboard becomes the `index` route's settings section. Phase 6 adds `/b/:slug/admin/knowledge`, Phase 7 adds the other three.
  - **Public chat route** stays at `/b/:slug` (unauth-friendly) and hits public `/api/chat/{slug}/…` endpoints — separate surface from the admin workspace.

---

## 2. Tech Stack (final, post-upgrades)

| Layer | Choice | Notes / swap from STEPS.md |
|---|---|---|
| **Backend runtime** | Python 3.11+, FastAPI, Uvicorn | unchanged |
| **Python package manager** | `uv` | replaces `pip` — 10–100× faster installs + lockfile |
| **Supabase client** | `supabase-py` (anon + service) | unchanged |
| **Postgres / Vectors** | Supabase Postgres + `pgvector` HNSW | unchanged |
| **LLM provider** | Azure OpenAI (embeddings + completions) | unchanged |
| **Background jobs** | FastAPI `BackgroundTasks` | **new** — prevents ingestion from blocking API |
| **Logging** | `structlog` (JSON) | **new** — replaces ad-hoc prints |
| **Auth** | Supabase Auth (JWT) | unchanged |
| **Frontend framework** | React 18 + Vite + TypeScript | **TS** instead of JSX |
| **Node package manager** | `pnpm` | replaces `npm` — faster, disk-efficient |
| **UI components** | shadcn/ui + Tailwind v4 + Radix primitives | **shadcn** added |
| **Forms** | React Hook Form + Zod | **new** — validation + type safety |
| **Data fetching** | TanStack Query v5 | **new** — caching, retries, loading states |
| **Global state** | Zustand | **new** — for auth + current business only |
| **Icons** | `lucide-react` | unchanged |
| **Routing** | `react-router-dom` v6 | unchanged |
| **DB migrations** | Supabase CLI (`supabase/migrations/`) | **new** — files instead of raw SQL pasting |
| **Linters / formatters** | `ruff` (Python), `eslint` + `prettier` (TS) | **new** |
| **Pre-commit** | `pre-commit` framework | **new** |
| **Testing — backend** | `pytest`, `pytest-asyncio`, `httpx` TestClient | **new** |
| **Testing — frontend unit** | `Vitest` + `@testing-library/react` | **new** |
| **Testing — E2E** | `Playwright` | **new** |
| **Error tracking** | Sentry (optional, deferred) | **new, flagged** |

---

## 3. Architecture Overview

### Request flow

```mermaid
flowchart LR
  Browser[Browser SPA]
  API[FastAPI Backend]
  Auth[Supabase Auth]
  PG[("Supabase Postgres<br/>pgvector + RLS")]
  Storage[Supabase Storage]
  Azure[Azure OpenAI<br/>embeddings + chat]

  Browser -- "JWT Bearer" --> API
  Browser -. "auth.signInWithPassword" .-> Auth
  API -- "validate JWT" --> Auth
  API -- "SQL + vector search" --> PG
  API -- "signed URLs / uploads" --> Storage
  API -- "embed + complete" --> Azure
  Browser -. "SSE stream tokens" .-> API
```

### Multi-tenant isolation

```mermaid
flowchart TB
  subgraph tenants [Tenant Isolation]
    B1["business_id = A"]
    B2["business_id = B"]
    B3["business_id = C"]
  end

  subgraph tables [Shared Tables with RLS]
    KC[knowledge_chunks]
    CM[chat_messages]
    AL[alerts]
    RC[response_cache]
  end

  RLS{{"Row-Level Security<br/>filters by business_id<br/>+ business_members role"}}

  B1 --> RLS
  B2 --> RLS
  B3 --> RLS
  RLS --> KC
  RLS --> CM
  RLS --> AL
  RLS --> RC
```

---

## 4. Data Model Cheat-Sheet

Full schema lives in [STEPS.md Phase 1](STEPS.md). Summary:

| Table | Purpose |
|---|---|
| `businesses` | Tenants — one row per business (name, slug, settings JSONB, `is_active`). |
| `business_members` | Maps `user_id` → `business_id` with role (`super_admin` / `admin` / `viewer`). |
| `user_profiles` | Extends `auth.users` with `full_name`, `is_super_admin`. Auto-created by trigger. |
| `knowledge_chunks` | RAG vector store (content, `vector(1536)`, `fts tsvector`, `content_hash`, `business_id`). |
| `conversations` | Chat threads (per business, per user or anonymous session). |
| `chat_messages` | Individual messages (role, content, confidence, sources JSONB, `is_failed`). |
| `alerts` | Per-business broadcast alerts injected into the RAG prompt when active. |
| `response_cache` | Query-hash → cached response, 24-hour TTL, per business. |

Supporting SQL:
- `search_knowledge(business_id, embedding, query_text, match_count, threshold)` — hybrid search function (70% semantic + 30% BM25-style).
- Storage bucket `uploads` — private, 50 MB cap, PDF/TXT/MD.

---

## 5. UI / UX Design System

Single source of truth for visual decisions. All design tokens live in `frontend/src/index.css` as CSS variables.

### 5.1 Color tokens (Tailwind v4 `@theme` directive)

Uses shadcn/ui's HSL convention. Dark theme is default; light theme is an override on `.light`.

```css
@theme {
  --color-background: hsl(240 10% 4%);
  --color-foreground: hsl(210 20% 98%);
  --color-surface:    hsl(240 6% 10%);
  --color-border:     hsl(240 4% 16%);
  --color-muted:      hsl(240 4% 22%);
  --color-muted-fg:   hsl(240 5% 65%);

  --color-primary:    hsl(239 84% 67%);  /* indigo-500 */
  --color-primary-fg: hsl(210 20% 98%);

  --color-accent:     hsl(262 83% 58%);  /* violet */
  --color-destructive:hsl(0   72% 51%);
  --color-success:    hsl(142 71% 45%);
  --color-warning:    hsl(38  92% 50%);
  --color-ring:       hsl(239 84% 67%);
}
```

### 5.2 Typography

- **Font:** Inter (self-hosted via `@fontsource/inter`).
- **Scale:** `text-xs` (12), `text-sm` (14), `text-base` (16), `text-lg` (18), `text-xl` (20), `text-2xl` (24), `text-3xl` (30), `text-4xl` (36).
- **Line height:** 1.5 body, 1.2 headings.
- **Mono font:** JetBrains Mono for code/chunk content.

### 5.3 Spacing, radius, elevation

- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px (Tailwind defaults).
- **Radius:** `--radius: 0.5rem` (8 px). Cards `rounded-lg`, inputs `rounded-md`, pills `rounded-full`.
- **Shadows:** avoid heavy shadows; use subtle `0 1px 2px rgb(0 0 0 / 0.3)` + border.

### 5.4 Motion

- **Default transition:** 150 ms `ease-out` (hover, focus, color).
- **Modals / drawers:** 300 ms `ease-out` (enter), 200 ms `ease-in` (exit).
- **Respect `prefers-reduced-motion: reduce`** — disable non-essential transitions.

### 5.5 shadcn/ui components per phase

Install with `pnpm dlx shadcn@latest add <names>` as you reach each phase — don't pre-install everything.

| Phase | Components to add |
|---|---|
| 3 (Auth) | `button`, `input`, `label`, `card`, `alert`, `form` |
| 4 (Super Admin) | `dialog`, `dropdown-menu`, `table`, `toast` (via `sonner`), `tabs`, `select`, `switch`, `slider` |
| 6 (Knowledge Base) | `progress`, `accordion`, `textarea`, `popover`, `command` |
| 7 (Business Admin) | `badge`, `skeleton`, `tooltip` |
| 8 (Chat Portal) | `scroll-area`, `avatar`, `separator`, `sheet` (mobile sidebar) |

### 5.6 Page archetypes

- **Auth pages** — centered `card`, max-width 400 px, glassmorphism backdrop (`backdrop-blur-xl bg-surface/60`).
- **Dashboard pages** — persistent 240 px sidebar + main content with a breadcrumb header.
- **Chat portal** — full-bleed layout, sticky input at bottom, messages in a scroll area, alert banner up top.
- **Empty states** — illustration placeholder + one-line explanation + primary CTA.

### 5.7 Accessibility baseline (WCAG AA)

- Contrast: all text ≥ 4.5:1 against its background (verify with Chrome DevTools).
- Visible focus ring on every interactive element (default shadcn `focus-visible:ring-2 ring-ring`).
- Icon-only buttons require `aria-label`.
- Forms: every `<input>` paired with `<label>`; errors announced via `aria-describedby`.
- Keyboard: full keyboard nav; Escape closes modals; Tab order matches visual order.
- Screen reader: live region (`role="status"`) for toast + streaming chat.

---

## 6. Repo Layout

```
RAG-Factory/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── logging.py                  # NEW: structlog config
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── super_admin.py
│   │   │   ├── business_admin.py
│   │   │   ├── chat.py
│   │   │   └── knowledge.py
│   │   ├── core/
│   │   │   ├── llm_router.py
│   │   │   ├── chunker.py
│   │   │   ├── ingestor.py
│   │   │   ├── searcher.py
│   │   │   ├── reranker.py             # NEW (optional, Phase 5.9)
│   │   │   ├── rag_brain.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── scraper.py
│   │   │   └── text_cleaner.py
│   │   ├── models/                     # Pydantic schemas
│   │   └── db/
│   │       ├── supabase_client.py
│   │       └── queries.py
│   ├── tests/                          # NEW: pytest
│   │   ├── conftest.py
│   │   ├── test_config.py
│   │   ├── test_dependencies.py
│   │   ├── test_api_auth.py
│   │   ├── test_api_super_admin.py
│   │   ├── test_core_chunker.py
│   │   ├── test_core_searcher.py
│   │   └── test_core_rag_brain.py
│   ├── pyproject.toml                  # NEW: uv + ruff + pytest config
│   ├── uv.lock                         # NEW
│   ├── .env.example
│   └── .env
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── lib/
│   │   │   ├── supabase.ts
│   │   │   ├── api.ts                  # typed fetch wrapper
│   │   │   ├── query-client.ts         # TanStack Query
│   │   │   ├── utils.ts
│   │   │   └── validators/             # NEW: Zod schemas
│   │   │       ├── auth.ts
│   │   │       ├── business.ts
│   │   │       └── chat.ts
│   │   ├── stores/                     # NEW: Zustand
│   │   │   ├── auth-store.ts
│   │   │   └── business-store.ts
│   │   ├── hooks/
│   │   ├── types/                      # NEW: shared TS types
│   │   │   ├── api.ts
│   │   │   └── models.ts
│   │   ├── components/
│   │   │   ├── ui/                     # NEW: shadcn copies
│   │   │   ├── layout/
│   │   │   ├── chat/
│   │   │   ├── knowledge/
│   │   │   └── common/
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   ├── super-admin/
│   │   │   ├── business-admin/
│   │   │   └── chat/
│   │   └── context/
│   ├── tests/                          # NEW: Vitest unit tests
│   ├── e2e/                            # NEW: Playwright
│   │   ├── auth.spec.ts
│   │   ├── super-admin.spec.ts
│   │   └── chat.spec.ts
│   ├── components.json                 # NEW: shadcn config
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── playwright.config.ts            # NEW
│   ├── vitest.config.ts                # NEW
│   └── .env
├── supabase/                           # NEW
│   └── migrations/
│       ├── 20260418000001_extensions.sql
│       ├── 20260418000002_businesses.sql
│       ├── 20260418000003_business_members.sql
│       ├── 20260418000004_knowledge_chunks.sql
│       ├── 20260418000005_conversations.sql
│       ├── 20260418000006_chat_messages.sql
│       ├── 20260418000007_alerts.sql
│       ├── 20260418000008_response_cache.sql
│       ├── 20260418000009_user_profiles.sql
│       ├── 20260418000010_rls_policies.sql
│       └── 20260418000011_search_knowledge_fn.sql
├── widget/
│   ├── widget.js
│   └── widget.css
├── .pre-commit-config.yaml             # NEW
├── .gitignore
├── README.md
├── STEPS.md
└── PLAN.md                             # this file
```

---

## 7. Phase-by-Phase Checklist

Commit message format: `Phase N: <description>` (matches STEPS.md).

---

### Phase 0 — Project Init & Environment  `[x]`

**Objective.** Scaffold repo, install toolchains, initialise git.

**Prereqs:** `[x]` none.

#### Tasks

- `[x]` 0.1 Create project root, `git init`, add `.gitignore`
  - `[x]` Include Python (`venv/`, `__pycache__/`, `.env`), Node (`node_modules/`, `dist/`), IDE, OS patterns
- `[x]` 0.2 Install system tooling
  - `[x]` Python 3.11+ confirmed (3.12.10)
  - `[x]` Node 18+ confirmed (v22.22)
  - `[x]` Install `uv` (0.8.22)
  - `[x]` Install `pnpm` (10.33)
  - `[ ]` Install Tesseract OCR (deferred — only needed for scanned-PDF OCR in Phase 5)
- `[x]` 0.3 Backend scaffold
  - `[x]` Create `backend/app/{api,core,models,db}/` with `__init__.py`
  - `[x]` `backend/pyproject.toml` with dependencies from STEPS.md plus `structlog`, `pytest`, `pytest-asyncio`, `ruff`, `httpx`, `slowapi`, `tiktoken`
  - `[x]` `uv sync` — creates `.venv`, installs everything
  - `[x]` Configure `ruff` in `pyproject.toml` (line-length 100, target py311)
  - `[x]` Configure `pytest` in `pyproject.toml` (asyncio mode auto, testpaths `tests`)
- `[x]` 0.4 Frontend scaffold
  - `[x]` `pnpm create vite frontend --template react-ts`
  - `[x]` `pnpm add react-router-dom @supabase/supabase-js axios lucide-react @tanstack/react-query zustand react-hook-form zod @hookform/resolvers sonner clsx tailwind-merge class-variance-authority`
  - `[x]` `pnpm add -D tailwindcss @tailwindcss/vite tw-animate-css vitest @vitest/ui jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @playwright/test prettier eslint-config-prettier`
  - `[x]` shadcn init equivalent — `components.json` + `lib/utils.ts` + CSS variables in `index.css`
  - `[x]` Configure Tailwind v4 in `vite.config.ts` + `src/index.css` (dark-mode tokens, `@theme inline`)
  - `[x]` Vite proxy `/api` → `http://localhost:8000`
  - `[x]` Configure `tsconfig.json` strict mode, path aliases (`@/*` → `src/*`)
- `[x]` 0.5 `.env.example` files
  - `[x]` `backend/.env.example` (Supabase + Azure OpenAI + app settings — see STEPS.md Phase 0.8)
  - `[x]` `frontend/.env.example` with `VITE_*` vars
- `[x]` 0.6 Dev tooling
  - `[x]` `.pre-commit-config.yaml` with ruff, prettier, eslint
  - `[ ]` `pre-commit install` (deferred — user runs locally once `pip install pre-commit`)
  - `[x]` ESLint + Prettier config in `frontend/`

#### Testing

Automated:
- `[x]` `cd backend && uv run pytest` — 1 test passed (`test_health`)
- `[x]` `cd frontend && pnpm test` — 4 tests passed (`cn()` suite)
- `[x]` `cd frontend && pnpm typecheck` — strict mode green
- `[x]` `cd frontend && pnpm build` — Vite build succeeds (19 modules, 15 kB CSS)
- `[x]` `cd frontend && pnpm lint && pnpm format:check` — clean

Manual:
- `[x]` `cd backend && uv run python -c "import fastapi; ..."` works (fastapi 0.136.0)
- `[ ]` `cd frontend && pnpm dev` starts Vite on :5173 (user verifies visually)
- `[x]` `git status` — no `node_modules/`, no `.venv/`, no `.env` tracked (after `git init`)

#### Definition of Done

- `[x]` All tasks checked (except two deferred user-system items)
- `[x]` All tests green
- `[ ]` `git add -A && git commit -m "Phase 0: Project scaffold, dependencies, and environment setup"` (next step)

---

### Phase 1 — Supabase Schema + RLS + pgvector  `[~]`

**Objective.** Provision Supabase project, enable pgvector, apply schema + RLS + helper functions via migration files.

**Prereqs:** `[x]` Phase 0 complete.

#### Tasks

- `[x]` 1.1 Create Supabase project (region close to you)
  - `[x]` Copy URL, anon/publishable key, service role key, DB connection string → `backend/.env` (local)
  - `[x]` Copy URL + key → `frontend/.env` (local)
- `[~]` 1.2 Supabase CLI setup (optional if using `apply_migrations.py`)
  - `[ ]` Install Supabase CLI (`npx supabase` works without global install)
  - `[ ]` `supabase login` + `supabase link --project-ref <ref>` (for `supabase db push`)
- `[x]` 1.3 Create migration files in `supabase/migrations/` (12 files, STEPS.md Phase 1)
  - `[x]` `20260418120000_enable_pgvector.sql`
  - `[x]` `20260418120001_create_businesses.sql`
  - `[x]` `20260418120002_create_business_members.sql`
  - `[x]` `20260418120003_create_knowledge_chunks.sql` (HNSW + FTS)
  - `[x]` `20260418120004_create_conversations.sql`
  - `[x]` `20260418120005_create_chat_messages.sql`
  - `[x]` `20260418120006_create_alerts.sql`
  - `[x]` `20260418120007_create_response_cache.sql`
  - `[x]` `20260418120008_create_user_profiles_and_trigger.sql`
  - `[x]` `20260418120009_enable_rls_policies.sql`
  - `[x]` `20260418120010_create_search_knowledge_function.sql`
  - `[x]` `20260418120011_storage_uploads_bucket.sql`
- `[x]` 1.3b `npx supabase init` → `supabase/config.toml` in repo
- `[x]` 1.3c `backend/scripts/apply_migrations.py` — applies migrations via `DATABASE_URL` + `sqlparse` (IPv6-friendly `hostaddr` on Windows)
- `[ ]` 1.4 Apply migrations **on your machine** (needs outbound TCP to Postgres; some networks block `:5432`)
  - `[ ]` **Option A:** `cd backend && uv sync && uv run python scripts/apply_migrations.py`
  - `[ ]` **Option B:** `npx supabase db push` (after `supabase link`)
  - `[ ]` **Option C:** paste each file in order into **SQL Editor** in the Supabase dashboard
  - `[ ]` Verify in Dashboard → **Database** → **Tables**
- `[x]` 1.5 Storage bucket `uploads` (migration `..._storage_uploads_bucket.sql`)
- `[ ]` 1.6 Create super-admin user
  - `[ ]` Add user via Supabase Dashboard → **Authentication** → **Users**
  - `[ ]` SQL: `UPDATE public.user_profiles SET is_super_admin = TRUE WHERE email = 'your@email';`

#### Testing

Automated:
- `[x]` Default `uv run pytest` — health test only (no live DB)
- `[ ]` Optional live check: `RUN_LIVE_DB=1 uv run pytest backend/tests/test_db_integration.py -m integration`

Manual (after 1.4 succeeds):
- `[ ]` `SELECT * FROM pg_extension WHERE extname = 'vector'` → 1 row
- `[ ]` RLS enabled on all 8 public tables
- `[ ]` HNSW index on `knowledge_chunks.embedding`
- `[ ]` `SELECT * FROM search_knowledge(gen_random_uuid(), array_fill(0::float, ARRAY[1536])::vector(1536), '', 1, 0.0);` — empty result, no error
- `[ ]` Storage → bucket `uploads` exists, private

#### Definition of Done

- `[ ]` Migrations applied on hosted Supabase + manual checks above
- `[x]` Migration SQL + apply script committed to git
- `[ ]` `git commit -m "Phase 1: Supabase schema, pgvector, RLS policies, and storage"` (pending push after you verify apply)

---

### Phase 2 — Backend Foundation  `[x]`

**Objective.** FastAPI app with config, Supabase clients, auth dependencies, structured logging, health endpoint.

**Prereqs:** `[x]` Phase 0 complete · `[~]` Phase 1 (schema applied on hosted DB).

#### Tasks

- `[x]` 2.1 `app/config.py` (Pydantic v2 `Settings` + `get_settings()` + `lru_cache`)
- `[x]` 2.2 `app/db/supabase_client.py` — `supabase` + `supabase_admin`
- `[x]` 2.3 `app/dependencies.py` — `get_current_user`, `require_super_admin`, `require_business_admin(business_id)`, `get_optional_user`
- `[x]` 2.3b `app/errors.py` — structured `{"error":{code,message,details?}}` via `HTTPException` handler
- `[x]` 2.4 `app/logging.py` — structlog (JSON non-TTY, console TTY)
- `[x]` 2.5 `app/main.py` — CORS, `X-Request-ID` middleware, lifespan (logging + supabase import), `/api/health`, `/api/health/db`, global exception handler, commented router stubs

#### Testing

Automated:
- `[x]` `tests/test_config.py`
- `[x]` `tests/test_dependencies.py` (mocked Supabase auth)
- `[x]` `tests/test_main.py` — OpenAPI + `/api/health` + `/api/health/db` shape
- `[x]` `backend/.env.test` + conftest load order

Manual:
- `[ ]` `uv run uvicorn app.main:app --reload --port 8000` — verify locally with real `.env`
- `[ ]` Wrong JWT on a protected route — deferred to Phase 3 (no auth routes yet)

#### Definition of Done

- `[x]` All tests green, `ruff check` passes
- `[x]` Git commit + push on `main`

---

### Phase 3 — Authentication  `[x]`

**Objective.** Auth API routes + React auth context + protected routes.

**Prereqs:** `[x]` Phase 2 complete.

#### Tasks

**Backend**
- `[x]` 3.1 `app/models/auth.py` — `SignupRequest`, `LoginRequest`, `UserProfile`, `BusinessSummary`, `TokenPair`, `LoginResponse`, `SignupResponse`, `LogoutResponse`
- `[x]` 3.2 `app/api/auth.py` routes
  - `[x]` `POST /api/auth/signup` — returns profile + optional session (handles email-confirmation flow)
  - `[x]` `POST /api/auth/login` — returns JWT + profile + admin memberships
  - `[x]` `GET /api/auth/me`
  - `[x]` `POST /api/auth/logout` (`supabase_admin.auth.admin.sign_out(jwt, scope="global")`)
  - `[x]` `_map_auth_api_error` for consistent `{error:{code,message,details}}` shape
- `[x]` 3.3 Register router in `main.py`
- `[x]` 3.bonus Added `SECURITY DEFINER` helper `public.auth_is_super_admin()` migration to avoid RLS recursion on `user_profiles`.

**Frontend**
- `[x]` 3.4 shadcn primitives used inline (no separate install needed yet); Tailwind v4 tokens
- `[x]` 3.5 `lib/supabase.ts` — typed Supabase client
- `[x]` 3.6 `lib/api.ts` — typed fetch wrapper + `ApiError` + FastAPI validation-error formatter
- `[ ]` 3.7 ~Zod validators~ (deferred — current forms use HTML5 constraints; will revisit with shadcn `form`)
- `[ ]` 3.8 ~Zustand store~ (deferred — `AuthProvider` exposes all state via context today)
- `[x]` 3.9 `context/auth-provider.tsx` + split files (`auth-types.ts`, `auth-state-context.ts`, `use-auth.ts`) for Fast-Refresh compliance
- `[x]` 3.10 `pages/auth/LoginPage.tsx`
- `[x]` 3.11 `pages/auth/SignupPage.tsx`
- `[x]` 3.12 `components/common/ProtectedRoute.tsx`
  - `[x]` Redirect to `/login` if no session
  - `[x]` `requireSuperAdmin` prop
  - `[x]` `requireBusinessAdminSlug` prop (matches `:slug` against `profile.businesses`)
  - `[x]` Loading state while hydrating
- `[x]` 3.13 `App.tsx` — routes: `/`, `/login`, `/signup`, `/dashboard/*` (super-admin gate + DashboardLayout), `/b/:slug/admin` (business-admin gate), `/b/:slug` (chat portal)

#### Testing

Automated:
- `[x]` Backend unit tests for auth dependencies + API routes (mocked Supabase auth client)
- `[x]` Frontend `tsc` + `eslint` green

Manual:
- `[x]` Signup → verify `user_profiles` trigger fires; super-admin flag togglable via SQL
- `[x]` Login → correct redirect (super-admin → `/dashboard`, business-admin → `/b/<slug>/admin`, else → home)
- `[x]` `/dashboard` without session → redirects to `/login`

#### Definition of Done

- `[x]` All tests green
- `[x]` Committed + pushed on `main`

---

### Phase 4 — Super Admin Dashboard + Per-Business Admin Provisioning  `[x]`

**Objective.** Business CRUD + platform stats for the super admin, **plus the per-business-admin ownership model** (each business gets its own Business Admin with their own email/password login).

**Prereqs:** `[x]` Phase 3 complete.

> **Scope expansion vs STEPS.md.** The original STEPS.md Phase 4 spec auto-added the super admin as the sole admin of every new business. During implementation we changed this to **"each business has its own dedicated Business Admin"** — the super admin provisions/invites admins by email, and those users sign in with their own credentials and are restricted to their business's workspace. See PLAN §1 "Ownership model".

#### Tasks

**Backend**
- `[x]` 4.1 `app/models/business.py`
  - `[x]` `BusinessCreate` (now with optional `admin_email` / `admin_password` / `admin_full_name`)
  - `[x]` `BusinessUpdate`, `BusinessResponse`
  - `[x]` **New:** `BusinessAdminInvite`, `BusinessAdminSummary`, `AdminCredentials`, `BusinessCreateResponse`
- `[x]` 4.2 `app/api/super_admin.py` (all protected by `require_super_admin`)
  - `[x]` `GET /api/super-admin/businesses` (aggregate counts via JOINs)
  - `[x]` `POST /api/super-admin/businesses` — when `admin_email` is provided, provisions the Business Admin (email auto-confirmed) and assigns them as `owner_id` + sole admin member; returns one-time credentials
  - `[x]` `GET /api/super-admin/businesses/{id}`
  - `[x]` `PUT /api/super-admin/businesses/{id}` (settings deep-merge with defaults)
  - `[x]` `DELETE /api/super-admin/businesses/{id}` (soft delete, super-admin only)
  - `[x]` `GET /api/super-admin/stats`
  - `[x]` **New:** `GET /api/super-admin/businesses/{id}/admins` — list admins with email/full_name/role/created_at
  - `[x]` **New:** `POST /api/super-admin/businesses/{id}/admins` — invite admin by email (creates or attaches); returns `AdminCredentials`
  - `[x]` `DELETE /api/super-admin/businesses/{id}/members/{user_id}`
  - `[x]` Legacy `POST /api/super-admin/businesses/{id}/members` (attach existing `user_id`)
- `[x]` 4.3 `app/services/users.py` — `create_or_get_admin_user()` helper using `supabase_admin.auth.admin.create_user`, with `list_users` fallback for the "email already exists" case; generates a secure random password when none supplied
- `[x]` 4.4 **New** `app/api/business_admin.py` (gated by `require_business_admin`)
  - `[x]` `GET /api/business/{id}` — tenant detail
  - `[x]` `PUT /api/business/{id}` — name/description/industry/logo_url/settings (deep merged); `is_active` intentionally filtered (super-admin only)
- `[x]` 4.5 Startup validation in `app/db/supabase_client.py` — rejects boot if `SUPABASE_SERVICE_ROLE_KEY` is not a real `service_role` JWT for the same project as `SUPABASE_URL`

**Frontend**
- `[x]` 4.6 `components/layout/DashboardLayout.tsx` — sidebar + logout
- `[x]` 4.7 `pages/super-admin/DashboardPage.tsx` — 4 stat cards + business grid with `Manage / Edit / Admins / Deactivate` actions; edit modal; admins modal
- `[x]` 4.8 `pages/super-admin/CreateBusinessPage.tsx` — full form + **"Assign a dedicated Business Admin"** section (email/full_name/optional password); one-time credentials reveal with copy buttons
- `[x]` 4.9 **New** `AdminsModal` inside DashboardPage — list admins, invite by email, remove, reveal one-time credentials
- `[x]` 4.10 `pages/business-admin/BusinessAdminDashboard.tsx` — real settings page (profile + chat settings + brand color + max chunks + confidence threshold). Resolves business id from `profile.businesses` by slug; `is_active` is view-only here.
- `[x]` 4.11 `components/common/ProtectedRoute.tsx` — new `requireBusinessAdminSlug` guard (super-admin bypass); `LoginPage` redirects business admins to their first `/b/<slug>/admin` workspace.
- `[x]` 4.12 Toast notifications via `sonner`

#### Testing

Automated:
- `[x]` Backend unit tests for super-admin CRUD + 25-test suite passes (`uv run pytest`)
- `[x]` Frontend `pnpm run lint` + `tsc && vite build` green

Manual:
- `[x]` Super admin creates business with `admin_email` → one-time creds shown → assigned user can sign in → lands on `/b/<slug>/admin` → can edit settings; cannot reach `/dashboard` or other tenants' `/b/<slug>/admin`.
- `[x]` Admins modal: invite by email (creates or attaches), remove admin.
- `[x]` Non-super-admin hitting `/dashboard` → Access Denied.

#### Definition of Done

- `[x]` All tests green
- `[x]` Committed + pushed on `main`

---

### Phase 5 — RAG Engine Core  `[x]`

**Objective.** Port the RAG engine from the UTS UniBot reference, replace ChromaDB with pgvector, upgrade to hybrid search, add streaming.

**Prereqs:** `[x]` Phase 2 complete.

Reference (read-only): `d:\Subs\sem4\research project\grp-p\src\*.py`.

#### Tasks

- `[x]` 5.1 `core/llm_router.py` — Azure OpenAI (sync + async via `asyncio.to_thread`); `get_embedding`, `get_completion`, `get_completion_streaming`; retries with exponential backoff; `tiktoken` token counting logged
- `[x]` 5.2 `core/text_cleaner.py` — industry-aware cleaner (education / restaurant / legal patterns)
- `[x]` 5.3 `core/pdf_parser.py` — `pymupdf4llm` with Tesseract OCR fallback, piped through `text_cleaner`
- `[x]` 5.4 `core/scraper.py` — Jina Reader wrapper, 30 s timeout, retries, UA rotation
- `[x]` 5.5 `core/chunker.py` — MarkdownHeader → RecursiveCharacter; `chunk_size=1200`, `chunk_overlap=150`; async 10-word summaries (batched); `content_hash = md5(url + content)`; drops chunks shorter than 50 chars
- `[x]` 5.6 `core/ingestor.py` — `ingest_chunks()` via `supabase_admin`, `ON CONFLICT (content_hash) DO NOTHING`, structured logging
- `[x]` 5.7 `core/searcher.py` — wraps `search_knowledge` RPC, LLM query expansion, returns rows with `combined_score`
- `[x]` 5.8 `core/rag_brain.py` — multi-turn context (last 5 messages), active-alerts injection, business-specific system prompt, `response_cache` lookup, confidence = avg relevance, streaming generator
- `[ ]` 5.9 `core/reranker.py` **(optional, deferred)** — cross-encoder / Cohere rerank not yet added

#### Testing

Automated:
- `[x]` Unit tests for chunker, ingestor, searcher, rag_brain, llm_router, text_cleaner with mocked Azure OpenAI via `respx` / `unittest.mock` — all green
- `[x]` Full backend suite (25 tests, 1 skipped) green as part of each phase gate

#### Definition of Done

- `[x]` All smoke tests pass; modules are consumed by the `super_admin` / `business_admin` flows
- `[x]` Committed on `main`

---

### Phase 6 — Knowledge Base Management  `[ ]`

**Objective.** Upload / scrape / view / edit / delete chunks per business.

**Prereqs:** `[x]` Phase 5 complete, `[x]` Phase 4 complete.

> **Routing decision (see §1 "Tenant routing & API conventions").** Mount knowledge endpoints under `/api/business/{business_id}/knowledge/…` — not under a standalone `/api/knowledge/{business_id}/…` prefix. Implement as `app/api/knowledge.py` with its own `APIRouter(prefix="/api/business", ...)` (separate module, shared prefix) so the single file stays focused on KB while the URL surface remains unified and `require_business_admin(business_id)` works unchanged.

#### Tasks

**Backend**
- `[ ]` 6.1 `app/api/knowledge.py` — endpoints under `/api/business/{business_id}/knowledge/…`, all gated by `require_business_admin`:
  - `[ ]` `POST   /upload`                 — multipart file → background ingestion; returns `task_id`
  - `[ ]` `POST   /scrape`                 — URL → background ingestion; returns `task_id`
  - `[ ]` `GET    /tasks/{task_id}`        — poll ingestion task status (queued / parsing / chunking / embedding / done / failed)
  - `[ ]` `GET    /chunks`                 — paginated list + search + source filter
  - `[ ]` `GET    /chunks/{chunk_id}`
  - `[ ]` `PUT    /chunks/{chunk_id}`      — edit content → re-embed
  - `[ ]` `DELETE /chunks/{chunk_id}`
  - `[ ]` `DELETE /chunks/batch`           — delete by `source_url`
  - `[ ]` `GET    /sources`                — grouped-by-source summary
  - `[ ]` `GET    /stats`                  — totals by type + storage usage
- `[ ]` 6.2 Upload flow — file → Supabase Storage (`uploads/{business_id}/{timestamp}_{filename}`) → BackgroundTask: parse → chunk → embed → ingest. Reject when `businesses.is_active = FALSE` (return 409 `business_inactive`).
- `[ ]` 6.3 Scrape flow — same BackgroundTask pipeline from `core/scraper.py`.
- `[ ]` 6.4 `models/knowledge.py` — Pydantic schemas (chunk, source, stats, task status).
- `[ ]` 6.5 Register the router in `main.py`.

**Frontend**
- `[ ]` 6.6 `pnpm dlx shadcn@latest add progress accordion textarea popover command`
- `[ ]` 6.7 `hooks/useKnowledge.ts` — list (paginated), sources, mutate. Accepts `businessId` resolved via the shared `useBusinessBySlug(slug)` hook.
- `[ ]` 6.8 Convert `/b/:slug/admin` into a nested layout (`BusinessAdminLayout`) — add a sidebar with placeholders for Settings / Knowledge / Chat / Alerts / Analytics; wire `index` to the existing settings form, `knowledge` to the new page.
- `[ ]` 6.9 `pages/business-admin/KnowledgeBasePage.tsx`
  - `[ ]` Drag-and-drop upload zone (native HTML5 + `react-dropzone` or custom)
  - `[ ]` URL input with "Scrape" button
  - `[ ]` Progress bar driven by status polling
  - `[ ]` Source accordion (group by source_url)
  - `[ ]` Chunk viewer with markdown render toggle
  - `[ ]` Inline edit → re-embed
  - `[ ]` Find & replace within a chunk
  - `[ ]` Filter by source type + keyword search
  - `[ ]` Pagination (10 sources / page)
  - `[ ]` Batch delete by source

#### Testing

Automated:
- `[ ]` `tests/test_api_knowledge.py` — upload small PDF, assert chunks exist; dedup works; delete cascades
- `[ ]` E2E: `e2e/knowledge.spec.ts` — upload sample PDF, edit chunk, delete source

Manual: STEPS.md Phase 6 checklist.

#### Definition of Done

- `[ ]` All tests green
- `[ ]` `git add -A && git commit -m "Phase 6: Knowledge base management (upload, scrape, edit, delete, search)"`

---

### Phase 7 — Business Admin Dashboard  `[~]`

**Objective.** Full admin workspace: test chat, alerts, analytics, settings.

**Prereqs:** `[ ]` Phase 6 complete. _(Settings slice was pulled forward during Phase 4 per the new ownership model.)_

#### Tasks

**Backend** — every endpoint lives under `/api/business/{business_id}/…` and is gated by `require_business_admin`.
- `[~]` 7.1 `app/api/business_admin.py` additions (reuse the existing router)
  - `[x]` Business detail (`GET  /api/business/{id}`)
  - `[x]` Business detail by slug (`GET /api/business/by-slug/{slug}`) — shared with Phase 6/8 sub-pages
  - `[x]` Settings update (`PUT  /api/business/{id}` — deep-merged; `is_active` is super-admin only). **No separate `PUT /{id}/settings` endpoint** — the unified PUT covers both profile and settings.
  - `[ ]` `GET    /api/business/{id}/analytics` — query volume, confidence distribution, top queries, cost estimate
  - `[ ]` `GET    /api/business/{id}/chat-logs` — paginated + filtered
  - `[ ]` `GET    /api/business/{id}/failed-queries`
  - `[ ]` `GET    /api/business/{id}/alerts` · `POST /api/business/{id}/alerts` · `DELETE /api/business/{id}/alerts/{alert_id}`
  - `[ ]` `DELETE /api/business/{id}/cache` — purge response cache

**Frontend** — all sub-pages mount under `/b/:slug/admin/*` and share `useBusinessBySlug(slug)` for id resolution.
- `[ ]` 7.2 `pnpm dlx shadcn@latest add badge skeleton tooltip`
- `[ ]` 7.3 `pnpm add recharts` (or `@tremor/react`)
- `[ ]` 7.4 `pages/business-admin/BusinessAdminLayout.tsx` — sidebar (Settings / Knowledge / Chat / Alerts / Analytics) + outlet. If Phase 6 hasn't built this yet, it's built here; otherwise reuse.
- `[ ]` 7.5 `pages/business-admin/AdminChatPage.tsx` → route `/b/:slug/admin/chat` — chat UI + debug panel (confidence color, sources, chunk count, response time)
- `[ ]` 7.6 `pages/business-admin/AlertsPage.tsx` → route `/b/:slug/admin/alerts`
- `[ ]` 7.7 `pages/business-admin/AnalyticsPage.tsx` → route `/b/:slug/admin/analytics` — stat cards + 3 charts + failed queries table + chat history browser + purge logs
- `[x]` 7.8 Settings section — `BusinessAdminDashboard.tsx` already live (profile + chat settings + brand color + max chunks + confidence threshold). Rename to `SettingsPage.tsx` and add logo upload + danger zone during this phase. Danger zone's "Deactivate business" calls the **super-admin** endpoint (not the business-admin one), so disable it for non-super-admins.

#### Testing

Automated:
- `[ ]` `tests/test_api_business_admin.py` — stats aggregate correct; alerts CRUD; non-member → 403
- `[ ]` Component tests for AnalyticsPage charts (snapshot)
- `[ ]` E2E: `e2e/business-admin.spec.ts` — create alert → purge cache → verify settings persist

Manual: STEPS.md Phase 7 checklist.

#### Definition of Done

- `[ ]` All tests green
- `[ ]` `git add -A && git commit -m "Phase 7: Business Admin Dashboard (chat test, alerts, analytics, settings)"`

---

### Phase 8 — User Chat Portal  `[ ]`

**Objective.** Public chat interface per business, streaming SSE, multi-turn conversations, rate-limited.

**Prereqs:** `[ ]` Phase 5 complete, `[ ]` Phase 7 complete.

#### Tasks

**Backend**
- `[ ]` 8.1 `app/api/chat.py` (all endpoints from STEPS.md 8.1)
  - `[ ]` `POST /{slug}/message` — non-streaming JSON
  - `[ ]` `GET /{slug}/stream` — `text/event-stream` via `sse-starlette`
  - `[ ]` `GET /{slug}/conversations` (authenticated)
  - `[ ]` `GET /{slug}/conversations/{id}/messages`
  - `[ ]` `GET /{slug}/info` — public business info
  - `[ ]` `GET /{slug}/alerts` — active alerts
- `[ ]` 8.2 Rate limiting **(promoted here from STEPS.md Phase 12)**
  - `[ ]` `pnpm add slowapi` / use `slowapi` middleware
  - `[ ]` 20 req / min per IP per business on `/message` + `/stream`
  - `[ ]` 429 response with `Retry-After`
- `[ ]` 8.3 Chat orchestration — implement full pipeline from STEPS.md 8.2 (cache → alerts → history → hybrid search → prompt → LLM → log → cache)
- `[ ]` 8.4 Anonymous session handling — `session_id` UUID in payload → associated with `conversations.session_id`

**Frontend**
- `[ ]` 8.5 `pnpm dlx shadcn@latest add scroll-area avatar separator sheet`
- `[ ]` 8.6 `pages/chat/ChatPortal.tsx`
  - `[ ]` Business branding (logo, name, primary color from `/info`)
  - `[ ]` Alert banner (dismissible per session via sessionStorage)
  - `[ ]` Scrollable messages area, auto-scroll to bottom
  - `[ ]` Sticky input with auto-resize textarea
  - `[ ]` Typing indicator (3 bouncing dots)
  - `[ ]` Source citations expandable per message
  - `[ ]` Confidence dot (green ≥ 0.3, orange ≥ 0.15, red otherwise)
  - `[ ]` Conversation sidebar (Sheet on mobile, fixed on desktop) — auth users only
  - `[ ]` New conversation button
  - `[ ]` Login gate when `user_login_required`
  - `[ ]` Session-ID generation + persistence in localStorage for anonymous
- `[ ]` 8.7 `hooks/useChatStream.ts` — EventSource wrapper, aborts on unmount, handles reconnection
- `[ ]` 8.8 Mobile responsive pass (sidebar → drawer, compact typography)

#### Testing

Automated:
- `[ ]` `tests/test_api_chat.py` — non-streaming happy path; cache hit; anonymous session; rate limit enforced
- `[ ]` `tests/test_chat_streaming.py` — assert SSE events arrive and complete
- `[ ]` Component test for `ChatPortal` — message send + render
- `[ ]` E2E: `e2e/chat.spec.ts` — anonymous user sends message, receives streamed response, alert banner shows

Manual: STEPS.md Phase 8 checklist.

#### Definition of Done

- `[ ]` All tests green
- `[ ]` `git add -A && git commit -m "Phase 8: User Chat Portal (streaming, conversations, alerts, responsive, rate-limited)"`

---

### Phase 9 — Integration Testing & E2E  `[ ]`

**Objective.** Full-flow validation across phases, bug hunt, performance sanity.

**Prereqs:** `[ ]` Phases 0–8 complete.

#### Tasks

- `[ ]` 9.1 Run end-to-end scenario manually (refreshed for the per-business-admin model)
  - `[ ]` **Super admin** creates "Sydney Burgers" **with** `admin_email=owner-sb@example.com` → copy one-time creds
  - `[ ]` Sign in as `owner-sb@example.com` → redirected to `/b/sydney-burgers/admin`
  - `[ ]` (As the Business Admin) upload PDF + scrape URL → chunks appear in KB
  - `[ ]` (As the Business Admin) admin chat test → confidence + sources shown
  - `[ ]` (As the Business Admin) create emergency alert
  - `[ ]` User portal chat (incognito) at `/b/sydney-burgers` → see alert banner, get streamed answer
  - `[ ]` Analytics verify (recorded chats, confidence distribution)
  - `[ ]` Back as **super admin**, create "UTS University" with a different `admin_email` → sign in as that admin → verify they can see only their tenant; confirm Sydney Burgers' admin cannot view UTS's `/b/uts/admin` (403) or `/api/business/<uts-id>` (403)
  - `[ ]` Super admin `DELETE`s Sydney Burgers (soft) → user portal `/b/sydney-burgers` returns 404 or inactive banner; the Business Admin can still sign in but cannot ingest new knowledge (KB writes 409 `business_inactive`)
- `[ ]` 9.2 Consolidated Playwright E2E suite
  - `[ ]` `e2e/full-flow.spec.ts` — ties all phase specs together as one scenario
  - `[ ]` `playwright.config.ts` — run against local dev servers
- `[ ]` 9.3 Bug-fix checklist (STEPS.md 9.2)
- `[ ]` 9.4 Performance checks (STEPS.md 9.3)
  - `[ ]` Measure KB search, chat response, dashboard load with 100+ chunks
  - `[ ]` Record numbers in this PLAN as baseline

#### Definition of Done

- `[ ]` Full E2E suite passes locally
- `[ ]` Zero critical bugs; non-critical bugs filed as TODOs
- `[ ]` `git add -A && git commit -m "Phase 9: Integration testing and bug fixes"`

---

### Phase 10 — Embeddable Widget  `[ ]`

**Objective.** `<script>`-embeddable chat widget for external sites.

**Prereqs:** `[ ]` Phase 8 complete.

#### Tasks

- `[ ]` 10.1 `widget/widget.js` — vanilla JS, Shadow DOM container, fetches `/api/chat/{slug}/info`
- `[ ]` 10.2 Chat bubble (60 px, business primary color, pulse anim)
- `[ ]` 10.3 Chat panel (400×600, close button, same UI patterns as portal but compact)
- `[ ]` 10.4 `widget/widget.css` — scoped styles
- `[ ]` 10.5 Embed code generator — add section to `SettingsPage.tsx` with copy button
- `[ ]` 10.6 CORS allow-list handling — widget passes origin, backend verifies against business settings
- `[ ]` 10.7 Test harness `widget/demo.html`

#### Testing

Automated:
- `[ ]` E2E: `e2e/widget.spec.ts` — load `demo.html`, open bubble, send message, receive reply

Manual: STEPS.md Phase 10 checklist.

#### Definition of Done

- `[ ]` All tests green
- `[ ]` `git add -A && git commit -m "Phase 10: Embeddable chat widget"`

---

### Phase 11 — UI Polish & Accessibility  `[ ]`

**Objective.** Loading states, animations, error boundaries, a11y, responsive pass.

**Prereqs:** `[ ]` Phase 10 complete.

#### Tasks

- `[ ]` 11.1 Skeleton loaders on every data-fetching page (`Skeleton` component)
- `[ ]` 11.2 `ErrorBoundary.tsx` wrapping every top-level page
- `[ ]` 11.3 Toast notifications standardised via `sonner` (success/error/info)
- `[ ]` 11.4 Micro-animations pass (page fade-in, card hover, button press, chat slide-in, modal scale-in)
- `[ ]` 11.5 A11y audit pass with axe DevTools — fix violations
  - `[ ]` All interactive elements have accessible names
  - `[ ]` Focus ring visible everywhere
  - `[ ]` WCAG AA contrast verified
  - `[ ]` Forms have labels + error announcements
- `[ ]` 11.6 Responsive final check at 1440 / 1280 / 1024 / 768 / 375 / 320 px

#### Testing

Automated:
- `[ ]` `pnpm add -D @axe-core/playwright`
- `[ ]` `e2e/a11y.spec.ts` — run axe on each main route, zero critical violations

Manual: visual QA at each breakpoint.

#### Definition of Done

- `[ ]` Zero axe-critical violations
- `[ ]` `git add -A && git commit -m "Phase 11: UI polish, animations, error handling, accessibility"`

---

### Phase 12 — Documentation  `[ ]`

**Objective.** Ship-ready docs (lighter scope — local only, no Docker for now).

**Prereqs:** `[ ]` Phase 11 complete.

#### Tasks

- `[ ]` 12.1 `README.md`
  - `[ ]` Project overview + screenshots (insert after Phase 11)
  - `[ ]` Architecture mermaid (reuse from this PLAN)
  - `[ ]` Tech stack table
  - `[ ]` Getting Started guide (clone → `uv sync` → `pnpm install` → `supabase db push` → run both servers)
  - `[ ]` Env vars reference
  - `[ ]` Link to `/docs` (auto Swagger) + `/redoc`
  - `[ ]` Troubleshooting section
- `[ ]` 12.2 API docstrings on every endpoint + request/response examples
- `[ ]` 12.3 Extended health checks
  - `[ ]` `GET /api/health/db`
  - `[ ]` `GET /api/health/llm`
  - `[ ]` `GET /api/health/storage`
- `[ ]` 12.4 Expand Risks & Open Questions section in this file with resolutions

Deferred (out of scope now):
- Docker / docker-compose
- Production CORS lockdown
- Deployment guide

#### Testing

- `[ ]` README renders cleanly in VS Code preview and on GitHub
- `[ ]` All 4 health endpoints return healthy
- `[ ]` Swagger shows all endpoints grouped by tag

#### Definition of Done

- `[ ]` `git add -A && git commit -m "Phase 12: Documentation and extended health checks"`

---

## 8. Testing Strategy

### Backend (`pytest`)

- Location: `backend/tests/`
- Runner: `uv run pytest` (async mode auto)
- Fixtures in `conftest.py`:
  - `test_settings` — loads `.env.test` with a dedicated Supabase test project
  - `supabase_admin_client` — module-scoped client
  - `clean_db` — truncates all tables before each test run
  - `super_admin_token`, `business_admin_token`, `anon_session_id`
  - `sample_business`, `sample_chunks` factories
- **Coverage target: 70%** on `app/api/` and `app/core/` modules.
- Mock external calls: `respx` for HTTP (Azure OpenAI, Jina), pytest monkeypatch for Supabase auth.
- Run on every commit via pre-commit hook (fast subset) + full suite on `git push`.

### Frontend units (`Vitest`)

- Location: `frontend/tests/` and co-located `*.test.ts(x)`.
- Runner: `pnpm vitest`.
- Focus areas:
  - Zod validators (`lib/validators/*`)
  - Zustand stores (state transitions)
  - Hooks (`useChatStream`, `useKnowledge`, etc.) via `@testing-library/react-hooks`
  - Small components with branching logic (ProtectedRoute, confidence dot, empty states)
- Snapshot tests for chart components (Analytics).

### E2E (`Playwright`)

- Location: `frontend/e2e/`.
- Runner: `pnpm exec playwright test`.
- One spec per critical flow:
  - `auth.spec.ts` — signup, login, logout
  - `super-admin.spec.ts` — create, edit, soft-delete business
  - `knowledge.spec.ts` — upload PDF, verify chunks, edit, delete
  - `business-admin.spec.ts` — create alert, analytics reflects a test query
  - `chat.spec.ts` — anonymous message → streamed response; alert banner; multi-turn
  - `widget.spec.ts` — embed in demo page, bubble → panel → message
  - `full-flow.spec.ts` — end-to-end scenario from Phase 9
  - `a11y.spec.ts` — axe on each main route
- Playwright starts dev servers automatically (`webServer` config) against a dedicated Supabase test project.

### Manual checklists

Keep STEPS.md per-phase manual checklists as a final smoke test before committing each phase.

---

## 9. Risks & Open Questions

| Risk / Question | Mitigation / Plan |
|---|---|
| **Azure OpenAI cost / quota** — no hard cap from SDK | Log tokens per request via `llm_router`; surface in Analytics; add a soft-cap setting per business later |
| **Large PDF timeouts (>50 MB)** | Supabase Storage cap at 50 MB; ingestion offloaded to `BackgroundTasks`; show user a task-status poll endpoint |
| **Embedding dim lock-in (1536)** | `knowledge_chunks.embedding vector(1536)` is fixed. If we ever change model, migration script must re-embed everything. Document in README. |
| **RLS edge cases for anonymous chat** | Anonymous inserts on `chat_messages` rely on `WITH CHECK (TRUE)` — backend is responsible for validating `business_id`. Cover with tests in Phase 8. |
| **Widget CORS / iframe styling on third-party sites** | Shadow DOM isolates CSS; business can allow-list their origin via Settings. Tested with `demo.html` and one real public site. |
| **Supabase free-tier limits** (500 MB DB, 1 GB storage, 50k monthly MAUs) | Fine for local dev. Revisit when scaling. |
| **Conversation history cost** | Last 5 messages is the hard cap for prompt context. Make it configurable per business if needed. |
| **Reranker latency** | Optional; off by default. If enabled, measure added latency in Phase 9 perf check. |
| **Tesseract OCR availability on Windows** | Document UB-Mannheim install link in README; skip OCR gracefully if binary missing (log warning, proceed with text-only extraction). |
| **Supabase CLI on Windows** | Windows requires scoop or manual install — document in Phase 0. |

---

## 10. Quick Reference

### Commit-message cheat sheet

```
Phase 0: Project scaffold, dependencies, and environment setup
Phase 1: Supabase schema, pgvector, RLS policies, and storage
Phase 2: FastAPI skeleton, Supabase client, auth dependencies
Phase 3: Authentication system (Supabase Auth + React context + protected routes)
Phase 4: Super Admin Dashboard with business CRUD management
Phase 5: RAG engine core - llm_router, chunker, ingestor, searcher, rag_brain (pgvector)
Phase 6: Knowledge base management (upload, scrape, edit, delete, search)
Phase 7: Business Admin Dashboard (chat test, alerts, analytics, settings)
Phase 8: User Chat Portal (streaming, conversations, alerts, responsive, rate-limited)
Phase 9: Integration testing and bug fixes
Phase 10: Embeddable chat widget
Phase 11: UI polish, animations, error handling, accessibility
Phase 12: Documentation and extended health checks
```

### Common commands

```bash
# Backend
cd backend
uv sync                                   # install / update deps
uv run uvicorn app.main:app --reload      # start API on :8000
uv run pytest                             # run all tests
uv run pytest tests/test_api_auth.py -v   # single file
uv run ruff check . && uv run ruff format .

# Frontend
cd frontend
pnpm install
pnpm dev                                  # Vite on :5173
pnpm vitest                               # unit tests (watch)
pnpm exec playwright test                 # E2E tests
pnpm exec playwright test --ui            # E2E with UI
pnpm dlx shadcn@latest add <component>    # add a shadcn component
pnpm lint && pnpm format

# Supabase
supabase login
supabase link --project-ref <ref>
supabase db push                          # apply local migrations to linked project
supabase db diff -f <name>                # generate a new migration from schema diff
supabase migration new <name>             # empty migration file

# Git per phase
git add -A && git commit -m "Phase N: <description>"
```

### Useful SQL snippets

Impersonate a user to test RLS in Supabase SQL Editor:

```sql
SET ROLE authenticated;
SET request.jwt.claims = '{"sub":"<user-uuid>","role":"authenticated"}';
-- ...run your query...
RESET ROLE;
```

Check RLS is enforced:

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
```

Inspect HNSW index:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'knowledge_chunks';
```

Purge expired cache entries:

```sql
DELETE FROM public.response_cache WHERE expires_at < NOW();
```

---

_End of PLAN.md. Keep this file in sync with reality — tick boxes as you go._
