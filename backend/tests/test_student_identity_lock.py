import importlib.util
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

from app.core.security import create_access_token
from app.models.enums import ExternalSource, UserRole
from app.models.user import User


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def users(session):
    admin = User(username="admin", role=UserRole.teacher, hashed_password="unused", is_platform_admin=True)
    teacher = User(username="teacher", role=UserRole.teacher, hashed_password="unused")
    student = User(username="student", role=UserRole.student, hashed_password="unused", full_name="Иванов Иван")
    session.add_all([admin, teacher, student])
    await session.commit()
    return admin, teacher, student


@pytest.mark.asyncio
async def test_lock_requires_admin_boolean_and_preserves_other_settings(client, users):
    admin, teacher, student = users
    path = "/api/v1/platform-settings"
    await client.patch(path, headers=auth(admin), json={"registration_enabled": False, "ai_hints_enabled": False, "show_problem_tags": True})
    before = (await client.get(path)).json()
    for headers in ({}, auth(teacher), auth(student)):
        assert (await client.patch(path, headers=headers, json={"student_identity_locked": True})).status_code in (401, 403)
    for invalid in (None, "true", 1):
        assert (await client.patch(path, headers=auth(admin), json={"student_identity_locked": invalid})).status_code == 422
    for enabled in (True, False):
        response = await client.patch(path, headers=auth(admin), json={"student_identity_locked": enabled})
        assert response.status_code == 200
        assert response.json() == {**before, "student_identity_locked": enabled}
        assert (await client.get(path)).json() == response.json()


@pytest.mark.asyncio
async def test_lock_blocks_name_changes_atomically_but_allows_avatar_and_reading(client, session, users):
    admin, _, student = users
    headers = auth(student)
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"student_identity_locked": True})
    for payload in ({"full_name": "Другое Имя"}, {"full_name": ""}, {"full_name": "Иванов Иван"}, {"full_name": "Другое Имя", "avatar_emoji": "🚀"}):
        response = await client.patch("/api/v1/me?view=teacher", headers=headers, json=payload)
        assert response.status_code == 403
        assert "отключено администратором" in response.text
    await session.refresh(student)
    assert (student.full_name, student.avatar_emoji) == ("Иванов Иван", "")
    response = await client.patch("/api/v1/me", headers=headers, json={"avatar_emoji": "🚀"})
    assert response.status_code == 200
    assert response.json()["avatar_emoji"] == "🚀"
    assert response.json()["full_name"] == "Иванов Иван"
    assert (await client.patch("/api/v1/me", headers=headers, json={})).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=headers)).json()["full_name"] == "Иванов Иван"
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"student_identity_locked": False})
    assert (await client.patch("/api/v1/me", headers=headers, json={"full_name": "Новое Имя"})).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("source", list(ExternalSource))
async def test_lock_blocks_creating_replacing_and_removing_judge_accounts(client, users, source):
    admin, _, student = users
    settings_path = "/api/v1/platform-settings"
    path = f"/api/v1/me/judge-accounts/{source.value}"
    headers = auth(student)
    await client.patch(settings_path, headers=auth(admin), json={"student_identity_locked": True})
    assert (await client.put(path, headers=headers, json={"handle": "12345"})).status_code == 403
    assert (await client.get("/api/v1/me/judge-accounts", headers=headers)).json() == []
    await client.patch(settings_path, headers=auth(admin), json={"student_identity_locked": False})
    assert (await client.put(path, headers=headers, json={"handle": "12345"})).status_code == 200
    before = (await client.get("/api/v1/me/judge-accounts", headers=headers)).json()
    await client.patch(settings_path, headers=auth(admin), json={"student_identity_locked": True})
    assert (await client.put(path, headers=headers, json={"handle": "67890"})).status_code == 403
    assert (await client.delete(path, headers=headers)).status_code == 403
    assert (await client.get("/api/v1/me/judge-accounts", headers=headers)).json() == before
    await client.patch(settings_path, headers=auth(admin), json={"student_identity_locked": False})
    assert (await client.delete(path, headers=headers)).status_code == 204


@pytest.mark.asyncio
async def test_teacher_unrestricted_and_role_changes_apply_to_existing_tokens(client, session, users):
    admin, teacher, student = users
    await client.patch("/api/v1/platform-settings", headers=auth(admin), json={"student_identity_locked": True})
    headers = auth(teacher)
    for user in (admin, teacher):
        assert (await client.patch("/api/v1/me", headers=auth(user), json={"full_name": "Учитель"})).status_code == 200
        assert (await client.put("/api/v1/me/judge-accounts/timus", headers=auth(user), json={"handle": "12345"})).status_code == 200
        assert (await client.delete("/api/v1/me/judge-accounts/timus", headers=auth(user))).status_code == 204
    teacher.role = UserRole.student
    student.is_platform_admin = True
    await session.commit()
    assert (await client.patch("/api/v1/me", headers=headers, json={"full_name": "Changed"})).status_code == 403
    assert (await client.patch("/api/v1/me", headers=auth(student), json={"full_name": "Changed"})).status_code == 403


def test_migration_preserves_existing_settings_and_defaults_to_unlocked(monkeypatch):
    path = Path(__file__).parents[1] / "alembic/versions/0012_student_identity_lock.py"
    spec = importlib.util.spec_from_file_location("student_identity_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE platform_settings (id INTEGER PRIMARY KEY, registration_enabled BOOLEAN NOT NULL, ai_hints_enabled BOOLEAN NOT NULL, show_problem_tags BOOLEAN NOT NULL, show_problem_difficulty BOOLEAN NOT NULL)")
            connection.exec_driver_sql("INSERT INTO platform_settings VALUES (1, 0, 0, 1, 0)")
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
            migration.upgrade()
            assert connection.exec_driver_sql("SELECT * FROM platform_settings").one() == (1, 0, 0, 1, 0, 0)
    finally:
        engine.dispose()
