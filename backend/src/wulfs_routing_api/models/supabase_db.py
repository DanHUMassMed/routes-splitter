import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase: Client | None = None

if not url or not key:
    print("WARNING: Supabase credentials not found in .env file. Database functionality will be disabled.")
else:
    try:
        supabase = create_client(url, key)  # no type hint here
        print("✅ Supabase client initialized.")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize Supabase client: {e}")