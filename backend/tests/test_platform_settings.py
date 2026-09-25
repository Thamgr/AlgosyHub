from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.services import ai_hint_service, contest_service


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def users(session):
    admin = User(username="admin", role=UserRole.teacher, hashed_password="unused", is_platform_admin=True)
    teacher = User(username="teacher", role=UserRole.teacher, hashed_password="unused")
    student = User(username="student", role=UserRole.student, hashed_password="unused")
    session.add_all([admin, teacher, student])
    await session.flush()
    return admin, teacher, student


@pytest.mark.asyncio
async def test_public_defaults_permissions_and_partial_updates(client, users):
    admin, teacher, student = users
    path = "/api/v1/platform-settings"
    response = await client.get(path)
    assert response.json() == {"registration_enabled": True, "ai_hints_enabled": True}
    assert response.headers["cache-control"] == "no-store"
    for headers in ({}, auth(teacher), auth(student)):
        response = await client.patch(path, headers=headers, json={"registration_enabled": False})
        assert response.status_code in (401, 403)
    assert (await client.get(path)).json()["registration_enabled"] is True
    assert (await client.get("/api/v1/auth/me", headers=auth(admin))).json()["is_platform_admin"] is True
    response = await client.patch(path, headers=auth(admin), json={"registration_enabled": False})
    assert response.status_code == 200
    assert response.json() == {"registration_enabled": False, "ai_hints_enabled": True}
    response = await client.patch(path, headers=auth(admin), json={"ai_hints_enabled": False})
    assert response.json() == {"registration_enabled": False, "ai_hints_enabled": False}
    assert (await client.get(path)).json() == response.json()
    for body in ({"ai_hints_enabled": None}, {"ai_hints_enabled": "false"}, {"unknown": False}):
        assert (await client.patch(path, headers=auth(admin), json=body)).status_code == 422


@pytest.mark.asyncio
async def test_registration_disabled_login_preserved_and_no_admin_self_assignment(client, session, users):
    admin, _, _ = users
    payload = {"username": "new_teacher", "password": "test-password", "role": "teacher", "is_platform_admin": True}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["is_platform_admin"] is False
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"registration_enabled": False})
    for role in ("teacher", "student"):
        response = await client.post("/api/v1/auth/register", json={**payload, "username": "blocked", "role": role})
        assert response.status_code == 403
    assert await session.scalar(select(User).where(User.username == "blocked")) is None
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"registration_enabled": True})
    assert (await client.post("/api/v1/auth/register", json={**payload, "username": "reopened"})).status_code == 201


@pytest.mark.asyncio
async def test_global_ai_blocks_cached_generated_and_regenerated_hints(client, users, monkeypatch):
    admin, teacher, student = users
    cached = AsyncMock(return_value=SimpleNamespace(problem_id=42, hint1="a", hint2="b", hint3="c"))
    generate = AsyncMock()
    regenerate = AsyncMock()
    monkeypatch.setattr(ai_hint_service, "get_cached", cached)
    monkeypatch.setattr(ai_hint_service, "get_or_generate", generate)
    monkeypatch.setattr(ai_hint_service, "regenerate", regenerate)
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"ai_hints_enabled": False})
    for user in users:
        for suffix in ("", "?contest_id=1"):
            assert (await client.get(f"/api/v1/problems/42/hints{suffix}", headers=auth(user))).status_code == 403
    for user in (admin, teacher):
        assert (await client.post("/api/v1/problems/42/hints/regenerate", headers=auth(user))).status_code == 403
    cached.assert_not_called()
    generate.assert_not_called()
    regenerate.assert_not_called()
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"ai_hints_enabled": True})
    response = await client.get("/api/v1/problems/42/hints", headers=auth(student))
    assert response.status_code == 200 and response.json()["cached"] is True
    # Global enable does not override a contest's own restriction.
    monkeypatch.setattr(contest_service, "assert_ai_hints_allowed", AsyncMock(side_effect=AppError("Contest hints disabled", 403)))
    assert (await client.get("/api/v1/problems/42/hints?contest_id=1", headers=auth(student))).status_code == 403
    cached.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoked_admin_cannot_use_existing_token(client, session, users):
    admin, _, _ = users
    headers = auth(admin)
    admin.is_platform_admin = False
    await session.commit()
    assert (await client.patch("/api/v1/platform-settings", headers=headers, json={"ai_hints_enabled": False})).status_code == 403
