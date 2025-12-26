-- Supabase Database Setup for Face Recognition App
-- Run this SQL in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)

-- Enable pgvector extension for face embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    phone TEXT,
    date_of_birth DATE,
    emergency_contact JSONB,
    medications JSONB,
    allergies TEXT[],
    accessibility_needs TEXT,
    preferred_language TEXT DEFAULT 'English',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User images table
CREATE TABLE IF NOT EXISTS public.user_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    public_url TEXT,
    width INTEGER,
    height INTEGER,
    mime_type TEXT DEFAULT 'image/jpeg',
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_profile BOOLEAN DEFAULT FALSE,
    file_size INTEGER
);

-- Embeddings table for face recognition (float8[] fallback)
CREATE TABLE IF NOT EXISTS public.embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    embedding double precision[],
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note: This schema uses PostgreSQL arrays for embeddings so it works
-- without the pgvector extension. For production / large datasets you
-- should enable pgvector and convert `embedding` to `vector(128)` and
-- create an appropriate index.

-- Nearest-neighbour function for pgvector (L2)
CREATE OR REPLACE FUNCTION public.find_nearest_embeddings(
  query_embedding vector,
  match_limit INT DEFAULT 1
)
RETURNS TABLE (
  embedding_id UUID,
  user_id UUID,
  dist FLOAT
)
LANGUAGE SQL
AS $$
  SELECT id, user_id, (embedding <-> query_embedding) AS dist
  FROM public.embeddings
  ORDER BY embedding <-> query_embedding
  LIMIT match_limit;
$$;

-- Enable Row Level Security (RLS)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.embeddings ENABLE ROW LEVEL SECURITY;

-- Create policies for service role (backend has full access)
CREATE POLICY "Service role has full access to users" ON public.users
    FOR ALL USING (true);

CREATE POLICY "Service role has full access to user_images" ON public.user_images
    FOR ALL USING (true);

CREATE POLICY "Service role has full access to embeddings" ON public.embeddings
    FOR ALL USING (true);

-- Grant permissions
GRANT ALL ON public.users TO service_role;
GRANT ALL ON public.user_images TO service_role;
GRANT ALL ON public.embeddings TO service_role;
GRANT EXECUTE ON FUNCTION public.find_nearest_embeddings TO service_role;

-- Create storage bucket (run this separately if needed)
-- Go to Storage in Supabase dashboard and create a bucket named: face_oftheusers
-- Make it private (not public)
