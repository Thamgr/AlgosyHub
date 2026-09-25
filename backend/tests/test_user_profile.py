import importlib.util
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import User


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def users(session):
    owner = User(username="profile_owner", role=UserRole.student, hashed_password="unused")
    other = User(username="other_user", role=UserRole.teacher, hashed_password="unused")
    session.add_all([owner, other])
    await session.commit()
    return owner, other


@pytest.mark.asyncio
async def test_names_saved_and_returned_in_private_and_public_profiles(client, session, users):
    owner, other = users
    response = await client.patch("/api/v1/me", headers=auth(owner), json={
        "full_name": "  Ван дер Берг Анна-Мария  ",
    })
    assert response.status_code == 200
    for data in (
        response.json(),
        (await client.get("/api/v1/auth/me", headers=auth(owner))).json(),
        (await client.get("/api/v1/users/profile_owner")).json(),
    ):
        assert data["username"] == "profile_owner"
        assert data["full_name"] == "Ван дер Берг Анна-Мария"
    await session.refresh(owner)
    await session.refresh(other)
    assert owner.full_name == "Ван дер Берг Анна-Мария"
    assert other.full_name == ""
    public = (await client.get("/api/v1/users/profile_owner")).json()
    assert public["stats"]["total_submissions"] == 0
    assert "hashed_password" not in public and "is_platform_admin" not in public


@pytest.mark.asyncio
async def test_partial_updates_and_clearing_names(client, users):
    owner, _ = users
    headers = auth(owner)
    await client.patch("/api/v1/me", headers=headers, json={"full_name": "Иванова Анна"})
    response = await client.patch("/api/v1/me", headers=headers, json={})
    assert response.json()["full_name"] == "Иванова Анна"
    response = await client.patch("/api/v1/me", headers=headers, json={"full_name": "   "})
    assert response.json()["full_name"] == ""
    assert (await client.get("/api/v1/users/profile_owner")).json()["full_name"] == ""


@pytest.mark.asyncio
async def test_username_and_privileges_cannot_be_changed_through_profile(client, session, users):
    owner, other = users
    for forbidden in (
        {"username": "renamed"}, {"id": other.id}, {"role": "teacher"}, {"is_platform_admin": True},
    ):
        response = await client.patch("/api/v1/me", headers=auth(owner), json={"full_name": "Changed", **forbidden})
        assert response.status_code == 422
    await session.refresh(owner)
    assert owner.username == "profile_owner"
    assert owner.full_name == ""
    assert owner.role == UserRole.student
    assert owner.is_platform_admin is False
    assert (await client.get("/api/v1/users/renamed")).status_code == 404


@pytest.mark.asyncio
async def test_names_validate_length_types_and_authentication(client, users):
    owner, _ = users
    response = await client.patch("/api/v1/me", json={"full_name": "Anonymous"})
    assert response.status_code in (401, 403)
    for value in (None, 123, [], "я" * 202):
        response = await client.patch("/api/v1/me", headers=auth(owner), json={"full_name": value})
        assert response.status_code == 422
    response = await client.patch("/api/v1/me", headers=auth(owner), json={"full_name": "я" * 201})
    assert response.status_code == 200


def test_migration_preserves_existing_names(monkeypatch):
    path = Path(__file__).parents[1] / "alembic/versions/0009_user_full_name.py"
    spec = importlib.util.spec_from_file_location("user_full_name_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    names = [("Анна-Мария", "Ван дер Берг"), ("Анна", ""), ("", "Иванова"), ("", ""), ("я" * 100, "ф" * 100)]
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, first_name VARCHAR(100) NOT NULL, last_name VARCHAR(100) NOT NULL)")
            for user_id, (first, last) in enumerate(names, 1):
                connection.exec_driver_sql("INSERT INTO users VALUES (?, ?, ?)", (user_id, first, last))
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
            migration.upgrade()
            rows = connection.exec_driver_sql("SELECT first_name, last_name, full_name FROM users ORDER BY id").all()
            assert [row.full_name for row in rows] == ["Ван дер Берг Анна-Мария", "Анна", "Иванова", "", "ф" * 100 + " " + "я" * 100]
            assert [(row.first_name, row.last_name) for row in rows] == names
    finally:
        engine.dispose()
