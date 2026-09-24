from sqlalchemy import and_, or_, select

from app.models.contest import Contest
from app.models.enums import ExternalSource
from app.models.problem import Problem
from app.models.submission import Submission
from app.repositories.base import BaseRepository


def contest_submission_filter(contest_id: int):
    """Use the current deadline, including after edits, without deleting history.

    A submission sent before the cutoff still counts when discovered/judged
    afterwards. Late submissions remain available in the user's history and
    become eligible if the teacher extends the deadline.
    """
    deadline = select(Contest.ends_at).where(Contest.id == contest_id).scalar_subquery()
    return and_(
        Submission.contest_id == contest_id,
        or_(deadline.is_(None), Submission.created_at < deadline),
    )


class SubmissionRepository(BaseRepository[Submission]):
    model = Submission

    async def list_for_contest(
        self, contest_id: int, user_id: int | None = None
    ) -> list[Submission]:
        stmt = (
            select(Submission)
            .where(contest_submission_filter(contest_id))
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
        self, user_id: int, source: ExternalSource, external_ids: list[str]
    ) -> dict[str, Submission]:
        """Возвращает наши Submission-записи для пользователя по id в пределах одного внешнего судьи.

        Используется поллером, чтобы понять — это новая посылка или обновление
        существующей.
        """
        if not external_ids:
            return {}
        result = await self.session.execute(
            select(Submission)
            .join(Problem, Problem.id == Submission.problem_id)
            .where(
                Submission.user_id == user_id,
                Problem.external_source == source,
                Submission.external_submission_id.in_(external_ids),
            )
        )
        return {
            row.external_submission_id: row
            for row in result.scalars().all()
            if row.external_submission_id is not None
        }
