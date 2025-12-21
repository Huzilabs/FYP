import webapp_new
from pathlib import Path
user_id = Path('tests/last_user_id.txt').read_text().strip()
conn = webapp_new.get_db_conn()
cur = conn.cursor()
cur.execute('SELECT embedding_id, user_id, source, created_at FROM public.embeddings WHERE user_id = %s', (user_id,))
rows = cur.fetchall()
print('found', len(rows), 'embeddings for user', user_id)
for r in rows:
    print(r)
cur.close()
conn.close()
