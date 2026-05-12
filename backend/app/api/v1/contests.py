from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.models.enums import ContestStatus, UserRole
from app.schemas.contest import AddProblemRequest, ContestCreate, ContestResponse
from app.schemas.problem import ProblemResponse
from app.services import contest_service

router = APIRouter(prefix="/contests", tags=["contests"])

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.get("", response_model=list[ContestResponse])
async def list_contests(group_id: int, session: SessionDep, _: CurrentUserID):
    return await contest_service.list_contests_for_group(session, group_id)


@router.post("", response_model=ContestResponse, status_code=201)
async def create_contest(body: ContestCreate, session: SessionDep, teacher_id: TeacherDep):
    contest = await contest_service.create_contest(
        session, teacher_id, body.group_id, body.title, body.starts_at, body.ends_at
    )
    await session.commit()
    return contest


@router.get("/{contest_id}", response_model=ContestResponse)
async def get_contest(contest_id: int, session: SessionDep, _: CurrentUserID):
    return await contest_service.get_contest(session, contest_id)


@router.get("/{contest_id}/problems", response_model=list[ProblemResponse])
async def get_problems(contest_id: int, session: SessionDep, _: CurrentUserID):
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


@router.post("/{contest_id}/start", response_model=ContestResponse)
async def start_contest(contest_id: int, session: SessionDep, teacher_id: TeacherDep):
    contest = await contest_service.set_status(
        session, contest_id, teacher_id, ContestStatus.running
    )
    await session.commit()
    return contest


@router.post("/{contest_id}/finish", response_model=ContestResponse)
async def finish_contest(contest_id: int, session: SessionDep, teacher_id: TeacherDep):
    contest = await contest_service.set_status(
        session, contest_id, teacher_id, ContestStatus.finished
    )
    await session.commit()
    return contest
