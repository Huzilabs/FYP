import sys
import os

# Ensure repo root is on sys.path (running from tools/ may set path0 to tools)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from db_supabase import get_all_users, get_all_embeddings

try:
    users = get_all_users()
    embeds = get_all_embeddings()
    print('Supabase: users =', len(users))
    print('Supabase: embeddings =', len(embeds))
except Exception as e:
    print('Error connecting to Supabase:', e)
