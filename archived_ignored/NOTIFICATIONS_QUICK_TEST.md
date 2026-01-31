Quick test: Notifications + SSE

1. Start your backend (local):

```bash
# from repo root
python webapp_new.py
```

2. Open browser console on same origin as backend (so cookies are sent). Create EventSource:

```js
const es = new EventSource("/api/users/TEST_USER_ID/notifications/stream");
es.onmessage = (e) => console.log("sse", e.data);
es.onerror = (e) => console.log("sse error", e);
```

Replace `TEST_USER_ID` with the user's id present in your DB.

3. Trigger the notifications creation (admin endpoint):

```bash
curl -X POST "http://localhost:5000/api/notifications/medications_due?slot=morning" \
  -H "X-Admin-Token: YOUR_TOKEN"
```

Or run the script directly (requires DB env var set):

```bash
SUPABASE_DB_URL="postgres://..." python scripts/notify_medications.py --slot morning
```

4. If SSE client is connected you should see the logged event in the browser console. If not connected, verify with the list endpoint:

```bash
curl "http://localhost:5000/api/users/TEST_USER_ID/notifications"
```

5. Verify DB rows:

```sql
SELECT * FROM public.medication_notifications_log WHERE scheduled_date = CURRENT_DATE;
SELECT * FROM public.user_notifications WHERE created_at::date = CURRENT_DATE;
```

Notes:

- The server currently identifies streams by `user_id` in the path. If you do not use cookies or other auth, any client that knows a `user_id` can open that user's stream — acceptable for dev, but insecure for production.
- For dev quick tests it's OK; secure later before production.
