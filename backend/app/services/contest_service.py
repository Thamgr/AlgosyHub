"""Contest-level domain logic.

A contest is owned by exactly one teacher and is exposed to zero or more
*groups* (which here function as student tags). The legacy scalar
``Contest.group_id`` is kept in sync with the first entry in the M2M
``contest_groups`` table so older clients keep working.
"""

import random
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.integrations.judges import registry
from app.integrations.judges.codeforces import CodeforcesAdapter
from app.models.contest import Contest
from app.models.enums import ContestStatus, ExternalSource, SubmissionVerdict, UserRole
from app.models.group import group_members
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.repositories.contest_repo import ContestRepository
from app.services import problem_service


@dataclass
class ScoreboardCell:
    attempts: int
    accepted: bool
    first_accepted_at: datetime | None


@dataclass
class ScoreboardRow:
    user_id: int
    username: str
    cells: dict[int, ScoreboardCell]  # problem_id -> cell
    solved: int
    attempts_total: int


async def create_contest(
    session: AsyncSession,
    teacher_id: int,
    group_ids: list[int],
    title: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> Contest:
    repo = ContestRepository(session)
    # Legacy ``group_id`` keeps the first attached group so old code paths
    # (e.g. the simple "contests for a group" listing) still see the contest.
    primary_group = group_ids[0] if group_ids else None
    contest = await repo.create(
        teacher_id=teacher_id,
        group_id=primary_group,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    if group_ids:
        await repo.set_groups(contest.id, group_ids)
    return contest


async def get_contest(session: AsyncSession, contest_id: int) -> Contest:
    contest = await ContestRepository(session).get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    return contest


async def get_contest_for_user(
    session: AsyncSession, contest_id: int, user_id: int
) -> Contest:
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    if not await repo.user_can_access(contest_id, user_id):
        raise AppError("Forbidden", 403)
    return contest


async def list_contests_for_group(session: AsyncSession, group_id: int) -> list[Contest]:
    return await ContestRepository(session).get_by_group(group_id)


async def list_contests_for_user(
    session: AsyncSession, user_id: int, role: UserRole
) -> list[Contest]:
    repo = ContestRepository(session)
    if role == UserRole.teacher:
        return await repo.get_by_teacher(user_id)
    return await repo.get_for_user(user_id)


async def get_group_ids(session: AsyncSession, contest_id: int) -> list[int]:
    return await ContestRepository(session).get_group_ids(contest_id)


async def set_groups(
    session: AsyncSession, contest_id: int, teacher_id: int, group_ids: list[int]
) -> Contest:
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    if contest.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)
    await repo.set_groups(contest_id, group_ids)
    contest.group_id = group_ids[0] if group_ids else None
    await session.flush()
    return contest


async def assign_group(
    session: AsyncSession, contest_id: int, teacher_id: int, group_id: int | None
) -> Contest:
    """Backward-compat single-group setter — replaces all tags with one."""
    return await set_groups(
        session, contest_id, teacher_id, [group_id] if group_id is not None else []
    )


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


async def create_matched_contest(
    *,
    session: AsyncSession,
    teacher_id: int,
    title: str,
    group_ids: list[int],
    tags: list[str],
    rating_min: int | None,
    rating_max: int | None,
    count: int,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> Contest:
    """Pull the full CF problemset, filter by tag+rating, pick ``count`` at random.

    Tags are passed through to the CF API (which AND-s them), so providing
    e.g. ``["dp", "graphs"]`` yields only problems that have *both* tags.
    Rating range is applied client-side because CF doesn't filter on it.
    """
    try:
        adapter = registry.get(ExternalSource.codeforces)
    except KeyError as e:
        raise AppError("Codeforces adapter is not registered", 500) from e
    if not isinstance(adapter, CodeforcesAdapter):
        raise AppError("Codeforces adapter is misconfigured", 500)

    try:
        problems = await adapter.fetch_problemset(tags=tags or None)
    except RuntimeError as e:
        raise AppError(f"Codeforces problemset unavailable: {e}", 502) from e

    def in_range(rating: int | None) -> bool:
        if rating is None:
            # Problems without a rating are useless for difficulty-matching.
            return rating_min is None and rating_max is None
        if rating_min is not None and rating < rating_min:
            return False
        if rating_max is not None and rating > rating_max:
            return False
        return True

    candidates = [p for p in problems if in_range(p.difficulty)]
    if not candidates:
        raise AppError(
            "No CF problems match the given tags and rating range", 400
        )

    sample = random.sample(candidates, min(count, len(candidates)))
    # Stable order: easiest first inside the contest.
    sample.sort(key=lambda p: (p.difficulty or 0, p.external_id))

    contest = await create_contest(
        session=session,
        teacher_id=teacher_id,
        group_ids=group_ids,
        title=title,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    repo = ContestRepository(session)
    for i, picked in enumerate(sample):
        problem = await problem_service.import_problem(
            session, ExternalSource.codeforces, picked.external_id
        )
        await repo.add_problem(contest.id, problem.id, i)

    return contest


# -- scoreboard ------------------------------------------------------------


async def scoreboard(session: AsyncSession, contest_id: int) -> list[ScoreboardRow]:
    """Build a scoreboard for the contest.

    Rows are all distinct users from any group attached to the contest plus
    every user that has at least one submission on a problem of this contest
    (covers the "ad-hoc" / not-in-a-group case). Cells aggregate per-problem
    attempts and the first AC time.
    """
    repo = ContestRepository(session)
    contest = await repo.get(contest_id)
    if not contest:
        raise AppError("Contest not found", 404)
    problems = await repo.get_problems(contest_id)
    problem_ids = [p.id for p in problems]

    # Users from the contest's groups.
    group_ids = await repo.get_group_ids(contest_id)
    users: dict[int, User] = {}
    if group_ids:
        members = await session.execute(
            select(User)
            .join(group_members, group_members.c.user_id == User.id)
            .where(group_members.c.group_id.in_(group_ids))
        )
        for u in members.scalars().unique().all():
            users[u.id] = u

    # Users that have submitted at all (in case the contest has no groups
    # attached yet, or a non-member somehow submitted).
    if problem_ids:
        submitters = await session.execute(
            select(User)
            .join(Submission, Submission.user_id == User.id)
            .where(Submission.contest_id == contest_id)
            .distinct()
        )
        for u in submitters.scalars().unique().all():
            users.setdefault(u.id, u)

    # Gather all relevant submissions in one query.
    cells: dict[int, dict[int, ScoreboardCell]] = {
        uid: {pid: ScoreboardCell(0, False, None) for pid in problem_ids}
        for uid in users
    }

    if users and problem_ids:
        subs = await session.execute(
            select(Submission)
            .where(
                Submission.contest_id == contest_id,
                Submission.user_id.in_(users.keys()),
                Submission.problem_id.in_(problem_ids),
            )
            .order_by(Submission.created_at.asc())
        )
        for sub in subs.scalars().all():
            cell = cells[sub.user_id][sub.problem_id]
            cell.attempts += 1
            if sub.verdict == SubmissionVerdict.accepted and not cell.accepted:
                cell.accepted = True
                cell.first_accepted_at = sub.created_at

    rows: list[ScoreboardRow] = []
    for uid, user in users.items():
        user_cells = cells[uid]
        solved = sum(1 for c in user_cells.values() if c.accepted)
        attempts_total = sum(c.attempts for c in user_cells.values())
        rows.append(
            ScoreboardRow(
                user_id=uid,
                username=user.username,
                cells=user_cells,
                solved=solved,
                attempts_total=attempts_total,
            )
        )

    # Solved desc, then total attempts asc, then username asc as a deterministic tiebreak.
    rows.sort(key=lambda r: (-r.solved, r.attempts_total, r.username))
    return rows
