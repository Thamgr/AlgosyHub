from sqlalchemy import and_, delete, or_, select

from app.models.contest import Contest, contest_groups, contest_problems
from app.models.group import group_members
from app.models.problem import Problem
from app.repositories.base import BaseRepository


class ContestRepository(BaseRepository[Contest]):
    model = Contest

    async def get_by_group(self, group_id: int, user_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest)
            .join(contest_groups, contest_groups.c.contest_id == Contest.id)
            .where(contest_groups.c.group_id == group_id)
            .where(self.access_filter(user_id))
            .order_by(Contest.id.desc())
        )
        return list(result.scalars().unique().all())

    async def get_by_teacher(self, teacher_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest)
            .where(Contest.teacher_id == teacher_id)
            .order_by(Contest.id.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    def access_filter(user_id: int):
        """Owners always have access; others need visibility and group access."""
        has_any_group = (
            select(contest_groups.c.contest_id)
            .where(contest_groups.c.contest_id == Contest.id)
            .correlate(Contest)
            .exists()
        )
        user_in_group = (
            select(contest_groups.c.contest_id)
            .join(
                group_members,
                group_members.c.group_id == contest_groups.c.group_id,
            )
            .where(
                contest_groups.c.contest_id == Contest.id,
                group_members.c.user_id == user_id,
            )
            .correlate(Contest)
            .exists()
        )
        return or_(
            Contest.teacher_id == user_id,
            and_(Contest.is_visible.is_(True), or_(~has_any_group, user_in_group)),
        )

    async def get_for_user(self, user_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest)
            .where(self.access_filter(user_id))
            .order_by(Contest.id.desc())
        )
        return list(result.scalars().unique().all())

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

    async def set_problem_order(self, contest_id: int, problem_ids: list[int]) -> None:
        """Rewrite ``order_index`` for the contest's problems in the given order.

        Problems not present in ``problem_ids`` are left untouched.
        """
        for idx, pid in enumerate(problem_ids):
            await self.session.execute(
                contest_problems.update()
                .where(
                    contest_problems.c.contest_id == contest_id,
                    contest_problems.c.problem_id == pid,
                )
                .values(order_index=idx)
            )

    async def problem_count(self, contest_id: int) -> int:
        problems = await self.get_problems(contest_id)
        return len(problems)

    # -- contest ↔ group (tags) --------------------------------------------

    async def get_group_ids(self, contest_id: int) -> list[int]:
        result = await self.session.execute(
            select(contest_groups.c.group_id).where(
                contest_groups.c.contest_id == contest_id
            )
        )
        return [row[0] for row in result.all()]

    async def set_groups(self, contest_id: int, group_ids: list[int]) -> None:
        await self.session.execute(
            delete(contest_groups).where(contest_groups.c.contest_id == contest_id)
        )
        if not group_ids:
            return
        await self.session.execute(
            contest_groups.insert(),
            [{"contest_id": contest_id, "group_id": gid} for gid in set(group_ids)],
        )

    async def user_can_access(self, contest_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(Contest.id).where(Contest.id == contest_id, self.access_filter(user_id))
        )
        return result.scalar_one_or_none() is not None
