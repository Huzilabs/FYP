from dotenv import load_dotenv
load_dotenv()
import os

d = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
print(d if d is not None else '')