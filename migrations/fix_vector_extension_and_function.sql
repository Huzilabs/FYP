-- Migration: move pgvector (vector) extension into dedicated schema and fix function
-- Run this in Supabase SQL editor as a single transaction (requires sufficient privileges).
-- This script is idempotent and safe to re-run.

BEGIN;

-- 1) Create a dedicated schema for extension objects
CREATE SCHEMA IF NOT EXISTS vector_ext;

-- 2) If the vector extension does not exist, create it inside pg_ext
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA vector_ext';
  END IF;
END$$;

-- 3) If the vector extension currently exists in a different schema, move it into pg_ext
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
    -- safe ALTER EXTENSION will move types/operators into vector_ext
    EXECUTE 'ALTER EXTENSION vector SET SCHEMA vector_ext';
  END IF;
END$$;

-- 4) Recreate the helper function with an explicit search_path and schema-qualified vector type
--    This avoids role-mutable search_path vulnerabilities by forcing operator/type resolution
CREATE OR REPLACE FUNCTION public.find_nearest_embeddings(
  q vector_ext.vector(128),
  limit_count integer DEFAULT 5
)
RETURNS TABLE (embedding_id bigint, user_id uuid, dist double precision, created_at timestamptz)
LANGUAGE sql
STABLE
SET search_path = vector_ext, public
AS $$
  SELECT id, user_id, (embedding <-> q) AS dist, created_at
  FROM public.embeddings
  ORDER BY embedding <-> q
  LIMIT limit_count;
$$;

-- 5) Conditionally alter the embeddings.embedding column type if it still references public.vector
DO $$
DECLARE
  vec_schema text;
  col_type_oid oid;
BEGIN
  -- find current schema of the 'vector' type (if present)
  SELECT n.nspname INTO vec_schema
  FROM pg_type t
  JOIN pg_namespace n ON t.typnamespace = n.oid
  WHERE t.typname = 'vector'
  LIMIT 1;

  -- if vector type exists and is defined in 'public', migrate column type to pg_ext.vector
  IF vec_schema = 'public' THEN
    -- change column type to vector_ext.vector(128)
    EXECUTE 'ALTER TABLE public.embeddings ALTER COLUMN embedding TYPE vector_ext.vector(128) USING embedding::vector_ext.vector';
  END IF;
EXCEPTION WHEN OTHERS THEN
  -- log and continue (this prevents the migration from failing in environments where column is already correct)
  RAISE NOTICE 'Warning: conditional column migration step encountered an issue: %', SQLERRM;
END$$;

COMMIT;

-- 6) Verification queries (run manually after migration if you want):
-- SELECT extname, nspname FROM pg_extension JOIN pg_namespace ON pg_extension.extnamespace = pg_namespace.oid;
-- SELECT nspname, typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE typname='vector';
-- SELECT * FROM public.find_nearest_embeddings(ARRAY[0.0,0.0,0.0 /* ... 128 floats ... */]::pg_ext.vector, 1);
