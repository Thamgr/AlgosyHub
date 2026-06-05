from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.core.exceptions import AppError
from app.integrations.judges import registry
from app.models.enums import UserRole
from app.schemas.problem import (
    CFTagsResponse,
    ProblemHintsResponse,
    ProblemResponse,
)
from app.services import ai_hint_service, contest_service, problem_service

router = APIRouter(prefix="/problems", tags=["problems"])

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.get("", response_model=list[ProblemResponse])
async def list_problems(session: SessionDep, _: CurrentUserID):
    return await problem_service.list_problems(session)


@router.get("/cf-tags", response_model=CFTagsResponse)
async def list_cf_tags(_: CurrentUserID):
    """Static-ish list of CF tags for the match-contest form."""
    return CFTagsResponse(tags=CF_TAGS)


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


@router.get("/{problem_id}/hints", response_model=ProblemHintsResponse)
async def get_hints(
    problem_id: int,
    session: SessionDep,
    user_id: CurrentUserID,
    contest_id: int | None = Query(default=None),
):
    if contest_id is not None:
        try:
            await contest_service.assert_ai_hints_allowed(
                session, contest_id, problem_id, user_id
            )
        except AppError as e:
            raise HTTPException(e.status_code, e.message) from e

    cached = await ai_hint_service.get_cached(session, problem_id)
    if cached is not None:
        return ProblemHintsResponse(
            problem_id=cached.problem_id,
            hint1=cached.hint1,
            hint2=cached.hint2,
            hint3=cached.hint3,
            cached=True,
        )
    hint = await ai_hint_service.get_or_generate(session, problem_id)
    await session.commit()
    return ProblemHintsResponse(
        problem_id=hint.problem_id,
        hint1=hint.hint1,
        hint2=hint.hint2,
        hint3=hint.hint3,
        cached=False,
    )


@router.post("/{problem_id}/hints/regenerate", response_model=ProblemHintsResponse)
async def regenerate_hints(
    problem_id: int,
    session: SessionDep,
    teacher_id: TeacherDep,
    contest_id: int | None = Query(default=None),
):
    if contest_id is not None:
        try:
            await contest_service.assert_ai_hints_allowed(
                session, contest_id, problem_id, teacher_id
            )
        except AppError as e:
            raise HTTPException(e.status_code, e.message) from e

    hint = await ai_hint_service.regenerate(session, problem_id)
    await session.commit()
    return ProblemHintsResponse(
        problem_id=hint.problem_id,
        hint1=hint.hint1,
        hint2=hint.hint2,
        hint3=hint.hint3,
        cached=False,
    )


# Curated list of CF tags. CF doesn't expose a tag-listing endpoint, so we keep
# the canonical set here — it changes maybe once a year on their side.
CF_TAGS: list[str] = [
    "implementation",
    "math",
    "greedy",
    "dp",
    "data structures",
    "brute force",
    "constructive algorithms",
    "graphs",
    "sortings",
    "binary search",
    "dfs and similar",
    "trees",
    "strings",
    "number theory",
    "combinatorics",
    "*special",
    "geometry",
    "bitmasks",
    "two pointers",
    "dsu",
    "shortest paths",
    "probabilities",
    "divide and conquer",
    "hashing",
    "games",
    "flows",
    "interactive",
    "matrices",
    "string suffix structures",
    "fft",
    "graph matchings",
    "ternary search",
    "expression parsing",
    "meet-in-the-middle",
    "2-sat",
    "chinese remainder theorem",
    "schedules",
]
