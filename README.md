# RAG Factory

Multi-tenant Retrieval-Augmented Generation platform. The **platform Super Admin** (you) creates isolated RAG chatbots for different businesses and assigns each one to its own **Business Admin** with dedicated credentials; each business gets its own admin workspace + user chat portal — powered by Azure OpenAI, Supabase (Postgres + pgvector), FastAPI, and React.

> **Status:** Phases 0–5 complete; **Phase 6** (Knowledge Base Management) is next. Migration SQL lives in `supabase/migrations/`. See [PLAN.md](PLAN.md) for the roadmap and [STEPS.md](STEPS.md) for the detailed reference.

---

## Ownership model

- **Super Admin** — the platform owner. Creates businesses, invites Business Admins, manages platform-wide stats, can soft-deactivate any business.
- **Business Admin** — assigned per business by the super admin. Owns a single tenant workspace (`/b/<slug>/admin`) and can manage its profile, settings, and (in upcoming phases) its knowledge base, alerts, and analytics. Cannot see other businesses.
- **End users / visitors** — talk to the business's chatbot at `/b/<slug>`. Anonymous by default; can be gated behind login via the `user_login_required` setting on each business.

When a super admin creates a business, they supply the Business Admin's email (optionally a password and full name). The backend provisions the auth account via Supabase Admin API with `email_confirm=true`, assigns them as `owner_id` and the sole `business_members` admin, and returns **one-time credentials** that the super admin can hand off. Row-level security + a backend `require_business_admin` dependency enforce tenant isolation end-to-end.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Python 3.11+, FastAPI, `uv`, `structlog`, pytest |
| Frontend | React 19, Vite, TypeScript (strict), Tailwind v4, shadcn/ui, TanStack Query, Zustand, React Hook Form + Zod |
| Database | Supabase Postgres with `pgvector` (HNSW) |
| LLM | Azure OpenAI (embeddings + completions) |
| Storage | Supabase Storage |
| Auth | Supabase Auth (JWT) |
| Testing | pytest, Vitest, Playwright |

---

## Quick Start

### Prerequisites

- Python 3.11+ (`python --version`)
- Node.js 18+ (`node --version`)
- [`uv`](https://github.com/astral-sh/uv) for Python (`pipx install uv` / `winget install astral-sh.uv`)
- [`pnpm`](https://pnpm.io) for Node (`npm i -g pnpm`)
- Git
- (Optional, for scanned-PDF OCR) [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)

### Backend

```bash
cd backend
uv sync                                      # install deps (creates .venv)
copy .env.example .env                       # Windows; or `cp` on *nix
# edit .env with your Supabase + Azure OpenAI credentials
uv run uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health> · Docs: <http://localhost:8000/docs>

### Frontend

```bash
cd frontend
pnpm install
copy .env.example .env
# edit .env with Supabase URL + anon key
pnpm dev
```

App: <http://localhost:5173>

### Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend unit tests
cd frontend && pnpm test

# Frontend E2E (once specs exist from Phase 3+)
cd frontend && pnpm test:e2e

# Frontend typecheck + lint
cd frontend && pnpm typecheck && pnpm lint
```

---

## Architecture

```
┌─────────────┐      JWT       ┌──────────────┐
│ React SPA   │ ─────────────► │   FastAPI    │
│ (Vite + TS) │                │   (Python)   │
└─────────────┘                └──────┬───────┘
                                      │
                ┌─────────────────────┼──────────────────────┐
                ▼                     ▼                      ▼
          ┌──────────┐         ┌─────────────┐         ┌────────────┐
          │ Supabase │         │  Supabase   │         │   Azure    │
          │   Auth   │         │  Postgres   │         │   OpenAI   │
          │  (JWT)   │         │  pgvector   │         │  embed+llm │
          └──────────┘         │   + RLS     │         └────────────┘
                               └─────────────┘
```

Full mermaid diagrams in [PLAN.md §3](PLAN.md).

---

## Project Layout

```
RAG-Factory/
├── backend/              FastAPI app (app/api, app/core, app/db, app/models)
├── frontend/             React + Vite + TS SPA (src/pages, src/components)
├── supabase/migrations/  Postgres schema (added in Phase 1)
├── widget/               Embeddable chat widget (added in Phase 10)
├── PLAN.md               Execution tracker with checkboxes
├── STEPS.md              Detailed reference guide
└── README.md             This file
```

---

## Progress

| Phase | Description | Status |
|---|---|---|
| 0 | Project scaffold & environment | Done |
| 1 | Supabase schema, pgvector, RLS | Migrations in repo — applied on dev DB |
| 2 | Backend foundation (config, Supabase clients, deps, logging) | Done |
| 3 | Authentication (Supabase Auth + React context + protected routes) | Done |
| 4 | Super Admin Dashboard + **per-business admin provisioning** | Done |
| 5 | RAG engine core (llm_router, chunker, ingestor, searcher, rag_brain) | Done |
| 6 | Knowledge base management | Pending |
| 7 | Business Admin Dashboard (settings page already live; KB/alerts/analytics pending) | In progress |
| 8 | User Chat Portal | Pending |
| 9 | Integration testing & E2E | Pending |
| 10 | Embeddable widget | Pending |
| 11 | UI polish & accessibility | Pending |
| 12 | Documentation | Pending |

See [PLAN.md](PLAN.md) for the granular checkbox task list.

---

## License

_To be decided._

## Contributing

See [PLAN.md](PLAN.md) for the current phase plan. Each phase ends with a git commit using the format `Phase N: <description>`.
