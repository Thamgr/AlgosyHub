from sqlalchemy import distinct, func, select

from app.models.enums import SubmissionVerdict
from app.models.submission import Submission
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def submission_stats(self, user_id: int) -> tuple[int, int, int]:
        """Возвращает (total_submissions, accepted_submissions, solved_problems).

        - total_submissions — все посылки пользователя в нашей БД;
        - accepted_submissions — посылки с вердиктом accepted;
        - solved_problems — количество уникальных задач с хотя бы одной accepted-посылкой.
        """
        totals_row = (
            await self.session.execute(
                select(
                    func.count(Submission.id),
                    func.count(Submission.id).filter(
                        Submission.verdict == SubmissionVerdict.accepted
                    ),
                ).where(Submission.user_id == user_id)
            )
        ).one()
        total, accepted = int(totals_row[0]), int(totals_row[1])

        solved = int(
            (
                await self.session.execute(
                    select(func.count(distinct(Submission.problem_id))).where(
                        Submission.user_id == user_id,
                        Submission.verdict == SubmissionVerdict.accepted,
                    )
                )
            ).scalar_one()
        )
        return total, accepted, solved
