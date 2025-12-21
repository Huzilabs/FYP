-- Migration: drop attendance_log table (idempotent)
-- Run this in Supabase SQL editor or via psql using a secure service_role key.

BEGIN;

-- Safe drop; will do nothing if the table doesn't exist
DROP TABLE IF EXISTS public.attendance_log;

-- If you know there are dependent objects you intend to remove, use CASCADE instead:
-- DROP TABLE IF EXISTS public.attendance_log CASCADE;

COMMIT;
