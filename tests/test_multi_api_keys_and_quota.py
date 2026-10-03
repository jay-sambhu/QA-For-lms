"""
Unit tests for User Multi-AI Provider Integrations and Free Plan Quota (>3 keys paywall).
"""
import pytest
from fastapi import HTTPException
from api.main import (
    list_user_api_keys,
    create_user_api_key,
    set_default_user_api_key,
    delete_user_api_key_by_id,
    UserApiKeyCreateRequest,
)
from db import SessionLocal
from models import User, UserApiKey


class MockUser:
    def __init__(self, uid: str, email: str = "test@example.com"):
        self.id = uid
        self.email = email


@pytest.mark.anyio
async def test_multi_api_keys_and_free_tier_quota_limit():
    user_id = "test-multi-key-user-1"
    user = MockUser(user_id, "multi@example.com")

    with SessionLocal() as db:
        # Clean up any existing keys for this test user
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id).delete()
        existing_u = db.query(User).filter(User.id == user_id).first()
        if existing_u:
            existing_u.gemini_api_key = None
            existing_u.plan_tier = "free"
            existing_u.role = "user"
        else:
            db_user = User(id=user_id, email="multi@example.com", plan_tier="free", role="user", gemini_api_key=None)
            db.add(db_user)
        db.commit()

    # 1. Initial list should be empty
    initial_res = await list_user_api_keys(user=user)
    assert initial_res["count"] == 0
    assert initial_res["max_allowed"] == 3
    assert initial_res["plan_tier"] == "free"
    assert initial_res["is_paid"] is False
    assert initial_res["can_add_more"] is True

    # 2. Add 1st key (Gemini)
    key1_res = await create_user_api_key(
        payload=UserApiKeyCreateRequest(
            provider_id="gemini",
            api_key="AIzaSy_GEMINI_KEY_001_TEST",
            key_name="My Primary Gemini",
            model="gemini-2.5-flash",
            is_default=True,
        ),
        user=user,
    )
    assert key1_res["status"] == "success"
    key1_id = key1_res["key"]["id"]
    assert key1_res["key"]["is_default"] is True

    # 3. Add 2nd key (OpenAI)
    key2_res = await create_user_api_key(
        payload=UserApiKeyCreateRequest(
            provider_id="openai",
            api_key="sk-proj-OPENAI_KEY_002_TEST",
            key_name="My OpenAI GPT-4o",
            model="gpt-4o",
        ),
        user=user,
    )
    assert key2_res["status"] == "success"

    # 4. Add 3rd key (Anthropic)
    key3_res = await create_user_api_key(
        payload=UserApiKeyCreateRequest(
            provider_id="anthropic",
            api_key="sk-ant-ANTHROPIC_KEY_003_TEST",
            key_name="My Claude 3.5 Sonnet",
            model="claude-3-5-sonnet-20241022",
        ),
        user=user,
    )
    assert key3_res["status"] == "success"

    # 5. Check count is 3
    res_at_3 = await list_user_api_keys(user=user)
    assert res_at_3["count"] == 3
    assert res_at_3["can_add_more"] is False

    # 6. Attempting to add 4th key on Free Tier MUST raise 403 Forbidden with upgrade prompt
    with pytest.raises(HTTPException) as exc_info:
        await create_user_api_key(
            payload=UserApiKeyCreateRequest(
                provider_id="deepseek",
                api_key="sk-deepseek-KEY_004_TEST",
                key_name="My DeepSeek Key",
                model="deepseek-chat",
            ),
            user=user,
        )
    assert exc_info.value.status_code == 403
    assert "subscription plan" in exc_info.value.detail.lower()

    # 7. Upgrade user to 'pro' plan tier
    with SessionLocal() as db:
        u = db.query(User).filter(User.id == user_id).first()
        u.plan_tier = "pro"
        db.commit()

    # 8. Check quota after upgrade: max_allowed is 999 and can_add_more is True
    res_pro = await list_user_api_keys(user=user)
    assert res_pro["count"] == 3
    assert res_pro["is_paid"] is True
    assert res_pro["can_add_more"] is True

    # 9. Now adding 4th key succeeds!
    key4_res = await create_user_api_key(
        payload=UserApiKeyCreateRequest(
            provider_id="deepseek",
            api_key="sk-deepseek-KEY_004_TEST",
            key_name="My DeepSeek Key",
            model="deepseek-chat",
        ),
        user=user,
    )
    assert key4_res["status"] == "success"

    # 10. Switch default key to DeepSeek
    key4_id = key4_res["key"]["id"]
    default_switch = await set_default_user_api_key(key_id=key4_id, user=user)
    assert default_switch["status"] == "success"

    # Verify key4 is now default and key1 is not
    res_after_switch = await list_user_api_keys(user=user)
    for k in res_after_switch["keys"]:
        if k["id"] == key4_id:
            assert k["is_default"] is True
        elif k["id"] == key1_id:
            assert k["is_default"] is False

    # 11. Delete key1
    del_res = await delete_user_api_key_by_id(key_id=key1_id, user=user)
    assert del_res["status"] == "success"
    res_final = await list_user_api_keys(user=user)
    assert res_final["count"] == 3
