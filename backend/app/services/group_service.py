from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.group import Group
from app.models.user import User
from app.repositories.group_repo import GroupRepository


async def create_group(
    session: AsyncSession, teacher_id: int, name: str, description: str | None
) -> Group:
    repo = GroupRepository(session)
    return await repo.create(teacher_id=teacher_id, name=name, description=description)


async def get_group(session: AsyncSession, group_id: int) -> Group:
    group = await GroupRepository(session).get(group_id)
    if not group:
        raise AppError("Group not found", 404)
    return group


async def list_groups(session: AsyncSession, user_id: int, role: str) -> list[Group]:
    repo = GroupRepository(session)
    if role == "teacher":
        return await repo.get_by_teacher(user_id)
    return await repo.get_for_user(user_id)


async def add_member_by_username(
    session: AsyncSession, group_id: int, teacher_id: int, username: str
) -> None:
    repo = GroupRepository(session)
    group = await repo.get(group_id)
    if not group or group.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)

    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise AppError(f"User '{username}' not found", 404)

    if await repo.is_member(group_id, user.id):
        raise AppError("Already a member", 409)

    await repo.add_member(group_id, user.id)


async def remove_member(
    session: AsyncSession, group_id: int, teacher_id: int, user_id: int
) -> None:
    repo = GroupRepository(session)
    group = await repo.get(group_id)
    if not group or group.teacher_id != teacher_id:
        raise AppError("Forbidden", 403)
    await repo.remove_member(group_id, user_id)


async def get_members(session: AsyncSession, group_id: int) -> list[User]:
    return await GroupRepository(session).get_members(group_id)
