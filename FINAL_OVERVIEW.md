Project: Face Recognition + Medication Notifications
===============================================

Overview
--------
- This repository implements a face-recognition backend and a medication reminders system. It includes a Flask API (`webapp_new.py`) for user, image, medication and SSE notification streaming, and an Edge Function (`functions/notify-medications`) to create deduped scheduled medication notifications that are persisted to the DB.

Tech stack
----------
- Python 3 (Flask) for the API and SSE streaming
- PostgreSQL (Supabase) for data storage, jsonb and RPCs
- pgvector (optional) for vector NN if available
- Deno (Edge Function) for scheduler/admin notify function
- Dockerfile to containerize the Flask app
- Railway or Supabase scheduler for periodic invocation

How to run locally
-------------------
1. Create a Python virtual environment and install dependencies:

   pip install -r requirements.txt

2. Configure environment variables (example):

   export SUPABASE_DB_URL="postgres://..."
   export SUPABASE_URL="https://..."
   export SUPABASE_SERVICE_ROLE_KEY="..."
   export NOTIFY_ADMIN_TOKEN="your-admin-token"

3. Run the Flask app:

   python webapp_new.py

4. (Optional) Run in Docker:

   docker build -t face-backend .
   docker run -e SUPABASE_DB_URL=... -p 5000:5000 face-backend

Deploy to Railway (high level)
------------------------------
1. Create a Railway project and connect to the Git repo or push the Docker image.
2. Set environment variables in Railway (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL, NOTIFY_ADMIN_TOKEN, SUPABASE_BUCKET).
3. If using Edge Function, deploy it to Supabase Edge Functions or a small Deno host and configure the scheduler to POST JSON to `/api/notifications/medications_due` with `{"slot":"morning","token":"<TOKEN>"}`.

Key files (purpose)
-------------------
- `requirements.txt`: Python dependencies required to run the Flask app.
- `Dockerfile`: Containerize the Flask app for production deployment.
- `webapp_new.py`: Main Flask application providing API endpoints and SSE streaming for notifications.
- `functions/notify-medications/index.ts`: Edge function that queries `user_medications` and inserts deduped entries into `medication_notifications_log` and `user_notifications` (scheduler entrypoint).
- `migrations/`: SQL migrations and RPCs for dedupe, cleanup and sync (run these on your Supabase DB).
- `scripts/notifications_audit_and_checks.sql`: Diagnostics and audit trigger to track delivered updates.

Notes
-----
- This branch will keep only `requirements.txt` and `Dockerfile` tracked; other project files are archived into `archived_ignored/` to produce a minimal final branch. You can restore archived files from that folder if needed.
