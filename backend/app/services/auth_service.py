from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


async def register(
    session: AsyncSession,
    username: str,
    password: str,
    role: str,
) -> User:
    existing = await session.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise AppError("Username уже занят", 409)

    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def login(session: AsyncSession, username: str, password: str) -> str:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise AppError("Неверный логин или пароль", 401)
    return create_access_token(user.id)


async def get_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise AppError("Пользователь не найден", 404)
    return user
