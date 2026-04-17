-- Private uploads bucket for PDF / text / markdown (STEPS.md Task 1.6)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'uploads',
    'uploads',
    FALSE,
    52428800,
    ARRAY['application/pdf', 'text/plain', 'text/markdown']::text[]
)
ON CONFLICT (id) DO NOTHING;
