from unittest.mock import AsyncMock

import pytest

from app.core.security import create_access_token
from app.integrations.judges.base import ProblemData
from app.integrations.judges.codeforces import CodeforcesAdapter
from app.models.enums import ExternalSource, UserRole
from app.models.problem import Problem
from app.models.user import User
from app.services import contest_service


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.mark.asyncio
async def test_credit_threshold_create_read_update_and_clear(client, session):
    teacher = User(username="teacher", hashed_password="unused", role=UserRole.teacher)
    student = User(username="student", hashed_password="unused", role=UserRole.student)
    session.add_all([teacher, student])
    await session.flush()

    created = await client.post(
        "/api/v1/contests",
        headers=auth(teacher),
        json={"title": "Credit contest", "min_solved_for_credit": 3},
    )
    assert created.status_code == 201, created.text
    contest_id = created.json()["id"]
    path = f"/api/v1/contests/{contest_id}"
    assert created.json()["min_solved_for_credit"] == 3
    assert (await client.get(path, headers=auth(student))).json()["min_solved_for_credit"] == 3
    assert (await client.get("/api/v1/contests", headers=auth(student))).json()[0]["min_solved_for_credit"] == 3

    assert (await client.patch(path, headers=auth(student), json={"min_solved_for_credit": 2})).status_code == 403
    renamed = await client.patch(path, headers=auth(teacher), json={"title": "Renamed"})
    assert renamed.json()["min_solved_for_credit"] == 3
    changed = await client.patch(path, headers=auth(teacher), json={"min_solved_for_credit": 2})
    assert changed.status_code == 200, changed.text
    assert changed.json()["min_solved_for_credit"] == 2
    cleared = await client.patch(path, headers=auth(teacher), json={"min_solved_for_credit": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["min_solved_for_credit"] is None
    assert (await client.get(path, headers=auth(student))).json()["min_solved_for_credit"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, -1, 1.5, True, "2", 2_147_483_648])
async def test_credit_threshold_rejects_non_positive_or_non_integer_values(client, session, value):
    teacher = User(username="teacher", hashed_password="unused", role=UserRole.teacher)
    session.add(teacher)
    await session.flush()
    headers = auth(teacher)
    created = await client.post("/api/v1/contests", headers=headers, json={"title": "No threshold"})
    assert created.status_code == 201, created.text
    assert created.json()["min_solved_for_credit"] is None
    path = f"/api/v1/contests/{created.json()['id']}"
    for method, url, body in (
        (client.post, "/api/v1/contests", {"title": "Invalid", "min_solved_for_credit": value}),
        (client.patch, path, {"min_solved_for_credit": value}),
        (client.post, "/api/v1/contests/match", {"title": "Invalid", "min_solved_for_credit": value}),
    ):
        response = await method(url, headers=headers, json=body)
        assert response.status_code == 422, response.text
    assert (await client.get(path, headers=headers)).json()["min_solved_for_credit"] is None


@pytest.mark.asyncio
async def test_matched_contest_persists_credit_threshold(client, session, monkeypatch):
    teacher = User(username="teacher", hashed_password="unused", role=UserRole.teacher)
    session.add(teacher)
    await session.flush()

    adapter = CodeforcesAdapter()
    monkeypatch.setattr(
        adapter,
        "fetch_problemset",
        AsyncMock(return_value=[ProblemData("1A", "Theatre Square", "https://codeforces.com/problemset/problem/1/A", difficulty=1000)]),
    )
    monkeypatch.setattr(contest_service.registry, "get", lambda _: adapter)

    async def import_problem(session, source, external_id):
        problem = Problem(
            external_source=source,
            external_id=external_id,
            title="Theatre Square",
            external_url="https://codeforces.com/problemset/problem/1/A",
        )
        session.add(problem)
        await session.flush()
        return problem

    monkeypatch.setattr(contest_service.problem_service, "import_problem", import_problem)
    response = await client.post(
        "/api/v1/contests/match",
        headers=auth(teacher),
        json={"title": "Matched", "count": 1, "min_solved_for_credit": 1},
    )
    assert response.status_code == 201, response.text
    contest_id = response.json()["id"]
    assert response.json()["min_solved_for_credit"] == 1
    assert (await client.get(f"/api/v1/contests/{contest_id}", headers=auth(teacher))).json()["min_solved_for_credit"] == 1
    problems = (await client.get(f"/api/v1/contests/{contest_id}/problems", headers=auth(teacher))).json()
    assert len(problems) == 1 and problems[0]["external_source"] == ExternalSource.codeforces
