import asyncio
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import httpx

load_dotenv("web/.env.local")
url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(url, key)

res = supabase.auth.sign_in_with_password({"email": "standarduser@example.com", "password": "SecurePass123!"})
jwt = res.session.access_token

# Hit an authenticated endpoint
resp = httpx.get("http://localhost:8000/api/v1/scans", headers={"Authorization": f"Bearer {jwt}"})
print(resp.json())
