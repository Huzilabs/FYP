# Supabase Migration Guide

This document describes how to migrate your local face embeddings and images (stored in `data/names.pkl`, `data/faces_data.pkl` and `data/images/`) into Supabase (Postgres tables + Storage). It also explains how to integrate Supabase into the current Flask `webapp.py` and security/verification best practices.

## Summary

- Current local storage:
  - `data/names.pkl` — list of display names (strings)
  - `data/faces_data.pkl` — list of 128-D face embeddings (float arrays)
  - `data/images/<name>/*` — captured images per user
- Goal: keep a backup locally and move canonical storage to Supabase:
  - `users` table: user metadata
  - `embeddings` table: embedding vectors (JSON or pgvector)
  - `images` bucket: upload user images to Supabase Storage

Keep the pickles as a backup until verification is complete.

## Why use Supabase

- Centralized storage and access from multiple servers
- Use Postgres features and Supabase Storage for images
- Optionally use `pgvector` for efficient nearest-neighbor queries
- Fine-grained access control via API keys and RLS

## Recommended Schema

1. Using pgvector (recommended for scale)

```sql
-- enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- users table
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  total_attendance INTEGER DEFAULT 0,
  last_attendance_time TIMESTAMP
);

-- embeddings table with pgvector
CREATE TABLE IF NOT EXISTS embeddings (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  embedding vector(128) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Optional: index for faster ANN (approximate search via ivfflat)
-- See pgvector docs for creating indexes appropriate to your usage
```

2. Simple JSON storage (quick, portable)

```sql
CREATE TABLE IF NOT EXISTS embeddings_json (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
  embedding JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## Storage bucket

- Create a bucket named `images` (public for demos; private for production). Store images at `users/{user_id}/{timestamp}.jpg`.

## Configuration (.env)

- Create a `.env` file (DO NOT commit). Add the keys:

```
SUPABASE_URL=https://<your-instance>.supabase.co
SUPABASE_KEY=<service-role-or-server-key>
# Optional: SUPABASE_ANON_KEY if you use anon keys for limited reads
```

Add `.env` to `.gitignore`. Keep only `.env.example` in the repo.

## Migration script (recommended)

Create `tools/migrate_to_supabase.py` (or run the script below). The script performs a dry-run by default — it prints actions without writing. After review you can run with `dry_run=False`.

Example script (concise version):

```python
import os, pickle
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA_DIR = os.path.join(ROOT, 'data')
NAMES_PKL = os.path.join(DATA_DIR, 'names.pkl')
FACES_PKL = os.path.join(DATA_DIR, 'faces_data.pkl')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')

def upload_image(user_id, local_path):
    key = f'users/{user_id}/{os.path.basename(local_path)}'
    with open(local_path, 'rb') as f:
        sb.storage.from_('images').upload(key, f)
    return sb.storage.from_('images').get_public_url(key)

def main(dry_run=True):
    names = pickle.load(open(NAMES_PKL, 'rb'))
    faces = pickle.load(open(FACES_PKL, 'rb'))
    assert len(names) == len(faces)
    for i, name in enumerate(names):
        user_id = name  # optionally generate UUIDs here
        print('MIGRATE', i+1, user_id)
        if not dry_run:
            sb.table('users').upsert({'id': user_id, 'name': name}).execute()
            emb = faces[i].tolist() if hasattr(faces[i], 'tolist') else faces[i]
            sb.table('embeddings').insert({'user_id': user_id, 'embedding': emb}).execute()
            user_images = os.path.join(IMAGES_DIR, name)
            if os.path.isdir(user_images):
                for fn in os.listdir(user_images):
                    upload_image(user_id, os.path.join(user_images, fn))

if __name__ == '__main__':
    main(dry_run=True)
```

Install client and run (PowerShell):

```powershell
conda run -n face-recognition-project pip install supabase
conda run -n face-recognition-project python tools\migrate_to_supabase.py
# inspect output, then run real migration
conda run -n face-recognition-project python -c "from tools.migrate_to_supabase import main; main(dry_run=False)"
```

## Update `webapp.py` to use Supabase (optional)

- Add a small helper to detect SUPABASE_URL/SUPABASE_KEY. If present, load embeddings from Supabase on startup (or on first request) and save new signups to Supabase (and to local pickles if you want a fallback).
- Keep imports lazy (`from supabase import create_client`) so the app still runs without `.env`.

Pseudocode:

```python
if SUPABASE_URL and SUPABASE_KEY:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    # load embeddings
    rows = sb.table('embeddings').select('user_id, embedding').execute().data
    names = [r['user_id'] for r in rows]
    encs = [np.array(r['embedding'], dtype=float) for r in rows]
else:
    names, encs = load_local_embeddings()
```

On signup: call `sb.table('users').upsert(...)`, `sb.table('embeddings').insert(...)` and upload the image via `sb.storage.from_('images').upload(...)`.

## Verification checklist

1. Run migration in dry-run mode and inspect output.
2. Migrate 2–3 sample users and verify rows in Supabase Console.
3. Confirm images are listed in Storage and public URLs (if bucket public) are reachable.
4. Update `webapp.py` to load from Supabase and test login for migrated users.
5. When satisfied, perform full migration and archive local pickles.

## Rollback strategy

- Keep local pickles intact until migration verified.
- If something goes wrong, you can delete inserted rows by `user_id` via Supabase Console or via the API.
- If you prefer, create a separate migration branch and push a tag when migration is completed.

## Security notes

- Use a server/service role key for migration and server writes. Keep it out of the repo.
- For production, configure RLS and minimum required privileges.

## Performance & scaling

- For small datasets (hundreds/thousands), fetching embeddings in memory and comparing in Python is OK.
- For bigger datasets, use `pgvector` and NN queries in SQL or an ANN engine (Faiss, Milvus).

## FAQ

- Q: Which model creates the embeddings?
- A: The current setup uses the `face_recognition` Python library which internally uses dlib's ResNet-based face embedding model (`dlib_face_recognition_resnet_model_v1`) to produce 128-D embeddings. In code this is produced by `face_recognition.face_encodings(image)`.

---

If you want, I can add `tools/migrate_to_supabase.py` to the repo (dry-run first) and a small patch in `webapp.py` to optionally use Supabase. Tell me which one you'd like me to create next.
