# Frontend → Supabase storage → Backend integration

## Goal

Describe how the frontend captures a photo, uploads it into the Supabase Storage bucket named `face_oftheusers` under the `Registration/` folder, then calls the backend `/api/register` endpoint so `webapp_new.py` can download the file, detect the face, compute the embedding and persist the user record.

## High-level flow

1. User fills registration form on the frontend and clicks Continue.
2. Frontend shows the face capture UI (camera). User clicks **Capture Photo**.
3. Frontend captures an image as a Data URL (JPEG) via the `CameraCapture` component.
4. Frontend uploads the image bytes to Supabase Storage into `face_oftheusers/Registration/<filename>.jpg` and records the storage path (e.g. `Registration/abc123.jpg`).
5. Frontend posts the registration data to the backend `/api/register` including `temp_storage_path` set to the storage path from step 4.
6. Backend (`webapp_new.py`) receives `temp_storage_path`, calls `download_from_storage(temp_storage_path)` to fetch the file, runs face detection/encoding, stores `user` and `user_images` rows and the embedding.

## Why use `temp_storage_path` (recommended)

- `webapp_new.py` already supports `temp_storage_path` on `/api/register` — when provided it will download the file from Supabase storage and attach it to the created user record.
- This avoids sending large base64 payloads to the backend and keeps uploads in the storage layer where they belong.

## Supabase storage details and URL form

- Bucket: `face_oftheusers`
- Folder for registration images: `Registration/`
- Stored object path example: `Registration/20251227_abcdef1234.jpg`
- Public URL pattern (if object is public):
  `https://<PROJECT>.supabase.co/storage/v1/object/public/face_oftheusers/Registration/<filename>.jpg`

## Frontend implementation (recommended)

Prerequisites:

- Install the official Supabase client in the frontend app (if you prefer client-side uploads):

```bash
cd face-auth-frontend
npm install @supabase/supabase-js
```

Example (React/Next) — upload captured image blob and call `/api/register`:

```tsx
// lib/supabaseClient.ts
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// In your register page / component
import { supabase } from "../lib/supabaseClient";
import { fileToDataURL } from "../lib/api"; // existing helper

async function uploadAndRegister(dataUrl: string, formData: any) {
  // Convert dataURL to blob
  const res = await fetch(dataUrl);
  const blob = await res.blob();

  const filename = `Registration/${Date.now()}_${Math.random()
    .toString(36)
    .slice(2, 10)}.jpg`;

  // Upload to Supabase Storage (public by default depending on your bucket policy)
  const { data, error: uploadError } = await supabase.storage
    .from("face_oftheusers")
    .upload(filename, blob, { contentType: "image/jpeg" });

  if (uploadError) throw uploadError;

  // `filename` is the storage path used by webapp_new.py when calling download_from_storage
  const payload = {
    ...formData,
    temp_storage_path: filename,
  };

  // Post to backend register endpoint
  const resp = await fetch(
    (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:5000") +
      "/api/register",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
  return resp.json();
}
```

## Notes on permissions and keys

- Client-side upload with `@supabase/supabase-js` typically uses the **anon** public key. That key allows uploads only when the bucket policy permits it. Configure Supabase Storage policies to allow authenticated/unauthenticated uploads as appropriate.
- If your bucket must remain private and you don't want to expose upload capability to the browser, implement a small backend endpoint that accepts the captured data URL (or blob via multipart), and the backend (using the service role key) uploads to storage and returns the `temp_storage_path` — then the frontend calls `/api/register` with that `temp_storage_path`.
- Avoid embedding the Supabase **service_role** key in client-side code — it must remain secret on the server.

## Alternative: upload via backend (if you don't want client upload)

1. Frontend posts captured `dataURL` (or multipart file) to a backend endpoint, e.g. `/api/upload_temp_and_register`.
2. Backend uses its `SUPABASE_SERVICE_ROLE_KEY` with the Supabase Python client to upload to `face_oftheusers/Registration/<filename>` and returns the `temp_storage_path` (or proceeds to call the existing `/api/register` logic internally).

## Backend expectations (`webapp_new.py`)

- Environment variables required for storage access:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY` (for server-side uploads or downloads when necessary)
  - `SUPABASE_DB_URL` (or `DATABASE_URL`) for Postgres
  - `SUPABASE_BUCKET` should be set to `face_oftheusers` (or pass the bucket name you use)
- `/api/register` supports `temp_storage_path` (or `temp_path`) in the request payload. When provided, `webapp_new.py` calls `download_from_storage(temp_path)` and proceeds to attach the image and compute embedding.
- No change to `/api/register` is required if you send `temp_storage_path` equal to the storage path (for example, `Registration/abc.jpg`).

## Example request payload to `/api/register`

POST /api/register
Content-Type: application/json

{
"display_name": "Alice",
"username": "alice123",
"consent_terms": true,
"email": "alice@example.com",
"temp_storage_path": "Registration/20251227_abcdef1234.jpg"
}

## How `webapp_new.py` uses `temp_storage_path`

- It calls `raw = download_from_storage(temp_path)` which will try the Supabase storage SDK download and, if necessary, resolve the public URL and fetch with `requests.get`.
- It will then compute face encoding (`compute_face_encoding`) and insert the user, user_image row, and embedding.

## Edge cases & debugging tips

- If `download_from_storage` fails with `unable to retrieve file from storage`, ensure the `SUPABASE_BUCKET` and keys are correct and the file exists at that path in the bucket.
- If client-side uploads are allowed but you need the file to be publicly accessible via the public URL pattern, make sure the bucket policy allows public read or call `get_public_url` after upload.
- To confirm the final URL format, check the Supabase dashboard or call `supabase.storage.from('face_oftheusers').get_public_url(filename)`.

## Next steps (implementation options)

- I can add the frontend upload code into `face-auth-frontend/app/register/page.tsx` to perform the capture → upload → register flow.
- Or I can implement a small backend upload proxy that uploads the captured data URL to Supabase (server-side) and returns `temp_storage_path` for the frontend to pass to `/api/register`.

If you want, I will now implement the client-side upload flow into the register page (requires adding `@supabase/supabase-js` and environment variables). Which option do you prefer?
