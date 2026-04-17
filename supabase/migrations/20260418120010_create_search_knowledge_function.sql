-- Hybrid search: semantic (vector) + keyword (full-text)
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
          AND kc.embedding IS NOT NULL
          AND 1 - (kc.embedding <=> p_query_embedding) > p_similarity_threshold
        ORDER BY kc.embedding <=> p_query_embedding
        LIMIT p_match_count * 2
    ),
    keyword AS (
        SELECT
            kc.id,
            ts_rank_cd(kc.fts, websearch_to_tsquery('english', p_query_text)) AS rank
        FROM public.knowledge_chunks kc
        WHERE kc.business_id = p_business_id
          AND p_query_text <> ''
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
        (s.similarity * 0.7 + COALESCE(k.rank, 0) * 0.3)::FLOAT AS combined_score
    FROM semantic s
    LEFT JOIN keyword k ON s.id = k.id
    ORDER BY (s.similarity * 0.7 + COALESCE(k.rank, 0) * 0.3) DESC
    LIMIT p_match_count;
END;
$$;
