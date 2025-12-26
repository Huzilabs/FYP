# Frontend Integration (Supabase uploads → Backend API)

This document explains how the frontend should upload images to Supabase storage and call the backend endpoints in this project.

1. Storage layout

- Create two folders (prefixes) in the Supabase storage bucket:
  - `registration/` — images uploaded during user signup/registration
  - `login/` — images uploaded to attempt a face login

When uploading from the client, store each file under one of those prefixes, e.g. `registration/<uuid>.jpg` or `login/<uuid>.jpg`.

2. What to send to the backend

- Prefer sending the public URL returned by Supabase (HTTP(S) link). If you only have a storage path, the backend will try to resolve a public URL, but sending the public URL is more reliable and faster.
- Endpoints and expected fields (JSON form):

  - `POST /api/register`

    - Required: `display_name`, `username`, `consent_terms` (true)
    - Image: `image_url` (HTTP(S) public URL) or `image`/`face_image` (data URL) or a storage path string.
    - Optional: `email`, `phone`, `date_of_birth`, `emergency_contact`, `medications`, `allergies`, `accessibility_needs`, `preferred_language`, `temp_storage_path` (if you used temporary upload step).
    - Behavior: server creates/updates `public.users`, saves a `public.user_images` row (uploads image into `user_id/<filename>`), computes face embedding and inserts into `public.embeddings`.

  - `POST /api/login_face`

    - Required: `image` or `face_image` (can be data URL, HTTP(S) URL, or storage path)
    - Optional: `threshold` (float, default 0.5), `limit` (int)
    - Behavior: server computes embedding and runs nearest-neighbor lookup (requires `pgvector` and DB helper `public.find_nearest_embeddings`). If match found below threshold, returns matched user details; otherwise returns `no_match`.

  - `POST /api/detect_face`

    - Required: `image`/`face_image` (data URL, HTTP URL, or storage path)
    - Behavior: read-only face detection; returns detected bounding boxes only.

  - `POST /api/upload_face_temp` (optional flow)
    - Accepts data URL; backend uploads to `temp/<uuid>.jpg` and returns `temp_storage_path` and `public_url`.

3. Table mappings (what backend saves where)

- `public.users`: user profile (display_name, username, email, phone, date_of_birth, emergency_contact (jsonb), medications (jsonb), allergies (text[]), accessibility_needs, preferred_language, created_at).
- `public.user_images`: image metadata saved when an image is attached / registered / captured. Fields used: `user_id`, `storage_path`, `public_url`, `width`, `height`, `mime_type`, `uploaded_at`, `is_profile`, `file_size`.
- `public.embeddings`: face embeddings. Columns used: `user_id`, `embedding` (either `float8[]` or `vector` depending on DB), `source` (`register`/`attach`/`capture`/`detect`), `created_at`.

4. Frontend flow recommendations

- Registration:

  1. Upload image to Supabase under `registration/` and obtain public URL or storage path.
  2. POST to `/api/register` with profile fields and `image_url` set to the uploaded URL (or provide data URL). The backend will move/copy the image into the user's folder and persist metadata + embedding.

- Login:
  1. Upload the live capture to Supabase under `login/` (or send data URL directly).
  2. POST to `/api/login_face` with `image` (URL or storage path). Backend will compute embedding and attempt nearest-neighbor lookup.
  3. If `no_match`, prompt user to register via the registration flow.

5. Actor identity & CRUD

- For `GET/PUT/DELETE /api/users/<user_id>` and image deletion, the server expects the caller identity via header `X-User-Id` or a request field `actor_user_id`. In production, replace this with real authentication (JWT / API key / Supabase auth).

6. Example requests

Register example (JSON):

```
POST /api/register
Content-Type: application/json

{
  "display_name": "Alice",
  "username": "alice01",
  "consent_terms": true,
  "image_url": "https://<bucket>.supabase.co/storage/v1/object/public/registration/abcd.jpg"
}
```

Login example:

```
POST /api/login_face
Content-Type: application/json

{
  "image": "https://<bucket>.supabase.co/storage/v1/object/public/login/xyz.jpg",
  "threshold": 0.5,
  "limit": 1
}
```

7. Notes

- `login_face` requires `pgvector` for nearest-neighbor search. If your Supabase DB does not have pgvector, see `tests/enable_pgvector.py` in the repo.
- The backend will not write to the database during `detect_face` — detection is read-only.


    - Required: `display_name`, `username`, `consent_terms` (true)
    - Image: `image_url` (HTTP(S) public URL) or `image`/`face_image` (data URL) or a storage path string.
    - Optional: `email`, `phone`, `date_of_birth`, `emergency_contact`, `medications`, `allergies`, `accessibility_needs`, `preferred_language`, `temp_storage_path` (if you used temporary upload step).
    - Behavior: server creates/updates `public.users`, saves a `public.user_images` row (uploads image into `user_id/<filename>`), computes face embedding and inserts into `public.embeddings`.

  - `POST /api/login_face`

    - Required: `image` or `face_image` (can be data URL, HTTP(S) URL, or storage path)
    - Optional: `threshold` (float, default 0.5), `limit` (int)
    - Behavior: server computes embedding and runs nearest-neighbor lookup (requires `pgvector` and DB helper `public.find_nearest_embeddings`). If match found below threshold, returns matched user details; otherwise returns `no_match`.

  - `POST /api/detect_face`

    - Required: `image`/`face_image` (data URL, HTTP URL, or storage path)
    - Behavior: read-only face detection; returns detected bounding boxes only.

  - `POST /api/upload_face_temp` (optional flow)
    - Accepts data URL; backend uploads to `temp/<uuid>.jpg` and returns `temp_storage_path` and `public_url`.

3. Table mappings (what backend saves where)

- `public.users`: user profile (display_name, username, email, phone, date_of_birth, emergency_contact (jsonb), medications (jsonb), allergies (text[]), accessibility_needs, preferred_language, created_at).
- `public.user_images`: image metadata saved when an image is attached / registered / captured. Fields used: `user_id`, `storage_path`, `public_url`, `width`, `height`, `mime_type`, `uploaded_at`, `is_profile`, `file_size`.
- `public.embeddings`: face embeddings. Columns used: `user_id`, `embedding` (either `float8[]` or `vector` depending on DB), `source` (`register`/`attach`/`capture`/`detect`), `created_at`.

4. Frontend flow recommendations

- Registration:

  1. Upload image to Supabase under `registration/` and obtain public URL or storage path.
  2. POST to `/api/register` with profile fields and `image_url` set to the uploaded URL (or provide data URL). The backend will move/copy the image into the user's folder and persist metadata + embedding.

- Login:
  1. Upload the live capture to Supabase under `login/` (or send data URL directly).
  2. POST to `/api/login_face` with `image` (URL or storage path). Backend will compute embedding and attempt nearest-neighbor lookup.
  3. If `no_match`, prompt user to register via the registration flow.

5. Actor identity & CRUD

- For `GET/PUT/DELETE /api/users/<user_id>` and image deletion, the server expects the caller identity via header `X-User-Id` or a request field `actor_user_id`. In production, replace this with real authentication (JWT / API key / Supabase auth).

6. Example requests

- Register example (JSON):

```
POST /api/register
Content-Type: application/json

{
  "display_name": "Alice",
  "username": "alice01",
  "consent_terms": true,
  "image_url": "https://<bucket>.supabase.co/storage/v1/object/public/registration/abcd.jpg"
}
```

- Login example:

```
POST /api/login_face
Content-Type: application/json

{
  "image": "https://<bucket>.supabase.co/storage/v1/object/public/login/xyz.jpg",
  "threshold": 0.5,
  "limit": 1
}
```

7. Notes

- `login_face` requires `pgvector` for nearest-neighbor search. If your Supabase DB does not have pgvector, see `tests/enable_pgvector.py` in the repo.
- The backend will not write to the database during `detect_face` — detection is read-only.

````
