from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.core.security import create_access_token
from app.models.contest import Contest
from app.models.enums import ContestStatus, ExternalSource, SubmissionVerdict, UserRole
from app.models.group import Group, group_members
from app.models.judge_account import JudgeAccount
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.contest_repo import ContestRepository
from app.repositories.submission_repo import SubmissionRepository
from app.services import contest_service, submission_service


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest_asyncio.fixture
async def setup(session):
    owner = User(username="owner", hashed_password="unused", role=UserRole.teacher)
    member = User(username="member", hashed_password="unused", role=UserRole.student)
    outsider = User(username="outsider", hashed_password="unused", role=UserRole.student)
    session.add_all([owner, member, outsider])
    await session.flush()
    group = Group(name="Course", teacher_id=owner.id)
    session.add(group)
    await session.flush()
    await session.execute(group_members.insert().values(group_id=group.id, user_id=member.id))
    return owner, member, outsider, group


@pytest.mark.asyncio
@pytest.mark.parametrize("grouped", [False, True])
async def test_visibility_all_lists_and_direct_access(client, session, setup, grouped):
    owner, member, outsider, group = setup
    response = await client.post('/api/v1/contests', headers=auth(owner), json={
        'title': 'Hidden', 'ends_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        'group_ids': [group.id] if grouped else [], 'is_visible': False,
    })
    assert response.status_code == 201, response.text
    cid = response.json()['id']
    assert response.json()['is_visible'] is False
    listings = ['/api/v1/contests', f'/api/v1/contests?group_id={group.id}', f'/api/v1/groups/{group.id}/contests']
    details = [f'/api/v1/contests/{cid}{suffix}' for suffix in ('', '/problems', '/scoreboard', '/submissions')]
    for user in (member, outsider):
        for path in listings:
            response = await client.get(path, headers=auth(user))
            assert response.status_code == 200, response.text
            assert response.json() == []
        for path in details:
            assert (await client.get(path, headers=auth(user))).status_code == 403
        assert (await client.patch(f'/api/v1/contests/{cid}', headers=auth(user), json={'is_visible':True})).status_code == 403
    for path in details:
        assert (await client.get(path, headers=auth(owner))).status_code == 200
    assert len((await client.get('/api/v1/contests', headers=auth(owner))).json()) == 1
    if grouped:
        assert len((await client.get(listings[-1], headers=auth(owner))).json()) == 1
    shown = await client.patch(f'/api/v1/contests/{cid}', headers=auth(owner), json={'is_visible': True})
    assert shown.json()['is_visible'] is True
    assert len((await client.get('/api/v1/contests', headers=auth(member))).json()) == 1
    assert (await client.get(details[0], headers=auth(outsider))).status_code == (403 if grouped else 200)
    assert (await client.patch(details[0], headers=auth(owner), json={'is_visible': None})).status_code == 422


@pytest.mark.asyncio
async def test_edit_schedule_and_partial_update_validation(client, session, setup):
    owner, member, _, _ = setup
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    response = await client.post('/api/v1/contests', headers=auth(owner), json={
        'title': 'Schedule', 'starts_at': start.isoformat(), 'ends_at': end.isoformat(),
    })
    assert response.status_code == 201, response.text
    cid = response.json()['id']
    path = f'/api/v1/contests/{cid}'
    assert response.json()['status'] == 'draft'
    assert response.json()['is_visible'] is True
    for fields in ({'starts_at': end.isoformat()}, {'ends_at': start.isoformat()}, {'starts_at':'2026-12-01T12:00:00'}):
        assert (await client.patch(path, headers=auth(owner), json=fields)).status_code == 422
    assert (await client.patch(path, headers=auth(member), json={'starts_at': None})).status_code == 403
    updated = await client.patch(path, headers=auth(owner), json={'starts_at':(end + timedelta(hours=1)).isoformat(), 'ends_at':(end + timedelta(hours=2)).isoformat(), 'is_visible':False})
    assert updated.status_code == 200, updated.text
    unchanged = await client.patch(path, headers=auth(owner), json={'title':'Renamed'})
    assert unchanged.json()['starts_at'] == updated.json()['starts_at']
    assert unchanged.json()['is_visible'] is False
    cleared = await client.patch(path, headers=auth(owner), json={'starts_at': None})
    assert cleared.json()['starts_at'] is None
    assert cleared.json()['status'] == 'draft'
    assert (await client.post(path+'/start', headers=auth(owner))).json()['status'] == 'running'


def test_status_at_schedule_boundaries():
    start = datetime(2026, 12, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    contest = Contest(status=ContestStatus.draft, starts_at=start, ends_at=end)
    assert contest.effective_status(start - timedelta(seconds=1)) == ContestStatus.draft
    assert contest.effective_status(start) == ContestStatus.running
    assert contest.effective_status(end - timedelta(seconds=1)) == ContestStatus.running
    assert contest.effective_status(end) == ContestStatus.finished
    contest.status = ContestStatus.finished
    assert contest.effective_status(start) == ContestStatus.finished


@pytest.mark.asyncio
@pytest.mark.parametrize('grouped', [False, True])
async def test_automatic_start_polling_and_scoring_window(client, session, setup, grouped):
    owner, member, _, group = setup
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)
    contest = await contest_service.create_contest(session, owner.id, [group.id] if grouped else [], 'Scheduled', start, end)
    problem = Problem(external_source=ExternalSource.timus, external_id='1000', title='A+B', external_url='https://acm.timus.ru/problem.aspx?num=1000')
    session.add(problem)
    session.add(JudgeAccount(user_id=member.id, source=ExternalSource.timus, handle='42'))
    await session.flush()
    await ContestRepository(session).add_problem(contest.id, problem.id, 0)
    # Schedule is effective even without a status mutation or a browser visit.
    assert contest.status == ContestStatus.draft
    targets = await submission_service._collect_polling_targets(session)
    assert targets[(member.id, ExternalSource.timus)].contest_id_by_problem_id[problem.id] == contest.id
    path = f'/api/v1/contests/{contest.id}'
    assert (await client.get(path, headers=auth(owner))).json()['status'] == 'running'
    assert (await client.delete(path+f'/problems/{problem.id}', headers=auth(owner))).status_code == 400
    for sent in (start-timedelta(seconds=1), start, end-timedelta(seconds=1), end):
        session.add(Submission(user_id=member.id, problem_id=problem.id, contest_id=contest.id, language='C++', verdict=SubmissionVerdict.accepted, created_at=sent))
    await session.flush()
    repo = SubmissionRepository(session)
    assert len(await repo.list_for_contest(contest.id)) == 2
    assert (await contest_service.scoreboard(session, contest.id))[0].attempts_total == 2
    await contest_service.update_contest(session, contest.id, owner.id, starts_at=start-timedelta(seconds=1))
    assert len(await repo.list_for_contest(contest.id)) == 3
    assert len(await repo.list_for_problem(member.id, problem.id)) == 4
    await contest_service.update_contest(session, contest.id, owner.id, starts_at=now+timedelta(minutes=30))
    assert await submission_service._collect_polling_targets(session) == {}
    assert (await client.get(path, headers=auth(owner))).json()['status'] == 'draft'
    # Explicit early launch moves a future start to now.
    started = await client.post(path+'/start', headers=auth(owner))
    assert started.json()['status'] == 'running'
    assert datetime.fromisoformat(started.json()['starts_at']) <= datetime.now(timezone.utc)
