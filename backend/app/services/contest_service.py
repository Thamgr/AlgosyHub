from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.contest import Contest
from app.models.enums import ContestStatus, ExternalSource
from app.models.problem import Problem
from app.repositories.contest_repo import ContestRepository
from app.services import problem_service


async def create_contest(
    session: AsyncSession,
    teacher_id: int,
    group_id: int,
    title: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> Contest:
    repo = ContestRepository(session)
    return await repo.create(
        teacher_id=teacher_id,
        group_id=group_id,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
    )


async def get_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await ContestRepository(session).get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    return contest


async def list_contests_for_group(session: AsyncSession, group_id: int) -> list[Contest]:
    return await ContestRepository(session).get_by_group(group_id)


async def assign_group(
    session: AsyncSession, contest_id: int, teacher_id: int, group_id: int | None
) -> Contest:
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    if contest.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)
    contest.group_id = group_id
    await session.flush()
    return contest


async def add_problem(
    session: AsyncSession,
    contest_id: int,
    teacher_id: int,
    source: ExternalSource,
    external_id: str,
) -> Problem:
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    if contest.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)
    if contest.status != ContestStatus.draft:
        raise AppError("Cannot modify a running or finished contest", 400)

    problem = await problem_service.import_problem(session, source, external_id)

    existing = await repo.get_problems(contest_id)
    if any(p.id == problem.id for p in existing):
        raise AppError("Problem already in contest", 409)

    order_index = len(existing)
    await repo.add_problem(contest_id, problem.id, order_index)
    return problem


async def get_problems(session: AsyncSession, contest_id: int) -> list[Problem]:
    return await ContestRepository(session).get_problems(contest_id)


async def set_status(
    session: AsyncSession, contest_id: int, teacher_id: int, status: ContestStatus
) -> Contest:
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    if contest.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)
    contest.status = status
    await session.flush()
    return contest
