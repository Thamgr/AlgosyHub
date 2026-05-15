from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, CurrentUserID, SessionDep, require_role
from app.models.contest import Contest
from app.models.enums import ContestStatus, UserRole
from app.schemas.contest import (
    AddProblemRequest,
    ContestCreate,
    ContestGroupsUpdate,
    ContestResponse,
    ContestUpdate,
    MatchContestRequest,
    ScoreboardCellResponse,
    ScoreboardResponse,
    ScoreboardRowResponse,
)
from app.schemas.problem import ProblemResponse
from app.services import contest_service

router = APIRouter(prefix="/contests", tags=["contests"])

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


async def _to_response(session, contest: Contest) -> ContestResponse:
    group_ids = await contest_service.get_group_ids(session, contest.id)
    return ContestResponse(
        id=contest.id,
        group_id=contest.group_id,
        group_ids=group_ids,
        title=contest.title,
        status=contest.status,
        starts_at=contest.starts_at,
        ends_at=contest.ends_at,
    )


async def _to_responses(session, contests: list[Contest]) -> list[ContestResponse]:
    return [await _to_response(session, c) for c in contests]


@router.get("", response_model=list[ContestResponse])
async def list_contests(
    session: SessionDep,
    user: CurrentUser,
    group_id: int | None = None,
):
    if group_id is not None:
        contests = await contest_service.list_contests_for_group(session, group_id)
    else:
        contests = await contest_service.list_contests_for_user(
            session, user.id, user.role
        )
    return await _to_responses(session, contests)


@router.post("", response_model=ContestResponse, status_code=201)
async def create_contest(body: ContestCreate, session: SessionDep, teacher_id: TeacherDep):
    group_ids = list(body.group_ids)
    if not group_ids and body.group_id is not None:
        group_ids = [body.group_id]

    contest = await contest_service.create_contest(
        session, teacher_id, group_ids, body.title, body.starts_at, body.ends_at
    )
    await session.commit()
    return await _to_response(session, contest)


@router.post("/match", response_model=ContestResponse, status_code=201)
async def match_contest(
    body: MatchContestRequest, session: SessionDep, teacher_id: TeacherDep
):
    """Auto-generate a contest from random CF problems matching tags+rating."""
    contest = await contest_service.create_matched_contest(
        session=session,
        teacher_id=teacher_id,
        title=body.title,
        group_ids=body.group_ids,
        tags=body.tags,
        rating_min=body.rating_min,
        rating_max=body.rating_max,
        count=body.count,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    await session.commit()
    return await _to_response(session, contest)


@router.get("/{contest_id}", response_model=ContestResponse)
async def get_contest(contest_id: int, session: SessionDep, user_id: CurrentUserID):
    contest = await contest_service.get_contest_for_user(session, contest_id, user_id)
    return await _to_response(session, contest)


@router.get("/{contest_id}/problems", response_model=list[ProblemResponse])
async def get_problems(contest_id: int, session: SessionDep, user_id: CurrentUserID):
    await contest_service.get_contest_for_user(session, contest_id, user_id)
    return await contest_service.get_problems(session, contest_id)


@router.post("/{contest_id}/problems", response_model=ProblemResponse, status_code=201)
async def add_problem(
    contest_id: int, body: AddProblemRequest, session: SessionDep, teacher_id: TeacherDep
):
    problem = await contest_service.add_problem(
        session, contest_id, teacher_id, body.external_source, body.external_id
    )
    await session.commit()
    return problem


@router.delete("/{contest_id}/problems/{problem_id}", status_code=204)
async def remove_problem(
    contest_id: int, problem_id: int, session: SessionDep, teacher_id: TeacherDep
):
    await contest_service.remove_problem(session, contest_id, teacher_id, problem_id)
    await session.commit()


@router.delete("/{contest_id}", status_code=204)
async def delete_contest(
    contest_id: int, session: SessionDep, teacher_id: TeacherDep
):
    await contest_service.delete_contest(session, contest_id, teacher_id)
    await session.commit()


@router.patch("/{contest_id}", response_model=ContestResponse)
async def update_contest(
    contest_id: int,
    body: ContestUpdate,
    session: SessionDep,
    teacher_id: TeacherDep,
):
    fields = body.model_dump(exclude_unset=True)
    contest = await contest_service.update_contest(
        session, contest_id, teacher_id, **fields
    )
    await session.commit()
    return await _to_response(session, contest)


@router.put("/{contest_id}/groups", response_model=ContestResponse)
async def update_groups(
    contest_id: int,
    body: ContestGroupsUpdate,
    session: SessionDep,
    teacher_id: TeacherDep,
):
    contest = await contest_service.set_groups(
        session, contest_id, teacher_id, body.group_ids
    )
    await session.commit()
    return await _to_response(session, contest)


@router.post("/{contest_id}/start", response_model=ContestResponse)
async def start_contest(contest_id: int, session: SessionDep, teacher_id: TeacherDep):
    contest = await contest_service.set_status(
        session, contest_id, teacher_id, ContestStatus.running
    )
    await session.commit()
    return await _to_response(session, contest)


@router.post("/{contest_id}/finish", response_model=ContestResponse)
async def finish_contest(contest_id: int, session: SessionDep, teacher_id: TeacherDep):
    contest = await contest_service.set_status(
        session, contest_id, teacher_id, ContestStatus.finished
    )
    await session.commit()
    return await _to_response(session, contest)


@router.get("/{contest_id}/scoreboard", response_model=ScoreboardResponse)
async def get_scoreboard(
    contest_id: int, session: SessionDep, user_id: CurrentUserID
):
    await contest_service.get_contest_for_user(session, contest_id, user_id)
    problems = await contest_service.get_problems(session, contest_id)
    rows = await contest_service.scoreboard(session, contest_id)
    return ScoreboardResponse(
        problem_ids=[p.id for p in problems],
        rows=[
            ScoreboardRowResponse(
                user_id=row.user_id,
                username=row.username,
                solved=row.solved,
                attempts_total=row.attempts_total,
                cells=[
                    ScoreboardCellResponse(
                        problem_id=pid,
                        attempts=cell.attempts,
                        accepted=cell.accepted,
                        first_accepted_at=cell.first_accepted_at,
                    )
                    for pid, cell in row.cells.items()
                ],
            )
            for row in rows
        ],
    )
