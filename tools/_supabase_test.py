from dotenv import load_dotenv
from supabase import create_client
import os
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print("SUPABASE_URL present?", bool(SUPABASE_URL))
print("SUPABASE_KEY present?", bool(SUPABASE_KEY))
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Missing credentials in .env or not readable")
else:
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        # list buckets
        try:
            buckets = sb.storage.list_buckets()
            print('Buckets call ok, count =', len(buckets))
        except Exception as e:
            print('Buckets call error:', e)
        # try to select one user row if table exists
        try:
            resp = sb.table('users').select('id,name').limit(1).execute()
            print('users query data:', getattr(resp, 'data', None))
        except Exception as e:
            print('users query error:', e)
    except Exception as e:
        print('Supabase client init error:', e)
