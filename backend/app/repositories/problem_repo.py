from sqlalchemy import or_, select

from app.models.contest import Contest, contest_problems
from app.models.enums import ExternalSource
from app.models.problem import Problem
from app.repositories.base import BaseRepository
from app.repositories.contest_repo import ContestRepository


class ProblemRepository(BaseRepository[Problem]):
    model = Problem

    @staticmethod
    def access_filter(user_id: int):
        linked = select(contest_problems.c.contest_id).where(
            contest_problems.c.problem_id == Problem.id
        ).correlate(Problem)
        available = linked.join(Contest, Contest.id == contest_problems.c.contest_id).where(
            ContestRepository.problems_access_filter(user_id)
        )
        return or_(~linked.exists(), available.exists())

    async def list_for_user(self, user_id: int) -> list[Problem]:
        return list((await self.session.scalars(
            select(Problem).where(self.access_filter(user_id)).order_by(Problem.id)
        )).all())

    async def get_by_external(self, source: ExternalSource, external_id: str) -> Problem | None:
        result = await self.session.execute(
            select(Problem).where(
                Problem.external_source == source,
                Problem.external_id == external_id,
            )
        )
        return result.scalar_one_or_none()
