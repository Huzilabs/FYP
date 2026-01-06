import psycopg2
import traceback
import sys

# Direct Supabase host DSN using provided password
dsn = "postgresql://postgres:SxQYiPMwdOksNLLB@db.qvdvxrpgxnlmflklbcep.supabase.co:5432/postgres?sslmode=require"
print('Attempting DB connect to host:', dsn.split('@')[1].split(':')[0])
try:
    conn = psycopg2.connect(dsn, connect_timeout=10)
    print('CONNECTED')
    conn.close()
    sys.exit(0)
except Exception:
    traceback.print_exc()
    sys.exit(2)
