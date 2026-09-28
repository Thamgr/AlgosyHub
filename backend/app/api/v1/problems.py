import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.core.deps import CurrentUserID, SessionDep, require_role
from app.core.exceptions import AppError
from app.integrations.judges import registry
from app.models.contest import Contest, contest_problems
from app.models.enums import UserRole
from app.repositories.problem_repo import ProblemRepository
from app.schemas.problem import (
    CFTagsResponse,
    ProblemHintsResponse,
    ProblemResponse,
)
from app.services import (
    ai_hint_service,
    contest_service,
    platform_settings_service,
    problem_service,
)

router = APIRouter(prefix="/problems", tags=["problems"])
logger = logging.getLogger(__name__)

TeacherDep = Annotated[int, Depends(require_role(UserRole.teacher))]


@router.get("", response_model=list[ProblemResponse])
async def list_problems(session: SessionDep, user_id: CurrentUserID):
    return await ProblemRepository(session).list_for_user(user_id)


@router.get("/cf-tags", response_model=CFTagsResponse)
async def list_cf_tags(_: CurrentUserID):
    """Static-ish list of CF tags for the match-contest form."""
    return CFTagsResponse(tags=CF_TAGS)


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(problem_id: int, session: SessionDep, user_id: CurrentUserID, contest_id: int | None = None):
    return await problem_service.get_problem_for_user(session, problem_id, user_id, contest_id)


@router.get("/{problem_id}/statement", response_class=HTMLResponse)
async def get_problem_statement(problem_id: int, session: SessionDep, user_id: CurrentUserID, contest_id: int | None = None):
    problem = await problem_service.get_problem_for_user(session, problem_id, user_id, contest_id)

    try:
        adapter = registry.get(problem.external_source)
    except KeyError:
        raise HTTPException(501, f"No adapter for {problem.external_source}")

    try:
        html = await adapter.render_statement_html(problem)
    except (httpx.HTTPError, RuntimeError) as e:
        logger.warning("Statement fetch failed for problem %s: %s", problem_id, e)
        raise HTTPException(
            502,
            "Источник временно не отдаёт условие задачи. Попробуйте ещё раз или откройте оригинал.",
        ) from e

    return HTMLResponse(html)


@router.get("/{problem_id}/hints", response_model=ProblemHintsResponse)
async def get_hints(
    problem_id: int,
    session: SessionDep,
    user_id: CurrentUserID,
    contest_id: int | None = Query(default=None),
):
    await platform_settings_service.require_ai_hints(session)
    if contest_id is not None:
        try:
            await contest_service.assert_ai_hints_allowed(
                session, contest_id, problem_id, user_id
            )
        except AppError as e:
            raise HTTPException(e.status_code, e.message) from e

    await problem_service.get_problem_for_user(session, problem_id, user_id, contest_id)

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
    await platform_settings_service.require_ai_hints(session)
    linked = select(contest_problems.c.contest_id).where(contest_problems.c.problem_id == problem_id)
    owned = linked.join(Contest, Contest.id == contest_problems.c.contest_id).where(Contest.teacher_id == teacher_id)
    if contest_id is not None:
        contest = await contest_service.get_contest_for_user(session, contest_id, teacher_id)
        if contest.teacher_id != teacher_id:
            raise AppError("Forbidden", 403)
    elif await session.scalar(linked.limit(1)) is not None and await session.scalar(owned.limit(1)) is None:
        raise AppError("Forbidden", 403)
    if contest_id is not None:
        try:
            await contest_service.assert_ai_hints_allowed(
                session, contest_id, problem_id, teacher_id
            )
        except AppError as e:
            raise HTTPException(e.status_code, e.message) from e

    await problem_service.get_problem_for_user(session, problem_id, teacher_id, contest_id)

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
