# Project: Face Recognition + Medication Notifications

## Overview

- This repository implements a face-recognition backend and a medication reminders system. It includes a Flask API (`webapp_new.py`) for user, image, medication and SSE notification streaming, and an Edge Function (`functions/notify-medications`) to create deduped scheduled medication notifications that are persisted to the DB.

## Tech stack

- Python 3 (Flask) for the API and SSE streaming
- PostgreSQL (Supabase) for data storage, jsonb and RPCs
- pgvector (optional) for vector NN if available
- Deno (Edge Function) for scheduler/admin notify function
- Dockerfile to containerize the Flask app
- Railway or Supabase scheduler for periodic invocation

## How to run locally

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

## Deploy to Railway (high level)

1. Create a Railway project and connect to the Git repo or push the Docker image.
2. Set environment variables in Railway (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL, NOTIFY_ADMIN_TOKEN, SUPABASE_BUCKET).
3. If using Edge Function, deploy it to Supabase Edge Functions or a small Deno host and configure the scheduler to POST JSON to `/api/notifications/medications_due` with `{"slot":"morning","token":"<TOKEN>"}`.

## Key files (purpose)

- `requirements.txt`: Python dependencies required to run the Flask app.
- `Dockerfile`: Containerize the Flask app for production deployment.
- `webapp_new.py`: Main Flask application providing API endpoints and SSE streaming for notifications.
- `functions/notify-medications/index.ts`: Edge function that queries `user_medications` and inserts deduped entries into `medication_notifications_log` and `user_notifications` (scheduler entrypoint).
- `migrations/`: SQL migrations and RPCs for dedupe, cleanup and sync (run these on your Supabase DB).
- `scripts/notifications_audit_and_checks.sql`: Diagnostics and audit trigger to track delivered updates.

## Endpoints

- `GET /health`: Liveness and quick checks (DB + face model availability).
- `GET /`: Basic OK status for the API.
- `POST /api/detect_face`: Accepts image (data URL or URL) and returns face bounding boxes (read-only).
- `POST /api/upload_face_temp`: Upload a face image to temporary storage; returns `temp_storage_path` and `public_url`.
- `POST /api/upload_face` (legacy): Alias to `/api/upload_face_temp`.
- `POST /api/capture_face`: Capture and attach face image to a user; may create provisional user and insert `user_images` and embedding.
- `POST /api/register`: Create or update a user; accepts profile fields and optional medications list.
- `POST /api/attach_image`: Attach an image to an existing user and optionally compute and store embedding.
- `POST /api/login_face`: Face-login endpoint using nearest-neighbor search (requires pgvector availability).
- `GET /api/admin/embeddings`: Admin helper to list embeddings for a user (local testing only).
- `GET /api/users/<user_id>`: Return user record, images, embeddings count and medications (owner-only via `X-User-Id` or body `actor_user_id`).
- `PUT /api/users/<user_id>`: Update allowed user fields (owner-only).
- `DELETE /api/users/<user_id>`: Delete user and related DB rows (owner-only).
- `GET/POST /api/users/<user_id>/medications`: List or create medications for a user.
- `PUT/DELETE /api/users/<user_id>/medications/<med_id>`: Update or delete a medication (owner-only).
- `GET /api/users/<user_id>/notifications`: List persisted notifications for a user (owner-only).
- `GET /api/users/<user_id>/notifications/stream`: Server-Sent Events (SSE) stream of pending notifications; notifications are marked `delivered` only after successful streaming.
- `GET/POST /api/notifications/medications_due`: Admin internal endpoint used by scheduler to create deduped medication notifications. Accepts `slot=morning|afternoon|evening` or `time=HH:MM` and requires `X-Admin-Token` header or JSON `token` when `NOTIFY_ADMIN_TOKEN` is set.

Endpoint details
----------------

- `GET /health`
   - Purpose: Return app liveness and quick checks for DB and face model availability.
   - Inputs: none.
   - Auth: none.
   - Response: JSON `{ok: true, db: {connected: bool}, face_model: {available: bool}}`.

- `POST /api/detect_face`
   - Purpose: Run face detection on an uploaded image (no DB writes).
   - Inputs: JSON body with `face_image` (data URL) or `image` (HTTP URL or storage path).
   - Auth: none.
   - Response: JSON with detected face bounding boxes.

- `POST /api/upload_face_temp`
   - Purpose: Save an uploaded image to temp storage and return a usable URL.
   - Inputs: `face_image` (data URL) or `image`.
   - Auth: none.
   - Response: `temp_storage_path`, `public_url`, and a preview data URL.

- `POST /api/capture_face`
   - Purpose: Attach a face image to a user record and optionally compute/store an embedding.
   - Inputs: `user_id` (optional), `face_image` or `temp_storage_path`.
   - Auth: none for capture-first; embedding and DB writes happen server-side.
   - Response: `profile_image_url`, `storage_path`.

- `POST /api/register`
   - Purpose: Create or update a user and optionally persist supplied medications.
   - Inputs: JSON with `display_name`, `username`, `consent_terms` and other profile fields.
   - Auth: none (intended for frontend registration flow).
   - Response: created user id and display name.

- `POST /api/attach_image`
   - Purpose: Attach an image to an existing user and compute embedding separately.
   - Inputs: `user_id` plus `face_image` or `temp_storage_path`.
   - Auth: owner-only via `X-User-Id` or `actor_user_id`.

- `POST /api/login_face`
   - Purpose: Face-login via nearest-neighbor search using embeddings (requires pgvector).
   - Inputs: `face_image` or `temp_storage_path`; optional `threshold` and `limit`.
   - Auth: none; returns matched `user` when distance below threshold.

- `GET /api/admin/embeddings`
   - Purpose: Admin helper to list embeddings (local testing only).
   - Inputs: `user_id` query param.
   - Auth: not enforced (local/dev use only).

- `GET/PUT/DELETE /api/users/<user_id>`
   - Purpose: CRUD for user profile (GET returns profile, images, meds, embedding count).
   - Inputs: path `user_id`; PUT body contains allowed fields.
   - Auth: owner-only — require `X-User-Id` header or `actor_user_id` to match `user_id`.

- Medications endpoints (`/api/users/<user_id>/medications`)
   - Purpose: List, create, update and delete medication rows tied to a user. `time` field supports slots or `HH:MM`.
   - Auth: owner-only for create/update/delete.

- Notifications endpoints
   - `GET /api/users/<user_id>/notifications`: list persisted notification rows (owner-only).
   - `GET /api/users/<user_id>/notifications/stream`: SSE stream for pending notifications; server marks each row `delivered` only after successful streaming.

- `GET/POST /api/notifications/medications_due`
   - Purpose: Admin/internal scheduler endpoint. Creates deduped rows in `medication_notifications_log` and `user_notifications` for the requested slot/time.
   - Inputs: query or JSON `slot=morning|afternoon|evening` or `time=HH:MM`. Optional JSON `cleanup=true` to run cleanup RPCs.
   - Auth: If `NOTIFY_ADMIN_TOKEN` is set, request must include `X-Admin-Token` header or JSON `token` matching the env var.


## Notes

- This branch will keep only `requirements.txt` and `Dockerfile` tracked; other project files are archived into `archived_ignored/` to produce a minimal final branch. You can restore archived files from that folder if needed.
