"""Group progress over visible contests, without one query per contest."""

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.contest import Contest, contest_groups, contest_problems
from app.models.enums import SubmissionVerdict
from app.models.group import group_members
from app.models.problem import Problem
from app.models.submission import Submission
from app.repositories.contest_repo import ContestRepository
from app.repositories.group_repo import GroupRepository
from app.repositories.submission_repo import submission_in_window
from app.schemas.group import (
    GroupScoreboardCell,
    GroupScoreboardContest,
    GroupScoreboardResponse,
    GroupScoreboardRow,
)
from app.schemas.problem import ProblemResponse
from app.services.group_service import get_group


async def scoreboard(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupScoreboardResponse:
    group = await get_group(session, group_id)
    repo = GroupRepository(session)
    if group.teacher_id != user_id and not await repo.is_member(group_id, user_id):
        raise AppError("Forbidden", 403)

    members = await repo.get_members(group_id)
    members.sort(key=lambda member: (member.username.casefold(), member.id))
    rows = {
        member.id: GroupScoreboardRow(
            user_id=member.id,
            username=member.username,
            solved=0,
            attempts_total=0,
            cells=[],
        )
        for member in members
    }

    # Each column is a contest/problem pair: repeated tasks keep separate results.
    problems = await session.execute(
        select(Contest.id, Contest.title, Problem)
        .join(contest_groups, contest_groups.c.contest_id == Contest.id)
        .join(contest_problems, contest_problems.c.contest_id == Contest.id)
        .join(Problem, Problem.id == contest_problems.c.problem_id)
        .where(
            contest_groups.c.group_id == group_id,
            Contest.is_visible.is_(True),
            ContestRepository.access_filter(user_id),
        )
        .order_by(Contest.id.desc(), contest_problems.c.order_index, Problem.id)
    )
    contests: dict[int, GroupScoreboardContest] = {}
    for cid, title, problem in problems:
        contest = contests.setdefault(
            cid, GroupScoreboardContest(id=cid, title=title, problems=[])
        )
        contest.problems.append(ProblemResponse.model_validate(problem))

    if rows and contests:
        results = await session.execute(
            select(
                Submission.user_id,
                Submission.contest_id,
                Submission.problem_id,
                func.count(Submission.id).label("attempts"),
                func.min(
                    case(
                        (
                            Submission.verdict == SubmissionVerdict.accepted,
                            Submission.created_at,
                        ),
                        else_=None,
                    )
                ).label("first_accepted_at"),
            )
            .join(Contest, Contest.id == Submission.contest_id)
            .join(
                contest_problems,
                (contest_problems.c.contest_id == Contest.id)
                & (contest_problems.c.problem_id == Submission.problem_id),
            )
            .join(
                group_members,
                (group_members.c.user_id == Submission.user_id)
                & (group_members.c.group_id == group_id),
            )
            .where(
                Contest.id.in_(contests),
                Submission.user_id.in_(rows),
                submission_in_window(Contest.starts_at, Contest.ends_at),
            )
            .group_by(Submission.user_id, Submission.contest_id, Submission.problem_id)
            .order_by(Submission.user_id, Submission.contest_id, Submission.problem_id)
        )
        for result in results:
            cell = GroupScoreboardCell(
                contest_id=result.contest_id,
                problem_id=result.problem_id,
                attempts=result.attempts,
                accepted=result.first_accepted_at is not None,
                first_accepted_at=result.first_accepted_at,
            )
            row = rows[result.user_id]
            row.cells.append(cell)
            row.solved += int(cell.accepted)
            row.attempts_total += cell.attempts

    return GroupScoreboardResponse(
        contests=list(contests.values()), rows=list(rows.values())
    )
