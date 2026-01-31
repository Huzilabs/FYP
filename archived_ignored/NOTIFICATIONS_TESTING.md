# Medication Notifications — Live Testing Guide

This document explains how to test the notification flow locally and on Railway without deploying the scheduler permanently. It includes SQL for the extra tables, quick test commands, SSE test steps, and cleanup commands.

Prerequisites

- `SUPABASE_DB_URL` or `DATABASE_URL` set and reachable from where you run tests.
- `webapp_new.py` can run locally (`python webapp_new.py`) and exposes SSE endpoint `/api/users/<user_id>/notifications/stream`.
- A test user exists or you can insert one using the SQL below.

New tables required (create once)
-- Deduplication log

```sql
CREATE TABLE IF NOT EXISTS public.medication_notifications_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_medication_id uuid NOT NULL,
  scheduled_date date NOT NULL,
  scheduled_time text NOT NULL,
  sent_at timestamptz NOT NULL DEFAULT now(),
  channel text,
  UNIQUE (user_medication_id, scheduled_date, scheduled_time)
);
```

-- Per-user notifications table (frontend reads this / SSE streams from it)

```sql
CREATE TABLE IF NOT EXISTS public.user_notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  title text NOT NULL,
  body text,
  payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  delivered boolean NOT NULL DEFAULT FALSE,
  read_at timestamptz NULL
);
CREATE INDEX IF NOT EXISTS idx_user_notifications_user_delivered ON public.user_notifications (user_id, delivered, created_at DESC);
```

Quick local test (no scheduler)

1. Start the backend locally:

```bash
conda activate face-recognition-project
python webapp_new.py
```

2. Create a test user (run in psql or your DB console):

```sql
INSERT INTO public.users (id, username, display_name, email) VALUES ('00000000-0000-0000-0000-000000000001', 'testuser', 'Test User', 'test@example.com')
ON CONFLICT (username) DO NOTHING;
```

3. Manually insert a `user_notifications` row for that user (this simulates the scheduler creating a notification):

```sql
INSERT INTO public.user_notifications (user_id, title, body, payload)
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Reminder', 'Take your morning medication', jsonb_build_object('med_id','abc','slot','morning'));
```

4. Open an SSE client to verify delivery (in a browser connect EventSource to `http://127.0.0.1:5000/api/users/00000000-0000-0000-0000-000000000001/notifications/stream`).

Alternatively use `curl` to stream SSE (developer test):

```bash
curl -N "http://127.0.0.1:5000/api/users/00000000-0000-0000-0000-000000000001/notifications/stream"
```

You should see `data: {...}` lines for the inserted row. The server (SSE handler) should mark `delivered = TRUE` after sending.

Quick scheduler simulation (slot override)
-- If you implement `scripts/notify_medications.py` with a `--slot` argument, run:

```bash
python scripts/notify_medications.py --slot morning
```

This will perform the same behavior as the scheduler: query meds for the `morning` slot, insert dedupe log, and create `user_notifications` rows.

Manual scheduler SQL (if you don't have the script yet)
-- Example transaction to dedupe + create notification for a specific `user_medications.id` (`<med_id>`) and `user_id`:

```sql
BEGIN;
INSERT INTO public.medication_notifications_log (user_medication_id, scheduled_date, scheduled_time)
VALUES ('<med_id>', CURRENT_DATE, '08:00')
ON CONFLICT DO NOTHING;

-- check if just inserted: insert notification only if not already logged
WITH ins AS (
  INSERT INTO public.user_notifications (user_id, title, body, payload)
  SELECT '<user_id>', 'Reminder', 'Take your med', jsonb_build_object('med_id','<med_id>')
  WHERE NOT EXISTS (
    SELECT 1 FROM public.medication_notifications_log ml WHERE ml.user_medication_id = '<med_id>' AND ml.scheduled_date = CURRENT_DATE AND ml.scheduled_time = '08:00'
  )
  RETURNING id
)
SELECT COUNT(*) FROM ins;
COMMIT;
```

Verify tables

```sql
SELECT * FROM public.user_notifications WHERE user_id='00000000-0000-0000-0000-000000000001' ORDER BY created_at DESC LIMIT 10;
SELECT * FROM public.medication_notifications_log WHERE scheduled_date = CURRENT_DATE;
```

Cleanup test data

```sql
DELETE FROM public.user_notifications WHERE user_id='00000000-0000-0000-0000-000000000001';
DELETE FROM public.medication_notifications_log WHERE scheduled_date = CURRENT_DATE;
DELETE FROM public.users WHERE id='00000000-0000-0000-0000-000000000001';
```

Railway quick test (recommended)

- Add `scripts/notify_medications.py` to repo and push to Railway.
- Create a Railway Scheduler job (one-off or recurring) with command:
  `python scripts/notify_medications.py --slot morning`
  and set job timezone to `Europe/London` for production timing.
- For quick manual test on Railway, run the job once from the Railway UI or CLI.

Notes & tips

- EventSource cannot attach custom headers; when testing SSE in the browser use the `user_id` in the path (as above) or rely on cookies.
- For fast iteration, manually inserting rows into `user_notifications` is the quickest verification step.
- When you're ready, I can create `scripts/notify_medications.py` with a `--slot` arg and add a small test runner you can call locally.

If you want me to add the scheduler script and SSE endpoint code now, say "implement scheduler and SSE" and I'll apply the changes and run a local smoke test.
