from dotenv import load_dotenv
load_dotenv()
import os, sys, traceback, re

d = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
print('SUPABASE_DB_URL present:', bool(d))
if d:
    # mask password for safe printing
    try:
        masked = re.sub(r'://([^:]+):[^@]+@', r'://\\1:****@', d)
    except Exception:
        masked = '<failed to mask>'
    print('CONNECT_STR_MASKED=', masked)
else:
    print('CONNECT_STR_MASKED= <none>')

try:
    import psycopg2
except Exception as e:
    print('psycopg2 not installed or import failed:', e)
    sys.exit(1)

if not d:
    print('No connection string available; aborting connect test')
    sys.exit(0)

try:
    print('Attempting psycopg2.connect...')
    conn = psycopg2.connect(d)
    conn.close()
    print('Connection succeeded')
except Exception as e:
    print('Connection failed:', e)
    traceback.print_exc()
    sys.exit(2)
