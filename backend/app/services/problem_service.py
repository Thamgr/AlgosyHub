from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.judges import registry
from app.models.enums import ExternalSource
from app.models.problem import Problem
from app.repositories.problem_repo import ProblemRepository


async def import_problem(
    session: AsyncSession,
    source: ExternalSource,
    external_id: str,
) -> Problem:
    repo = ProblemRepository(session)
    existing = await repo.get_by_external(source, external_id.upper())
    if existing:
        return existing

    adapter = registry.get(source)
    data = await adapter.fetch_problem(external_id)

    return await repo.create(
        external_source=source,
        external_id=data.external_id,
        title=data.title,
        tags=data.tags,
        difficulty=data.difficulty,
        time_limit_ms=data.time_limit_ms,
        memory_limit_mb=data.memory_limit_mb,
        cf_url=data.cf_url,
    )


async def get_problem(session: AsyncSession, problem_id: int) -> Problem | None:
    return await ProblemRepository(session).get(problem_id)


async def list_problems(session: AsyncSession) -> list[Problem]:
    return await ProblemRepository(session).list()
