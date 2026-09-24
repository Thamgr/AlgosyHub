from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.core.security import create_access_token
from app.integrations.judges.base import ExternalSubmission
from app.models.contest import Contest
from app.models.enums import ContestStatus, ExternalSource, SubmissionVerdict, UserRole
from app.models.judge_account import JudgeAccount
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.contest_repo import ContestRepository
from app.repositories.submission_repo import SubmissionRepository
from app.schemas.contest import ContestCreate, ContestUpdate, MatchContestRequest
from app.services import contest_service, submission_service
from pydantic import ValidationError
from sqlalchemy import select


@pytest_asyncio.fixture
async def participants(session):
    teacher = User(username="teacher", hashed_password="unused", role=UserRole.teacher)
    student = User(username="student", hashed_password="unused", role=UserRole.student)
    other = User(username="other", hashed_password="unused", role=UserRole.teacher)
    session.add_all([teacher, student, other])
    await session.flush()
    return teacher, student, other


def auth(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.mark.parametrize("schema", [ContestCreate, MatchContestRequest])
def test_creation_requires_aware_ordered_deadline(schema):
    for fields in (
        {},
        {"ends_at": None},
        {"ends_at": "2026-09-25T12:00:00"},
        {"starts_at": "2026-09-25T12:00:00Z", "ends_at": "2026-09-25T12:00:00Z"},
    ):
        with pytest.raises(ValidationError):
            schema(title="Contest", **fields)
    model = schema(title="Contest", ends_at="2026-09-25T15:00:00+03:00")
    assert model.ends_at.astimezone(timezone.utc).hour == 12


def test_partial_update_distinguishes_missing_and_null():
    assert ContestUpdate(title="New").model_dump(exclude_unset=True) == {"title": "New"}
    with pytest.raises(ValidationError):
        ContestUpdate(ends_at=None)


@pytest.mark.asyncio
async def test_create_edit_deadline_permissions_and_status(
    client, session, participants
):
    teacher, student, other = participants
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    response = await client.post(
        "/api/v1/contests",
        headers=auth(teacher),
        json={"title": "Timed contest", "ends_at": future.isoformat()},
    )
    assert response.status_code == 201, response.text
    cid = response.json()["id"]
    assert datetime.fromisoformat(response.json()["ends_at"]) == future
    assert (
        await client.post(
            "/api/v1/contests",
            headers=auth(teacher),
            json={"title": "Missing deadline"},
        )
    ).status_code == 422
    for user in (student, other):
        assert (
            await client.patch(
                f"/api/v1/contests/{cid}",
                headers=auth(user),
                json={"ends_at": future.isoformat()},
            )
        ).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/contests/{cid}", headers=auth(teacher), json={"ends_at": None}
        )
    ).status_code == 422
    started = await client.post(f"/api/v1/contests/{cid}/start", headers=auth(teacher))
    assert started.json()["status"] == "running"
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = await client.patch(
        f"/api/v1/contests/{cid}",
        headers=auth(teacher),
        json={"ends_at": past.isoformat()},
    )
    assert expired.status_code == 200, expired.text
    assert expired.json()["status"] == "finished"
    extended = await client.patch(
        f"/api/v1/contests/{cid}",
        headers=auth(teacher),
        json={"ends_at": future.isoformat()},
    )
    assert extended.json()["status"] == "running"
    # Unrelated metadata edits preserve the deadline.
    renamed = await client.patch(
        f"/api/v1/contests/{cid}", headers=auth(teacher), json={"title": "Renamed"}
    )
    assert renamed.json()["ends_at"] == extended.json()["ends_at"]
    contest = await session.get(Contest, cid)
    contest.starts_at = future - timedelta(minutes=10)
    await session.flush()
    invalid = await client.patch(
        f"/api/v1/contests/{cid}",
        headers=auth(teacher),
        json={"ends_at": past.isoformat()},
    )
    assert invalid.status_code == 422


@pytest_asyncio.fixture
async def contest_setup(session, participants):
    teacher, student, _ = participants
    end = datetime.now(timezone.utc) - timedelta(hours=1)
    contest = await contest_service.create_contest(
        session, teacher.id, [], "Contest", None, end
    )
    contest.status = ContestStatus.running
    problem = Problem(
        external_source=ExternalSource.timus,
        external_id="1000",
        title="A+B",
        external_url="https://acm.timus.ru/problem.aspx?num=1000",
    )
    session.add(problem)
    await session.flush()
    await ContestRepository(session).add_problem(contest.id, problem.id, 0)
    session.add(
        JudgeAccount(user_id=student.id, source=ExternalSource.timus, handle="42")
    )
    await session.flush()
    return contest, problem, student, end


@pytest.mark.asyncio
async def test_cutoff_late_polling_rejudging_and_deadline_edits(session, contest_setup):
    contest, problem, student, end = contest_setup
    targets = await submission_service._collect_polling_targets(session)
    info = targets[(student.id, ExternalSource.timus)]
    rows = [
        ExternalSubmission(
            external_id=str(i),
            external_problem_id="1000",
            language="C++",
            verdict=SubmissionVerdict.running,
            submitted_at=end + timedelta(seconds=delta),
        )
        for i, delta in enumerate((-1, 0, 1))
    ]
    # All three are discovered after the deadline. Only the first counts.
    await submission_service._sync_user_submissions(session, student.id, info, rows)
    await session.flush()
    repo = SubmissionRepository(session)
    assert len(await repo.list_for_problem(student.id, problem.id)) == 3
    assert len(await repo.list_for_contest(contest.id)) == 1
    board = await contest_service.scoreboard(session, contest.id)
    assert (board[0].attempts_total, board[0].solved) == (1, 0)
    # Timely submission gets its final AC after the deadline; still counts.
    rows[0].verdict = SubmissionVerdict.accepted
    rows[2].verdict = SubmissionVerdict.accepted
    await submission_service._sync_user_submissions(session, student.id, info, rows)
    await session.flush()
    board = await contest_service.scoreboard(session, contest.id)
    assert (board[0].attempts_total, board[0].solved) == (1, 1)
    assert board[0].cells[problem.id].first_accepted_at == end - timedelta(seconds=1)
    await contest_service.update_contest(
        session, contest.id, contest.teacher_id, ends_at=end - timedelta(seconds=2)
    )
    assert await repo.list_for_contest(contest.id) == []
    assert (await contest_service.scoreboard(session, contest.id))[0].solved == 0
    await contest_service.update_contest(
        session, contest.id, contest.teacher_id, ends_at=end + timedelta(seconds=2)
    )
    assert len(await repo.list_for_contest(contest.id)) == 3
    assert (await contest_service.scoreboard(session, contest.id))[
        0
    ].attempts_total == 3
    assert len(await repo.list_for_problem(student.id, problem.id)) == 3


@pytest.mark.asyncio
async def test_same_external_submission_id_from_different_judges(
    session, contest_setup
):
    contest, problem, student, end = contest_setup
    cf = Problem(
        external_source=ExternalSource.codeforces,
        external_id="1A",
        title="Theatre Square",
        external_url="https://codeforces.com/problemset/problem/1/A",
    )
    session.add(cf)
    await session.flush()
    existing = Submission(
        user_id=student.id,
        problem_id=cf.id,
        contest_id=contest.id,
        language="Python",
        verdict=SubmissionVerdict.wrong_answer,
        external_submission_id="123",
        created_at=end - timedelta(minutes=1),
    )
    session.add(existing)
    await session.flush()
    targets = await submission_service._collect_polling_targets(session)
    await submission_service._sync_user_submissions(
        session,
        student.id,
        targets[(student.id, ExternalSource.timus)],
        [
            ExternalSubmission(
                external_id="123",
                external_problem_id="1000",
                language="C++",
                verdict=SubmissionVerdict.accepted,
                submitted_at=end - timedelta(seconds=1),
            )
        ],
    )
    await session.flush()
    all_rows = list((await session.scalars(select(Submission))).all())
    assert len(all_rows) == 2
    assert existing.verdict == SubmissionVerdict.wrong_answer
    assert (
        next(s for s in all_rows if s.problem_id == problem.id).verdict
        == SubmissionVerdict.accepted
    )


@pytest.mark.asyncio
async def test_legacy_contest_and_manual_finish(session, contest_setup):
    contest, problem, student, _ = contest_setup
    contest.ends_at = None
    sent = datetime.now(timezone.utc) - timedelta(seconds=1)
    session.add(
        Submission(
            user_id=student.id,
            problem_id=problem.id,
            contest_id=contest.id,
            language="C++",
            verdict=SubmissionVerdict.accepted,
            created_at=sent,
        )
    )
    await session.flush()
    assert len(await SubmissionRepository(session).list_for_contest(contest.id)) == 1
    await contest_service.set_status(
        session, contest.id, contest.teacher_id, ContestStatus.finished
    )
    assert contest.ends_at is not None
    assert contest.ends_at > sent


@pytest.mark.asyncio
async def test_link_timus_account(client, participants):
    _, student, _ = participants
    url = "/api/v1/me/judge-accounts/timus"
    invalid = await client.put(url, headers=auth(student), json={"handle": "42AB"})
    assert invalid.status_code == 422
    assert "JUDGE_ID" in invalid.json()["detail"]
    linked = await client.put(url, headers=auth(student), json={"handle": " 0042 "})
    assert linked.status_code == 200, linked.text
    assert linked.json()["source"] == "timus"
    assert linked.json()["handle"] == "42"
    updated = await client.put(url, headers=auth(student), json={"handle": "43"})
    assert updated.json()["handle"] == "43"
    accounts = await client.get("/api/v1/me/judge-accounts", headers=auth(student))
    assert len(accounts.json()) == 1
