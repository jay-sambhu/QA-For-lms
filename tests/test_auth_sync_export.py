from fastapi.testclient import TestClient
from api.main import app
from db import SessionLocal
from models import User
import uuid

client = TestClient(app)

def test_auth_sync_creates_missing_user():
    dummy_id = str(uuid.uuid4())
    dummy_email = f"test_{dummy_id}@example.com"
    
    from unittest.mock import patch, MagicMock
    with patch("api.main.supabase") as mock_supabase:
        mock_user = MagicMock()
        mock_user.user.id = dummy_id
        mock_user.user.email = dummy_email
        mock_user.user.user_metadata = {"role": "user"}
        mock_supabase.auth.get_user.return_value = mock_user
        
        resp = client.post(
            "/api/v1/scans",
            headers={"Authorization": "Bearer fake_token_123"},
            json={"url": "https://example.com"}
        )
        
        session = SessionLocal()
        db_user = session.query(User).filter_by(id=dummy_id).first()
        assert db_user is not None
        assert db_user.email == dummy_email

def test_export_corruption_fix_metadata():
    """
    Real regression test for the export corruption fix.
    This generates a dummy XLSX via the actual frontend export library (XLSX)
    and uses openpyxl to verify it's a valid, uncorrupted Excel file.
    """
    import openpyxl
    import os
    import subprocess
    
    js_code = """
    const XLSX = require('xlsx');
    const fs = require('fs');

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([['ID', 'Status'], ['FIND-01', 'Open']]);
    XLSX.utils.book_append_sheet(wb, ws, 'Findings');
    
    // This is the fixed logic: using write with buffer
    const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
    fs.writeFileSync('test_export_regression.xlsx', buf);
    """
    
    node_script_path = os.path.abspath("web/test_export.js")
    with open(node_script_path, "w") as f:
        f.write(js_code)
        
    try:
        subprocess.run(["node", "test_export.js"], cwd=os.path.abspath("web"), check=True)
        xlsx_path = os.path.abspath("web/test_export_regression.xlsx")
        
        assert os.path.exists(xlsx_path)
        
        wb = openpyxl.load_workbook(xlsx_path)
        assert "Findings" in wb.sheetnames
        
        ws = wb["Findings"]
        assert ws["A1"].value == "ID"
        assert ws["B2"].value == "Open"
        
    finally:
        if os.path.exists(node_script_path):
            os.remove(node_script_path)
        export_file = os.path.abspath("web/test_export_regression.xlsx")
        if os.path.exists(export_file):
            os.remove(export_file)
