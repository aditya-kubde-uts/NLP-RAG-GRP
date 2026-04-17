-- Response cache: Caches frequent questions to save API costs
CREATE TABLE public.response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    query_hash TEXT NOT NULL,
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
