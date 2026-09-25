from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.core.security import create_access_token
from app.models.enums import ExternalSource, SubmissionVerdict, UserRole
from app.models.group import Group, group_members
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.contest_repo import ContestRepository
from app.services import contest_service


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest_asyncio.fixture
async def course(session):
    owner = User(username="teacher", hashed_password="unused", role=UserRole.teacher)
    alice = User(username="alice", hashed_password="unused", role=UserRole.student)
    bob = User(username="bob", hashed_password="unused", role=UserRole.student)
    outsider = User(
        username="outsider", hashed_password="unused", role=UserRole.student
    )
    session.add_all([owner, alice, bob, outsider])
    await session.flush()
    group = Group(name="Course", teacher_id=owner.id)
    session.add(group)
    await session.flush()
    await session.execute(
        group_members.insert(),
        [{"group_id": group.id, "user_id": u.id} for u in (alice, bob)],
    )
    start = datetime.now(timezone.utc) - timedelta(hours=2)
    end = start + timedelta(hours=1)
    contests = []
    for i in range(4):
        contests.append(
            await contest_service.create_contest(
                session,
                owner.id,
                [group.id] if i < 3 else [],
                f"Contest {i}",
                start,
                end,
                is_visible=i != 2,
            )
        )
    problems = [
        Problem(
            external_source=ExternalSource.timus,
            external_id=str(1000 + i),
            title=f"Task {i}",
            external_url=f"https://acm.timus.ru/problem.aspx?num={1000 + i}",
        )
        for i in range(3)
    ]
    session.add_all(problems)
    await session.flush()
    repo = ContestRepository(session)
    for contest, assigned in zip(
        contests,
        [[problems[1], problems[0]], [problems[0]], [problems[2]], [problems[2]]],
    ):
        for index, problem in enumerate(assigned):
            await repo.add_problem(contest.id, problem.id, index)

    async def submit(user, contest, problem, verdict, sent):
        session.add(
            Submission(
                user_id=user.id,
                contest_id=contest.id,
                problem_id=problem.id,
                language="C++",
                verdict=verdict,
                created_at=sent,
            )
        )

    # Before start and at end do not count; at start does.
    await submit(
        alice,
        contests[0],
        problems[0],
        SubmissionVerdict.accepted,
        start - timedelta(seconds=1),
    )
    await submit(alice, contests[0], problems[0], SubmissionVerdict.wrong_answer, start)
    await submit(
        alice,
        contests[0],
        problems[0],
        SubmissionVerdict.accepted,
        start + timedelta(seconds=1),
    )
    await submit(alice, contests[0], problems[0], SubmissionVerdict.accepted, end)
    await submit(alice, contests[1], problems[0], SubmissionVerdict.wrong_answer, start)
    await submit(alice, contests[2], problems[2], SubmissionVerdict.accepted, start)
    await submit(alice, contests[3], problems[2], SubmissionVerdict.accepted, start)
    await submit(outsider, contests[0], problems[0], SubmissionVerdict.accepted, start)
    # A removed task must not create an extra cell.
    await submit(alice, contests[0], problems[2], SubmissionVerdict.accepted, start)
    await session.flush()
    return owner, alice, bob, outsider, group, contests, problems, start, end


@pytest.mark.asyncio
async def test_group_scoreboard_columns_members_and_scoring(client, session, course):
    owner, alice, _bob, outsider, group, contests, problems, _start, _end = course
    url = f"/api/v1/groups/{group.id}/scoreboard"
    response = await client.get(url, headers=auth(owner))
    assert response.status_code == 200, response.text
    data = response.json()
    assert [c["id"] for c in data["contests"]] == [contests[1].id, contests[0].id]
    assert [p["id"] for p in data["contests"][1]["problems"]] == [
        problems[1].id,
        problems[0].id,
    ]
    assert data["contests"][0]["problems"][0]["title"] == "Task 0"
    assert [r["username"] for r in data["rows"]] == ["alice", "bob"]
    row, empty = data["rows"]
    assert (row["solved"], row["attempts_total"]) == (1, 3)
    assert empty["cells"] == [] and empty["solved"] == 0
    cells = {(c["contest_id"], c["problem_id"]): c for c in row["cells"]}
    assert cells[(contests[0].id, problems[0].id)]["accepted"] is True
    assert cells[(contests[1].id, problems[0].id)]["accepted"] is False
    for contest in contests[:2]:
        board = await contest_service.scoreboard(session, contest.id)
        student = next(r for r in board if r.user_id == alice.id)
        cell = cells[(contest.id, problems[0].id)]
        assert cell["attempts"] == student.cells[problems[0].id].attempts
        assert cell["accepted"] == student.cells[problems[0].id].accepted
    assert (await client.get(url, headers=auth(alice))).json() == data
    assert (await client.get(url, headers=auth(outsider))).status_code == 403
    assert (await client.get(url)).status_code == 401
    assert (
        await client.get("/api/v1/groups/99999/scoreboard", headers=auth(owner))
    ).status_code == 404


@pytest.mark.asyncio
async def test_group_scoreboard_reflects_visibility_deadline_and_members(
    client, session, course
):
    owner, alice, _bob, _outsider, group, contests, _problems, start, _end = course
    url = f"/api/v1/groups/{group.id}/scoreboard"
    await contest_service.update_contest(
        session, contests[0].id, owner.id, starts_at=start + timedelta(seconds=2)
    )
    data = (await client.get(url, headers=auth(owner))).json()
    assert data["rows"][0]["solved"] == 0
    await contest_service.update_contest(
        session, contests[1].id, owner.id, is_visible=False
    )
    data = (await client.get(url, headers=auth(owner))).json()
    assert len(data["contests"]) == 1
    assert data["rows"][0]["cells"] == []
    await client.delete(
        f"/api/v1/groups/{group.id}/members/{alice.id}", headers=auth(owner)
    )
    data = (await client.get(url, headers=auth(owner))).json()
    assert [row["username"] for row in data["rows"]] == ["bob"]
    assert (await client.get(url, headers=auth(alice))).status_code == 403


@pytest.mark.asyncio
async def test_empty_group_scoreboard(client, session):
    owner = User(username="owner", hashed_password="unused", role=UserRole.teacher)
    session.add(owner)
    await session.flush()
    group = Group(teacher_id=owner.id, name="Empty")
    session.add(group)
    await session.flush()
    response = await client.get(
        f"/api/v1/groups/{group.id}/scoreboard", headers=auth(owner)
    )
    assert response.status_code == 200
    assert response.json() == {"contests": [], "rows": []}
