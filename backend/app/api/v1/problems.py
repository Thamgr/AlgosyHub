from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.models.enums import ExternalSource, UserRole
from app.schemas.problem import ProblemResponse
from app.services import problem_service

router = APIRouter(prefix="/problems", tags=["problems"])

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.get("", response_model=list[ProblemResponse])
async def list_problems(session: SessionDep, _: CurrentUserID):
    return await problem_service.list_problems(session)


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: int, session: SessionDep, _: CurrentUserID):
    problem = await problem_service.get_problem(session, problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")
    return problem
