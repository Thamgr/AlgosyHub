import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.user_repo import UserRepository

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


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


async def rename(session: AsyncSession, user_id: int, new_username: str) -> User:
    new_username = new_username.strip()
    if not USERNAME_RE.match(new_username):
        raise AppError(
            "Username должен быть 3–32 символа: латиница, цифры, _ . -", 400
        )

    repo = UserRepository(session)
    user = await repo.get(user_id)
    if not user:
        raise AppError("Пользователь не найден", 404)

    if user.username == new_username:
        return user

    existing = await repo.get_by_username(new_username)
    if existing and existing.id != user_id:
        raise AppError("Username уже занят", 409)

    user.username = new_username
    await session.flush()
    await session.refresh(user)
    return user
