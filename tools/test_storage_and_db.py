"""
Quick test script to verify Supabase Storage upload and basic DB insert.
Usage (from repo root, after activating conda env):

conda activate face-recognition-project
python .\tools\test_storage_and_db.py --image data/test_upload.jpg

It will:
- Load env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_URL, SUPABASE_BUCKET)
- Connect to Postgres and print a few table column names
- Upload the provided image to Storage under `temp/` and print public URL
- Insert a test user row and a corresponding `user_images` row

Make sure you have `python-dotenv`, `supabase`, `psycopg2` (or psycopg2-binary), and `Pillow` installed.
"""
import os
import argparse
import uuid
import io
from dotenv import load_dotenv
from supabase import create_client
import psycopg2
from PIL import Image

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_DB_URL = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET')


def fail(msg):
    print('ERROR:', msg)
    raise SystemExit(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image', default='data/test_upload.jpg', help='Path to an image to upload')
    args = p.parse_args()

    print('env:', 'SUPABASE_URL' , bool(SUPABASE_URL), 'SUPABASE_BUCKET', SUPABASE_BUCKET)
    if not (SUPABASE_URL and SUPABASE_KEY and SUPABASE_DB_URL and SUPABASE_BUCKET):
        fail('Missing one or more required env vars. See README and .env')

    # verify DB connection
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()
        cur.execute('SELECT version()')
        print('Postgres version:', cur.fetchone())
        # list columns for users/user_images/embeddings
        for t in ('users','user_images','embeddings'):
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", (t,))
            cols = cur.fetchall()
            print(f"Table {t} columns: {len(cols)}")
            for c in cols:
                print('  ', c)
        cur.close()
        conn.close()
    except Exception as e:
        fail('DB connection/listing failed: ' + repr(e))

    # verify storage client
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        print('Supabase client created')
        # list bucket (may be permission restricted)
        try:
            listing = sb.storage.from_(SUPABASE_BUCKET).list(limit=1)
            print('Storage list result (trim):', type(listing), str(listing)[:200])
        except Exception as le:
            print('Storage list failed (may be permissioned):', repr(le))
    except Exception as e:
        fail('Supabase client creation failed: ' + repr(e))

    # upload image
    if not os.path.exists(args.image):
        fail(f'Image not found: {args.image} - please place a test image at that path')
    with open(args.image, 'rb') as f:
        data = f.read()

    key = f"temp/test_upload_{uuid.uuid4().hex}.jpg"
    try:
        res = sb.storage.from_(SUPABASE_BUCKET).upload(key, data)
        public = sb.storage.from_(SUPABASE_BUCKET).get_public_url(key)
        public_url = None
        if isinstance(public, dict):
            public_url = public.get('publicURL') or public.get('public_url')
        else:
            # older/newer clients may return different shapes
            try:
                public_url = public['publicURL']
            except Exception:
                public_url = str(public)
        print('Uploaded to', key, 'public_url:', public_url)
    except Exception as e:
        fail('Upload failed: ' + repr(e))

    # Create test user and user_images row
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO public.users (display_name, username, email, created_at) VALUES (%s,%s,%s,now()) RETURNING id", ('Test Upload', 'test_upload_'+uuid.uuid4().hex[:8], 'test@example.com'))
        uid = cur.fetchone()[0]
        conn.commit()
        print('Created user id', uid)
        # insert user_images
        cur.execute("INSERT INTO public.user_images (user_id, storage_path, public_url, width, height, mime_type, uploaded_at, is_profile, file_size) VALUES (%s,%s,%s,%s,%s,%s,now(),%s,%s) RETURNING id",
                    (uid, key, public_url, None, None, 'image/jpeg', True, len(data)))
        imgid = cur.fetchone()[0]
        conn.commit()
        print('Inserted user_images id', imgid)
        cur.close()
        conn.close()
    except Exception as e:
        fail('DB insert failed: ' + repr(e))

    print('Test completed successfully. Verify in Supabase dashboard: users and storage bucket')

if __name__ == '__main__':
    main()
