import importlib.util
import traceback

# load webapp_new by path
spec = importlib.util.spec_from_file_location('webapp_new', r'c:\Users\uses\Downloads\face recognition\webapp_new.py')
webapp_new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webapp_new)

print('Connected to DB, running pgvector enablement steps...')
conn = webapp_new.get_db_conn()
cur = conn.cursor()
try:
    # Create extension
    print('Creating extension vector if not exists...')
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    print('Extension ensured.')

    # Alter column type to vector(128) if possible (try qualified type)
    try:
        print('Altering public.embeddings.embedding to vector_ext.vector(128) if needed...')
        cur.execute("ALTER TABLE public.embeddings ALTER COLUMN embedding TYPE vector_ext.vector(128) USING embedding::vector_ext.vector")
        conn.commit()
        print('Altered column to vector_ext.vector(128).')
    except Exception as exc:
        conn.rollback()
        print('Alter column step skipped or failed (non-fatal):', exc)

    # Create or replace nearest function
        print('Creating public.find_nearest_embeddings function (vector_ext.vector type)...')
        cur.execute('''
        CREATE OR REPLACE FUNCTION public.find_nearest_embeddings(q vector_ext.vector(128), limit_count INT DEFAULT 5)
        RETURNS TABLE (embedding_id BIGINT, user_id UUID, dist DOUBLE PRECISION, created_at TIMESTAMPTZ)
        LANGUAGE sql STABLE
        SET search_path = vector_ext, public
        AS $$
            SELECT id, user_id, (embedding <-> q) AS dist, created_at
            FROM public.embeddings
            ORDER BY embedding <-> q
            LIMIT limit_count;
        $$;
        ''')
    conn.commit()
    print('Function created.')

except Exception:
    traceback.print_exc()
    try:
        conn.rollback()
    except Exception:
        pass
finally:
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass

print('pgvector enablement completed.')

# Quick verification: compute encoding for test image and call the function
IMG = r'c:\Users\uses\Downloads\face recognition\data\temp\2fd455e0-f9db-419e-95b4-922e5869bc02.jpg'
import os
if os.path.exists(IMG):
    from PIL import Image
    import numpy as np
    import base64
    import io
    with open(IMG, 'rb') as f:
        b = f.read()
    img = Image.open(io.BytesIO(b)).convert('RGB')
else:
    print('Test image not found:', IMG)
    raise SystemExit(1)

arr = np.array(img)
enc = webapp_new.compute_face_encoding(arr)
if enc is None:
    print('No face encoding computed; cannot verify function call')
    raise SystemExit(1)

# call the DB function with limit 5
conn = webapp_new.get_db_conn()
cur = conn.cursor()
try:
    vec_literal = 'ARRAY[' + ','.join(repr(float(x)) for x in enc) + ']::vector_ext.vector'
    sql = f"SELECT embedding_id, user_id, dist FROM public.find_nearest_embeddings({vec_literal}, %s)"
    cur.execute(sql, (5,))
    rows = cur.fetchall()
    print('find_nearest_embeddings returned', len(rows), 'rows')
    for r in rows:
        print(r)
    conn.commit()
except Exception:
    traceback.print_exc()
    try:
        conn.rollback()
    except Exception:
        pass
finally:
    try:
        cur.close()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass

print('Verification completed.')
