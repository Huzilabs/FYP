import importlib, pathlib
m = importlib.import_module('webapp_new')
conn = m.get_db_conn()
cur = conn.cursor()
uid = pathlib.Path('tests/last_user_id.txt').read_text().strip()
cur.execute('SELECT id, user_id, source, created_at FROM public.embeddings WHERE user_id = %s', (uid,))
rows = cur.fetchall()
print('found', len(rows))
for r in rows:
    print(r)
cur.close()
conn.close()
