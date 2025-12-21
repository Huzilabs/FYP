-- Supabase / Postgres schema for Face Recognition (pgvector)
-- Paste this into the Supabase SQL editor and run.

-- 1) Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector

-- 2) Users table (normalized user metadata)
CREATE TABLE IF NOT EXISTS public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name TEXT NOT NULL,            -- human-friendly name (the 'name' field)
  username TEXT UNIQUE NOT NULL,         -- stable machine id / slug (optional)
  email TEXT,                             -- optional
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen TIMESTAMPTZ
);

-- 3) Images table (store metadata about images uploaded to Storage)
CREATE TABLE IF NOT EXISTS public.user_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,            -- path inside Supabase Storage (e.g. users/<user_id>/12345.jpg)
  public_url TEXT,                       -- optional cached public URL
  width INTEGER,
  height INTEGER,
  mime_type TEXT,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4) Embeddings table (pgvector column) - normalized: multiple embeddings per user allowed
CREATE TABLE IF NOT EXISTS public.embeddings (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  embedding VECTOR(128) NOT NULL,
  source TEXT,                -- optional (e.g. 'webapp_signup' or 'migration')
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- 6) Indexes for fast vector search (ivfflat with L2 distance)
-- Tune 'lists' parameter based on dataset size (100 is a reasonable default for medium datasets)
CREATE INDEX IF NOT EXISTS idx_embeddings_embedding_ivfflat
  ON public.embeddings USING ivfflat (embedding vector_l2_ops)
  WITH (lists = 100);

-- Optional: a composite index for recently created embeddings per user
CREATE INDEX IF NOT EXISTS idx_embeddings_user_created
  ON public.embeddings (user_id, created_at DESC);

-- 7) Convenience function to find nearest neighbors (returns id, user_id, distance)
-- Uses the '<->' operator (L2 distance) provided by pgvector
CREATE OR REPLACE FUNCTION public.find_nearest_embeddings(q VECTOR(128), limit_count INT DEFAULT 5)
RETURNS TABLE (embedding_id BIGINT, user_id UUID, dist DOUBLE PRECISION, created_at TIMESTAMPTZ) AS $$
  SELECT id, user_id, (embedding <-> q) AS dist, created_at
  FROM public.embeddings
  ORDER BY embedding <-> q
  LIMIT limit_count;
$$ LANGUAGE sql STABLE;

-- 8) Example SQL for inserting a user and an embedding (use in SQL editor or raw SQL)
-- Replace the ARRAY[...] with the comma-separated 128 floats from your embedding.
-- Example: INSERT INTO public.embeddings (user_id, embedding) VALUES ('<user-uuid>', ARRAY[0.123, -0.234, ...]::vector);

-- Create a sample user (change values as needed)
-- INSERT INTO public.users (username, display_name, email) VALUES ('alice','Alice Example','alice@example.com');

-- Example: insert embedding for a specific user (use the user's id from the users table)
-- INSERT INTO public.embeddings (user_id, embedding, source) VALUES (
--   '<user-uuid>', ARRAY[0.01, 0.02, ... , -0.03]::vector, 'migration'
-- );

-- 9) Permissions / Grants (suggested minimal grants; adjust for your needs)
-- By default Supabase manages roles; you can add grants for admin/service roles if necessary.
-- GRANT SELECT ON public.users TO anon;
-- GRANT EXECUTE ON FUNCTION public.find_nearest_embeddings TO anon;

-- 10) Notes on normalization and design decisions
--  - Users are stored in a dedicated `users` table and referenced by UUID in other tables.
--  - Embeddings are stored separately to allow multiple captures per user, auditing, and deletion cascade.
--  - Images are stored in Storage; `user_images` keeps metadata and a convenient link to the object path.

-- After running this DDL, you can use the supplied migration script to insert rows and upload images.
