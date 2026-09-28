from sqlalchemy import distinct, func, or_, select

from app.models.contest import Contest
from app.models.enums import SubmissionVerdict
from app.models.submission import Submission
from app.models.user import User
from app.repositories.base import BaseRepository
from app.repositories.submission_repo import submission_in_window


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def submission_stats(self, user_id: int) -> tuple[int, int, int]:
        """Возвращает (total_submissions, accepted_submissions, solved_problems).

        Посылки контестов учитываются только внутри текущего интервала зачёта.
        Посылки без контеста по-прежнему входят в общую статистику.

        - total_submissions — все подходящие посылки пользователя;
        - accepted_submissions — посылки с вердиктом accepted;
        - solved_problems — количество уникальных задач с хотя бы одной accepted-посылкой.
        """
        row = (
            await self.session.execute(
                select(
                    func.count(Submission.id),
                    func.count(Submission.id).filter(
                        Submission.verdict == SubmissionVerdict.accepted
                    ),
                    func.count(distinct(Submission.problem_id)).filter(
                        Submission.verdict == SubmissionVerdict.accepted
                    ),
                )
                .outerjoin(Contest, Contest.id == Submission.contest_id)
                .where(
                    Submission.user_id == user_id,
                    or_(
                        Submission.contest_id.is_(None),
                        submission_in_window(Contest.starts_at, Contest.ends_at),
                    ),
                )
            )
        ).one()
        return int(row[0]), int(row[1]), int(row[2])
