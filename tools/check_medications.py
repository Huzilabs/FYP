import os,sys,psycopg2,traceback

def load_dsn_from_envfile(path='.env'):
    try:
        with open(path,'r',encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line.startswith('SUPABASE_DB_URL='):
                    return line.split('=',1)[1]
    except Exception:
        pass
    return None

if __name__=='__main__':
    user='2c8e853a-017e-4ccd-80d2-52d136b86571'
    dsn=os.environ.get('SUPABASE_DB_URL') or load_dsn_from_envfile()
    if not dsn:
        print('NO DSN')
        sys.exit(2)
    print('Using DSN prefix:', dsn.split('@')[0]+"@...")
    try:
        conn=psycopg2.connect(dsn)
        cur=conn.cursor()
        cur.execute('SELECT id, name, dosage, frequency, time, instructions, created_at FROM public.user_medications WHERE user_id=%s ORDER BY created_at DESC', (user,))
        rows=cur.fetchall()
        print('Found', len(rows), 'rows')
        for r in rows:
            print(r)
        cur.close()
        conn.close()
    except Exception:
        traceback.print_exc()
        sys.exit(3)
