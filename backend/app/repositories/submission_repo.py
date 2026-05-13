from sqlalchemy import select

from app.models.enums import SubmissionVerdict
from app.models.submission import Submission
from app.repositories.base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    model = Submission

    async def list_pending(self) -> list[Submission]:
        """Сабмиты, по которым ещё не пришёл финальный вердикт."""
        result = await self.session.execute(
            select(Submission).where(
                Submission.verdict.in_(
                    [SubmissionVerdict.pending, SubmissionVerdict.running]
                )
            )
        )
        return list(result.scalars().all())

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
