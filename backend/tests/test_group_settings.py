import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.group import Group, group_members
from app.models.user import User


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def group_data(session):
    owner = User(username="owner", hashed_password="unused", role=UserRole.teacher)
    other = User(username="other_teacher", hashed_password="unused", role=UserRole.teacher, is_platform_admin=True)
    member = User(username="member", hashed_password="unused", role=UserRole.student)
    newcomer = User(username="newcomer", hashed_password="unused", role=UserRole.student)
    session.add_all([owner, other, member, newcomer])
    await session.flush()
    group = Group(name="Original", description="Keep description", teacher_id=owner.id)
    session.add(group)
    await session.flush()
    await session.execute(group_members.insert().values(group_id=group.id, user_id=member.id))
    await session.commit()
    return group, owner, other, member, newcomer


@pytest.mark.asyncio
async def test_owner_reads_settings_and_renames_group(client, session, group_data):
    group, owner, _, member, _ = group_data
    path = f"/api/v1/groups/{group.id}"
    response = await client.get(path + "/settings", headers=auth(owner))
    assert response.status_code == 200
    assert response.json()["group"]["name"] == "Original"
    assert [user["id"] for user in response.json()["members"]] == [member.id]
    assert "hashed_password" not in response.json()["members"][0]
    response = await client.patch(path, headers=auth(owner), json={"name": "  Алгоритмы 2027  "})
    assert response.status_code == 200
    assert response.json() == {
        "id": group.id, "teacher_id": owner.id, "name": "Алгоритмы 2027", "description": "Keep description",
    }
    await session.refresh(group)
    assert group.name == "Алгоритмы 2027"
    assert (await client.get(path, headers=auth(member))).json()["name"] == "Алгоритмы 2027"
    assert (await client.get("/api/v1/groups", headers=auth(owner))).json()[0]["name"] == "Алгоритмы 2027"
    assert [row["user_id"] for row in (await client.get(path + "/scoreboard", headers=auth(owner))).json()["rows"]] == [member.id]


@pytest.mark.asyncio
async def test_settings_and_changes_require_teacher_owner(client, session, group_data):
    group, owner, other, member, newcomer = group_data
    path = f"/api/v1/groups/{group.id}"
    for headers in ({}, auth(other), auth(member), auth(newcomer)):
        for response in (
            await client.get(path + "/settings", headers=headers),
            await client.patch(path, headers=headers, json={"name": "Forbidden"}),
            await client.post(path + "/members", headers=headers, json={"username": newcomer.username}),
            await client.delete(path + f"/members/{member.id}", headers=headers),
        ):
            assert response.status_code in (401, 403)
    await session.refresh(group)
    assert group.name == "Original"
    assert [user["id"] for user in (await client.get(path + "/settings", headers=auth(owner))).json()["members"]] == [member.id]
    # Owning a group does not bypass the teacher role requirement after demotion.
    owner.role = UserRole.student
    await session.commit()
    assert (await client.get(path + "/settings", headers=auth(owner))).status_code == 403
    assert (await client.patch(path, headers=auth(owner), json={"name": "Forbidden"})).status_code == 403


@pytest.mark.asyncio
async def test_name_validation_and_unknown_group(client, session, group_data):
    group, owner, other, _, _ = group_data
    path = f"/api/v1/groups/{group.id}"
    for body in ({}, {"name": ""}, {"name": "   "}, {"name": None}, {"name": 123}, {"name": "a" * 201}, {"name": "Rename", "teacher_id": other.id}, {"name": "Rename", "description": "Changed"}):
        assert (await client.patch(path, headers=auth(owner), json=body)).status_code == 422
    await session.refresh(group)
    assert group.name == "Original" and group.teacher_id == owner.id
    assert (await client.patch(path, headers=auth(owner), json={"name": "я" * 200})).status_code == 200
    assert (await client.patch("/api/v1/groups/99999", headers=auth(owner), json={"name": "Missing"})).status_code == 404
    assert (await client.get("/api/v1/groups/99999/settings", headers=auth(owner))).status_code == 404


@pytest.mark.asyncio
async def test_owner_member_management_updates_settings_and_scoreboard(client, group_data):
    group, owner, _, member, newcomer = group_data
    path = f"/api/v1/groups/{group.id}"
    assert (await client.post(path + "/members", headers=auth(owner), json={"username": newcomer.username})).status_code == 204
    settings = (await client.get(path + "/settings", headers=auth(owner))).json()
    assert {user["id"] for user in settings["members"]} == {member.id, newcomer.id}
    assert (await client.delete(path + f"/members/{member.id}", headers=auth(owner))).status_code == 204
    settings = (await client.get(path + "/settings", headers=auth(owner))).json()
    assert [user["id"] for user in settings["members"]] == [newcomer.id]
    scoreboard = (await client.get(path + "/scoreboard", headers=auth(owner))).json()
    assert [row["user_id"] for row in scoreboard["rows"]] == [newcomer.id]
