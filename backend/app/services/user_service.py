from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.user_repo import UserRepository


async def get_by_username(session: AsyncSession, username: str) -> User:
    user = await UserRepository(session).get_by_username(username)
    if not user:
        raise AppError("User not found", 404)
    return user


async def get_stats(session: AsyncSession, user_id: int) -> dict:
    total, accepted, solved = await UserRepository(session).submission_stats(user_id)
    success_rate = (accepted / total) if total > 0 else 0.0
    return {
        "solved_problems": solved,
        "total_submissions": total,
        "accepted_submissions": accepted,
        "success_rate": success_rate,
    }


async def update_profile(
    session: AsyncSession,
    user_id: int,
    *,
    full_name: str | None = None,
) -> User:
    user = await UserRepository(session).get(user_id)
    if not user:
        raise AppError("Пользователь не найден", 404)
    if full_name is not None:
        user.full_name = full_name
    await session.flush()
    await session.refresh(user)
    return user
