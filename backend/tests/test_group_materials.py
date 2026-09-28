import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.group import Group, group_members
from app.models.group_material import GroupMaterial
from app.models.user import User


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def payload(**updates):
    return {"title": "  Бинарный поиск  ", "date": "2026-09-27", "description": "  Теория\nи примеры  ", "links": [{"label": " Часть 1 ", "url": "https://example.com/video?a=1&b=2"}, {"label": "Конспект", "url": "https://example.com/notes"}], **updates}


@pytest_asyncio.fixture
async def material_users(session):
    users = [User(username=name, hashed_password="unused", role=role, is_platform_admin=admin) for name, role, admin in [("owner", UserRole.teacher, False), ("member", UserRole.student, False), ("outsider", UserRole.student, False), ("other", UserRole.teacher, True)]]
    session.add_all(users)
    await session.flush()
    group = Group(name="Курс", teacher_id=users[0].id)
    other_group = Group(name="Другой курс", teacher_id=users[3].id)
    session.add_all([group, other_group])
    await session.flush()
    await session.execute(group_members.insert().values(group_id=group.id, user_id=users[1].id))
    await session.commit()
    return group, other_group, users


@pytest.mark.asyncio
async def test_create_persists_multiple_links_and_member_can_read(client, session, material_users):
    group, _, (owner, member, *_) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    response = await client.post(path, headers=auth(owner), json=payload())
    assert response.status_code == 201, response.text
    value = response.json()
    assert value["title"] == "Бинарный поиск"
    assert value["date"] == "2026-09-27"
    assert value["description"] == "Теория\nи примеры"
    assert [link["label"] for link in value["links"]] == ["Часть 1", "Конспект"]
    assert value["links"][0]["url"] == "https://example.com/video?a=1&b=2"
    assert (await session.get(GroupMaterial, value["id"])).group_id == group.id
    assert (await client.get(path, headers=auth(member))).json() == [value]
    assert (await client.get(path, headers=auth(owner))).json() == [value]


@pytest.mark.asyncio
async def test_permissions_isolation_and_demotion(client, session, material_users):
    group, other_group, (owner, member, outsider, other) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    for user in (member, outsider, other):
        assert (await client.post(path, headers=auth(user), json=payload())).status_code == 403
    for user in (outsider, other):
        assert (await client.get(path, headers=auth(user))).status_code == 403
    assert (await client.get(path)).status_code in (401, 403)
    assert (await client.post(path, json=payload())).status_code in (401, 403)
    assert (await client.post(path, headers=auth(owner), json=payload())).status_code == 201
    assert (await client.get(f"/api/v1/groups/{other_group.id}/materials", headers=auth(other))).json() == []
    await session.execute(group_members.delete().where(group_members.c.group_id == group.id))
    owner.role = UserRole.student
    await session.commit()
    assert (await client.get(path, headers=auth(member))).status_code == 403
    assert (await client.post(path, headers=auth(owner), json=payload())).status_code == 403


@pytest.mark.asyncio
async def test_ordering_empty_group_and_missing_group(client, material_users):
    group, _, (owner, *_) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    assert (await client.get(path, headers=auth(owner))).json() == []
    for title, date in [("old", "2025-12-31"), ("first", "2026-09-27"), ("second", "2026-09-27")]:
        assert (await client.post(path, headers=auth(owner), json=payload(title=title, date=date))).status_code == 201
    assert [m["title"] for m in (await client.get(path, headers=auth(owner))).json()] == ["second", "first", "old"]
    assert (await client.get("/api/v1/groups/99999/materials", headers=auth(owner))).status_code == 404
    assert (await client.post("/api/v1/groups/99999/materials", headers=auth(owner), json=payload())).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("updates", [
    {"title": "  "}, {"title": "x" * 161}, {"date": "2026-02-30"}, {"description": "x" * 10001},
    {"links": []}, {"links": [{"label": "x", "url": "https://example.com"}] * 21},
    {"links": [{"label": " ", "url": "https://example.com"}]},
    *({"links": [{"label": "x", "url": url}]} for url in ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "ftp://example.com", "/relative", "https://user:pass@example.com", "https://example.com/" + "x" * 2048]),
    {"group_id": 2}, {"teacher_id": 2},
])
async def test_invalid_materials_rejected_without_writes(client, session, material_users, updates):
    group, _, (owner, *_) = material_users
    response = await client.post(f"/api/v1/groups/{group.id}/materials", headers=auth(owner), json=payload(**updates))
    assert response.status_code == 422, response.text
    assert (await session.execute(select(GroupMaterial))).scalars().all() == []


@pytest.mark.asyncio
async def test_edit_preserves_identity_and_replaces_fields_and_links(client, session, material_users):
    group, _, (owner, member, *_) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    original = (await client.post(path, headers=auth(owner), json=payload())).json()
    stored = await session.get(GroupMaterial, original["id"])
    created_at = stored.created_at
    updated = payload(title="  Новая тема  ", date="2027-01-02", description="", links=[{"label": "  Новая ссылка ", "url": "https://example.com/updated"}])
    response = await client.put(f'{path}/{original["id"]}', headers=auth(owner), json=updated)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["id"] == original["id"] and value["group_id"] == group.id
    assert value["title"] == "Новая тема" and value["date"] == "2027-01-02"
    assert value["description"] == ""
    assert value["links"] == [{"label": "Новая ссылка", "url": "https://example.com/updated"}]
    assert (await client.get(path, headers=auth(member))).json() == [value]
    await session.refresh(stored)
    assert stored.created_at == created_at
    assert len((await session.execute(select(GroupMaterial))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_edit_permissions_and_cross_group_ids(client, session, material_users):
    group, other_group, (owner, member, outsider, other) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    original = (await client.post(path, headers=auth(owner), json=payload())).json()
    edit_path = f'{path}/{original["id"]}'
    for headers in ({}, auth(member), auth(outsider), auth(other)):
        assert (await client.put(edit_path, headers=headers, json=payload(title="Forbidden"))).status_code in (401, 403)
    # A teacher cannot edit another group's material through their own group URL.
    assert (await client.put(f'/api/v1/groups/{other_group.id}/materials/{original["id"]}', headers=auth(other), json=payload())).status_code == 404
    assert (await client.put(path + "/99999", headers=auth(owner), json=payload())).status_code == 404
    assert (await client.put("/api/v1/groups/99999/materials/1", headers=auth(owner), json=payload())).status_code == 404
    owner.role = UserRole.student
    await session.commit()
    assert (await client.put(edit_path, headers=auth(owner), json=payload())).status_code == 403
    assert (await client.get(path, headers=auth(member))).json() == [original]


@pytest.mark.asyncio
@pytest.mark.parametrize("updates", [{"title": " "}, {"links": []}, {"links": [{"label": "x", "url": "javascript:alert(1)"}]}, {"date": "2027-02-30"}, {"group_id": 2}])
async def test_invalid_edit_preserves_original(client, material_users, updates):
    group, _, (owner, *_) = material_users
    path = f"/api/v1/groups/{group.id}/materials"
    original = (await client.post(path, headers=auth(owner), json=payload())).json()
    response = await client.put(f'{path}/{original["id"]}', headers=auth(owner), json=payload(**updates))
    assert response.status_code == 422
    assert (await client.get(path, headers=auth(owner))).json() == [original]
