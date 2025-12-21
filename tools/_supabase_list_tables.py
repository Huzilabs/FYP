from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    print('Missing credentials in .env')
    raise SystemExit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check existence of expected tables by attempting a safe LIMIT 0 select.
tables_to_check = ['users', 'embeddings', 'user_images']
existing = {}
for t in tables_to_check:
    try:
        # try selecting zero rows; if table doesn't exist PostgREST will return an error
        # Use '*' instead of literal '1' to avoid PostgREST interpreting it as a column name
        resp = sb.postgrest.from_(t).select('*').limit(0).execute()
        # If execute() returned without exception, table exists (resp.data may be [])
        existing[t] = True
    except Exception as e:
        existing[t] = False
        # capture the error message for debugging
        existing[f"{t}_error"] = str(e)

print('table existence:')
for t in tables_to_check:
    if existing.get(t):
        print(f"  {t}: EXISTS")
    else:
        print(f"  {t}: MISSING (error: {existing.get(f'{t}_error')})")

# If users exists, try to fetch zero rows and report column keys by requesting 1 row (if any rows exist)
if existing.get('users'):
    try:
        resp = sb.postgrest.from_('users').select('*').limit(1).execute()
        if resp.data:
            print('\nSample users row columns:')
            for k in resp.data[0].keys():
                print(' ', k)
        else:
            print('\nusers table exists but has no rows; columns cannot be inferred from data via PostgREST.')
            print('If you want column listing, run this SQL in Supabase SQL editor:')
            print("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='users';")
    except Exception as e:
        print('users sample query error:', e)
