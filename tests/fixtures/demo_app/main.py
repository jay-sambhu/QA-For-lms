"""
Deliberately Testable Local Application for JASUSS Self-Testing & Golden Defect Verification.
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

app = FastAPI(title="JASUSS Self-Test Benchmark App")


@app.get("/", response_class=HTMLResponse)
def get_home():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>JASUSS Demo App</title></head>
    <body>
        <h1>Welcome to JASUSS Self-Test Target</h1>
        <a href="/login">Login Page</a>
        <a href="/form">Form Page</a>
        <a href="/broken-link">Broken Route</a>
        <a href="/js-error">JS Error Page</a>
        <a href="/layout">Layout Overflow Page</a>
        <a href="/admin">Unprotected Admin</a>
    </body>
    </html>
    """


@app.get("/login", response_class=HTMLResponse)
def get_login():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Login</title></head>
    <body>
        <h2>Login Form</h2>
        <form action="/login" method="POST">
            <input type="email" name="email" placeholder="Email" id="email" />
            <input type="password" name="password" placeholder="Password" id="password" />
            <button type="submit">Log In</button>
        </form>
    </body>
    </html>
    """


@app.post("/login")
def post_login():
    raise HTTPException(status_code=500, detail="Intentional Login System Crash")


@app.get("/form", response_class=HTMLResponse)
def get_form():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Form Validation</title></head>
    <body>
        <form action="/api/v1/submit" method="POST">
            <input type="text" name="data" id="data_input" />
            <button type="submit">Submit Data</button>
        </form>
    </body>
    </html>
    """


@app.get("/js-error", response_class=HTMLResponse)
def get_js_error():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>JS Error Page</title></head>
    <body>
        <script>
            console.error("Uncaught TypeError: Cannot read properties of undefined (reading 'process')");
        </script>
        <h1>Page with Console Error</h1>
    </body>
    </html>
    """


@app.get("/layout", response_class=HTMLResponse)
def get_layout():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Layout Overflow</title></head>
    <body>
        <div style="width: 5000px; overflow: scroll;">
            <p>Intentional horizontal layout overflow text causing UI clipping</p>
        </div>
    </body>
    </html>
    """


@app.get("/admin", response_class=HTMLResponse)
def get_admin():
    # Intentionally missing authentication check
    return "<h1>Admin Dashboard (Unprotected Authorization Bug)</h1>"


@app.get("/api/v1/broken")
def get_broken_api():
    raise HTTPException(status_code=500, detail="Internal Server Error")
