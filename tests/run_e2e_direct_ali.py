import base64
import io
import uuid
import time
from pathlib import Path
import json

import importlib.util
spec = importlib.util.spec_from_file_location('webapp_new', r'c:\Users\uses\Downloads\face recognition\webapp_new.py')
webapp_new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webapp_new)
from PIL import Image
import numpy as np

IMG_PATH = Path('data/images/ali/1765734988.jpg')
if not IMG_PATH.exists():
    print('image not found:', IMG_PATH)
    raise SystemExit(1)

with open(IMG_PATH, 'rb') as f:
    img_bytes = f.read()

img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
img_arr = np.array(img)

print('Computing face encoding...')
enc = webapp_new.compute_face_encoding(img_arr)
if enc is None:
    print('No face encoding found; aborting')
    raise SystemExit(1)
print('Encoding length:', len(enc))

# Create a user
conn = webapp_new.get_db_conn()
cur = conn.cursor()
try:
    username = 'ali_direct_' + uuid.uuid4().hex[:8]
    display_name = 'Ali Direct E2E'
    cur.execute(
        """
            INSERT INTO public.users (display_name, username, email, phone, created_at, verified)
            VALUES (%s, %s, %s, %s, now(), false) RETURNING id
        """,
        (display_name, username, None, None),
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    print('Created user:', user_id)
except Exception as exc:
    conn.rollback()
    print('Failed to create user:', exc)
    raise
finally:
    cur.close()
    conn.close()

# Save image to storage and insert user_images
try:
    filename = f"{int(time.time())}_{uuid.uuid4().hex}.jpg"
    storage_path = f"{user_id}/{filename}"
    public_url = webapp_new.save_image_to_storage(storage_path, img_bytes) or storage_path
    print('Saved image to storage:', public_url)
except Exception as exc:
    print('Failed to save image to storage:', exc)
    raise

# Insert user_images row
conn = webapp_new.get_db_conn()
cur = conn.cursor()
try:
    cur.execute(
        """
            INSERT INTO public.user_images (user_id, storage_path, public_url, width, height, mime_type, uploaded_at, is_profile, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, now(), %s, %s)
        """,
        (user_id, storage_path, public_url, img_arr.shape[1], img_arr.shape[0], 'image/jpeg', True, len(img_bytes)),
    )
    conn.commit()
    print('Inserted user_images row')
except Exception as exc:
    conn.rollback()
    print('Failed to insert user_images:', exc)
    raise
finally:
    cur.close()
    conn.close()

# Insert embedding
emb_conn = webapp_new.get_db_conn()
emb_cur = emb_conn.cursor()
try:
    webapp_new.insert_embedding(emb_cur, user_id, enc, 'direct_ali')
    emb_conn.commit()
    print('Inserted embedding for user', user_id)
except Exception as exc:
    emb_conn.rollback()
    print('Failed to insert embedding:', repr(exc))
    raise
finally:
    emb_cur.close()
    emb_conn.close()

# Verify embeddings
vconn = webapp_new.get_db_conn()
vcur = vconn.cursor()
try:
    vcur.execute('SELECT id, user_id, source, created_at FROM public.embeddings WHERE user_id = %s', (user_id,))
    rows = vcur.fetchall()
    print('Embeddings rows found:', len(rows))
    for r in rows:
        print(r)
    vconn.commit()
except Exception as exc:
    vconn.rollback()
    print('Failed to query embeddings:', exc)
finally:
    vcur.close()
    vconn.close()

print('Direct E2E for ALI completed.')
