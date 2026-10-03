import pytest
from api.main import get_current_user_profile
from api.admin import update_user_role
from db import SessionLocal
from models import User


class MockUser:
    def __init__(self, uid: str, email: str = "test@example.com"):
        self.id = uid
        self.email = email


@pytest.mark.anyio
async def test_auth_me_regular_user():
    user_id = "test-regular-user-77"
    email = "regular_user_77@example.com"
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).delete()
        db_user = User(id=user_id, email=email, role="user", plan_tier="free")
        db.add(db_user)
        db.commit()

    user = MockUser(user_id, email)
    res = await get_current_user_profile(user=user)
    assert res["id"] == user_id
    assert res["email"] == email
    assert res["role"] == "user"
    assert res["is_admin"] is False
    assert res["dashboard_url"] == "/dashboard"


@pytest.mark.anyio
async def test_auth_me_admin_user():
    user_id = "test-admin-user-88"
    email = "admin_suite_88@admin.jasuss.io"
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).delete()
        db.query(User).filter(User.email == email).delete()
        db_user = User(id=user_id, email=email, role="admin", plan_tier="pro")
        db.add(db_user)
        db.commit()

    user = MockUser(user_id, email)
    res = await get_current_user_profile(user=user)
    assert res["id"] == user_id
    assert res["email"] == email
    assert res["role"] == "admin"
    assert res["is_admin"] is True
    assert res["dashboard_url"] == "/admin"


@pytest.mark.anyio
async def test_update_user_role():
    user_id = "test-role-toggle-99"
    email = "toggle_role@example.com"
    with SessionLocal() as db:
        db.query(User).filter(User.id == user_id).delete()
        db_user = User(id=user_id, email=email, role="user", plan_tier="free")
        db.add(db_user)
        db.commit()

    # Elevate to admin
    res = await update_user_role(user_id=user_id, payload={"role": "admin"})
    assert res["status"] == "success"
    assert res["role"] == "admin"

    with SessionLocal() as db:
        updated = db.query(User).filter(User.id == user_id).first()
        assert updated.role == "admin"

    # Demote back to user
    res2 = await update_user_role(user_id=user_id, payload={"role": "user"})
    assert res2["status"] == "success"
    assert res2["role"] == "user"
