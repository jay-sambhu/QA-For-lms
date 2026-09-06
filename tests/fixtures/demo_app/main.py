"""
Full QA Benchmark Application with Intentional Seeded Defects (Phase 18).
"""
import time
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="JASUSS Phase 18 Comprehensive QA Benchmark App")


@app.get("/", response_class=HTMLResponse)
def get_home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>JASUSS Benchmark Target Application</title></head>
    <body>
        <h1>JASUSS Phase 18 Autonomous QA Benchmark Target</h1>
        <nav>
            <a href="/login">Login Page</a> |
            <a href="/form">Form Page</a> |
            <a href="/user/100/profile">User 100 Profile</a> |
            <a href="/admin">Admin Area (Unprotected)</a> |
            <a href="/ui/nav">Broken Link Page</a> |
            <a href="/ui/overflow">Layout Overflow Page</a> |
            <a href="/js/error">JS Error Page</a> |
            <a href="/js/rejection">JS Rejection Page</a>
        </nav>
    </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
def get_login():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Login Page</title></head>
    <body>
        <h2>Account Login</h2>
        <form action="/login" method="POST">
            <input type="email" name="email" placeholder="Email" id="email" required />
            <input type="password" name="password" placeholder="Password" id="password" required />
            <button type="submit" id="btn_submit">Sign In</button>
        </form>
    </body>
    </html>
    """


@app.post("/login")
def post_login():
    # Defect AUTH-001: Server crashes on login attempt
    raise HTTPException(status_code=500, detail="Authentication server exception")


@app.get("/form", response_class=HTMLResponse)
def get_form():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Form Validation Benchmark</title></head>
    <body>
        <h2>Data Submission Form</h2>
        <form action="/form/submit" method="POST">
            <input type="text" name="username" placeholder="Username" id="username" />
            <input type="text" name="age" placeholder="Age (Boundary Bug)" id="age" />
            <button type="submit" id="btn_form_submit">Submit</button>
        </form>
    </body>
    </html>
    """


@app.post("/form/submit")
def post_form_submit():
    # Defect FORM-001: Missing validation accepts malicious input
    return {"status": "success", "message": "Payload accepted without validation"}


@app.get("/admin", response_class=HTMLResponse)
def get_admin():
    # Defect AUTHZ-001: Unprotected admin dashboard accessible without Bearer token
    return "<h1>Admin Control Panel (Unprotected Authorization Bypass Defect)</h1>"


@app.get("/user/{user_id}/profile", response_class=HTMLResponse)
def get_user_profile(user_id: int):
    # Defect AUTHZ-002: Horizontal privilege escalation allows reading arbitrary user profiles
    return f"<h1>Profile of User #{user_id} (Horizontal Privacy Leak Defect)</h1>"


@app.get("/ui/nav", response_class=HTMLResponse)
def get_broken_nav():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Broken Navigation</title></head>
    <body>
        <h1>Broken Navigation Page</h1>
        <a href="/non-existent-dead-link-404">Click Dead Link</a>
    </body>
    </html>
    """


@app.get("/ui/overflow", response_class=HTMLResponse)
def get_layout_overflow():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>Layout Overflow Benchmark</title></head>
    <body>
        <h1>Layout Overflow Page</h1>
        <div style="width: 8000px; white-space: nowrap; background: red;">
            Overflowing Content Clipping Layout Elements Beyond Viewport Width Boundary
        </div>
    </body>
    </html>
    """


@app.get("/js/error", response_class=HTMLResponse)
def get_js_error():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>JS Console Error</title></head>
    <body>
        <h1>JS Error Page</h1>
        <script>
            console.error("Uncaught TypeError: Cannot read properties of undefined (reading 'token')");
        </script>
    </body>
    </html>
    """


@app.get("/js/rejection", response_class=HTMLResponse)
def get_js_rejection():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head><title>JS Unhandled Rejection</title></head>
    <body>
        <h1>JS Unhandled Rejection Page</h1>
        <script>
            Promise.reject(new Error("Unhandled async promise rejection in background worker"));
        </script>
    </body>
    </html>
    """


@app.get("/api/v1/broken")
def get_broken_api():
    # Defect API-001: Internal Server Error 500
    raise HTTPException(status_code=500, detail="Database connection timeout error")


@app.get("/api/v1/slow")
def get_slow_api():
    time.sleep(2.0)
    return {"status": "ok", "latency": "2000ms"}
