"""
Challenge App E — Single Page Application (SPA).
Defects:
1. Fetch API /api/v1/feed?page=3 returns HTTP 500 (Async API Error)
2. Dynamic module load button throws Uncaught Promise Rejection (JavaScript)
3. Settings view contains unconstrained element causing layout overflow (UI Overflow)
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Challenge SPA App")


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Modern SPA Dashboard</title>
        <style>
            .page { display: none; }
            .active { display: block; }
        </style>
    </head>
    <body>
        <h1>Single Page Application</h1>
        <nav>
            <button onclick="showPage('feed-page')" id="tab-feed">Feed</button>
            <button onclick="showPage('settings-page')" id="tab-settings">Settings</button>
            <button onclick="loadLazyChunk()" id="tab-lazy">Load Lazy Chunk (Broken JS)</button>
        </nav>

        <div id="feed-page" class="page active">
            <h2>Activity Feed</h2>
            <div id="feed-content">Loading feed...</div>
            <button onclick="fetchFeed(3)" id="btn-page-3">Load Feed Page 3 (Triggers 500)</button>
        </div>

        <div id="settings-page" class="page">
            <h2>User Settings</h2>
            <div style="width: 5000px; background: orange; height: 40px;" id="spa-overflow">
                SPA Overflow Banner Stretching Viewport
            </div>
        </div>

        <script>
        function showPage(pageId) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(pageId).classList.add('active');
        }

        function fetchFeed(page) {
            fetch('/api/v1/feed?page=' + page)
                .then(res => {
                    if(!res.ok) throw new Error("HTTP error " + res.status);
                    return res.json();
                })
                .then(data => {
                    document.getElementById('feed-content').innerText = JSON.stringify(data);
                })
                .catch(err => console.error("Feed error:", err));
        }

        function loadLazyChunk() {
            // DEFECT: Unhandled Promise Rejection!
            Promise.reject(new Error("ChunkLoadError: Failed to fetch module /static/chunk_missing.js"));
        }

        // Initial load
        fetchFeed(1);
        </script>
    </body>
    </html>
    """


@app.get("/api/v1/feed")
def get_feed(page: int = 1):
    # DEFECT: Page 3 returns HTTP 500!
    if page == 3:
        raise HTTPException(status_code=500, detail="Async Feed Aggregator Service Unavailable")
    return {"page": page, "items": [{"id": 1, "text": "Post 1"}]}
