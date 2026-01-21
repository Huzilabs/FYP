# SSE Notifications — Frontend Integration

Overview
- The backend streams live notifications via Server-Sent Events (SSE) at: `/api/users/<user_id>/notifications/stream`.
- Notifications are persisted server-side and deduplicated; users must be authenticated (logged in) to receive their notifications.
- Use SSE for real-time UI updates; also fetch persisted notifications via the REST API when the UI loads.

Requirements
- Frontend must identify the currently signed-in user (session cookie or token).
- The server requires authentication to ensure notifications are scoped to the user. The simplest options are:
  - Use the same site cookie/session the backend recognizes (preferred for `EventSource`).
  - Or open a streaming request that includes an authorization token (see "Fetch-based streaming" below).

Event stream details
- Endpoint: `/api/users/<user_id>/notifications/stream`
- Connection: SSE (`text/event-stream`) that emits JSON payloads as notification events.
- Typical payload (example):
  {
    "id": "uuid",
    "user_id": "...",
    "title": "Medication due",
    "body": "Time to take Aspirin 100mg",
    "data": {"medication_id": 123},
    "created_at": "2026-01-22T08:00:00Z",
    "read": false
  }
- EventSource will auto-reconnect on network error; handle reconnect/backoff in the client as needed.

Frontend integration — Option A: EventSource (cookie/session auth)
- Best when your app authenticates via cookies or a session that the backend can read.
- Simple usage:

```js
// Assume `userId` is available in your app state
const es = new EventSource(`/api/users/${userId}/notifications/stream`);
es.onmessage = (e) => {
  try {
    const note = JSON.parse(e.data);
    // Add to UI: show toast, increment unread count, insert into list
    showNotificationToast(note);
    addNotificationToList(note);
  } catch (err) {
    console.error('invalid SSE data', err);
  }
};
es.onerror = (err) => {
  console.warn('SSE error', err);
  // Optionally show offline indicator; EventSource will auto-reconnect.
};
```

Notes:
- Browsers' native `EventSource` does not allow custom headers. If your backend requires a custom header for auth, prefer cookie-based auth or use the fetch-based approach below.

Frontend integration — Option B: Fetch streaming (Authorization header)
- Use when you must send `Authorization: Bearer <token>` or custom headers (`X-User-Id`).
- This uses `fetch()` and reads the response stream; implement your own parser for SSE-style lines or have the backend send newline-delimited JSON.

```js
async function streamNotifications(userId, token) {
  const res = await fetch(`/api/users/${userId}/notifications/stream`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let parts = buf.split('\n\n');
    buf = parts.pop();
    for (const p of parts) {
      // p contains SSE-style fields; simplest case: raw JSON line
      const jsonLine = p.trim();
      if (!jsonLine) continue;
      try {
        const note = JSON.parse(jsonLine);
        showNotificationToast(note);
        addNotificationToList(note);
      } catch (err) {
        console.error('parse stream item', err, jsonLine);
      }
    }
  }
}
```

Message handling and UI
- On receiving a message: show a transient toast and also insert the notification into your persisted list and unread counter.
- Provide a notifications panel (history) that reads persisted notifications from the REST API (e.g. `GET /api/users/<user_id>/notifications`). Use that endpoint on page load to populate the list.
- Mark items as read by calling the backend (PUT/POST) when the user views or dismisses them.

Authentication & Authorization
- The frontend must be logged in; the backend will only stream notifications for the authenticated user.
- If you rely on `EventSource`, use cookie/session authentication so no custom headers are required.
- If you use token-based auth, use the fetch-based streaming method or an EventSource polyfill that supports headers.

Testing locally
- Start the backend locally (e.g. `python webapp_new.py`) and open the frontend that connects to the SSE endpoint.
- Trigger a test notification from the admin/test endpoint:

```bash
# Example: trigger medication notifications (local Flask admin endpoint)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-admin-token: $NOTIFY_ADMIN_TOKEN" \
  -d '{"slot":"morning"}' \
  http://localhost:5000/api/notifications/medications_due

# Or call the Edge Function / scheduled function endpoint (if deployed locally)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-admin-token: $NOTIFY_ADMIN_TOKEN" \
  -d '{"slot":"morning"}' \
  https://<project>.functions.supabase.co/notify-medications
```

- Verify the frontend receives the streamed event and that the notification appears in the list and toast UI.
- Also verify the notification was persisted (query `user_notifications` table) or use the REST API to list notifications.

Notes & operational
- Deduplication: the backend uses a log table (`medication_notifications_log`) and `ON CONFLICT DO NOTHING` to avoid duplicate notifications.
- Persistence: notifications are persisted in `user_notifications` so the UI can show history even if the client was disconnected when the push happened.
- Logged-in requirement: users must be authenticated to view their own notifications; unauthenticated clients will not receive events.
- Reconnect/backoff: rely on EventSource's automatic reconnect or implement an exponential backoff for custom fetch streams.

Troubleshooting
- No events received:
  - Verify the frontend session/cookie or token is valid.
  - Confirm backend logs show the SSE connection established for your `user_id`.
  - Use `curl` to hit the admin trigger and ensure the server creates a row in `user_notifications`.
- Custom headers needed but EventSource used:
  - Switch to fetch-based streaming or use server-side session cookies.

References
- See `scripts/notify_medications.py` and the Edge Function `functions/notify-medications` for how scheduled/administrative triggers create notifications.

