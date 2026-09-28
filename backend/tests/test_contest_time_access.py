import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select

from app.core.security import create_access_token
from app.integrations.judges import registry
from app.models.enums import ExternalSource, SubmissionVerdict, UserRole
from app.models.group import Group, group_members
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.contest_repo import ContestRepository
from app.repositories.submission_repo import SubmissionRepository
from app.services import ai_hint_service, contest_service


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest_asyncio.fixture
async def course(session, monkeypatch):
    owner = User(username="owner", role=UserRole.teacher, hashed_password="unused")
    member = User(username="member", role=UserRole.student, hashed_password="unused")
    session.add_all([owner, member])
    await session.flush()
    group = Group(name="Time course", teacher_id=owner.id)
    session.add(group)
    await session.flush()
    await session.execute(group_members.insert().values(group_id=group.id, user_id=member.id))
    now = datetime.now(timezone.utc)
    contest = await contest_service.create_contest(session, owner.id, [group.id], "Future", now + timedelta(hours=1), now + timedelta(hours=2))
    problem = Problem(external_source=ExternalSource.timus, external_id="1000", title="Secret task", external_url="https://acm.timus.ru/problem.aspx?num=1000")
    session.add(problem)
    await session.flush()
    await ContestRepository(session).add_problem(contest.id, problem.id, 0)
    submission = Submission(user_id=member.id, problem_id=problem.id, contest_id=contest.id, language="C++", verdict=SubmissionVerdict.accepted, external_submission_id="old", created_at=now - timedelta(minutes=2))
    session.add(submission)
    await session.commit()
    statement = AsyncMock(return_value="<html><body>Statement</body></html>")
    monkeypatch.setattr(registry, "get", lambda source: SimpleNamespace(render_statement_html=statement))
    hints = AsyncMock(return_value=SimpleNamespace(problem_id=problem.id, hint1="one", hint2="two", hint3="three"))
    monkeypatch.setattr(ai_hint_service, "get_cached", hints)
    return owner, member, group, contest, problem, submission, statement, hints


@pytest.mark.asyncio
async def test_before_start_content_is_hidden_through_every_read_path(client, session, course):
    owner, member, group, contest, problem, submission, statement, hints = course
    cp = f"/api/v1/contests/{contest.id}"
    pp = f"/api/v1/problems/{problem.id}"
    response = await client.get(cp, headers=auth(member))
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert "status" not in response.json()
    paths = [cp + suffix for suffix in ("/problems", "/scoreboard", "/submissions")]
    paths += [pp + suffix + query for suffix in ("", "/statement", "/hints") for query in ("", f"?contest_id={contest.id}")]
    paths += [f"/api/v1/submissions/{submission.id}"]
    for path in paths:
        assert (await client.get(path, headers=auth(member))).status_code == 403, path
    statement.assert_not_called()
    hints.assert_not_called()
    assert (await client.get(pp + "/statement")).status_code == 401
    assert (await client.get("/api/v1/problems", headers=auth(member))).json() == []
    for user in (owner, member):
        board = (await client.get(f"/api/v1/groups/{group.id}/scoreboard", headers=auth(user))).json()
        assert board["contests"] == []
        assert [row["user_id"] for row in board["rows"]] == [member.id]
    # The owner can prepare the content, and existing submissions remain stored.
    for path in paths:
        assert (await client.get(path, headers=auth(owner))).status_code == 200, path
    assert (await client.get("/api/v1/problems", headers=auth(owner))).json()[0]["id"] == problem.id
    assert await session.scalar(select(Submission.id)) == submission.id


@pytest.mark.asyncio
async def test_time_edits_open_content_and_keep_all_submissions_after_end(client, session, course):
    owner, member, group, contest, problem, submission, _, _ = course
    cp = f"/api/v1/contests/{contest.id}"
    now = datetime.now(timezone.utc)
    changed = await client.patch(cp, headers=auth(owner), json={"starts_at": None})
    assert changed.json()["is_active"] is True
    pp = f"/api/v1/problems/{problem.id}"
    assert (await client.get(cp + "/problems", headers=auth(member))).json()[0]["id"] == problem.id
    assert (await client.get(pp + f"/statement?contest_id={contest.id}", headers=auth(member))).status_code == 200
    assert (await client.get(cp + "/scoreboard", headers=auth(member))).json()["rows"][0]["solved"] == 1
    late = Submission(user_id=member.id, problem_id=problem.id, contest_id=contest.id, language="C++", verdict=SubmissionVerdict.accepted, external_submission_id="late", created_at=now)
    session.add(late)
    await session.commit()
    cutoff = now - timedelta(minutes=1)
    changed = await client.patch(cp, headers=auth(owner), json={"ends_at": cutoff.isoformat()})
    assert changed.json()["is_active"] is False
    for suffix in ("/problems", "/scoreboard", "/submissions"):
        assert (await client.get(cp + suffix, headers=auth(member))).status_code == 200
    assert (await client.get(pp + "/statement", headers=auth(member))).status_code == 200
    assert [row["id"] for row in (await client.get(cp + "/submissions", headers=auth(member))).json()] == [submission.id]
    board = (await client.get(f"/api/v1/groups/{group.id}/scoreboard", headers=auth(member))).json()
    assert board["rows"][0]["attempts_total"] == 1
    assert len(await SubmissionRepository(session).list_for_problem(member.id, problem.id)) == 2
    # Removing the end restores late submissions to scoring, without recreating them.
    cleared = await client.patch(cp, headers=auth(owner), json={"ends_at": None})
    assert cleared.json()["is_active"] is True and cleared.json()["ends_at"] is None
    assert {s["id"] for s in (await client.get(cp + "/submissions", headers=auth(member))).json()} == {submission.id, late.id}


@pytest.mark.asyncio
async def test_shared_problem_stays_available_elsewhere_without_exposing_future_contest(client, session, course):
    owner, member, _, contest, problem, *_ = course
    open_contest = await contest_service.create_contest(session, owner.id, [], "Open", None, None)
    await ContestRepository(session).add_problem(open_contest.id, problem.id, 0)
    await session.commit()
    pp = f"/api/v1/problems/{problem.id}"
    assert (await client.get(pp, headers=auth(member))).status_code == 200
    assert (await client.get(pp + f"?contest_id={contest.id}", headers=auth(member))).status_code == 403
    assert (await client.get(pp + f"/statement?contest_id={contest.id}", headers=auth(member))).status_code == 403


@pytest.mark.asyncio
async def test_owner_can_edit_tasks_without_manual_state_and_history_survives(client, session, course):
    owner, member, _, contest, problem, submission, *_ = course
    cp = f"/api/v1/contests/{contest.id}"
    await client.patch(cp, headers=auth(owner), json={"starts_at": None, "ends_at": None})
    assert (await client.delete(cp + f"/problems/{problem.id}", headers=auth(member))).status_code == 403
    assert (await client.delete(cp + f"/problems/{problem.id}", headers=auth(owner))).status_code == 204
    await session.refresh(submission)
    assert submission.contest_id == contest.id
    added = await client.post(cp + "/problems", headers=auth(owner), json={"external_source": "timus", "external_id": "1000"})
    assert added.status_code == 201
    assert (await client.get(cp + "/scoreboard", headers=auth(member))).json()["rows"][0]["solved"] == 1


def test_status_removal_migration_preserves_schedules_relations_and_full_submission_rows(monkeypatch):
    path = Path(__file__).parents[1] / "alembic/versions/0013_contest_time_only.py"
    spec = importlib.util.spec_from_file_location("contest_time_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.exec_driver_sql("CREATE TABLE contests (id INTEGER PRIMARY KEY, status TEXT NOT NULL, starts_at TEXT, ends_at TEXT, is_visible BOOLEAN)")
            connection.exec_driver_sql("CREATE TABLE submissions (id INTEGER PRIMARY KEY, contest_id INTEGER REFERENCES contests(id), user_id INTEGER, problem_id INTEGER, verdict TEXT, created_at TEXT, external_submission_id TEXT)")
            connection.exec_driver_sql("CREATE TABLE contest_problems (contest_id INTEGER REFERENCES contests(id), problem_id INTEGER)")
            connection.exec_driver_sql("INSERT INTO contests VALUES (1, 'draft', NULL, '2026-12-31T20:59:00Z', 0), (2, 'running', NULL, NULL, 1), (3, 'finished', '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z', 1)")
            connection.exec_driver_sql("INSERT INTO submissions VALUES (42, 2, 7, 9, 'accepted', '2026-09-27T10:00:00Z', '11268292'), (43, 3, 7, 9, 'pending', '2026-01-01T10:00:00Z', 'pending-run')")
            connection.exec_driver_sql("INSERT INTO contest_problems VALUES (2, 9), (3, 9)")
            before = connection.exec_driver_sql("SELECT * FROM submissions").all()
            dates = connection.exec_driver_sql("SELECT id, starts_at, ends_at, is_visible FROM contests").all()
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(connection)))
            migration.upgrade()
            assert connection.exec_driver_sql("SELECT * FROM submissions").all() == before
            assert connection.exec_driver_sql("SELECT * FROM contests").all() == dates
            assert connection.exec_driver_sql("SELECT * FROM contest_problems").all() == [(2, 9), (3, 9)]
    finally:
        engine.dispose()
