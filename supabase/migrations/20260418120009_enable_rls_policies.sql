-- Enable RLS on all tenant tables
ALTER TABLE public.businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.response_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- ===== BUSINESSES =====
CREATE POLICY "Super admins can manage all businesses"
    ON public.businesses FOR ALL
    USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND is_super_admin = TRUE)
    );

CREATE POLICY "Members can view their businesses"
    ON public.businesses FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.business_members WHERE business_id = id AND user_id = auth.uid())
    );

-- ===== KNOWLEDGE CHUNKS =====
CREATE POLICY "Business admins manage knowledge"
    ON public.knowledge_chunks FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.business_members
            WHERE business_id = knowledge_chunks.business_id
              AND user_id = auth.uid()
              AND role IN ('admin', 'super_admin')
        )
    );

CREATE POLICY "Public can read knowledge for active businesses"
    ON public.knowledge_chunks FOR SELECT
    USING (
        EXISTS (SELECT 1 FROM public.businesses WHERE id = knowledge_chunks.business_id AND is_active = TRUE)
    );

-- ===== CHAT MESSAGES =====
CREATE POLICY "Admins view business chats"
    ON public.chat_messages FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.business_members
            WHERE business_id = chat_messages.business_id
              AND user_id = auth.uid()
              AND role IN ('admin', 'super_admin')
        )
    );

CREATE POLICY "Anyone can insert chat messages"
    ON public.chat_messages FOR INSERT
    WITH CHECK (TRUE);

-- ===== ALERTS =====
CREATE POLICY "Admins manage alerts"
    ON public.alerts FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.business_members
            WHERE business_id = alerts.business_id
              AND user_id = auth.uid()
              AND role IN ('admin', 'super_admin')
        )
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
        EXISTS (
            SELECT 1 FROM public.business_members
            WHERE business_id = response_cache.business_id
              AND user_id = auth.uid()
        )
    );
