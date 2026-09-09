import httpx
from db import SessionLocal
from models import Scan
import uuid

session = SessionLocal()
# Create dummy scan
scan_id = str(uuid.uuid4())
dummy = Scan(id=scan_id, target_url="https://example.com", status="running", user_id="ba3f1a03-e5cc-4e9e-a32b-92816582ec50")
session.add(dummy)
session.commit()

s1 = session.query(Scan).filter_by(id=scan_id).first()
print(f"BEFORE CANCEL: {s1.id} -> {s1.status}")

# Cancel via API
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("web/.env.local")
url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supa = create_client(url, key)
res = supa.auth.sign_in_with_password({"email": "standarduser@example.com", "password": "SecurePass123!"})
jwt = res.session.access_token

resp = httpx.post(f"http://localhost:8000/api/v1/scans/{scan_id}/cancel", headers={"Authorization": f"Bearer {jwt}"})
print(f"API RESPONSE: {resp.status_code} {resp.text}")

session.refresh(s1)
print(f"AFTER CANCEL: {s1.id} -> {s1.status}")
