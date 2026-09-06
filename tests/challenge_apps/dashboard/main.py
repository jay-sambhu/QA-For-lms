"""
Challenge App D — Admin Dashboard Application.
Defects:
1. Role escalation via query string ?role=superadmin on /admin/users (Security / Escalation)
2. Modal export button causes Uncaught ReferenceError on /audit (JavaScript UI)
3. Filter status=ALL_EXCEPT_SYSTEM raises HTTP 500 on /api/v1/system-logs (API)
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI(title="Challenge Dashboard App")


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Enterprise Admin Console</title></head>
    <body>
        <h1>Enterprise Management Console</h1>
        <nav>
            <a href="/admin/users" id="link-users">User Management</a> | 
            <a href="/admin/audit" id="link-audit">Audit Logs</a> | 
            <a href="/api/v1/system-logs?status=ALL_EXCEPT_SYSTEM" id="link-logs">System Logs API</a>
        </nav>
        <p>Current Role: Standard User</p>
    </body>
    </html>
    """


@app.get("/admin/users", response_class=HTMLResponse)
def user_management(role: str = "guest"):
    # DEFECT: If role=superadmin passed in URL, grant full admin privilege without session check!
    is_admin = (role == "superadmin")
    status_msg = "Superadmin Granted (Security Vulnerability)" if is_admin else "Access Restricted"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>User Management</title></head>
    <body>
        <h1>User Management Portal</h1>
        <h2>Status: <span id="auth-status">{status_msg}</span></h2>
        <table border="1">
            <tr><th>User ID</th><th>Email</th><th>Role</th></tr>
            <tr><td>1</td><td>admin@enterprise.com</td><td>SUPERADMIN</td></tr>
            <tr><td>2</td><td>user@enterprise.com</td><td>USER</td></tr>
        </table>
        <p><a href="/admin/users?role=superadmin" id="escalate-role">Escalate to Superadmin</a></p>
    </body>
    </html>
    """


@app.get("/admin/audit", response_class=HTMLResponse)
def audit_logs():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Audit Logs</title></head>
    <body>
        <h1>System Audit Logs</h1>
        <button onclick="exportAuditLogsModal()" id="btn-export-modal">Export Audit Logs (Broken JS)</button>
        <table border="1">
            <tr><th>Timestamp</th><th>Action</th><th>User</th></tr>
            <tr><td>2026-09-06 10:00:00</td><td>USER_LOGIN</td><td>admin@enterprise.com</td></tr>
        </table>
    </body>
    </html>
    """


@app.get("/api/v1/system-logs")
def system_logs(status: str = "ALL"):
    # DEFECT: Query param status=ALL_EXCEPT_SYSTEM triggers 500!
    if status == "ALL_EXCEPT_SYSTEM":
        raise HTTPException(status_code=500, detail="Log Engine Internal Database Deadlock")
    return {"status": status, "logs": [{"id": 1, "msg": "System operational"}]}
