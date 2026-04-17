-- Chat messages: Individual messages within a conversation
CREATE TABLE public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES public.businesses(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    confidence FLOAT,
    sources JSONB,
    token_count INTEGER DEFAULT 0,
    is_failed BOOLEAN DEFAULT FALSE,
    feedback_rating INTEGER CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON public.chat_messages(conversation_id);
CREATE INDEX idx_messages_business ON public.chat_messages(business_id);
CREATE INDEX idx_messages_failed ON public.chat_messages(business_id, is_failed) WHERE is_failed = TRUE;
