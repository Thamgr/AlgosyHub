from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.integrations.judges import registry
from app.models.enums import UserRole
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


@router.get("/{problem_id}/statement", response_class=HTMLResponse)
async def get_problem_statement(problem_id: int, session: SessionDep):
    # No auth: opened via plain <a target="_blank"> which can't carry the JWT.
    # Content is public judge HTML anyway; this is just a proxy.
    problem = await problem_service.get_problem(session, problem_id)
    if not problem:
        raise HTTPException(404, "Problem not found")

    try:
        adapter = registry.get(problem.external_source)
    except KeyError:
        raise HTTPException(501, f"No adapter for {problem.external_source}")

    try:
        html = await adapter.render_statement_html(problem)
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Upstream judge returned {e.response.status_code}")

    return HTMLResponse(html)
