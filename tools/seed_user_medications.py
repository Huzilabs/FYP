import os
import sys
import psycopg2
import traceback

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python tools/seed_user_medications.py <user_id> <med1>[,<med2>,...]')
        sys.exit(2)
    user_id = sys.argv[1]
    meds = sys.argv[2].split(',')
    dsn = os.getenv('SUPABASE_DB_URL')
    if not dsn:
        print('SUPABASE_DB_URL not set in environment')
        sys.exit(2)
    print('Using DSN prefix:', dsn.split('@')[0] + '@...')
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        inserted = []
        for m in meds:
            name = m.strip()
            if not name:
                continue
            cur.execute("INSERT INTO public.user_medications (user_id, name) VALUES (%s, %s) RETURNING id", (user_id, name))
            row = cur.fetchone()
            inserted.append(str(row[0]))
        conn.commit()
        cur.close()
        conn.close()
        print('Inserted medication ids:', inserted)
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(3)
