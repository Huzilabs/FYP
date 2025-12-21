import importlib.util
spec = importlib.util.spec_from_file_location('webapp_new', r'c:\Users\uses\Downloads\face recognition\webapp_new.py')
webapp_new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(webapp_new)

conn = webapp_new.get_db_conn()
cur = conn.cursor()
try:
    cur.execute("SELECT n.nspname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE t.typname = 'vector'")
    rows = cur.fetchall()
    print('vector type schema rows:', rows)
    conn.commit()
except Exception as e:
    print('error querying pg_type:', e)
    conn.rollback()
finally:
    try:
        cur.close()
    except:
        pass
    try:
        conn.close()
    except:
        pass
