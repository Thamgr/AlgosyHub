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
    # Быстрая проверка по тому, что ввёл юзер. Для CF этого достаточно
    # (фронт делает `.toUpperCase()`), для Информатикса работает, если
    # ввели чистый chapterid. Если ввели URL — нормализованное значение
    # совпадёт только после adapter.fetch_problem; тогда сверим ещё раз.
    existing = await repo.get_by_external(source, external_id.upper())
    if existing:
        return existing

    adapter = registry.get(source)
    data = await adapter.fetch_problem(external_id)

    if data.external_id != external_id.upper():
        existing = await repo.get_by_external(source, data.external_id)
        if existing:
            return existing

    return await repo.create(
        external_source=source,
        external_id=data.external_id,
        title=data.title,
        tags=data.tags,
        difficulty=data.difficulty,
        external_url=data.external_url,
    )


async def get_problem(session: AsyncSession, problem_id: int) -> Problem | None:
    return await ProblemRepository(session).get(problem_id)


async def list_problems(session: AsyncSession) -> list[Problem]:
    return await ProblemRepository(session).list()
