from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, group_members
from app.models.user import User
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    model = Group

    async def get_by_teacher(self, teacher_id: int) -> list[Group]:
        result = await self.session.execute(
            select(Group).where(Group.teacher_id == teacher_id)
        )
        return list(result.scalars().all())

    async def get_for_user(self, user_id: int) -> list[Group]:
        result = await self.session.execute(
            select(Group)
            .join(group_members, group_members.c.group_id == Group.id)
            .where(group_members.c.user_id == user_id)
        )
        return list(result.scalars().all())

    async def add_member(self, group_id: int, user_id: int) -> None:
        await self.session.execute(
            group_members.insert().values(group_id=group_id, user_id=user_id)
        )

    async def remove_member(self, group_id: int, user_id: int) -> None:
        await self.session.execute(
            delete(group_members).where(
                group_members.c.group_id == group_id,
                group_members.c.user_id == user_id,
            )
        )

    async def get_members(self, group_id: int) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(group_members, group_members.c.user_id == User.id)
            .where(group_members.c.group_id == group_id)
        )
        return list(result.scalars().all())

    async def is_member(self, group_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(group_members).where(
                group_members.c.group_id == group_id,
                group_members.c.user_id == user_id,
            )
        )
        return result.first() is not None
