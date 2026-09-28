from datetime import datetime, timedelta, timezone

import pytest
from app.core.security import create_access_token
from app.models.contest import Contest
from app.models.enums import ExternalSource, SubmissionVerdict, UserRole
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from sqlalchemy import func, select


@pytest.mark.asyncio
async def test_profile_statistics_follow_contest_window_and_date_edits(client, session):
    student = User(username="stats_student", role=UserRole.student, hashed_password="unused")
    teacher = User(username="stats_teacher", role=UserRole.teacher, hashed_password="unused")
    session.add_all([student, teacher])
    await session.flush()
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    contest = Contest(title="Timed", teacher_id=teacher.id, starts_at=start, ends_at=end)
    problems = [
        Problem(external_source=ExternalSource.codeforces, external_id=f"1{letter}",
                title=letter, external_url=f"https://codeforces.com/problemset/problem/1/{letter}")
        for letter in "ABC"
    ]
    session.add_all([contest, *problems])
    await session.flush()
    # Old AC, two in-window ACs on the same problem, a failed attempt,
    # an AC exactly at the deadline, and an unrelated user's AC.
    cases = [
        (student.id, 0, start - timedelta(seconds=1), SubmissionVerdict.accepted),
        (student.id, 1, start, SubmissionVerdict.accepted),
        (student.id, 1, start + timedelta(seconds=1), SubmissionVerdict.accepted),
        (student.id, 2, end - timedelta(seconds=1), SubmissionVerdict.wrong_answer),
        (student.id, 2, end, SubmissionVerdict.accepted),
        (teacher.id, 0, start, SubmissionVerdict.accepted),
    ]
    session.add_all([
        Submission(user_id=uid, problem_id=problems[index].id, contest_id=contest.id,
                   language="Python", verdict=verdict, created_at=sent_at)
        for uid, index, sent_at, verdict in cases
    ])
    await session.commit()

    async def stats():
        response = await client.get("/api/v1/users/stats_student")
        assert response.status_code == 200
        return response.json()["stats"]

    assert await stats() == {
        "total_submissions": 3, "accepted_submissions": 2,
        "solved_problems": 1, "success_rate": pytest.approx(2 / 3),
    }

    # Reproduce the reported bug: moving the start into the future must
    # remove historical submissions from every profile statistic.
    headers = {"Authorization": f"Bearer {create_access_token(teacher.id)}"}
    response = await client.patch(f"/api/v1/contests/{contest.id}", headers=headers, json={
        "starts_at": "2027-05-31T00:00:00+03:00", "ends_at": None,
    })
    assert response.status_code == 200
    assert await stats() == {
        "total_submissions": 0, "accepted_submissions": 0,
        "solved_problems": 0, "success_rate": 0,
    }

    # Removing boundaries restores eligibility without changing history.
    response = await client.patch(f"/api/v1/contests/{contest.id}", headers=headers,
                                  json={"starts_at": None})
    assert response.status_code == 200
    assert await stats() == {
        "total_submissions": 5, "accepted_submissions": 4,
        "solved_problems": 3, "success_rate": 0.8,
    }
    assert await session.scalar(select(func.count(Submission.id))) == len(cases)


@pytest.mark.asyncio
async def test_standalone_submission_statistics_are_preserved(client, session):
    user = User(username="standalone", role=UserRole.student, hashed_password="unused")
    problem = Problem(external_source=ExternalSource.codeforces, external_id="1A",
                      title="A", external_url="https://codeforces.com/problemset/problem/1/A")
    session.add_all([user, problem])
    await session.flush()
    session.add(Submission(user_id=user.id, problem_id=problem.id, contest_id=None,
                           language="Python", verdict=SubmissionVerdict.accepted))
    await session.commit()
    response = await client.get("/api/v1/users/standalone")
    assert response.status_code == 200
    assert response.json()["stats"] == {
        "total_submissions": 1, "accepted_submissions": 1,
        "solved_problems": 1, "success_rate": 1,
    }
