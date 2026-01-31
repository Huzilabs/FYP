**Notifications: Deployment & Testing**

This document explains what `scripts/notify_medications.py` does, how to schedule it on Railway (preferred), an alternative with a Supabase Edge Function that calls the admin HTTP endpoint, how to generate the admin token, and how the frontend uses SSE to receive live notifications.

- **Script**: `scripts/notify_medications.py`
  - Purpose: queries `public.user_medications` for a scheduled slot/time (e.g. `08:00`, `14:00`, `18:00`), inserts an idempotent row into `public.medication_notifications_log` (uses `ON CONFLICT DO NOTHING`) and creates a per-user `public.user_notifications` row when a notification is newly created.
  - Run manually for testing:
    ```bash
    python scripts/notify_medications.py --slot morning
    ```
  - Environment required: `SUPABASE_DB_URL` (or `DATABASE_URL`) so the script can connect using the same DB credentials as your backend.

- **Preferred Deployment: Railway Scheduler (direct DB access)**
  - Description: Configure Railway Scheduler to execute the Python script on the host that has network access to the Postgres DB (preferred because the script writes directly to the DB).
  - Railway job command examples (set timezone or convert times to UTC if scheduler runs UTC):

    ```bash
    # morning (Europe/London 08:00)
    python scripts/notify_medications.py --slot morning

    # afternoon
    python scripts/notify_medications.py --slot afternoon

    # evening
    python scripts/notify_medications.py --slot evening
    ```

  - Railway env vars to set: `SUPABASE_DB_URL` (or `DATABASE_URL`).
  - Verify: check `public.medication_notifications_log` and `public.user_notifications` after a run.

- **Alternate Deployment: Supabase Edge Function -> Backend admin endpoint**
  - When to use: the scheduler cannot directly access your Postgres DB (e.g. constrained network), but it can call the backend over HTTPS.
  - Flow: Scheduler -> Supabase Edge Function (or any scheduled HTTP caller) -> POST `https://<YOUR_BACKEND>/api/notifications/medications_due?slot=<slot>` with header `X-Admin-Token: <token>`.
  - Minimal Edge Function (Deno/TypeScript) example (save as `functions/notify-medications/index.ts`):
    ```ts
    export async function handler(req: Request): Promise<Response> {
      try {
        const body = await req.json().catch(() => ({}));
        const slot = body.slot || "morning";
        const BACKEND_URL = Deno.env.get("BACKEND_URL");
        const NOTIFY_ADMIN_TOKEN = Deno.env.get("NOTIFY_ADMIN_TOKEN");
        const resp = await fetch(
          `${BACKEND_URL}/api/notifications/medications_due?slot=${encodeURIComponent(slot)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Admin-Token": NOTIFY_ADMIN_TOKEN,
            },
            body: JSON.stringify({ slot }),
          },
        );
        return new Response(await resp.text(), {
          status: resp.status,
          headers: { "Content-Type": "application/json" },
        });
      } catch (err) {
        return new Response(JSON.stringify({ ok: false, error: String(err) }), {
          status: 500,
        });
      }
    }
    ```
  - Supabase env vars: `BACKEND_URL` (base URL of your backend), `NOTIFY_ADMIN_TOKEN`.
  - Test locally with Supabase CLI:
    ```bash
    supabase functions invoke notify-medications --body '{"slot":"morning"}'
    ```

- **Generating `NOTIFY_ADMIN_TOKEN`**
  - Quick methods:

    ```bash
    # OpenSSL
    openssl rand -hex 24

    # Python
    python -c "import secrets; print(secrets.token_hex(24))"
    ```

  - Set the same token value as the backend env var `NOTIFY_ADMIN_TOKEN` (your backend reads this to authenticate admin calls).
  - Use the same token as the Edge Function env secret or pass it in the scheduler's HTTP header `X-Admin-Token`.

- **Admin endpoint (backend)**
  - URL: `POST /api/notifications/medications_due` (also accepts `GET`)
  - Query params / JSON: `slot=morning|afternoon|evening` or `time=HH:MM`.
  - Auth: `X-Admin-Token` header (or `admin_token` query param). Backend checks `NOTIFY_ADMIN_TOKEN`.
  - Response: JSON `{ok: true, found: <n>, created: <m>}`.

- **Frontend: SSE for live delivery**
  - Endpoint: `GET /api/users/<user_id>/notifications/stream` (Server-Sent Events).
  - Basic browser example:
    ```js
    const es = new EventSource(
      "/api/users/" + userId + "/notifications/stream",
    );
    es.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data); /* show notification */
      } catch (e) {
        console.log("sse:", ev.data);
      }
    };
    es.onerror = () => {
      /* fallback to polling / reconnect logic */
    };
    ```
  - Fallback: GET `/api/users/<user_id>/notifications` to list stored notifications.
  - Note: SSE connection is long-lived; server marks notifications `delivered = TRUE` when sent. The frontend must authenticate as the user (cookies, session, or Authorization header) so the server can identify `user_id` via the actor identity logic.

- **Testing checklist (quick)**
  1. Create a test medication row in `public.user_medications` with `time = '08:00'` and a test user.
  2. Manually run `python scripts/notify_medications.py --slot morning` or `curl -X POST <backend>/api/notifications/medications_due?slot=morning -H 'X-Admin-Token: <token>'`.
  3. Verify `public.medication_notifications_log` has a row for today's date and the correct `user_medication_id`.
  4. Verify `public.user_notifications` contains the created notification.
  5. Open an SSE connection from the frontend and verify the event arrives; if not connected, the notification should appear via GET list.

- **Security & timezone notes**
  - Keep `NOTIFY_ADMIN_TOKEN` secret. Do not embed it in client code.
  - Ensure the scheduler and Edge Function use HTTPS to call the backend.
  - Confirm scheduler timezone. If scheduler runs in UTC, convert Europe/London times to UTC or schedule with a scheduler that accepts timezone settings.

If you want, I can also add the Edge Function file and a small `README.md` with these commands into the repo — tell me and I'll add them now.
