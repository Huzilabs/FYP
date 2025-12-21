-- Migration: add user profile fields (idempotent)
-- Run in Supabase SQL editor or via psql using a secure service_role key.

BEGIN;

-- Add owner_id and user profile fields to public.users
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS owner_id uuid,
  ADD COLUMN IF NOT EXISTS phone text,
  ADD COLUMN IF NOT EXISTS date_of_birth date,
  ADD COLUMN IF NOT EXISTS emergency_contact jsonb,
  ADD COLUMN IF NOT EXISTS medications jsonb,
  ADD COLUMN IF NOT EXISTS allergies text[],
  ADD COLUMN IF NOT EXISTS accessibility_needs text,
  ADD COLUMN IF NOT EXISTS preferred_language text,
  ADD COLUMN IF NOT EXISTS verified boolean DEFAULT false;

-- Add image metadata fields to public.user_images
ALTER TABLE public.user_images
  ADD COLUMN IF NOT EXISTS is_profile boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS file_size bigint;

COMMIT;
