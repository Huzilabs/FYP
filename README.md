# Face Recognition Flask API

## Overview

This repository provides a small Flask server (webapp_new.py) that implements a "capture-first" face authentication flow using Supabase Storage for images and PostgreSQL for user and embedding storage. The server uses the face_recognition library for face detection and 128-d embeddings.

Environment variables (required)

- SUPABASE_URL — your Supabase project URL
- SUPABASE_SERVICE_ROLE_KEY — service role key used for storage and DB operations
- SUPABASE_DB_URL or DATABASE_URL — Postgres connection string used by the server
- SUPABASE_BUCKET — Supabase storage bucket name used for uploading images

Important behavior notes

- Storage: images are uploaded to the configured Supabase bucket. The server first tries to use the bucket's public URL and falls back to creating a signed URL if the bucket/object is private. Signed URLs are created with a long expiry (one year) for convenience.
- Embeddings: the server will insert 128-d embeddings into `public.embeddings`. It tries to insert as a PostgreSQL `float8[]` first (works without pgvector). If the DB has the `vector` type available (pgvector), the server may use a `::vector` cast and DB helper functions for nearest-neighbor lookups.
- Face detection: the service prefers the lightweight `hog` detector for speed and falls back to `cnn` when necessary.

## HTTP API (summary)

All endpoints are under `/api/` except the legacy `/signup` form endpoint.

- `POST /api/detect_face`

  - Body: JSON or form data with `face_image` (data URL) or `image` (data URL).
  - Returns: `{ok: true, faces: [{top,right,bottom,left}, ...]}` or `{ok:false}` on error.

- `POST /api/upload_face_temp` (and legacy alias `/api/upload_face`)

  - Purpose: upload a temporary image to storage for preview before registering.
  - Body: `face_image` (data URL) or `image` (data URL).
  - Returns: `{ok:true, temp_storage_path, public_url, preview_data_url}`. `preview_data_url` is a base64 data URL suitable for immediate client preview.

- `POST /api/capture_face`

  - Purpose: capture a face image and attach it to a user; supports capture-first flow.
  - Body: `face_image` or `image` (data URL). Optional `user_id` to attach to an existing user.
  - Behavior: if `user_id` is omitted, a provisional user record is created, then the image is saved to storage, a `user_images` row is inserted, and an embedding is inserted into `public.embeddings`.
  - Returns: `{ok:true, profile_image_url, storage_path, preview_data_url}` on success.

- `POST /api/register` (also `/signup` form POST)

  - Purpose: create or update a user. This endpoint uses `ON CONFLICT (username) DO UPDATE` so POSTing the same `username` updates the existing record.
  - Required fields (must provide these to create):
    - `display_name` (string) — full name or display name
    - `username` (string) — unique username
    - `consent_terms` (boolean or truthy string) — must be true to register
  - Optional fields accepted:
    - `email`, `phone`
    - `date_of_birth` (string)
    - `emergency_contact` (JSON string or form-encoded string)
    - `medications` (JSON array string or comma-separated list)
    - `allergies` (comma-separated string or array)
    - `accessibility_needs`, `preferred_language`
    - `image` or `face_image` (data URL) — an image to attach and create embedding
    - `temp_storage_path` or `temp_path` — a path previously returned by `/api/upload_face_temp`
  - Behavior: user row is created/updated in one transaction. If an image is supplied, it is processed in a separate transaction/flow so user creation will not be rolled back because of image/embedding errors.
  - Returns: `{ok:true, user_id, display_name}` on success.

- `POST /api/attach_image`

  - Purpose: attach an image to an existing user.
  - Body: `user_id` (required) and either `face_image` (data URL) or `temp_storage_path`.
  - Behavior: inserts a `user_images` row in its own transaction (won't roll back user creation). Attempts to compute an embedding and insert it separately; embedding failures do not roll back the image insert.
  - Returns: `{ok:true, storage_path, public_url}` on success.

- `POST /api/login_face`

  - Purpose: attempt a face login using nearest-neighbour search against stored embeddings.
  - Body: `face_image` (data URL) or `image` (data URL). Optional `threshold` (float, default 0.5) and `limit` (int, default 1).
  - Important: nearest-neighbor lookup requires pgvector / `vector` type and a DB helper `public.find_nearest_embeddings`. If your Postgres does not have pgvector installed, the endpoint will return a helpful error `{error: 'nearest_embeddings_not_supported'}` with status 501. The server supports float8[] storage of embeddings, but efficient nearest lookups require pgvector.
  - On success: returns `{ok:true, user: {id, display_name, username}, distance}` where `distance` is the L2 distance (lower is closer). If no match within the provided `threshold`, the endpoint returns a no-match response.

  - Purpose: debug helper to list embedding metadata for a user. Intended for local testing only (not secured).

## Owner-only CRUD behavior

  - Preferred: set HTTP header `X-User-Id: <user_id>` on the request.
  - Alternative: include `actor_user_id` (or `user_id`) in the JSON body or form data.
  - `GET /api/users/<user_id>` — returns user details only if actor matches `user_id`.
  - `PUT /api/users/<user_id>` — updates user fields only if actor matches `user_id`.
  - `DELETE /api/users/<user_id>` — deletes user and related data only if actor matches `user_id`.
  - `DELETE /api/user_images/<image_id>` — deletes image only if the actor is the owner of that image.

```bash
curl -H "Content-Type: application/json" -H "X-User-Id: <USER_ID>" \
  -d '{"display_name":"New Name"}' \
  -X PUT https://your-host/api/users/<USER_ID>
```

Security note: this header-based check is a minimal convenience for local or trusted frontends. For production, replace with proper authentication (JWT, Supabase auth, or API keys) and validate tokens server-side before authorizing CRUD operations.


## Data model & CRUD notes

- Users:

  - Create / Update: `POST /api/register` with `username` will create or update the user. The endpoint returns the user `id`.
  - Read: no specific HTTP read endpoint is provided beyond what `login_face` returns; you can query the DB directly or add a read endpoint if needed.
  - Delete: there is no HTTP delete-user endpoint in the current server. Deleting a user must be done directly in the database or by adding an API endpoint.

- Images (`public.user_images`):
  - Add: use `/api/capture_face`, `/api/attach_image`, or `/api/register` (with `image`) to insert new images. Uploaded image files are stored at keys like `user_id/<timestamp>_<uuid>.jpg` or `temp/<uuid>.jpg` for temporary uploads.
  - Update (set profile image): image uploads mark `is_profile = true` for the inserted row. The server currently writes new files with unique filenames — it does not overwrite previous files by default. If you prefer overwrite behavior (e.g., always use `profile.jpg`), request the change and we can update the upload logic.
  - Delete: there is no HTTP delete-image endpoint; deletion must be done in the DB and storage manually or by adding an endpoint.

## Embedding storage & nearest-neighbor

- Insert strategy: the server first tries to insert embeddings as `float8[]` so the app works without pgvector. If pgvector is available, the code can use a `::vector` cast and DB helper functions for efficient nearest-neighbor queries.
- For `login_face`, the server expects pgvector and a DB function like `public.find_nearest_embeddings(vector, limit)` to exist. If you want nearest lookups without pgvector, you must add custom SQL or a server-side fallback (not included by default).

## Storage URLs

- The server calls Supabase Storage `get_public_url` and, if that doesn't return a usable public URL, calls `create_signed_url` to produce a usable URL. If both fail the server may still return the storage path so the client can handle retrieval.

## Running locally

1. Ensure the environment variables above are set.
2. Install dependencies listed in `requirements.txt` (creates a Python environment with Flask, face_recognition, Pillow, numpy, psycopg2, supabase client, etc.).
3. Run the server:

```bash
python webapp_new.py
```

\*\*\* End Patch
