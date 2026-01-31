# Frontend Login Flow — Capture, Upload, and Backend Contract

Purpose

- Describe the frontend changes and backend expectations for the login (live capture) flow.
- Ensure captures are stored under the `Login/` prefix in the Supabase storage bucket and the backend receives a usable reference (storage path or public URL) to perform face matching.

Frontend responsibilities

- Capture image from camera (same component used for registration). Produce either a data URL or a File/Blob.
- Preferred flow (recommended):

  1. Upload the captured Blob/File directly to Supabase Storage under the `Login/` prefix:

     - Example (supabase-js):

       ```js
       const filename = `Login/${crypto.randomUUID()}.jpg`;
       const { error } = await supabase.storage
         .from("face_oftheusers")
         .upload(filename, file);
       // Then get public URL (or pass storage path)
       const { publicURL } = supabase.storage
         .from("face_oftheusers")
         .getPublicUrl(filename);
       ```

  2. Send the backend `/api/login_face` a JSON payload containing either:
     - `temp_storage_path` (e.g. `Login/<uuid>.jpg`) — preferred, fast; or
     - `image` (data URL) — backend will compute embedding but will not have a stored image unless you uploaded.

- If you cannot upload from the client, you may send the data URL directly to `/api/login_face`; backend will compute embedding but will not create a Login/ storage object unless backend is changed to do so.

Backend expectations and recommended behavior

- Acceptable inputs for `/api/login_face`:

  - `image` or `face_image` (data URL) — compute embedding on-the-fly.
  - `image_url` (HTTP(S) public URL) — backend should fetch and compute embedding.
  - `temp_storage_path` or `temp_path` (storage path string) — backend should resolve/download that object and compute embedding.

- To support the frontend upload-first flow, backend should: (preferred)

  1. If `temp_storage_path` provided: reuse that storage path (do NOT re-upload). Download it to compute encoding and run nearest-neighbor. Optionally return `storage_path` and `public_url` in the response so the frontend knows what was checked.
  2. If only `image` (data URL) present and you want to persist the login capture, require frontend to upload it first (recommended) or change backend to upload it under `Login/<uuid>.jpg` and then return the saved path.

- Current repo status (from `webapp_new.py`):
  - `api_register` reuses frontend-provided `temp_storage_path` (does not re-upload) and inserts a `public.user_images` row.
  - `api_login_face` currently computes embeddings from provided image data but does not persist login captures to storage or accept `temp_storage_path` to reuse — to support the upload-first flow it should be extended as above.

Required changes (high level)

- Frontend: implement client upload to `Login/` prefix and pass `temp_storage_path` (or public URL) to `/api/login_face`.
- Backend (recommendation): update `/api/login_face` to accept `temp_storage_path` and behave like `api_register` for image handling:
  - If `temp_storage_path` present: download and reuse the storage path, compute encoding, run nearest-neighbor, return match/no_match plus the `storage_path`/`public_url` used.
  - If `image` data URL present and you want persistence: either require frontend upload-first or document that the backend will not persist captures unless changed.

API contract examples

- Client upload + login check (preferred):

  1. Upload to storage (client): returns `temp_storage_path` and `public_url`.

  2. POST to backend:

     ```json
     POST /api/login_face
     {
       "temp_storage_path": "Login/0123-... .jpg"
     }
     ```

  3. Backend response (recommended):

     ```json
     {
       "ok": true,
       "result": "match|no_match",
       "user": {
         /* matched user if any */
       },
       "storage_path": "Login/0123-... .jpg",
       "public_url": "https://.../storage/v1/object/public/face_oftheusers/Login/0123-... .jpg"
     }
     ```

Bucket bug / observed issues (notes to fix later)

- Observed: `get_public_url()` sometimes returns a URL with a trailing `?` and some storage resolutions can be inconsistent for private vs public buckets. Symptoms:
  - Returned `public_url` containing a trailing `?` (cosmetic but can confuse some consumers).
  - If bucket is private, `get_public_url` may return a placeholder or `not_found` — code should fallback to `create_signed_url` (the repo already contains a `_public_or_signed_url` helper which does this).
  - Permission/CORS problems can prevent direct public fetches from the backend or frontend; verify bucket public policy and CORS settings.

Actions to fix later (short list)

- Normalize `get_public_url` output (remove trailing `?`) before returning to frontend.
- Ensure `_public_or_signed_url` is always used when returning URLs and that signed URLs are generated for private buckets.
- Verify Supabase Storage bucket policies, CORS, and that the `face_oftheusers` prefix exists with correct case (`Login/` vs `login/` matters).

Testing checklist for frontend devs

- Upload a test capture to `Login/` and ensure you receive `temp_storage_path` + `public_url`.
- Call `/api/login_face` with `temp_storage_path` and verify response returns `match`/`no_match` and the `public_url` used.
- If no match, ensure the UI routes user to registration flow.

Notes

- Do not change the existing `FRONTEND_INTEGRATION.md` yet — this file supplements it specifically for login capture behavior.
- When you are ready, I can implement the backend change to `/api/login_face` to accept `temp_storage_path` and return the storage info.

---

Created by the project maintainer assistant. Follow up if you want me to implement the backend changes now.
