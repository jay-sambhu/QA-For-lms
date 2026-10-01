"""
Unit and integration tests for User Gemini API Key settings and scan enforcement.
Ensures:
1. Users can query, set, and delete their Gemini API key via API endpoints.
2. User API key is masked securely.
3. Scans strictly reject creation when user has no personal Gemini API key.
4. Scans queue when user has configured their Gemini API key.
5. get_scan_status returns results for completed scans reliably on reload.
"""
import pytest
import os
import json
from uuid import UUID
from fastapi import HTTPException
from api.main import (
    get_user_gemini_api_key,
    update_user_gemini_api_key,
    delete_user_gemini_api_key,
    get_scan_status,
    create_scan,
    ApiKeyUpdateRequest,
    ScanRequest,
)
from db import SessionLocal
from models import User, Scan


class MockUser:
    def __init__(self, uid: str, email: str = "test@example.com"):
        self.id = uid
        self.email = email


@pytest.mark.anyio
async def test_user_api_key_crud():
    user_id = "test-user-api-key-101"
    user = MockUser(user_id, "byok-user@example.com")

    with SessionLocal() as db:
        db_user = User(id=user_id, email="byok-user@example.com", gemini_api_key=None)
        db.merge(db_user)
        db.commit()

    # 1. Initial status: no key
    status = await get_user_gemini_api_key(user=user)
    assert status["has_key"] is False
    assert status["masked_key"] is None

    # 2. Update with valid key
    valid_key = "AIzaSyD_TEST_KEY_1234567890ABCDEF"
    update_res = await update_user_gemini_api_key(
        payload=ApiKeyUpdateRequest(api_key=valid_key),
        user=user
    )
    assert update_res["status"] == "success"
    assert update_res["has_key"] is True
    assert update_res["masked_key"].startswith("AIzaSy")
    assert update_res["masked_key"].endswith("CDEF")

    # 3. Retrieve status again: should be configured and masked
    status_after = await get_user_gemini_api_key(user=user)
    assert status_after["has_key"] is True
    assert status_after["masked_key"] == update_res["masked_key"]

    # 4. Delete key
    del_res = await delete_user_gemini_api_key(user=user)
    assert del_res["has_key"] is False

    status_final = await get_user_gemini_api_key(user=user)
    assert status_final["has_key"] is False


@pytest.mark.anyio
async def test_create_scan_strictly_requires_user_api_key():
    user_id = "test-user-no-key-202"
    user = MockUser(user_id, "nokey@example.com")

    with SessionLocal() as db:
        db_user = User(id=user_id, email="nokey@example.com", gemini_api_key=None)
        db.merge(db_user)
        db.commit()

    from fastapi import BackgroundTasks
    bg = BackgroundTasks()

    # Attempt to create scan without Gemini API key -> should raise 400
    with pytest.raises(HTTPException) as exc_info:
        await create_scan(
            request=ScanRequest(url="https://example.com", max_pages=5),
            background_tasks=bg,
            user=user,
            _rate_ok=True,
        )

    assert exc_info.value.status_code == 400
    assert "Google Gemini API key is required" in exc_info.value.detail


@pytest.mark.anyio
async def test_create_scan_succeeds_with_user_api_key():
    user_id = "test-user-has-key-303"
    user = MockUser(user_id, "haskey@example.com")

    with SessionLocal() as db:
        db_user = User(
            id=user_id,
            email="haskey@example.com",
            gemini_api_key="AIzaSy_VALID_TEST_KEY_FOR_USER_999"
        )
        db.merge(db_user)
        db.commit()

    from fastapi import BackgroundTasks
    bg = BackgroundTasks()

    res = await create_scan(
        request=ScanRequest(url="https://example.com", max_pages=5),
        background_tasks=bg,
        user=user,
        _rate_ok=True,
    )

    assert "scan_id" in res
    assert res["status"] == "pending"


@pytest.mark.anyio
async def test_get_scan_status_resolves_report_on_reload():
    user_id = "test-user-reload-404"
    scan_id = "88888888-4444-5555-6666-777777777777"
    user = MockUser(user_id, "reload@example.com")

    user_results_dir = os.path.join("user_data", user_id, "results")
    os.makedirs(user_results_dir, exist_ok=True)
    report_file = os.path.join(user_results_dir, f"final_qa_report_{scan_id}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "url": "https://example.com",
            "summary": {"total_candidates": 3, "confirmed_bugs": 1},
            "findings": []
        }, f)

    with SessionLocal() as db:
        u = User(id=user_id, email="reload@example.com", gemini_api_key="AIzaSy...")
        db.merge(u)
        s = Scan(
            id=scan_id,
            user_id=user_id,
            url="https://example.com",
            status="completed",
            json_path=report_file
        )
        db.merge(s)
        db.commit()

    res = await get_scan_status(UUID(scan_id), user=user)
    assert res["status"] == "completed"
    assert res["results"] is not None
    assert res["results"]["summary"]["confirmed_bugs"] == 1
