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
