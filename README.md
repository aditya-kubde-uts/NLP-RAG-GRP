# RAG Factory

Multi-tenant Retrieval-Augmented Generation platform. Super Admins create isolated RAG chatbots for different businesses; each business gets its own admin dashboard + user chat portal — powered by Azure OpenAI, Supabase (Postgres + pgvector), FastAPI, and React.

> **Status:** Phase 0 complete — project scaffold ready. See [PLAN.md](PLAN.md) for the full 12-phase roadmap and [STEPS.md](STEPS.md) for the detailed implementation reference.

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
| 1 | Supabase schema, pgvector, RLS | Pending |
| 2 | Backend foundation | Pending |
| 3 | Authentication | Pending |
| 4 | Super Admin Dashboard | Pending |
| 5 | RAG engine core | Pending |
| 6 | Knowledge base management | Pending |
| 7 | Business Admin Dashboard | Pending |
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
