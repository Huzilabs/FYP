"""
Migration script: upload local pickles/images to Supabase
- Reads `data/names.pkl` and `data/faces_data.pkl` (parallel lists)
- Uploads images from `data/images/<name>/` to Supabase Storage bucket
- Inserts/updates users in `public.users`
- Inserts image metadata in `public.user_images`
- Inserts embeddings in `public.embeddings` as VECTOR(128)

USAGE (run locally from project root):

# set env vars first (example)
# Windows PowerShell example:
# $env:SUPABASE_URL='https://xyz.supabase.co'
# $env:SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'
# $env:SUPABASE_DB_URL='postgresql://postgres:password@db.xyz.supabase.co:5432/postgres'
# $env:SUPABASE_BUCKET='your-bucket-name'

# then run:
# conda run -n face-recognition-project python .\tools\migrate_pickles_to_supabase.py

NOTE: This script requires network access to your Supabase project and a server-only service role key.
Do NOT run this key from untrusted machines or embed it in client code.
"""

import os
import sys
import pickle
import glob
import mimetypes
from pathlib import Path
from PIL import Image
import psycopg2
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
NAMES_PKL = DATA_DIR / 'names.pkl'
EMB_PKL = DATA_DIR / 'faces_data.pkl'
IMAGES_DIR = DATA_DIR / 'images'

# env vars
SUPABASE_URL = os.getenv('SUPABASE_URL')
SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET')

if not (SUPABASE_URL and SERVICE_ROLE_KEY and SUPABASE_DB_URL and SUPABASE_BUCKET):
    print('Missing one or more required environment variables:')
    print('SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL (or DATABASE_URL), SUPABASE_BUCKET')
    sys.exit(2)

# Load pickles
if not NAMES_PKL.exists() or not EMB_PKL.exists():
    print('Pickle files not found in data/. Make sure names.pkl and faces_data.pkl exist.')
    sys.exit(1)

with open(NAMES_PKL, 'rb') as f:
    names = pickle.load(f)

with open(EMB_PKL, 'rb') as f:
    embeddings = pickle.load(f)

if not (isinstance(names, (list, tuple)) and isinstance(embeddings, (list, tuple))):
    print('Expected lists in pickles (names, embeddings).')
    sys.exit(1)

if len(names) != len(embeddings):
    print('names.pkl and faces_data.pkl lengths differ:', len(names), len(embeddings))
    # continue but warn

# Init Supabase storage client
sb = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# Connect to Postgres directly for reliable vector INSERTs
print('Connecting to Postgres...')
conn = psycopg2.connect(SUPABASE_DB_URL)
conn.autocommit = False
cur = conn.cursor()

summary = {'users_created':0, 'images_uploaded':0, 'embeddings_inserted':0}

for idx, name in enumerate(names):
    display_name = name
    username = (name.lower().replace(' ', '_'))[:60]
    emb = embeddings[idx] if idx < len(embeddings) else None

    # 1) create or get user
    try:
        cur.execute(
            """
            INSERT INTO public.users (display_name, username)
            VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (display_name, username)
        )
        user_id = cur.fetchone()[0]
        summary['users_created'] += 1
    except Exception as e:
        conn.rollback()
        print('Error inserting user', username, e)
        continue

    # 2) upload images if present
    user_images_path = IMAGES_DIR / name
    if user_images_path.exists() and user_images_path.is_dir():
        image_files = sorted(user_images_path.glob('*'))
        for i, img_path in enumerate(image_files):
            try:
                with open(img_path, 'rb') as fh:
                    data = fh.read()
                mime = mimetypes.guess_type(img_path.name)[0] or 'application/octet-stream'
                storage_path = f"{user_id}/{img_path.name}"
                # upload (upsert)
                res = sb.storage.from_(SUPABASE_BUCKET).upload(storage_path, data)
                # get public url
                public_url = sb.storage.from_(SUPABASE_BUCKET).get_public_url(storage_path).get('publicURL')
                # get image metadata
                try:
                    im = Image.open(img_path)
                    width, height = im.size
                    im.close()
                except Exception:
                    width = height = None
                file_size = img_path.stat().st_size

                # insert metadata
                cur.execute(
                    """
                    INSERT INTO public.user_images (user_id, storage_path, public_url, width, height, mime_type, uploaded_at, is_profile, file_size)
                    VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s)
                    RETURNING id
                    """,
                    (user_id, storage_path, public_url, width, height, mime, True if i==0 else False, file_size)
                )
                _img_id = cur.fetchone()[0]
                summary['images_uploaded'] += 1
            except Exception as e:
                conn.rollback()
                print('Failed to upload/record image', img_path, e)
                continue

    # 3) insert embedding
    if emb is not None:
        try:
            # build vector literal (cast to vector)
            # Note: numbers are injected directly; this script runs locally under your control.
            vec_literal = 'ARRAY[' + ','.join(repr(float(x)) for x in emb) + ']::vector'
            sql = f"INSERT INTO public.embeddings (user_id, embedding, source, created_at) VALUES (%s, {vec_literal}, %s, now()) RETURNING id"
            cur.execute(sql, (user_id, 'migration'))
            _eid = cur.fetchone()[0]
            summary['embeddings_inserted'] += 1
        except Exception as e:
            conn.rollback()
            print('Failed to insert embedding for', username, e)
            continue

    # commit per user to avoid large transactions
    conn.commit()
    print(f'Processed user {display_name} (id={user_id})')

print('\nMigration complete. Summary:')
for k,v in summary.items():
    print(f' - {k}: {v}')

cur.close()
conn.close()
