import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = FastAPI(title="AI QA Agent SaaS API")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_anon_key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase_service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Use Service Role Key for backend if available to bypass RLS, otherwise fallback to Anon Key
supabase_key = supabase_service_key if supabase_service_key else supabase_anon_key

if not supabase_url or not supabase_key:
    raise RuntimeError("Supabase credentials not found in .env")

supabase: Client = create_client(supabase_url, supabase_key)

class ScanRequest(BaseModel):
    url: str
    max_pages: int = 10
    auth_token: str | None = None

def get_scan(scan_id: str):
    response = supabase.table("scans").select("*").eq("id", scan_id).execute()
    if len(response.data) > 0:
        return response.data[0]
    return None

def update_scan(scan_id: str, status: str, report_path: str = None, json_path: str = None):
    data = {"status": status}
    if status == "completed":
        data["completed_at"] = datetime.now().isoformat()
        data["report_path"] = report_path
        data["json_path"] = json_path
        
    supabase.table("scans").update(data).eq("id", scan_id).execute()

def run_qa_pipeline(scan_id: str, url: str, max_pages: int, auth_token: str):
    """Run the QA pipeline as a background subprocess."""
    update_scan(scan_id, "running")
    
    # Set up environment variables to tell run_qa.py to use a specific prefix if we were to modify it.
    # Currently we just run it, but we can capture the output.
    cmd = [sys.executable, "run_qa.py", url, "--max-pages", str(max_pages)]
    if auth_token:
        cmd.extend(["--auth-token", auth_token])
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT_DIR)
        
        # We need to find the final report generated from the stdout
        # The script prints: 
        # Final JSON: results/final_qa_report_xxx.json
        # Final Markdown: results/final_qa_report_xxx.md
        json_path = None
        md_path = None
        for line in result.stdout.splitlines():
            if line.startswith("Final JSON:"):
                json_path = line.split(":", 1)[1].strip()
            elif line.startswith("Final Markdown:"):
                md_path = line.split(":", 1)[1].strip()
                
        if json_path and md_path and result.returncode == 0:
            update_scan(scan_id, "completed", md_path, json_path)
        else:
            update_scan(scan_id, "failed")
            print(f"Subprocess failed. Return code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            
    except Exception as e:
        update_scan(scan_id, "failed")
        print(f"Background task exception: {e}")

@app.post("/api/scans")
async def create_scan(request: ScanRequest, background_tasks: BackgroundTasks, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise Exception("Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

    scan_id = str(uuid4())
    
    supabase.table("scans").insert({
        "id": scan_id,
        "user_id": user.id,
        "url": request.url,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }).execute()
    
    background_tasks.add_task(run_qa_pipeline, scan_id, request.url, request.max_pages, request.auth_token)
    
    return {"scan_id": scan_id, "status": "pending", "message": "Scan queued successfully."}

@app.get("/api/scans/{scan_id}")
async def get_scan_status(scan_id: str):
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    # If completed, load the JSON results so the frontend can display them easily
    response = scan.copy()
    if scan["status"] == "completed" and scan["json_path"]:
        try:
            with open(os.path.join(ROOT_DIR, scan["json_path"]), "r") as f:
                response["results"] = json.load(f)
        except Exception:
            response["results"] = None
            
    return response

@app.get("/")
def read_root():
    return {"message": "AI QA Agent SaaS API is running."}
