from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExternalSource
from app.models.judge_account import JudgeAccount
from app.repositories.judge_account_repo import JudgeAccountRepository


async def list_for_user(session: AsyncSession, user_id: int) -> list[JudgeAccount]:
    return await JudgeAccountRepository(session).list_for_user(user_id)


async def upsert(
    session: AsyncSession, user_id: int, source: ExternalSource, handle: str
) -> JudgeAccount:
    repo = JudgeAccountRepository(session)
    existing = await repo.get_for_user(user_id, source)
    if existing:
        existing.handle = handle
        await session.flush()
        await session.refresh(existing)
        return existing
    return await repo.create(user_id=user_id, source=source, handle=handle)


async def delete(
    session: AsyncSession, user_id: int, source: ExternalSource
) -> bool:
    repo = JudgeAccountRepository(session)
    existing = await repo.get_for_user(user_id, source)
    if not existing:
        return False
    await repo.delete(existing)
    return True
