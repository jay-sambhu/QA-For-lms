"""
Unit tests for scan status API endpoint (/api/v1/scans/{scan_id}).
Verifies progress and results loading for completed and active scans.
"""
import pytest
import os
import json
from uuid import UUID
from api.main import get_scan_status
from db import SessionLocal
from models import User, Scan

class MockUser:
    def __init__(self, uid: str):
        self.id = uid

@pytest.mark.anyio
async def test_completed_scan_returns_progress_and_results():
    user_id = "test-user-scan-status-99"
    scan_id = "11111111-2222-3333-4444-555555555555"

    with SessionLocal() as db:
        user = User(id=user_id, email="status-test@example.com")
        db.merge(user)
        db.commit()

        # Create mock report file in user_data directory
        user_results_dir = os.path.join("user_data", user_id, "results")
        os.makedirs(user_results_dir, exist_ok=True)
        report_file = os.path.join(user_results_dir, f"final_qa_report_{scan_id}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "report_metadata": {
                    "target": "https://example.com",
                    "pages_crawled": 5,
                    "quality_score": {"score": 90, "grade": "A", "summary": "Great"}
                },
                "summary": {"confirmed_bugs": 1},
                "findings": [],
                "qa_metrics": {
                    "quality_score": {"score": 90, "grade": "A", "summary": "Great"},
                    "duration_seconds": 45.0
                }
            }, f)

        scan = Scan(
            id=scan_id,
            user_id=user_id,
            url="https://example.com",
            status="completed",
            json_path=report_file
        )
        db.merge(scan)
        db.commit()

    # Call get_scan_status
    res = await get_scan_status(UUID(scan_id), user=MockUser(user_id))

    assert res["status"] == "completed"
    assert "progress" in res
    assert res["progress"]["stage"] == "COMPLETED"
    assert res["progress"]["percent"] == 100
    assert "results" in res
    assert res["results"] is not None
    assert res["results"]["report_metadata"]["target"] == "https://example.com"
