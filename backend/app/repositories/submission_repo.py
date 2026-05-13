from sqlalchemy import select

from app.models.submission import Submission
from app.repositories.base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    model = Submission

    async def list_for_contest(
        self, contest_id: int, user_id: int | None = None
    ) -> list[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.contest_id == contest_id)
            .order_by(Submission.created_at.desc())
        )
        if user_id is not None:
            stmt = stmt.where(Submission.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_problem(self, user_id: int, problem_id: int) -> list[Submission]:
        result = await self.session.execute(
            select(Submission)
            .where(Submission.user_id == user_id, Submission.problem_id == problem_id)
            .order_by(Submission.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_external_ids(
        self, user_id: int, external_ids: list[str]
    ) -> dict[str, Submission]:
        """Возвращает наши Submission-записи для пользователя по их CF-id.

        Используется поллером, чтобы понять — это новая посылка или обновление
        существующей.
        """
        if not external_ids:
            return {}
        result = await self.session.execute(
            select(Submission).where(
                Submission.user_id == user_id,
                Submission.external_submission_id.in_(external_ids),
            )
        )
        return {
            row.external_submission_id: row
            for row in result.scalars().all()
            if row.external_submission_id is not None
        }
