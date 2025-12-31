import psycopg2
import traceback
import sys

def main():
    try:
        conn = psycopg2.connect(
            user='postgres',
            password='ualWlyhkFgCmcliy',
            host='db.gnftheueosouyceptdsb.supabase.co',
            port=5432,
            dbname='postgres',
            sslmode='require',
            connect_timeout=10
        )
        conn.close()
        print('CONNECT_OK')
    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
