from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.core.security import create_access_token
from app.models import Group, JudgeAccount, Problem, Submission, User
from app.models.contest import contest_problems
from app.models.enums import ExternalSource, SubmissionVerdict, UserRole
from app.models.group import group_members
from app.services.submission_service import _collect_polling_targets


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def data(session, client):
    owner, observer, member, stranger = [
        User(username=name, hashed_password="unused", role=role)
        for name, role in [("owner", UserRole.teacher), ("observer", UserRole.teacher),
                           ("member", UserRole.student), ("stranger", UserRole.teacher)]
    ]
    session.add_all([owner, observer, member, stranger])
    await session.flush()
    group = Group(name="Observed", teacher_id=owner.id)
    other_group = Group(name="Other", teacher_id=stranger.id)
    session.add_all([group, other_group])
    await session.flush()
    await session.execute(group_members.insert().values(group_id=group.id, user_id=member.id))
    await session.commit()
    now = datetime.now(timezone.utc)
    contests = []
    for title, visible, start, gid, teacher in [
        ("Current", True, now - timedelta(hours=1), group.id, owner),
        ("Hidden", False, now - timedelta(hours=1), group.id, owner),
        ("Future", True, now + timedelta(hours=1), group.id, owner),
        ("Unrelated", True, now - timedelta(hours=1), other_group.id, stranger),
    ]:
        response = await client.post("/api/v1/contests", headers=auth(teacher), json={
            "title": title, "group_ids": [gid], "is_visible": visible,
            "starts_at": start.isoformat(), "ends_at": (now + timedelta(days=1)).isoformat(),
        })
        assert response.status_code == 201, response.text
        contests.append(response.json()["id"])
    material = {"title": "Notes", "date": "2026-09-27", "description": "Theory",
                "links": [{"label": "Video", "url": "https://example.com/video"}]}
    response = await client.post(f"/api/v1/groups/{group.id}/materials", headers=auth(owner), json=material)
    assert response.status_code == 201
    return group, owner, observer, member, stranger, contests, response.json(), material


@pytest.mark.asyncio
async def test_observer_reads_visible_content_without_becoming_participant(client, data):
    group, owner, observer, member, _, (current, hidden, future, unrelated), material, _ = data
    path = f"/api/v1/groups/{group.id}"
    assert (await client.post(path + "/observers", headers=auth(owner), json={"username": observer.username})).status_code == 204
    settings = (await client.get(path + "/settings", headers=auth(owner))).json()
    assert [u["id"] for u in settings["observers"]] == [observer.id]
    assert [u["id"] for u in settings["members"]] == [member.id]
    assert "hashed_password" not in settings["observers"][0]
    assert [g["id"] for g in (await client.get("/api/v1/groups", headers=auth(observer))).json()] == [group.id]
    for listing in ("/api/v1/contests", path + "/contests"):
        assert {c["id"] for c in (await client.get(listing, headers=auth(observer))).json()} == {current, future}
    assert (await client.get(path + "/materials", headers=auth(observer))).json() == [material]
    assert [r["user_id"] for r in (await client.get(path + "/scoreboard", headers=auth(observer))).json()["rows"]] == [member.id]
    for suffix in ("", "/problems", "/scoreboard", "/submissions"):
        assert (await client.get(f"/api/v1/contests/{current}{suffix}", headers=auth(observer))).status_code == 200
    assert [r["user_id"] for r in (await client.get(f"/api/v1/contests/{current}/scoreboard", headers=auth(observer))).json()["rows"]] == [member.id]
    for cid in (hidden, unrelated):
        assert (await client.get(f"/api/v1/contests/{cid}", headers=auth(observer))).status_code == 403
    assert (await client.get(f"/api/v1/contests/{future}/problems", headers=auth(observer))).status_code == 403
    assert (await client.delete(path + f"/observers/{observer.id}", headers=auth(owner))).status_code == 204
    assert (await client.get("/api/v1/groups", headers=auth(observer))).json() == []
    assert (await client.get("/api/v1/contests", headers=auth(observer))).json() == []
    for url in (path + "/materials", path + "/scoreboard", f"/api/v1/contests/{current}/problems"):
        assert (await client.get(url, headers=auth(observer))).status_code == 403


@pytest.mark.asyncio
async def test_observer_cannot_edit_or_assign_contests_to_observed_group(client, data):
    group, owner, observer, member, stranger, (current, *_), material, body = data
    path = f"/api/v1/groups/{group.id}"
    assert (await client.post(path + "/observers", headers=auth(owner), json={"username": observer.username})).status_code == 204
    for method, url, payload in [
        ("get", path + "/settings", None),
        ("patch", path, {"name": "Changed"}),
        ("post", path + "/materials", body),
        ("put", path + f'/materials/{material["id"]}', body),
        ("post", path + "/members", {"username": stranger.username}),
        ("delete", path + f"/members/{member.id}", None),
        ("post", path + "/observers", {"username": stranger.username}),
        ("delete", path + f"/observers/{observer.id}", None),
        ("patch", f"/api/v1/contests/{current}", {"title": "Changed"}),
        ("delete", f"/api/v1/contests/{current}", None),
        ("put", f"/api/v1/contests/{current}/groups", {"group_ids": []}),
        ("post", f"/api/v1/contests/{current}/problems", {"external_source": "timus", "external_id": "1000"}),
        ("delete", f"/api/v1/contests/{current}/problems/1", None),
        ("post", "/api/v1/contests", {"title": "Injected", "group_ids": [group.id]}),
        ("post", "/api/v1/contests/match", {"title": "Injected", "group_ids": [group.id], "count": 1}),
    ]:
        response = await client.request(method, url, headers=auth(observer), **({"json": payload} if payload is not None else {}))
        assert response.status_code == 403, (method, url, response.text)
    own = await client.post("/api/v1/contests", headers=auth(observer), json={"title": "Own"})
    assert own.status_code == 201
    assert (await client.put(f'/api/v1/contests/{own.json()["id"]}/groups', headers=auth(observer), json={"group_ids": [group.id]})).status_code == 403
    assert (await client.get(path + "/materials", headers=auth(observer))).json() == [material]


@pytest.mark.asyncio
async def test_only_owner_manages_observers_and_membership_is_exclusive(client, session, data):
    group, owner, observer, member, stranger, *_ = data
    path = f"/api/v1/groups/{group.id}"
    for user in (observer, member, stranger):
        assert (await client.post(path + "/observers", headers=auth(user), json={"username": observer.username})).status_code == 403
    for username, status in [(owner.username, 409), (member.username, 409), ("missing", 404), (observer.username, 204), (observer.username, 409)]:
        assert (await client.post(path + "/observers", headers=auth(owner), json={"username": username})).status_code == status
    assert (await client.post(path + "/members", headers=auth(owner), json={"username": observer.username})).status_code == 409
    # Group observation also works for a student and does not change their global role.
    observer.role = UserRole.student
    await session.commit()
    assert (await client.get(path + "/materials", headers=auth(observer))).status_code == 200
    assert (await client.get("/api/v1/contests", headers=auth(observer))).status_code == 200
    owner.role = UserRole.student
    await session.commit()
    assert (await client.delete(path + f"/observers/{observer.id}", headers=auth(owner))).status_code == 403


@pytest.mark.asyncio
async def test_problem_access_is_read_only_and_old_submissions_do_not_add_observer(client, session, data):
    group, owner, observer, member, _, (current, *_), *_ = data
    problem = Problem(external_source=ExternalSource.timus, external_id="1000", title="Sum", external_url="https://acm.timus.ru/problem.aspx?num=1000")
    session.add(problem)
    await session.flush()
    await session.execute(contest_problems.insert().values(contest_id=current, problem_id=problem.id, order_index=0))
    session.add(Submission(user_id=observer.id, problem_id=problem.id, contest_id=current, language="cpp", verdict=SubmissionVerdict.accepted))
    session.add(JudgeAccount(user_id=observer.id, source=ExternalSource.timus, handle="12345"))
    await session.commit()
    assert (await client.post(f"/api/v1/groups/{group.id}/observers", headers=auth(owner), json={"username": observer.username})).status_code == 204
    for query in ("", f"?contest_id={current}"):
        assert (await client.get(f"/api/v1/problems/{problem.id}{query}", headers=auth(observer))).status_code == 200
        assert (await client.post(f"/api/v1/problems/{problem.id}/hints/regenerate{query}", headers=auth(observer))).status_code == 403
    rows = (await client.get(f"/api/v1/contests/{current}/scoreboard", headers=auth(observer))).json()["rows"]
    assert [row["user_id"] for row in rows] == [member.id]
    assert not any(user_id == observer.id for user_id, _ in await _collect_polling_targets(session))
