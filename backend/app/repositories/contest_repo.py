from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contest import Contest, contest_problems
from app.models.group import group_members
from app.models.problem import Problem
from app.repositories.base import BaseRepository


class ContestRepository(BaseRepository[Contest]):
    model = Contest

    async def get_by_group(self, group_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest).where(Contest.group_id == group_id)
        )
        return list(result.scalars().all())

    async def get_by_teacher(self, teacher_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest).where(Contest.teacher_id == teacher_id)
        )
        return list(result.scalars().all())

    async def get_for_user(self, user_id: int) -> list[Contest]:
        """Контесты, доступные студенту через группы, в которых он состоит."""
        result = await self.session.execute(
            select(Contest)
            .join(group_members, group_members.c.group_id == Contest.group_id)
            .where(group_members.c.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_problems(self, contest_id: int) -> list[Problem]:
        result = await self.session.execute(
            select(Problem)
            .join(contest_problems, contest_problems.c.problem_id == Problem.id)
            .where(contest_problems.c.contest_id == contest_id)
            .order_by(contest_problems.c.order_index)
        )
        return list(result.scalars().all())

    async def add_problem(self, contest_id: int, problem_id: int, order_index: int) -> None:
        await self.session.execute(
            contest_problems.insert().values(
                contest_id=contest_id,
                problem_id=problem_id,
                order_index=order_index,
            )
        )

    async def remove_problem(self, contest_id: int, problem_id: int) -> None:
        await self.session.execute(
            delete(contest_problems).where(
                contest_problems.c.contest_id == contest_id,
                contest_problems.c.problem_id == problem_id,
            )
        )

    async def problem_count(self, contest_id: int) -> int:
        problems = await self.get_problems(contest_id)
        return len(problems)
