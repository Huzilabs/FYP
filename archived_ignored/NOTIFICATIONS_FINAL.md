# Medication Notifications — Final Design & Integration Guide

Purpose

- Deliver reliable in-app medication reminders to users at three fixed Europe/London times (08:00, 14:00, 18:00).
- Provide near-real-time delivery to users who are online (via Server-Sent Events), and reliable delivery for offline users (stored notifications fetched on next app open).

Goals / Constraints

- Anchor scheduling to Europe/London for all users.
- Use simple, robust primitives: Postgres rows for deduplication and per-user notification storage + an SSE endpoint for live delivery.
- Keep authentication minimal for now (dev-mode: identify by `user_id`); plan for stronger auth later.

High-level flow

1. A scheduler runs at the three fixed slots (in Europe/London). It finds all medications due at that slot for all users.
2. For each medication due the scheduler:
   - attempt to insert a dedupe row into `medication_notifications_log` (unique constraint prevents duplicates),
   - if insert succeeds, create a `user_notifications` row for that user (unread/delivered=false).
3. Any logged-in browser opens an SSE connection to `/api/users/<user_id>/notifications/stream`. The server streams unread `user_notifications` for that `user_id` and marks them delivered.
4. If a user is offline, the `user_notifications` row remains; frontend will fetch unread notifications on next load.

Database schema (migrations)

- Deduplication log (run once):

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

- Per-user notifications table:

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

API endpoints (server)

1. GET /api/notifications/medications_due

- Purpose: admin/internal feed (optional). Returns grouped users and medications for a given slot or the current London time.
- Query params: `slot=morning|afternoon|evening` (optional). If omitted, server maps current Europe/London HH:MM to a slot.
- Auth: require `X-Admin-Token` header (validate against `NOTIFY_ADMIN_TOKEN`) or restrict to internal scheduler.
- Sample response: JSON grouping users and their meds.

2. GET /api/users/<user_id>/notifications

- Purpose: return unread or recent notifications for the user (fallback / on-load).
- Auth: `X-User-Id` header or dev-mode matching path; for production use tokens.

3. SSE: GET /api/users/<user_id>/notifications/stream

- Purpose: stream unread notifications live to the logged-in browser.
- Behavior: server queries `user_notifications WHERE user_id=%s AND delivered=FALSE`, yields events `data: <json>\n\n`, then marks rows `delivered=TRUE` after sending. Repeat poll (1-2s) until client disconnect.
- Note: EventSource cannot send custom headers; identify user via URL path or cookie.

Scheduler behavior (recommended)

- Run a small worker process at the three London slots (08:00, 14:00, 18:00). Options: Railway Scheduler, cron on a small VM, GitHub Actions (less ideal but possible).
- Steps:
  1. Compute Europe/London slot time (HH:MM), e.g. '08:00'.
  2. Query `user_medications` (join `users`) where `to_char(time::time,'HH24:MI') = %s`.
  3. For each med found, try:
     INSERT INTO medication_notifications_log (user_medication_id, scheduled_date, scheduled_time) VALUES (...) ON CONFLICT DO NOTHING;
     If the insert affected 1 row (meaning this send hasn't been recorded yet):
     INSERT INTO user_notifications (user_id, title, body, payload) VALUES (...).
  4. Commit and continue.
- Rationale: simple, idempotent, and resilient to retries.

SSE implementation notes

- Flask devserver is suitable for local testing only. For production use a server that supports long-lived responses (e.g. Gunicorn + gevent/uvicorn or an async server). Configure any reverse proxy timeouts accordingly.
- Example streaming loop: poll DB for unread rows, yield `data: <json>\n\n` for each row, mark delivered, then sleep(1).
- Consider using Postgres `LISTEN/NOTIFY` or a pub/sub if you want the server to wake instantly without polling.

Frontend integration (React)

- Simple client using EventSource:

```javascript
const es = new EventSource(
  `https://<your-backend>/api/users/${userId}/notifications/stream`,
);
es.onmessage = (e) => {
  const payload = JSON.parse(e.data);
  // show in-app toast; add to notifications list
};
es.onerror = (err) => {
  // try reconnecting with backoff or fallback to polling
};
```

- Fallback: periodic `GET /api/users/<user_id>/notifications` on load and every 30–60s while the app is active.

Delivery guarantees and offline users

- Connected users: near-instant delivery via SSE (1–2s poll window). Use `delivered` flag to avoid resending.
- Offline users: notifications remain in `user_notifications` and are visible when they next open the app.

Deployment & runtime notes

- Server: use a worker/process manager that allows long-lived HTTP responses.
  - Example: `gunicorn -k gevent -w 2 webapp_new:app`.
- Railway / Vercel specifics:
  - Frontend (Vercel) serves the React SPA; EventSource connections go directly from browser to Railway-hosted Flask app.
  - Ensure Railway's HTTP timeout is high enough to allow SSE; configure keepalive.

Environment variables

- `SUPABASE_DB_URL` or `DATABASE_URL` — database connection string used by `get_db_conn()`.
- `NOTIFY_ADMIN_TOKEN` — secret for scheduler to call admin endpoint (optional).

Testing checklist

1. Apply DB migrations.
2. Seed a test user and `user_medications` row with `time = '08:00'`.
3. Start Flask locally and open frontend; connect SSE for test user.
4. Run scheduler locally with `slot=morning` argument — verify SSE received and `user_notifications` row created and marked delivered.
5. Verify dedupe: run scheduler twice for same slot — second run should not create duplicate `user_notifications` due to `medication_notifications_log` unique constraint.

Security & privacy notes

- Current dev-mode plan uses `user_id` in path for SSE; this is simple but not secure. For production, add per-session tokens or JWTs.
- Limit the `/api/notifications/medications_due` endpoint to internal callers only.

Next steps

- If you approve this documentation, I will implement the DB migrations and add the SSE endpoint in `webapp_new.py` (dev-mode `user_id` auth), plus a small `scripts/notify_medications.py` scheduler script you can run with Railway Scheduler.

---

File: `NOTIFICATIONS_FINAL.md`
