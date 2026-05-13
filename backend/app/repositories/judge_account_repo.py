from sqlalchemy import select

from app.models.enums import ExternalSource
from app.models.judge_account import JudgeAccount
from app.repositories.base import BaseRepository


class JudgeAccountRepository(BaseRepository[JudgeAccount]):
    model = JudgeAccount

    async def list_for_user(self, user_id: int) -> list[JudgeAccount]:
        result = await self.session.execute(
            select(JudgeAccount).where(JudgeAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_for_user(
        self, user_id: int, source: ExternalSource
    ) -> JudgeAccount | None:
        result = await self.session.execute(
            select(JudgeAccount).where(
                JudgeAccount.user_id == user_id,
                JudgeAccount.source == source,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_users(
        self, user_ids: list[int], source: ExternalSource
    ) -> list[JudgeAccount]:
        if not user_ids:
            return []
        result = await self.session.execute(
            select(JudgeAccount).where(
                JudgeAccount.user_id.in_(user_ids),
                JudgeAccount.source == source,
            )
        )
        return list(result.scalars().all())
