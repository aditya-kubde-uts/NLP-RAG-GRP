# 🏭 RAG Factory — Multi-Tenant RAG Platform Implementation Guide

## Project Overview

Welcome to the **RAG Factory** project! Our goal here is to build a scalable, multi-tenant SaaS platform where an administrative team can effortlessly spin up, customize, and manage independent Retrieval-Augmented Generation (RAG) chatbots for different business clients. 

Imagine a scenario where a university ("UTS") needs a bot to answer student queries from handbooks, and a restaurant needs a different bot to answer questions about its menu and opening hours. Instead of deploying separate codebases for each, RAG Factory will serve as a central "command center". 

**Key Features:**
- **Super Admin Dashboard:** A top-level view to onboard new businesses, track API usage, and manage platform-wide analytics.
- **Business Admin Portals:** A dedicated space for each business to upload their own unique PDFs or web links, monitor chat logs, and broadcast emergency alerts to their users.
- **User Chat Portals:** The public or authenticated interface where end-users actually converse with the chatbots.
- **Embeddable Widgets:** Small JavaScript snippets allowing the chatbot to be easily embedded directly into the business's own external website.

We are upgrading our architecture from a single-tenant local prototype to a robust cloud-ready product. We'll be using **FastAPI** for a performant backend, a **React/Vite** Single Page Application for a smooth administrative experience, and **Supabase (PostgreSQL with pgvector)** to handle true multi-tenant data isolation and hybrid semantic search. We will continue using **Azure OpenAI** as our core language model provider.

This document breaks down the entire development lifecycle into structured, testable phases. Let's get building!

---

## 📐 Architecture Overview

```text
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

## 🎯 Target Improvements Over Prototype V1

| Area | V1 | RAG Factory (V2) |
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
> We will use **Tailwind CSS v4** (via Vite plugin) + custom components inspired by shadcn/ui patterns.
> Build reusable components manually to keep the bundle small and debugging straightforward.

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

### Phase 0 Checklist
- [ ] `cd backend && python -c "import fastapi; print(fastapi.__version__)"` prints a version
- [ ] `cd backend && python -c "import openai; print('Azure OpenAI SDK OK')"` runs with no errors
- [ ] `cd frontend && npm run dev` successfully starts the Vite dev server on `http://localhost:5173`
- [ ] `.gitignore` is working (no `node_modules/` or `venv/` tracked)

---

# ============================================================
# PHASE 1: SUPABASE PROJECT SETUP & DATABASE SCHEMA
# ============================================================

## Objective
Create the Supabase project, enable pgvector, define all tables with Row-Level Security (RLS), and configure authentication.

### Task 1.1: Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Select an appropriate region.
3. Save the project URL, anon key, and service role key to `backend/.env` and `frontend/.env`.
4. Go to **Settings > Database** and copy the connection string to `DATABASE_URL` in `backend/.env`.

### Task 1.2: Enable pgvector Extension
Run this SQL in Supabase SQL Editor:
```sql
-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;
```

### Task 1.3: Create Database Schema

Run the following migrations using the Supabase SQL Editor or migration CLI:

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
2. Click "Add User" → enter an email and password.
3. Then mark them as super admin:
```sql
UPDATE public.user_profiles SET is_super_admin = TRUE WHERE email = 'YOUR_EMAIL_HERE';
```

---

### Phase 1 Checklist
- [ ] All migrations applied successfully (verify in Supabase Dashboard > Database > Tables).
- [ ] The `vector` extension is active.
- [ ] RLS policies are enabled on all tables.
- [ ] `search_knowledge` function exists and runs without error.
- [ ] Storage bucket `uploads` is properly configured.
- [ ] Base Super Admin user account is set up.

---

# ============================================================
# PHASE 2: BACKEND FOUNDATION (FastAPI + Supabase Integration)
# ============================================================

## Objective
Build the FastAPI application skeleton with the Supabase client, environment config, CORS, health check endpoints, and authentication middleware.

### Task 2.1: Create `backend/app/config.py`
Set up environment configuration using Pydantic Settings so the app safely parses `.env` variables.
- Include definitions for Supabase URLs and Keys.
- Include definitions for Azure OpenAI variables.

### Task 2.2: Create `backend/app/db/supabase_client.py`
Instantiate two clients:
- A regular client using the Anon key (for operations where RLS applies).
- A Service Role client for backend-only operations that need to bypass RLS.

### Task 2.3: Create `backend/app/dependencies.py`
Set up dependency injection functions for FastAPI endpoints:
- Validate JWTs arriving from headers using Supabase Auth.
- Create specific checks ensuring certain routes can only be accessed by Super Admins or Business Admins.

### Task 2.4: Create `backend/app/main.py`
- Initialize the FastAPI application.
- Set up CORS middleware allowing your frontend domain.
- Create a basic `/api/health` endpoint.
- Prepare comments or placeholders for future route inclusions.

---

### Phase 2 Checklist
- [ ] Command `uvicorn app.main:app --reload --port 8000` starts the server without errors.
- [ ] `GET http://localhost:8000/api/health` returns a healthy status.
- [ ] `.env` configurations load appropriately via Pydantic.

---

# ============================================================
# PHASE 3: AUTHENTICATION SYSTEM
# ============================================================

## Objective
Build auth API routes (signup, login, profile) and wire up the React frontend auth flow with protected routes.

### Task 3.1: Create `backend/app/api/auth.py`
Define the backend proxies for:
- Signups and Logins
- Fetching user profiles via the session token
- Logouts
These will interact heavily with Supabase's Auth endpoints.

### Task 3.2: Create `backend/app/models/auth.py`
Define Pydantic schemas validating expected `SignupRequest`, `LoginRequest`, and `UserProfile` response shapes.

### Task 3.3: Create Frontend Auth Context (`frontend/src/context/AuthContext.jsx`)
- Initialize the Supabase JS client.
- Provide user context throughout the app based on `onAuthStateChange`.
- Expose methods to sign in, out, and register.

### Task 3.4: Create Frontend Auth Pages
Build the UI:
- `frontend/src/pages/auth/LoginPage.jsx`
- `frontend/src/pages/auth/SignupPage.jsx`
Implement a modern design standard (e.g., glassmorphism, appropriate visual hierarchy).

### Task 3.5: Create Protected Route Wrapper
Provide a `ProtectedRoute.jsx` component that wraps specific React-Router views, ejecting users to the login page if they lack valid credentials or roles.

### Task 3.6: Set Up React Router in `frontend/src/App.jsx`
Establish routes for login, signup, super-admin, business-admin, and user chat portals.

---

### Phase 3 Checklist
- [ ] Registering a test user successfully updates Supabase Auth and triggers a row creation in `user_profiles`.
- [ ] Frontend can login to that test user and navigate naturally to a placeholder dashboard page.
- [ ] Unauthorized attempts to reach protected views redirect back to the login screen.

---

# ============================================================
# PHASE 4: SUPER ADMIN DASHBOARD — BUSINESS MANAGEMENT
# ============================================================

## Objective
Build the "command center" dashboard restricting to users marked as `is_super_admin`, allowing them to organize all sub-businesses.

### Task 4.1: Create APIs in `backend/app/api/super_admin.py`
Provide endpoints for CRUD operations on the `businesses` table, assigning admins, and calculating platform-wide totals.

### Task 4.2: Create Pydantic Models in `backend/app/models/business.py`
Ensure solid validation for incoming payload shapes when creating or updating organizations.

### Task 4.3: Implement Frontend Pages
- `DashboardPage.jsx`: Top stats bar, responsive grid of managed businesses, inline CRUD actions.
- `CreateBusinessPage.jsx`: Standardized intake form capturing Name, Industry, branding configurations and initial RAG rules.

### Task 4.4: Create Sidebar Layout Component
Provide a clean `DashboardLayout.jsx` with persistent sidebar navigation.

---

### Phase 4 Checklist
- [ ] The Super Admin view populates with functional widgets measuring system state.
- [ ] Creating a new business successfully reflects within both the dashboard and the database.
- [ ] "Delete" functionality cascades effectively or flags `is_active` correctly.
- [ ] Ordinary users cannot access this dashboard.

---

# ============================================================
# PHASE 5: RAG ENGINE CORE
# ============================================================

## Objective
Develop the intelligent pipeline parsing files, chunking data, vectorizing context, and orchestrating responses via Azure OpenAI.

### Task 5.1: Create `backend/app/core/llm_router.py`
Define a wrapper connecting exclusively to the `openai.AzureOpenAI` client. Include backoff logic, token counting, and methods capable of operating fully asynchronously in Python.

### Task 5.2: Create `backend/app/core/text_cleaner.py`
Establish noise-removal logic (filtering headers, footers, ad placeholders). Accommodate different industries (e.g., removing standard restaurant menu boilerplate vs legal disclaimers).

### Task 5.3: Create `backend/app/core/pdf_parser.py`
Implement `pymupdf4llm` to process documents optimally to Markdown. Standardize OCR fallback approaches using tools like Tesseract.

### Task 5.4: Create `backend/app/core/scraper.py`
Build out the web-scraping logic. Maintain strict timeout safety, structured formatting goals, and simple error handling.

### Task 5.5: Create `backend/app/core/chunker.py`
Implement `RecursiveCharacterTextSplitter`. Include concurrent LLM enrichment where an asynchronous call asks the AI to 10-word summarize every chunk (benefitting later hybrid searches).

### Task 5.6: Create `backend/app/core/ingestor.py`
Script the pipeline that takes finalized chunks, runs them through the embedder, and `INSERT`s them directly to the `knowledge_chunks` pgvector table.

### Task 5.7: Create `backend/app/core/searcher.py`
Define python methods to utilize your hybrid Postgres `search_knowledge` SQL function.

### Task 5.8: Create `backend/app/core/rag_brain.py`
Build the final prompt-crafting engine taking context, alerts, business-specific settings, and multi-turn history to supply the main response request.

---

### Phase 5 Checklist
- [ ] Core ingestion scripts behave as expected natively in Python, successfully loading data into pgvector.
- [ ] Hybrid search can fetch results appropriately.
- [ ] The RAG script operates properly alongside mock prompts.

---

# ============================================================
# PHASE 6: KNOWLEDGE BASE MANAGEMENT API + UI
# ============================================================

## Objective
Enable Business Admins to curate their knowledge base sources through an interactive UI.

### Task 6.1: Complete Endpoints in `backend/app/api/knowledge.py`
Support file uploads (saving correctly to Supabase bucket), web scraping calls, chunk retrieval/editing routines, and batch removal actions.

### Task 6.2: Build the `KnowledgeBasePage.jsx` React Component
Build a powerful portal supporting:
- Drag-and-drop ingestion paired with manual URL inputs.
- Source explorers returning interactive table lists.
- Inline Markdown-friendly chunk editors allowing text cleanup.

---

### Phase 6 Checklist
- [ ] Front-to-back testing of an uploaded PDF returns organized chunks in the business's database profile.
- [ ] URL processing is fully functional.
- [ ] Chunks can be successfully individually pruned or batch deleted.

---

# ============================================================
# PHASE 7: BUSINESS ADMIN DASHBOARD
# ============================================================

## Objective
Equip businesses with monitoring and analytics capabilities.

### Task 7.1: Build `backend/app/api/business_admin.py`
Create pathways for updating core business behavior settings, purging caches, and extracting usage analytics across chat histories.

### Task 7.2: Develop Business Admin Component Collection
Build dedicated pages in the `business-admin` route for:
- Chat Debugging (Simulating requests and viewing confidence indicators directly).
- Actioning Emergency Alerts.
- Evaluating Analytical statistics like "Most Asked Questions" and usage metrics over time.
- Customizing global business settings including primary brand colors and behavior profiles.

---

### Phase 7 Checklist
- [ ] Emergency Alerts correctly route responses in test simulations.
- [ ] Analytics graphs populate based on dummy message data.
- [ ] Changes to brand configurations correctly update database rules.

---

# ============================================================
# PHASE 8: USER CHAT PORTAL
# ============================================================

## Objective
Develop the end-user public chat implementation matching respective business branding and functionality rules.

### Task 8.1: Construct `backend/app/api/chat.py`
Ensure Chat routes are properly mapped and include robust features like the Server-Sent Event (SSE) model for token-by-token response streaming.

### Task 8.2: Build the Chat API Lifecycle Pipeline
Connect the entire workflow: Verify business active state -> optionally validate Session/JWT Auth -> test Cache hit -> run Semantic/Keyword search context builder -> Stream response out and log results natively.

### Task 8.3: Construct the Chat UI Panel
Model `ChatPortal.jsx` similar to leading AI chatbots but inheriting visual aesthetics from the specific database entry (Business color configurations, dynamically populated Welcome messaging, etc.). Establish logic handling threaded conversations natively in history sidebars.

---

### Phase 8 Checklist
- [ ] Chat responds accurately based on context injected from the business's specific RLS-isolated chunk data.
- [ ] Token streaming presents a smooth and stable UI visual.
- [ ] Optional auth gating rules appropriately trap or permit external visitors.

---

# ============================================================
# PHASE 9: INTEGRATION & BUG FIXING
# ============================================================

## Objective
End-to-End stress testing and ensuring the production-ready state of the environment.

### Task 9.1: Comprehensive End-to-End Audit
Have team members step through the process: Login -> Make Business -> Populate Business Sandbox -> Make user queries matching edge cases -> Analyze dashboard reporting results.

### Task 9.2: Technical Cleanups
Resolve any noted console errors, manage memory handling for long-running context chains in the frontend widget UI, ensure browser history tracking handles SPA routing beautifully, and optimize initial render speeds over CORS.

---

# ============================================================
# PHASE 10: EMBEDDABLE CHAT WIDGET
# ============================================================

## Objective
Distribute the application logically so client platforms can place RAG chatbots directly on their own landing properties.

### Task 10.1: Assemble `widget.js` and `widget.css`
Formulate a lightweight standalone script targeting `<div id="chat-widget">` objects, mounting a styled chat bubble that spawns an iframe or shadow-dom communication link back to the FastAPI instance endpoints.

### Task 10.2: Provide Generator Toolkit
Include logic inside the Business Admin to automatically populate accurate HTML snippet generation strings so businesses easily implement integration codes.

---

# ============================================================
# PHASE 11: UI POLISHING
# ============================================================

## Objective
Refine the UX experience targeting optimal visual flow.

### Task 11.1: Standardize Load states & Error Boundaries
Deploy comprehensive skeleton loaders, reliable retry boundaries for unexpected faults, and clean user-notification toast messaging for API events (both successes and failures).

### Task 11.2: Polish Micro-Animations and Accessibility (a11y)
Add transition lifecycles on modals, hover feedback on components, and complete a deep WCAG accessibility scan ensuring navigation outlines and contrast standards are optimal throughout.

---

# ============================================================
# PHASE 12: DOCUMENTATION DEPLOYMENT STANDARDS
# ============================================================

## Objective
Prepare to host and maintain the implementation effectively.

### Task 12.1: Finalize README Architecture Plans
Document environment builds, architecture graphs, and developer contribution setups strictly.

### Task 12.2: Establish API documentation and Prod Environments
Ensure FastAPI's automatic swagger endpoints represent actual payload assumptions properly. Formulate production restriction configurations for rate limits to prevent exploitation, finalize Docker deployment blueprints or CI/CD runner workflows.

---

Great work! Completing these stages correctly delivers a highly capable framework positioned powerfully for external cloud deployments and robust scaling.
