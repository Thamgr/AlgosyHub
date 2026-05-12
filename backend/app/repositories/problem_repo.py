from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExternalSource
from app.models.problem import Problem
from app.repositories.base import BaseRepository


class ProblemRepository(BaseRepository[Problem]):
    model = Problem

    async def get_by_external(self, source: ExternalSource, external_id: str) -> Problem | None:
        result = await self.session.execute(
            select(Problem).where(
                Problem.external_source == source,
                Problem.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()
