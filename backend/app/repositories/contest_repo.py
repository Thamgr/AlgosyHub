from sqlalchemy import delete, select

from app.models.contest import Contest, contest_groups, contest_problems
from app.models.group import group_members
from app.models.problem import Problem
from app.repositories.base import BaseRepository


class ContestRepository(BaseRepository[Contest]):
    model = Contest

    async def get_by_group(self, group_id: int) -> list[Contest]:
        result = await self.session.execute(
            select(Contest)
            .join(contest_groups, contest_groups.c.contest_id == Contest.id)
            .where(contest_groups.c.group_id == group_id)
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

    async def get_for_user(self, user_id: int) -> list[Contest]:
        """Contests visible to a student through any of the contest's groups."""
        result = await self.session.execute(
            select(Contest)
            .join(contest_groups, contest_groups.c.contest_id == Contest.id)
            .join(group_members, group_members.c.group_id == contest_groups.c.group_id)
            .where(group_members.c.user_id == user_id)
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
        """True if user is the teacher or a member of any of the contest's groups."""
        teacher_row = await self.session.execute(
            select(Contest.teacher_id).where(Contest.id == contest_id)
        )
        teacher_id = teacher_row.scalar_one_or_none()
        if teacher_id is None:
            return False
        if teacher_id == user_id:
            return True

        membership = await self.session.execute(
            select(contest_groups.c.group_id)
            .join(group_members, group_members.c.group_id == contest_groups.c.group_id)
            .where(
                contest_groups.c.contest_id == contest_id,
                group_members.c.user_id == user_id,
            )
            .limit(1)
        )
        return membership.first() is not None
