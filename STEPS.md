# 🏭 RAG Factory — Multi-Tenant RAG Platform

## Complete Implementation Guide for Cursor AI

> **PROJECT CODENAME:** RAG Factory
> **DESCRIPTION:** A multi-tenant platform where a Super Admin can create, manage, and deploy isolated RAG (Retrieval-Augmented Generation) chatbot systems for different businesses. Each business gets its own Admin Dashboard + User Chat Portal — powered by a shared Azure OpenAI backbone and Supabase (PostgreSQL + pgvector) for data isolation.

---

> [!IMPORTANT]
> ## Instructions for Cursor AI
>
> 1. **Read this entire document before starting any work.**
> 2. **After completing each MAJOR TASK (Phase)**, stop and report what was done. Wait for the user to say "continue" or "proceed" before moving to the next phase.
> 3. **Git backup after every phase:** Run `git add -A && git commit -m "<FEAT/ADD/etc..>: <description>"` after each completed phase.
> 4. **Testing is mandatory.** Each phase includes test cases. Do NOT skip them.
> 5. **If you identify a better approach** for any step, suggest it to the user before implementing.
> 6. **Use Cursor features:** Use `@codebase` for context, Composer for multi-file edits, and set up MCP servers (Supabase MCP) if available in your environment.
> 7. **Reference Project:** The existing UTS UniBot RAG project at `d:\Subs\sem4\research project\grp-p\` is the architectural reference. DO NOT modify it. Use `@file` to reference its files when porting logic.
> 8. **Error Handling:** Every API endpoint must return structured JSON errors. No bare exceptions.
> 9. **If you encounter Supabase MCP:** Connect it via `Settings > MCP > Add Server` using the `@supabase/mcp-server-supabase` npm package. Use it for database migrations and schema management.

---

## 📐 Architecture Overview

```
RAG-Factory/
├── backend/                    # FastAPI Python Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI entry point + CORS
│   │   ├── config.py           # Environment config loader
│   │   ├── dependencies.py     # Shared dependencies (auth, db)
│   │   ├── api/                # API Route modules
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Login, signup, token refresh
│   │   │   ├── super_admin.py  # Business CRUD, platform stats
│   │   │   ├── business_admin.py # Knowledge mgmt, alerts, analytics
│   │   │   ├── chat.py         # RAG chat endpoint (streaming SSE)
│   │   │   └── knowledge.py   # Upload, scrape, ingest, delete
│   │   ├── core/               # RAG Engine (ported + enhanced)
│   │   │   ├── __init__.py
│   │   │   ├── llm_router.py   # Azure OpenAI provider
│   │   │   ├── chunker.py      # Structure-aware markdown chunking
│   │   │   ├── ingestor.py     # Embedding + pgvector upsert
│   │   │   ├── searcher.py     # Hybrid search (semantic + keyword)
│   │   │   ├── rag_brain.py    # Prompt builder + response generator
│   │   │   ├── pdf_parser.py   # PyMuPDF + OCR fallback
│   │   │   ├── scraper.py      # Jina Reader web scraper
│   │   │   └── text_cleaner.py # Noise removal pipeline
│   │   ├── models/             # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── business.py
│   │   │   ├── knowledge.py
│   │   │   └── chat.py
│   │   └── db/                 # Database layer
│   │       ├── __init__.py
│   │       ├── supabase_client.py  # Supabase Python client
│   │       └── queries.py          # Raw SQL helpers for pgvector
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
├── frontend/                   # React + Vite SPA
│   ├── public/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css           # Global styles + design tokens
│   │   ├── lib/
│   │   │   ├── supabase.js     # Supabase JS client
│   │   │   ├── api.js          # Axios/fetch wrapper for backend
│   │   │   └── utils.js
│   │   ├── hooks/              # Custom React hooks
│   │   │   ├── useAuth.js
│   │   │   └── useBusiness.js
│   │   ├── components/         # Shared UI components
│   │   │   ├── Layout/
│   │   │   ├── Chat/
│   │   │   ├── KnowledgeBase/
│   │   │   └── common/
│   │   ├── pages/
│   │   │   ├── auth/           # Login, Signup
│   │   │   ├── super-admin/    # Platform dashboard
│   │   │   ├── business-admin/ # Per-business admin
│   │   │   └── chat/           # User-facing chat
│   │   └── context/
│   │       └── AuthContext.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── .env
├── widget/                     # Embeddable chat widget (Phase 13)
│   ├── widget.js
│   └── widget.css
├── .gitignore
├── README.md
└── STEPS.md                    # This file
```

---

## 🎯 Improvements Over Reference Project (UTS UniBot)

| Area | UTS UniBot (Reference) | RAG Factory (New) |
|---|---|---|
| **Frontend** | Streamlit (limited routing, no custom layouts) | React + Vite + shadcn/ui (full SPA, modern UI) |
| **Vector DB** | ChromaDB (local file-based, single tenant) | pgvector in Supabase (cloud PostgreSQL, multi-tenant) |
| **Auth** | streamlit-authenticator (basic) | Supabase Auth (JWT, OAuth-ready, RBAC) |
| **Data Isolation** | Single collection for all data | Row-Level Security (RLS) per `business_id` |
| **File Storage** | Local filesystem | Supabase Storage (cloud, CDN-ready) |
| **Chat Logs** | JSON file on disk | PostgreSQL table with analytics |
| **Alerts** | JSON file on disk | PostgreSQL table with per-business isolation |
| **Search** | Pure semantic (ChromaDB cosine) | Hybrid: pgvector semantic + PostgreSQL full-text (BM25) |
| **Streaming** | None (blocks until complete) | Server-Sent Events (SSE) for real-time token streaming |
| **Conversations** | Single-turn only | Multi-turn with conversation threading + context window |
| **Deployment** | Local Streamlit only | FastAPI + React SPA (deployable anywhere) |
| **Embeddable** | Not possible | JavaScript widget snippet for external websites |
| **Caching** | JSON file cache | PostgreSQL-based response caching with TTL |
| **Analytics** | Basic query count | Per-business token usage, cost tracking, confidence distribution |

---

# ============================================================
# PHASE 0: PROJECT INITIALIZATION & ENVIRONMENT SETUP
# ============================================================

## Objective
Create the project scaffold, initialize Git, set up Python virtual environment, and install core dependencies.

### Task 0.1: Create Project Directory
```bash
mkdir RAG-Factory
cd RAG-Factory
git init
```

### Task 0.2: Create `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.env
*.egg-info/
dist/
build/

# Node
node_modules/
frontend/dist/
frontend/.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log
```

### Task 0.3: Create Backend Scaffold
```bash
mkdir -p backend/app/api
mkdir -p backend/app/core
mkdir -p backend/app/models
mkdir -p backend/app/db
```

Create all `__init__.py` files in each Python package directory.

### Task 0.4: Create `backend/requirements.txt`
```txt
# Web Framework
fastapi[standard]
uvicorn[standard]

# Supabase
supabase
postgrest-py

# Database (direct PostgreSQL for pgvector)
psycopg2-binary
asyncpg
pgvector

# AI / LLM
openai               # Azure OpenAI SDK

# Document Processing
pymupdf
pymupdf4llm
pytesseract
pillow

# Text Processing
langchain-text-splitters

# Web Scraping
requests
beautifulsoup4

# Data
pydantic
pydantic-settings
python-dotenv
pandas

# Auth
PyJWT

# Utilities
httpx
python-multipart
sse-starlette        # Server-Sent Events for streaming
```

### Task 0.5: Create Python Virtual Environment
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
pip install -r requirements.txt
```

### Task 0.6: Create Frontend Scaffold (Vite + React)
```bash
cd ..
npx -y create-vite@latest frontend -- --template react
cd frontend
npm install
```

Then install UI dependencies:
```bash
npm install react-router-dom @supabase/supabase-js axios lucide-react
npm install -D tailwindcss @tailwindcss/vite
```

> [!NOTE]
> We use **Tailwind CSS v4** (via Vite plugin) + custom components inspired by shadcn/ui patterns.
> This gives us a premium, modern look without installing a heavy component library.
> Build reusable components manually — this keeps the bundle small and debugging easy.

### Task 0.7: Configure Tailwind CSS v4
In `frontend/vite.config.js`:
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'  // Proxy API calls to FastAPI
    }
  }
})
```

In `frontend/src/index.css`, add as the very first line:
```css
@import "tailwindcss";
```

### Task 0.8: Create `.env.example` files

**`backend/.env.example`:**
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-small
AZURE_LLM_DEPLOYMENT_NAME=gpt-4.1-mini

# App Settings
SUPER_ADMIN_EMAIL=admin@ragfactory.com
CORS_ORIGINS=http://localhost:5173
```

**`frontend/.env`:**
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_API_BASE_URL=http://localhost:8000
```

---

### ✅ Phase 0 Testing Checklist
- [ ] `cd backend && python -c "import fastapi; print(fastapi.__version__)"` → prints version
- [ ] `cd backend && python -c "import openai; print('Azure OpenAI SDK OK')"` → no errors
- [ ] `cd frontend && npm run dev` → Vite dev server starts on `http://localhost:5173`
- [ ] `.gitignore` is working (no `node_modules/` or `venv/` tracked)

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 0: Project scaffold, dependencies, and environment setup"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 1.

---

# ============================================================
# PHASE 1: SUPABASE PROJECT SETUP & DATABASE SCHEMA
# ============================================================

## Objective
Create the Supabase project, enable pgvector, define all tables with Row-Level Security (RLS), and configure authentication.

> [!IMPORTANT]
> **Cursor MCP:** If Cursor has Supabase MCP available, connect it now:
> - Go to `Settings > MCP > Add Server`
> - Use `npx -y @supabase/mcp-server-supabase@latest`
> - Provide your Supabase access token
> - Use the MCP tools (`apply_migration`, `execute_sql`, `list_tables`) throughout this phase

### Task 1.1: Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose region closest to you (e.g., `ap-southeast-2` for Australia)
3. Save the project URL, anon key, and service role key to `backend/.env` and `frontend/.env`
4. Go to **Settings > Database** and copy the connection string to `DATABASE_URL` in `backend/.env`

### Task 1.2: Enable pgvector Extension
Run this SQL in Supabase SQL Editor (or via MCP `apply_migration`):

```sql
-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
```

### Task 1.3: Create Database Schema

> [!NOTE]
> Run each migration separately for clean version control. If using Supabase MCP, use `apply_migration` for each.

#### Migration 1: `create_businesses_table`
```sql
-- Businesses table: Each business is a tenant in the platform
CREATE TABLE public.businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,              -- URL-friendly identifier (e.g., "uts-university")
    description TEXT,
    industry TEXT,                           -- e.g., "Education", "Restaurant", "Healthcare"
    logo_url TEXT,
    owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    settings JSONB DEFAULT '{
        "user_login_required": false,
        "custom_system_prompt": "",
        "welcome_message": "Hello! How can I help you today?",
        "primary_color": "#6366f1",
        "max_chunks_per_query": 8,
        "confidence_threshold": 0.15
    }'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for slug lookups (used in URL routing)
CREATE INDEX idx_businesses_slug ON public.businesses(slug);
CREATE INDEX idx_businesses_owner ON public.businesses(owner_id);
```

#### Migration 2: `create_business_members_table`
```sql
-- Business members: Maps users to businesses with roles
CREATE TABLE public.business_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'admin' CHECK (role IN ('super_admin', 'admin', 'viewer')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(business_id, user_id)
);

CREATE INDEX idx_business_members_user ON public.business_members(user_id);
CREATE INDEX idx_business_members_business ON public.business_members(business_id);
```

#### Migration 3: `create_knowledge_chunks_table`
```sql
-- Knowledge chunks: The RAG vector store (pgvector)
-- Using 1536 dimensions for Azure text-embedding-3-small
CREATE TABLE public.knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),                 -- pgvector column
    title TEXT,
    source_url TEXT,
    source_type TEXT DEFAULT 'manual',      -- 'pdf', 'web', 'manual'
    department TEXT DEFAULT 'General',
    llm_summary TEXT,                       -- AI-generated 10-word summary
    metadata JSONB DEFAULT '{}',
    content_hash TEXT,                      -- MD5 hash to prevent duplicates
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Critical indexes for fast vector search
CREATE INDEX idx_knowledge_business ON public.knowledge_chunks(business_id);
CREATE INDEX idx_knowledge_hash ON public.knowledge_chunks(content_hash);

-- HNSW index for fast approximate nearest neighbor search
-- This is MUCH faster than brute-force for large datasets
CREATE INDEX idx_knowledge_embedding ON public.knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Full-text search index for hybrid search (BM25-style keyword matching)
ALTER TABLE public.knowledge_chunks ADD COLUMN fts tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, '') || ' ' || coalesce(title, ''))) STORED;
CREATE INDEX idx_knowledge_fts ON public.knowledge_chunks USING gin(fts);
```

#### Migration 4: `create_conversations_table`
```sql
-- Conversations: Groups chat messages into threads
CREATE TABLE public.conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,  -- NULL for anonymous
    session_id TEXT,                         -- Browser session ID for anonymous users
    title TEXT DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_business ON public.conversations(business_id);
CREATE INDEX idx_conversations_user ON public.conversations(user_id);
```

#### Migration 5: `create_chat_messages_table`
```sql
-- Chat messages: Individual messages within a conversation
CREATE TABLE public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    confidence FLOAT,
    sources JSONB,                           -- Array of source URLs used
    token_count INTEGER DEFAULT 0,
    is_failed BOOLEAN DEFAULT FALSE,         -- Flagged as low-confidence / handoff
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON public.chat_messages(conversation_id);
CREATE INDEX idx_messages_business ON public.chat_messages(business_id);
CREATE INDEX idx_messages_failed ON public.chat_messages(business_id, is_failed) WHERE is_failed = TRUE;
```

#### Migration 6: `create_alerts_table`
```sql
-- Emergency alerts: Per-business broadcast alerts
CREATE TABLE public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_business_active ON public.alerts(business_id, is_active) WHERE is_active = TRUE;
```

#### Migration 7: `create_response_cache_table`
```sql
-- Response cache: Caches frequent questions to save API costs
CREATE TABLE public.response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    query_hash TEXT NOT NULL,                -- MD5 of normalized query
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    sources JSONB,
    confidence FLOAT,
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),
    UNIQUE(business_id, query_hash)
);

CREATE INDEX idx_cache_lookup ON public.response_cache(business_id, query_hash);
CREATE INDEX idx_cache_expiry ON public.response_cache(expires_at);
```

#### Migration 8: `create_user_profiles_table`
```sql
-- User profiles: Extended user info (synced from auth.users via trigger)
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    is_super_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger: Auto-create profile when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### Task 1.4: Enable Row-Level Security (RLS)

#### Migration 9: `enable_rls_policies`
```sql
-- Enable RLS on all tables
ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.response_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- ===== BUSINESSES =====
-- Super admins can see all businesses
CREATE POLICY "Super admins can manage all businesses"
    ON public.businesses FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND is_super_admin = TRUE)
    );

-- Business members can view their own businesses
CREATE POLICY "Members can view their businesses"
    ON public.businesses FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = id AND user_id = auth.uid())
    );

-- ===== KNOWLEDGE CHUNKS =====
-- Business admins can manage their knowledge
CREATE POLICY "Business admins manage knowledge"
    ON public.knowledge_chunks FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = knowledge_chunks.business_id AND user_id = auth.uid() AND role IN ('admin', 'super_admin'))
    );

-- Public read for chat (anon users can search knowledge for active businesses)
CREATE POLICY "Public can read knowledge for active businesses"
    ON public.knowledge_chunks FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.businesses WHERE id = knowledge_chunks.business_id AND is_active = TRUE)
    );

-- ===== CHAT MESSAGES =====
-- Business admins can view all chats for their business
CREATE POLICY "Admins view business chats"
    ON public.chat_messages FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = chat_messages.business_id AND user_id = auth.uid() AND role IN ('admin', 'super_admin'))
    );

-- Users can insert chat messages (via API, the backend validates business_id)
CREATE POLICY "Anyone can insert chat messages"
    ON public.chat_messages FOR INSERT
    WITH CHECK (TRUE);

-- ===== ALERTS =====
CREATE POLICY "Admins manage alerts"
    ON public.alerts FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = alerts.business_id AND user_id = auth.uid() AND role IN ('admin', 'super_admin'))
    );

CREATE POLICY "Public can read active alerts"
    ON public.alerts FOR SELECT
    USING (is_active = TRUE);

-- ===== USER PROFILES =====
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (id = auth.uid());

CREATE POLICY "Super admins can view all profiles"
    ON public.user_profiles FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND is_super_admin = TRUE)
    );

-- ===== CONVERSATIONS =====
CREATE POLICY "Users see own conversations"
    ON public.conversations FOR SELECT
    USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Anyone can create conversations"
    ON public.conversations FOR INSERT
    WITH CHECK (TRUE);

-- ===== BUSINESS MEMBERS =====
CREATE POLICY "Members see own membership"
    ON public.business_members FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Super admins manage members"
    ON public.business_members FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND is_super_admin = TRUE)
    );

-- ===== RESPONSE CACHE =====
CREATE POLICY "Public can read cache"
    ON public.response_cache FOR SELECT USING (TRUE);

CREATE POLICY "Admins manage cache"
    ON public.response_cache FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = response_cache.business_id AND user_id = auth.uid())
    );
```

### Task 1.5: Create Helper SQL Functions

#### Migration 10: `create_vector_search_function`
```sql
-- Hybrid search function: Combines semantic (vector) + keyword (full-text) search
-- This is the CORE improvement over the reference project's pure-semantic search
CREATE OR REPLACE FUNCTION search_knowledge(
    p_business_id UUID,
    p_query_embedding vector(1536),
    p_query_text TEXT DEFAULT '',
    p_match_count INT DEFAULT 8,
    p_similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    title TEXT,
    source_url TEXT,
    source_type TEXT,
    department TEXT,
    llm_summary TEXT,
    metadata JSONB,
    similarity FLOAT,
    keyword_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH semantic AS (
        SELECT
            kc.id,
            kc.content,
            kc.title,
            kc.source_url,
            kc.source_type,
            kc.department,
            kc.llm_summary,
            kc.metadata,
            1 - (kc.embedding <=> p_query_embedding) AS similarity
        FROM public.knowledge_chunks kc
        WHERE kc.business_id = p_business_id
          AND 1 - (kc.embedding <=> p_query_embedding) > p_similarity_threshold
        ORDER BY kc.embedding <=> p_query_embedding
        LIMIT p_match_count * 2  -- Fetch extra for re-ranking
    ),
    keyword AS (
        SELECT
            kc.id,
            ts_rank_cd(kc.fts, websearch_to_tsquery('english', p_query_text)) AS rank
        FROM public.knowledge_chunks kc
        WHERE kc.business_id = p_business_id
          AND p_query_text != ''
          AND kc.fts @@ websearch_to_tsquery('english', p_query_text)
    )
    SELECT
        s.id,
        s.content,
        s.title,
        s.source_url,
        s.source_type,
        s.department,
        s.llm_summary,
        s.metadata,
        s.similarity::FLOAT,
        COALESCE(k.rank, 0)::FLOAT AS keyword_rank,
        -- Combined score: 70% semantic + 30% keyword (Reciprocal Rank Fusion inspired)
        (s.similarity * 0.7 + COALESCE(k.rank, 0) * 0.3)::FLOAT AS combined_score
    FROM semantic s
    LEFT JOIN keyword k ON s.id = k.id
    ORDER BY (s.similarity * 0.7 + COALESCE(k.rank, 0) * 0.3) DESC
    LIMIT p_match_count;
END;
$$;
```

### Task 1.6: Set Up Supabase Storage Bucket

Go to Supabase Dashboard > Storage > Create new bucket:
- **Bucket name:** `uploads`
- **Public:** No (private, accessed via signed URLs)
- **File size limit:** 50MB
- **Allowed MIME types:** `application/pdf, text/plain, text/markdown`

Or run via SQL:
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('uploads', 'uploads', FALSE, 52428800, ARRAY['application/pdf', 'text/plain', 'text/markdown']);
```

### Task 1.7: Create First Super Admin User
1. Go to Supabase Dashboard > Authentication > Users
2. Click "Add User" → enter your email and password
3. Then mark them as super admin:
```sql
UPDATE public.user_profiles SET is_super_admin = TRUE WHERE email = 'YOUR_EMAIL_HERE';
```

---

### ✅ Phase 1 Testing Checklist
- [ ] All 10 migrations applied successfully (check Supabase Dashboard > Database > Tables)
- [ ] Verify tables exist: `businesses`, `business_members`, `knowledge_chunks`, `conversations`, `chat_messages`, `alerts`, `response_cache`, `user_profiles`
- [ ] Verify pgvector extension: Run `SELECT * FROM pg_extension WHERE extname = 'vector';` — should return 1 row
- [ ] Verify HNSW index exists on `knowledge_chunks.embedding`
- [ ] Verify RLS is enabled on all tables (green lock icon in Supabase Dashboard)
- [ ] Verify `search_knowledge` function exists: Run `SELECT search_knowledge(gen_random_uuid(), '[0,0,...,0]'::vector(1536));` — should return empty (not error)
- [ ] Storage bucket `uploads` is created
- [ ] Super admin user exists and `is_super_admin = TRUE` in `user_profiles`

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 1: Supabase schema, pgvector, RLS policies, and storage"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 2.

---

# ============================================================
# PHASE 2: BACKEND FOUNDATION (FastAPI + Supabase Integration)
# ============================================================

## Objective
Build the FastAPI application skeleton with Supabase client, environment config, CORS, health check endpoints, and the authentication middleware.

### Task 2.1: Create `backend/app/config.py`
Environment configuration using Pydantic Settings:
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    database_url: str

    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-02-01"
    azure_embedding_deployment_name: str = "text-embedding-3-small"
    azure_llm_deployment_name: str = "gpt-4.1-mini"

    # App
    super_admin_email: str = "admin@ragfactory.com"
    cors_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()
```

### Task 2.2: Create `backend/app/db/supabase_client.py`
```python
from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# Public client (uses anon key, respects RLS)
supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

# Service client (bypasses RLS, for backend-only operations)
supabase_admin: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)
```

### Task 2.3: Create `backend/app/dependencies.py`
Shared dependencies for auth validation and injecting business context:
```python
from fastapi import Depends, HTTPException, Header
from app.db.supabase_client import supabase, supabase_admin

async def get_current_user(authorization: str = Header(None)):
    """Validate JWT token from Supabase Auth and return user info."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

async def require_super_admin(user = Depends(get_current_user)):
    """Ensure the user is a super admin."""
    profile = supabase_admin.table("user_profiles").select("is_super_admin").eq("id", str(user.id)).single().execute()
    if not profile.data or not profile.data.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user

async def require_business_admin(user = Depends(get_current_user)):
    """Return user but will need business_id check at route level."""
    return user

# Optional auth: Returns None if not authenticated (for public chat endpoints)
async def get_optional_user(authorization: str = Header(None)):
    """Returns user if authenticated, None otherwise."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ")[1]
        user_response = supabase.auth.get_user(token)
        return user_response.user if user_response and user_response.user else None
    except:
        return None
```

### Task 2.4: Create `backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="RAG Factory API",
    description="Multi-tenant RAG platform backend",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "RAG Factory API"}

# Import and include routers (will be created in later phases)
# from app.api import auth, super_admin, business_admin, chat, knowledge
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(super_admin.router, prefix="/api/super-admin", tags=["Super Admin"])
# app.include_router(business_admin.router, prefix="/api/business", tags=["Business Admin"])
# app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
# app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge Base"])
```

### Task 2.5: Test Backend Startup
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

---

### ✅ Phase 2 Testing Checklist
- [ ] `uvicorn app.main:app --reload --port 8000` starts without errors
- [ ] `GET http://localhost:8000/api/health` returns `{"status": "healthy", "service": "RAG Factory API"}`
- [ ] `GET http://localhost:8000/docs` shows Swagger UI
- [ ] Environment variables load correctly (no `ValidationError` from Pydantic Settings)
- [ ] Supabase client initializes (no import errors)

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 2: FastAPI skeleton, Supabase client, auth dependencies"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 3.

---

# ============================================================
# PHASE 3: AUTHENTICATION SYSTEM
# ============================================================

## Objective
Build auth API routes (signup, login, profile) and the React frontend auth flow with protected routes.

### Task 3.1: Create `backend/app/api/auth.py`
Implement these endpoints:
- `POST /api/auth/signup` — Register new user (email + password + full_name)
- `POST /api/auth/login` — Login with email + password, return JWT + user profile
- `GET /api/auth/me` — Get current user profile (requires JWT)
- `POST /api/auth/logout` — Invalidate session

> [!NOTE]
> Use Supabase Auth SDK for all auth operations. The backend acts as a proxy to add business logic (like checking super_admin status).

### Task 3.2: Create `backend/app/models/auth.py`
Pydantic schemas for request/response:
```python
from pydantic import BaseModel, EmailStr
from typing import Optional

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_super_admin: bool = False
    businesses: list = []  # List of businesses user is admin of
```

### Task 3.3: Create Frontend Auth Context (`frontend/src/context/AuthContext.jsx`)
- Initialize Supabase JS client
- Listen to `onAuthStateChange` events
- Provide `user`, `session`, `signIn`, `signUp`, `signOut` to all components
- Auto-redirect to login if accessing protected routes without session

### Task 3.4: Create Frontend Auth Pages
- `frontend/src/pages/auth/LoginPage.jsx` — Email + password login form
- `frontend/src/pages/auth/SignupPage.jsx` — Registration form (email + password + full name)

> [!TIP]
> **Design Guidelines:**
> - Use a centered card layout with glassmorphism effect (backdrop-blur, subtle border)
> - Dark theme by default (#0f0f23 background, #1a1a2e cards)
> - Accent color: Indigo (#6366f1) for buttons and focus rings
> - Smooth transitions on form inputs (border-color, box-shadow)
> - Show loading spinner on submit buttons
> - Display error messages inline (red text below the input)

### Task 3.5: Create Protected Route Wrapper
`frontend/src/components/common/ProtectedRoute.jsx`:
- If user is authenticated → render children
- If not → redirect to `/login`
- If route requires super_admin but user isn't → show "Access Denied" page

### Task 3.6: Set Up React Router
`frontend/src/App.jsx`:
```jsx
// Route structure:
// /login          → LoginPage
// /signup         → SignupPage
// /dashboard      → SuperAdmin Dashboard (protected, super_admin only)
// /b/:slug/admin  → Business Admin Dashboard (protected, business admin)
// /b/:slug        → User Chat Portal (public or protected based on business settings)
```

---

### ✅ Phase 3 Testing Checklist

#### Manual Tests:
- [ ] Navigate to `http://localhost:5173/signup` → see registration form
- [ ] Register a new user → user appears in Supabase Auth dashboard
- [ ] The `user_profiles` table auto-creates a row (via trigger) for the new user
- [ ] Navigate to `http://localhost:5173/login` → login with created user
- [ ] After login, `GET /api/auth/me` returns correct user profile
- [ ] Accessing `/dashboard` without login → redirects to `/login`
- [ ] After login as super admin → `/dashboard` loads correctly
- [ ] Logout → session cleared, redirected to `/login`

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 3: Authentication system (Supabase Auth + React context + protected routes)"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 4.

---

# ============================================================
# PHASE 4: SUPER ADMIN DASHBOARD — BUSINESS MANAGEMENT
# ============================================================

## Objective
Build the Super Admin Dashboard where the platform owner can create, view, edit, and delete businesses. This is the "command center" of the entire platform.

### Task 4.1: Create `backend/app/api/super_admin.py`
Implement these endpoints (all require `super_admin` role):
- `GET /api/super-admin/businesses` — List all businesses with stats (chunk count, chat count)
- `POST /api/super-admin/businesses` — Create new business
- `GET /api/super-admin/businesses/{business_id}` — Get business details
- `PUT /api/super-admin/businesses/{business_id}` — Update business
- `DELETE /api/super-admin/businesses/{business_id}` — Soft delete (set `is_active = FALSE`)
- `GET /api/super-admin/stats` — Platform-wide stats (total businesses, users, queries, API cost)
- `POST /api/super-admin/businesses/{business_id}/members` — Add admin to a business
- `DELETE /api/super-admin/businesses/{business_id}/members/{user_id}` — Remove admin

### Task 4.2: Create `backend/app/models/business.py`
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BusinessCreate(BaseModel):
    name: str
    slug: str            # Auto-generated from name, editable
    description: Optional[str] = None
    industry: str        # Dropdown: Education, Restaurant, Healthcare, Retail, Legal, Other
    settings: Optional[dict] = None

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict] = None
    is_active: Optional[bool] = None

class BusinessResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    industry: str
    logo_url: Optional[str]
    settings: dict
    is_active: bool
    created_at: datetime
    chunk_count: int = 0
    chat_count: int = 0
    admin_count: int = 0
```

### Task 4.3: Create Super Admin Dashboard Pages (Frontend)

#### `frontend/src/pages/super-admin/DashboardPage.jsx`
- **Top Stats Bar:** 4 metric cards (Total Businesses, Total Knowledge Chunks, Total Chats, Estimated API Cost)
- **Business List:** Responsive grid of business cards, each showing:
  - Business name + industry badge
  - Chunk count, Chat count, Admin count
  - Status indicator (Active/Inactive)
  - "Manage" button → navigates to business admin
  - "Edit" button → opens edit modal
  - "Delete" button → confirmation dialog

#### `frontend/src/pages/super-admin/CreateBusinessPage.jsx`
- **Form fields:**
  - Business Name (required)
  - Slug (auto-generated from name, editable, validated for uniqueness)
  - Description (textarea)
  - Industry (dropdown: Education, Restaurant, Healthcare, Retail, Legal, Technology, Other)
  - Settings:
    - Toggle: "Require User Login for Chat" (default: OFF)
    - Custom Welcome Message (textarea)
    - Primary Brand Color (color picker)
    - Max Chunks Per Query (number input, default: 8)
    - Confidence Threshold (slider, default: 0.15)
- **On submit:** Create business → auto-add current user as admin → redirect to dashboard

> [!TIP]
> **Design Guidelines for Dashboard:**
> - Use a persistent sidebar navigation (collapsible on mobile)
> - Dark theme: `#0a0a1a` background, `#12122a` sidebar, `#1a1a3e` cards
> - Stat cards: Gradient borders (indigo → purple), subtle glow on hover
> - Business cards: Hover lift effect (transform: translateY(-2px)), smooth shadow transition
> - Use Lucide icons throughout (Building2, Database, MessageSquare, Users, Settings, Plus)
> - Loading states: Skeleton placeholders (pulsing gray rectangles)
> - Toast notifications for success/error actions (bottom-right corner)
> - Empty state: Illustration + "Create your first business" CTA button

### Task 4.4: Create Sidebar Layout Component
`frontend/src/components/Layout/DashboardLayout.jsx`:
- Fixed sidebar (240px wide) with:
  - App logo/name at top
  - Navigation links (Dashboard, Settings)
  - User avatar + name at bottom
  - Logout button
- Main content area with top breadcrumb bar

---

### ✅ Phase 4 Testing Checklist

#### Manual Tests:
- [ ] Login as super admin → Dashboard loads with empty state
- [ ] Click "Create Business" → form renders with all fields
- [ ] Fill form and submit → business created, appears in dashboard
- [ ] Create 3 businesses with different industries → all appear in grid
- [ ] Click "Edit" on a business → edit modal shows current values
- [ ] Update business name → change reflected immediately
- [ ] Click "Delete" → confirmation dialog shows → confirm → business disappears
- [ ] Verify in Supabase: business row has `is_active = FALSE` (soft delete)
- [ ] Stats bar shows correct counts
- [ ] Non-super-admin user accessing `/dashboard` → "Access Denied" page

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 4: Super Admin Dashboard with business CRUD management"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 5.

---

# ============================================================
# PHASE 5: RAG ENGINE CORE (Port + Enhance)
# ============================================================

## Objective
Port the RAG engine from the reference project, replacing ChromaDB with pgvector and upgrading to hybrid search. This is the brain of the platform.

> [!IMPORTANT]
> **Reference Files (DO NOT MODIFY — read only):**
> - `@file d:\Subs\sem4\research project\grp-p\src\llm_router.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\chunker.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\ingestor.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\searcher.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\rag_brain.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\pdf_parser.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\scraper.py`
> - `@file d:\Subs\sem4\research project\grp-p\src\text_cleaner.py`

### Task 5.1: Create `backend/app/core/llm_router.py`
Port from reference, but:
- **Remove** Gemini/Groq providers — Azure OpenAI only
- **Use** `openai.AzureOpenAI` client
- **Add** explicit error handling with retries (3 attempts, exponential backoff)
- **Add** token counting for cost tracking
- **Add** async versions of all functions using `asyncio.to_thread()`
- **Expose:** `get_embedding(texts: List[str]) → List[List[float]]`
- **Expose:** `get_completion(prompt: str, system_prompt: str = "") → str`
- **Expose:** `get_completion_streaming(prompt: str, system_prompt: str = "") → AsyncGenerator[str]` (for SSE)

### Task 5.2: Create `backend/app/core/text_cleaner.py`
Port directly from reference with these additions:
- Add patterns for cleaning restaurant menus (remove pricing artifacts)
- Add patterns for cleaning legal documents (remove page headers/footers)
- Make noise patterns configurable per business (pass `industry` parameter)

### Task 5.3: Create `backend/app/core/pdf_parser.py`
Port directly from reference. Key logic:
1. Try `pymupdf4llm.to_markdown()` first
2. Fallback to Tesseract OCR for scanned/image PDFs
3. Run through `text_cleaner.clean_text_for_llm()`
4. Return `{"content": str, "metadata": dict}`

### Task 5.4: Create `backend/app/core/scraper.py`
Port from reference (Jina Reader approach). Enhancements:
- Add timeout handling (30s)
- Add retry logic (2 retries)
- Add user-agent rotation
- Return structured `{"content": str, "metadata": dict}` with proper error messages

### Task 5.5: Create `backend/app/core/chunker.py`
Port from reference with these enhancements:
- Keep `MarkdownHeaderTextSplitter` → `RecursiveCharacterTextSplitter` pipeline
- **Increase** `chunk_size` to 1200 and `chunk_overlap` to 150 (better for pgvector)
- **Keep** the LLM-powered 10-word summary enrichment (async batch)
- **Add** `content_hash` generation (MD5 of URL + content) for dedup
- **Filter** chunks with `MIN_CHUNK_LENGTH = 50`

### Task 5.6: Create `backend/app/core/ingestor.py`
Replace ChromaDB upsert with pgvector insert:
```python
# Key changes from reference:
# 1. Instead of ChromaDB collection.upsert(), INSERT INTO knowledge_chunks with ON CONFLICT
# 2. Embeddings are stored as pgvector vector(1536) type
# 3. business_id is required for multi-tenant isolation
# 4. content_hash used for dedup instead of ChromaDB's internal ID
```

Core function signature:
```python
async def ingest_chunks(
    chunks: List[Dict],
    business_id: str,
    source_url: str,
    source_type: str
) -> int:  # Returns number of chunks ingested
```

### Task 5.7: Create `backend/app/core/searcher.py`
Replace ChromaDB search with the `search_knowledge` SQL function:
```python
# Key changes:
# 1. Uses the search_knowledge() PostgreSQL function (hybrid semantic + keyword)
# 2. Adds query expansion via LLM (same as reference)
# 3. Returns results with combined_score instead of just distance
# 4. business_id filtering is built into the SQL function
```

### Task 5.8: Create `backend/app/core/rag_brain.py`
Port from reference with these enhancements:
- **Multi-turn context:** Accept optional `conversation_history` parameter with last 5 messages
- **Business-aware prompts:** Include business name and custom system prompt from settings
- **Alert injection:** Same as reference (alerts table instead of JSON file)
- **Streaming support:** Add `generate_rag_response_streaming()` that yields tokens
- **Cache check:** Before calling LLM, check `response_cache` table for matching query hash
- **Confidence scoring:** Same as reference (average relevance of used chunks)
- **Feedback storage:** Log query + response to `chat_messages` table

---

### ✅ Phase 5 Testing Checklist (Backend Only)

Create a test script `backend/test_rag_core.py`:
```python
# Test each module independently:
# 1. llm_router: get_embedding(["test"]) → returns list of 1536-dim vector
# 2. llm_router: get_completion("Say hello") → returns string
# 3. text_cleaner: clean("test content with ===== dividers") → cleaned
# 4. pdf_parser: parse_pdf("test.pdf") → returns content + metadata
# 5. chunker: process_document("# Title\nContent...") → returns chunks list
# 6. ingestor: ingest_chunks(test_chunks, test_business_id) → returns count
# 7. searcher: search_knowledge_base("test query", business_id) → returns results
# 8. rag_brain: generate_rag_response("What is this?", business_id) → returns answer
```

- [ ] `python test_rag_core.py` passes all 8 tests
- [ ] Embeddings are stored in `knowledge_chunks` table in Supabase (verify via dashboard)
- [ ] Vector search returns relevant results ordered by `combined_score`
- [ ] LLM generates answers using only provided context (no hallucination)
- [ ] Cache stores responses and returns cached result on duplicate query

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 5: RAG engine core - llm_router, chunker, ingestor, searcher, rag_brain (pgvector)"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 6.

---

# ============================================================
# PHASE 6: KNOWLEDGE BASE MANAGEMENT API + UI
# ============================================================

## Objective
Build the knowledge base management system — upload PDFs, scrape URLs, view/edit/delete chunks — for business admins.

### Task 6.1: Create `backend/app/api/knowledge.py`
Endpoints (require business admin role):
- `POST /api/knowledge/{business_id}/upload` — Upload PDF/TXT file → ingest
- `POST /api/knowledge/{business_id}/scrape` — Scrape URL → ingest
- `GET /api/knowledge/{business_id}/chunks` — List chunks with pagination, filtering, search
- `GET /api/knowledge/{business_id}/chunks/{chunk_id}` — Get single chunk
- `PUT /api/knowledge/{business_id}/chunks/{chunk_id}` — Edit chunk content (re-embed)
- `DELETE /api/knowledge/{business_id}/chunks/{chunk_id}` — Delete single chunk
- `DELETE /api/knowledge/{business_id}/chunks/batch` — Delete chunks by source URL (batch)
- `GET /api/knowledge/{business_id}/sources` — List unique sources (grouped by URL/title)
- `GET /api/knowledge/{business_id}/stats` — Knowledge base stats (total chunks, by type, storage)

### Task 6.2: File Upload Flow (Backend)
```
Client uploads PDF → FastAPI receives file →
  1. Save to Supabase Storage (uploads/{business_id}/{timestamp}_{filename})
  2. Parse PDF (pdf_parser.py)
  3. Clean text (text_cleaner.py)
  4. Chunk text (chunker.py) — async with LLM enrichment
  5. Generate embeddings (llm_router.py)
  6. Insert into knowledge_chunks (ingestor.py)
  7. Return summary: { chunks_created: N, source_url: "...", title: "..." }
```

### Task 6.3: Create Business Admin Knowledge Base Pages (Frontend)

#### `frontend/src/pages/business-admin/KnowledgeBasePage.jsx`
Port the "Manage Database" page from reference `admin_ui.py` (lines 250-422) with these upgrades:
- **Upload Zone:** Drag-and-drop area for PDFs + URL input field (side by side)
- **Progress indicator:** Show real-time progress during ingestion (uploading → parsing → chunking → embedding → done)
- **Source Explorer:** Group chunks by source (URL/filename), expandable cards
- **Chunk Viewer:** Display chunk content with syntax highlighting for markdown
- **Inline Editor:** Click "Edit" → textarea with "Save & Re-Embed" button (same as reference)
- **Find & Replace:** Same as reference (lines 374-385) — search text within chunk and replace
- **Filters:** Source type dropdown + date range picker + keyword search (same as reference)
- **Pagination:** Dropdown page selector (same as reference)
- **Batch Delete:** Select multiple sources → delete all their chunks at once

> [!TIP]
> The reference project's database explorer (lines 250-422 of admin_ui.py) has excellent UX patterns.
> Port the grouping-by-source, pagination, and inline editing features but use React components.
> Replace Streamlit's `st.expander` with collapsible `<details>` or a custom accordion component.
> Replace `st.text_area` with a `<textarea>` that has line numbers and a markdown preview toggle.

---

### ✅ Phase 6 Testing Checklist

#### Manual Tests:
- [ ] Upload a PDF → chunks appear in database explorer within 30 seconds
- [ ] Upload a TXT file → chunks appear correctly
- [ ] Scrape a URL (e.g., any public webpage) → chunks ingested
- [ ] View ingested chunks grouped by source
- [ ] Click "Edit" on a chunk → text area opens with content
- [ ] Modify chunk text → click "Save & Re-Embed" → embedding updates in DB
- [ ] Use Find & Replace → replaces text within chunk correctly
- [ ] Delete single chunk → disappears from list
- [ ] Delete all chunks for a source → entire source group disappears
- [ ] Filter by source type (PDF/Web) → correctly filters
- [ ] Keyword search → finds chunks containing the search term
- [ ] Pagination works (5 sources per page)
- [ ] Upload duplicate PDF → no duplicate chunks created (content_hash dedup)

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 6: Knowledge base management (upload, scrape, edit, delete, search)"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 7.

---

# ============================================================
# PHASE 7: BUSINESS ADMIN DASHBOARD
# ============================================================

## Objective
Build the complete Business Admin Dashboard with sidebar navigation, mirroring all features from the reference project's admin_ui.py but enhanced for multi-tenant.

### Task 7.1: Create `backend/app/api/business_admin.py`
Endpoints:
- `GET /api/business/{business_id}` — Get business details + stats
- `PUT /api/business/{business_id}/settings` — Update business settings
- `GET /api/business/{business_id}/analytics` — Dashboard analytics (query volume, confidence distribution, top queries, API cost estimate)
- `GET /api/business/{business_id}/chat-logs` — Chat history with pagination + filters
- `GET /api/business/{business_id}/failed-queries` — Failed/low-confidence queries
- `POST /api/business/{business_id}/alerts` — Create emergency alert
- `GET /api/business/{business_id}/alerts` — List alerts
- `DELETE /api/business/{business_id}/alerts/{alert_id}` — Remove alert
- `DELETE /api/business/{business_id}/cache` — Purge response cache

### Task 7.2: Create Business Admin Layout
`frontend/src/pages/business-admin/BusinessAdminLayout.jsx`:
- Sidebar with business name + logo at top
- Navigation sections:
  1. 💬 **Chat (Admin Test)** — Test the RAG as a user would
  2. 📚 **Knowledge Base** — Upload, manage chunks (from Phase 6)
  3. 🚨 **Emergency Alerts** — Broadcast alerts (from reference)
  4. 📊 **Analytics & QC** — Dashboard analytics (from reference)
  5. ⚙️ **Settings** — Business configuration

### Task 7.3: Admin Chat Test Page
`frontend/src/pages/business-admin/AdminChatPage.jsx`:
- Same chat interface as user portal but with additional debug info:
  - Show confidence score color-coded (green/orange/red)
  - Show cited sources in expandable section
  - Show "chunks used" count
  - Show response time in milliseconds

### Task 7.4: Emergency Alerts Page
`frontend/src/pages/business-admin/AlertsPage.jsx`:
Port from reference `admin_ui.py` (lines 424-474):
- Text input to create new alert
- List of active alerts with "Remove" button
- Cache management section with "Purge Cache" button

### Task 7.5: Analytics & Quality Control Page
`frontend/src/pages/business-admin/AnalyticsPage.jsx`:
Port from reference `admin_ui.py` (lines 476-537) with enhancements:
- **Stats cards:** Total Queries, Failed Queries, API Cost Estimate, Avg Confidence
- **Charts** (use a lightweight library like `recharts`):
  - Queries over time (line chart, last 30 days)
  - Confidence distribution (bar chart)
  - Top 10 most asked questions (horizontal bar)
- **Failed queries log:** Table with pagination (same as reference)
- **Chat history browser:** Expandable log entries (same as reference)
- **Purge logs button**

### Task 7.6: Business Settings Page
`frontend/src/pages/business-admin/SettingsPage.jsx`:
- Edit business name, description, industry
- Upload logo (via Supabase Storage)
- Toggle: Require user login for chat
- Custom welcome message
- Custom system prompt (override default RAG prompt)
- Primary brand color
- Max chunks per query
- Confidence threshold slider
- **Danger zone:** Deactivate business, purge all data

---

### ✅ Phase 7 Testing Checklist

#### Manual Tests:
- [ ] Navigate to `/b/{slug}/admin` → Business admin dashboard loads
- [ ] Sidebar shows all 5 navigation items
- [ ] Admin Chat: Ask a question → get RAG-powered response with confidence score
- [ ] Admin Chat: Confidence color is correct (green > 0.3, orange > 0.15, red < 0.15)
- [ ] Emergency Alerts: Create an alert → appears in active list
- [ ] Emergency Alerts: Ask a question related to alert → alert content is prioritized in response
- [ ] Emergency Alerts: Remove alert → disappears from list
- [ ] Emergency Alerts: Purge cache → success message
- [ ] Analytics: Stats cards show correct numbers
- [ ] Analytics: Failed queries table shows low-confidence queries
- [ ] Analytics: Chat history shows paginated log entries
- [ ] Settings: Change welcome message → reflected in user chat portal
- [ ] Settings: Toggle "Require login" → user portal now requires auth
- [ ] Settings: Update brand color → user portal uses new color

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 7: Business Admin Dashboard (chat test, alerts, analytics, settings)"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 8.

---

# ============================================================
# PHASE 8: USER CHAT PORTAL
# ============================================================

## Objective
Build the public-facing chat interface where end users interact with the business's RAG chatbot. This is the equivalent of the reference project's `chat_ui.py` — but as a full React SPA with streaming responses.

### Task 8.1: Create `backend/app/api/chat.py`
Endpoints:
- `POST /api/chat/{business_slug}/message` — Send a message, get RAG response
  - Accept: `{ message: str, conversation_id?: str, session_id?: str }`
  - Return: `{ answer: str, confidence: float, sources: [], conversation_id: str }`
- `GET /api/chat/{business_slug}/stream` — SSE endpoint for streaming responses
  - Same input, but returns `text/event-stream` with token-by-token output
- `GET /api/chat/{business_slug}/conversations` — List user's conversations (if authenticated)
- `GET /api/chat/{business_slug}/conversations/{conv_id}/messages` — Get conversation history
- `GET /api/chat/{business_slug}/info` — Get business public info (name, welcome message, branding, login required)
- `GET /api/chat/{business_slug}/alerts` — Get active alerts for this business

### Task 8.2: Chat API Logic
```
User sends message →
  1. Validate business exists and is active (by slug)
  2. Check if login required (business settings) — if yes, validate JWT
  3. Check response cache (query_hash + business_id) — if hit, return cached
  4. Check active alerts — if any match query context, inject into prompt
  5. Load last 5 messages from conversation (if conversation_id provided)
  6. Search knowledge base (hybrid: semantic + keyword via search_knowledge function)
  7. Build RAG prompt with context + conversation history + alerts
  8. Call Azure OpenAI (streaming or non-streaming)
  9. Log message pair to chat_messages table
  10. Cache the response (24hr TTL)
  11. Return response
```

### Task 8.3: Create User Chat Portal (Frontend)
`frontend/src/pages/chat/ChatPortal.jsx`:

Route: `/b/:slug`

**Layout:**
- Full-screen chat layout (like ChatGPT/Claude UI)
- Business branding header (logo + name + custom color)
- Active alerts banner (red, dismissible per session)
- Chat messages area (scrollable, auto-scroll to bottom)
- Message input bar at bottom (textarea + send button)

**Features:**
- **Streaming responses:** Use `EventSource` API to display tokens as they arrive
- **Confidence indicator:** Small colored dot next to each response
- **Source citations:** "View Sources" button below response → expandable panel
- **Conversation history:** Sidebar (collapsible) showing past conversations (if logged in)
- **New conversation:** Button to start fresh thread
- **Welcome message:** Show business's custom welcome message on empty state
- **Responsive:** Works on mobile (sidebar hidden, chat takes full width)
- **Typing indicator:** Animated dots while waiting for response

> [!TIP]
> **Design for Chat Portal:**
> - Clean, minimal design (the business's content should be the focus)
> - Use the business's `primary_color` from settings for accents
> - User messages: Right-aligned, colored bubble
> - Assistant messages: Left-aligned, white/light bubble
> - Smooth message entry animation (fade-in + slide-up)
> - Input bar: Sticky at bottom, subtle shadow, auto-resize textarea
> - Show "Powered by RAG Factory" watermark at bottom (subtle)

### Task 8.4: Optional Auth Gate
If business settings have `user_login_required: true`:
- Show a login/signup form before the chat
- Use same Supabase Auth (shared auth system)
- Store `user_id` with messages for tracking
- If `user_login_required: false`:
  - Generate a random `session_id` (UUID stored in localStorage)
  - Associate messages with session_id for conversation continuity

### Task 8.5: Mobile Responsive Design
- Test and optimize for mobile viewport (<768px)
- Conversation sidebar becomes a slide-out drawer
- Input bar stays at bottom (above keyboard on mobile)
- Messages use smaller font on mobile

---

### ✅ Phase 8 Testing Checklist

#### Manual Tests:
- [ ] Navigate to `/b/{slug}` → Chat portal loads with business branding
- [ ] Welcome message displays on empty chat
- [ ] Type a question → response appears (based on ingested knowledge)
- [ ] Confidence score displays with correct color
- [ ] "View Sources" shows the source URLs used
- [ ] Create an emergency alert (via admin) → banner appears in chat portal
- [ ] Ask alert-related question → response prioritizes alert content
- [ ] Send multiple messages → conversation context is maintained
- [ ] Start new conversation → fresh thread, no old context
- [ ] If login required: unauthenticated user sees login form
- [ ] If login NOT required: anonymous user can chat freely
- [ ] Streaming: tokens appear one-by-one (not blocked until complete)
- [ ] Mobile: chat works on phone-width viewport
- [ ] Ask same question twice → second response is faster (cached)
- [ ] Ask question with no relevant knowledge → "I don't have enough information" response

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 8: User Chat Portal (streaming, conversations, alerts, responsive)"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 9.

---

# ============================================================
# PHASE 9: INTEGRATION TESTING & BUG FIXES
# ============================================================

## Objective
End-to-end testing of the complete flow from business creation to user chat. Fix all bugs discovered.

### Task 9.1: Full Integration Test Scenario

Execute this test script manually:

1. **Login as Super Admin** → Dashboard loads
2. **Create Business:** "Sydney Burgers" (industry: Restaurant)
3. **Navigate to Business Admin:** `/b/sydney-burgers/admin`
4. **Upload Knowledge:**
   - Upload a PDF (any test PDF with content)
   - Scrape a URL (any public restaurant menu page)
   - Verify chunks appear in Knowledge Base explorer
5. **Test Admin Chat:**
   - Ask: "What items are on the menu?" → should get relevant answer
   - Check confidence score is reasonable
6. **Create Emergency Alert:** "We are closed today due to renovations"
7. **Test User Portal:** Open `/b/sydney-burgers` in incognito window
   - Ask: "Are you open today?" → should mention the emergency alert
   - Ask: "What's on the menu?" → should use knowledge base
   - Verify sources are cited
8. **Check Analytics:** Go back to admin → analytics shows the queries
9. **Test another business:**
   - Create "UTS University" (industry: Education)
   - Upload different knowledge
   - Verify data isolation: UTS chat doesn't return Sydney Burgers content

### Task 9.2: Bug Fix Checklist
- [ ] No CORS errors in browser console
- [ ] No unhandled promise rejections
- [ ] Auth token is refreshed before expiry (Supabase auto-refresh)
- [ ] File uploads > 10MB work without timeout
- [ ] Unicode content in PDFs/web pages is handled correctly
- [ ] Empty knowledge base returns graceful "no info" message (not error)
- [ ] Deleting a business doesn't leave orphan data (CASCADE works)
- [ ] Concurrent uploads don't cause race conditions
- [ ] Browser back button works correctly with router

### Task 9.3: Performance Checks
- [ ] Knowledge base search responds in < 2 seconds
- [ ] Chat response (non-streaming) completes in < 5 seconds
- [ ] Dashboard with 100+ chunks loads in < 3 seconds
- [ ] No memory leaks in long chat sessions (check React DevTools)

---

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 9: Integration testing and bug fixes"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 10.

---

# ============================================================
# PHASE 10: EMBEDDABLE CHAT WIDGET
# ============================================================

## Objective
Create a JavaScript widget that businesses can embed on their own external websites to provide the RAG chatbot.

### Task 10.1: Create `widget/widget.js`
A standalone JavaScript file that:
1. Creates an iframe or shadow DOM container
2. Renders a chat bubble (floating button, bottom-right corner)
3. On click: Opens a chat panel (same UI as user portal, embedded)
4. Communicates with the RAG Factory API via business slug
5. Auto-detects business branding (color, welcome message) from API

### Task 10.2: Create Embed Code Generator
In Business Admin Settings, add a section:
```
📋 Embed Chat Widget on Your Website
Copy this code and paste it before the </body> tag:

<script src="https://your-domain.com/widget/widget.js" data-business="sydney-burgers"></script>
```

### Task 10.3: Widget Styling (`widget/widget.css`)
- Chat bubble: 60px circle, business primary color, chat icon, pulse animation
- Chat panel: 400px × 600px, fixed bottom-right, rounded corners, shadow
- Close button (X) in top-right of panel
- Same chat UI as user portal but compact

---

### ✅ Phase 10 Testing Checklist
- [ ] Include widget script in a simple HTML file → chat bubble appears
- [ ] Click bubble → chat panel opens
- [ ] Send message → gets RAG response from correct business
- [ ] Close panel → bubble returns to normal state
- [ ] Widget uses business brand color
- [ ] Multiple widgets on same page (different businesses) work independently

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 10: Embeddable chat widget"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 11.

---

# ============================================================
# PHASE 11: POLISH, ANIMATIONS & FINAL UI PASS
# ============================================================

## Objective
Final UI/UX polish pass — add micro-animations, loading states, error boundaries, and ensure visual consistency.

### Task 11.1: Loading States
- All pages: Show skeleton loader (Tailwind `animate-pulse`) while data loads
- File upload: Progress bar with percentage
- Chat: Typing indicator animation (3 bouncing dots)
- Business creation: Spinner inside submit button

### Task 11.2: Error Boundaries
- Create `ErrorBoundary.jsx` React component
- Wrap all page components
- Show friendly error message + "Retry" button
- Log errors to console (and optionally to a Supabase `error_logs` table)

### Task 11.3: Toast Notifications
- Create a toast component (bottom-right, auto-dismiss after 3s)
- Success: Green border, checkmark icon
- Error: Red border, X icon
- Info: Blue border, info icon
- Use for: CRUD operations, auth actions, ingestion completion

### Task 11.4: Micro-Animations (CSS)
- Page transitions: Fade-in (opacity 0→1, 200ms)
- Card hover: Lift + shadow (transform, box-shadow, 150ms)
- Button press: Scale down (transform: scale(0.98), 100ms)
- Sidebar nav: Active item slide indicator
- Chat messages: Slide-in from bottom (transform: translateY, 200ms)
- Modal: Backdrop fade + content scale-in

### Task 11.5: Accessibility Pass
- All interactive elements have proper `aria-label`
- Focus visible indicators (outline) on tab navigation
- Color contrast meets WCAG AA (check with browser DevTools)
- Form inputs have associated `<label>` elements

### Task 11.6: Responsive Final Check
Test all pages at these breakpoints:
- Desktop: 1440px, 1280px, 1024px
- Tablet: 768px
- Mobile: 375px, 320px

---

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 11: UI polish, animations, error handling, accessibility"
```

### 🛑 STOP — Wait for user confirmation before proceeding to Phase 12.

---

# ============================================================
# PHASE 12: DOCUMENTATION & DEPLOYMENT PREP
# ============================================================

## Objective
Write documentation, create production configs, and prepare for deployment.

### Task 12.1: Create `README.md`
Professional README with:
- Project overview + screenshots
- Architecture diagram (Mermaid)
- Tech stack table
- Getting Started guide (step by step)
- Environment variables reference
- API documentation link (FastAPI auto-generates this at `/docs`)
- Deployment guide (local + Oracle Linux VPS)
- Contributing guidelines

### Task 12.2: API Documentation
FastAPI auto-generates Swagger at `/docs` and ReDoc at `/redoc`.
- Add docstrings to all endpoints
- Add request/response examples in Pydantic models
- Group endpoints by tag (Auth, Super Admin, Business, Chat, Knowledge)

### Task 12.3: Production Configuration
Create `backend/app/config_prod.py`:
- HTTPS enforcement
- Rate limiting (per IP, per business)
- Logging configuration (structured JSON logs)
- CORS restricted to production domain

### Task 12.4: Docker Setup (Optional, for VPS)
Create `docker-compose.yml`:
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

Create `backend/Dockerfile` and `frontend/Dockerfile` (Nginx serving built React).

### Task 12.5: Health Check Endpoints
- `GET /api/health` — Basic health
- `GET /api/health/db` — Database connectivity
- `GET /api/health/llm` — Azure OpenAI connectivity
- `GET /api/health/storage` — Supabase Storage connectivity

---

### ✅ Phase 12 Testing Checklist
- [ ] README renders correctly on GitHub
- [ ] API docs accessible at `/docs` with all endpoints documented
- [ ] Health check endpoints pass (all return "healthy")
- [ ] (If Docker): `docker-compose up` starts both services

### 🔒 Git Backup
```bash
git add -A && git commit -m "Phase 12: Documentation, deployment prep, and Docker config"
```

### 🛑 STOP — Final review with user.

---

# ============================================================
# APPENDIX A: KEY DESIGN DECISIONS
# ============================================================

## Why pgvector over ChromaDB?
- ChromaDB runs as a separate process, needs its own data directory per tenant
- pgvector runs inside PostgreSQL (already have Supabase), zero additional infrastructure
- HNSW indexes in pgvector provide fast approximate nearest neighbor search
- Full-text search (BM25) is native to PostgreSQL — enables hybrid search
- RLS (Row Level Security) provides automatic multi-tenant data isolation
- Backups, scaling, and replication are handled by Supabase

## Why React + Vite over Streamlit?
- Streamlit cannot handle multiple tenants/routes in a single app
- Streamlit has limited control over styling, layout, and navigation
- React provides full SPA routing (Super Admin ↔ Business Admin ↔ User Chat)
- Vite is the fastest build tool for React, with HMR (Hot Module Replacement)
- shadcn/ui-inspired components give a premium, customizable look

## Why SSE Streaming?
- WebSockets are overkill for one-directional token streaming
- SSE (Server-Sent Events) is simpler, works with HTTP/2, auto-reconnects
- FastAPI supports SSE natively via `sse-starlette` package
- Frontend uses standard `EventSource` API (no library needed)

## Why Hybrid Search (Semantic + Keyword)?
- Pure semantic search misses exact keyword matches (e.g., filename "Profile.pdf")
- Pure keyword search misses semantic similarity (e.g., "exam dates" → "assessment schedule")
- Combining 70% semantic + 30% keyword score gives best-of-both-worlds
- The reference project only used semantic search — this is a key accuracy improvement

---

# ============================================================
# APPENDIX B: ENVIRONMENT SETUP REFERENCE
# ============================================================

## Required API Keys & Services
| Service | Where to Get | Free Tier? |
|---|---|---|
| Supabase | [supabase.com](https://supabase.com) | ✅ Yes (generous) |
| Azure OpenAI | [Azure Portal](https://portal.azure.com) | ❌ (Student credits work) |
| Jina Reader | No key needed (free API) | ✅ Yes |
| Tesseract OCR | System install | ✅ Yes (open source) |

## System Requirements
- Python 3.10+
- Node.js 18+
- Git
- Tesseract OCR (for scanned PDF support)
  - Windows: [Install from GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt-get install tesseract-ocr`
  - Mac: `brew install tesseract`

---

# ============================================================
# APPENDIX C: CURSOR AI SPECIFIC TIPS
# ============================================================

## Recommended Cursor Settings for This Project:
1. **MCP Servers:**
   - Add Supabase MCP: `npx -y @supabase/mcp-server-supabase@latest` (for DB migrations)
   - This lets you run SQL migrations directly from Cursor

2. **Context Management:**
   - Use `@codebase` when asking about cross-module dependencies
   - Use `@file` to reference specific files when porting from the reference project
   - Use `@web` to look up PostgreSQL/pgvector syntax if unsure
   - Pin `backend/app/config.py` and `backend/app/dependencies.py` as always-open files

3. **Composer Usage:**
   - Use Composer (Ctrl+I) for multi-file edits within a phase
   - For each phase, start a new Composer session with this context:
     ```
     @STEPS.md (the relevant phase section)
     @file backend/app/config.py
     @file backend/app/dependencies.py
     ```

4. **Debugging Tips:**
   - FastAPI errors: Check the terminal running `uvicorn` for tracebacks
   - React errors: Check browser DevTools console
   - Supabase RLS errors: Test queries in Supabase SQL Editor with `SET ROLE authenticated; SET request.jwt.claims = '{"sub":"user-id"}';`
   - pgvector errors: Make sure embedding dimensions match (1536 for text-embedding-3-small)

5. **Code Style:**
   - Python: Use type hints everywhere, async where possible
   - React: Functional components only, hooks for state
   - CSS: Tailwind utility classes, custom CSS only for animations
   - Naming: snake_case for Python, camelCase for JavaScript, kebab-case for CSS classes
