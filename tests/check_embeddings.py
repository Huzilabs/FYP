import os, psycopg2, json
from pathlib import Path

DB = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
if not DB:
    print('SUPABASE_DB_URL not set')
    raise SystemExit(1)

user_id = Path('tests/last_user_id.txt').read_text().strip()
conn = psycopg2.connect(DB)
cur = conn.cursor()
cur.execute('SELECT embedding_id, user_id, source, created_at FROM public.embeddings WHERE user_id = %s', (user_id,))
rows = cur.fetchall()
print('found', len(rows), 'embeddings for user', user_id)
for r in rows:
    print(r)
cur.close()
conn.close()
