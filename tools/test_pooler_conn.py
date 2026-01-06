import os
import sys
import traceback
import psycopg2

# Use SUPABASE_DB_URL from env if set, otherwise fall back to provided DSN
dsn = os.getenv(
    "SUPABASE_DB_URL",
    "postgresql://postgres.qvdvxrpgxnlmflklbcep:SxQYiPMwdOksNLLB@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require",
)
print('Attempting DB connect using DSN prefix:', dsn.split('@')[0] + '@...')
try:
    conn = psycopg2.connect(dsn, connect_timeout=10)
    print('CONNECTED')
    conn.close()
    sys.exit(0)
except Exception:
    traceback.print_exc()
    sys.exit(2)
