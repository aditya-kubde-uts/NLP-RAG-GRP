-- Knowledge chunks: The RAG vector store (pgvector)
-- Using 1536 dimensions for Azure text-embedding-3-small
CREATE TABLE public.knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    title TEXT,
    source_url TEXT,
    source_type TEXT DEFAULT 'manual',
    department TEXT DEFAULT 'General',
    llm_summary TEXT,
    metadata JSONB DEFAULT '{}',
    content_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_business ON public.knowledge_chunks(business_id);
CREATE INDEX idx_knowledge_hash ON public.knowledge_chunks(content_hash);

CREATE INDEX idx_knowledge_embedding ON public.knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

ALTER TABLE public.knowledge_chunks ADD COLUMN fts tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, '') || ' ' || coalesce(title, ''))) STORED;

CREATE INDEX idx_knowledge_fts ON public.knowledge_chunks USING gin(fts);
