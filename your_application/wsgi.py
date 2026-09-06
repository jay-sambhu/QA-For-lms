import os
import sys

# Fail-safe launcher for Render default 'gunicorn your_application.wsgi' command.
# Replaces gunicorn process with Uvicorn running FastAPI api.main:app.
port = os.environ.get("PORT", "8000")
print(f"JASUSS Render Fallback: Launching Uvicorn on port {port}...")
os.execvp("uvicorn", ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", port])
