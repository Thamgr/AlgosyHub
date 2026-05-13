import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppError
from app.integrations.judges import registry
from app.integrations.judges.base import SubmissionResult
from app.models.contest import Contest
from app.models.enums import ContestStatus, SubmissionVerdict
from app.models.submission import Submission
from app.repositories.contest_repo import ContestRepository
from app.repositories.problem_repo import ProblemRepository
from app.repositories.submission_repo import SubmissionRepository

logger = logging.getLogger(__name__)


async def submit(
    session: AsyncSession,
    user_id: int,
    problem_id: int,
    contest_id: int | None,
    language: str,
    source_code: str,
) -> Submission:
    problem = await ProblemRepository(session).get(problem_id)
    if not problem:
        raise AppError("Problem not found", 404)

    if contest_id is not None:
        contest = await ContestRepository(session).get(contest_id)
        if not contest:
            raise AppError("Contest not found", 404)
        _check_contest_open(contest)
        problems = await ContestRepository(session).get_problems(contest_id)
        if not any(p.id == problem_id for p in problems):
            raise AppError("Problem is not part of this contest", 400)

    adapter = registry.get(problem.external_source)

    submission = await SubmissionRepository(session).create(
        user_id=user_id,
        problem_id=problem_id,
        contest_id=contest_id,
        language=language,
        source_code=source_code,
        verdict=SubmissionVerdict.pending,
    )
    # Сохраняем pending-запись сразу, чтобы UI её увидел даже если CF тормозит.
    await session.commit()

    try:
        external_id = await adapter.submit(
            problem.external_id, language, source_code
        )
    except Exception as exc:
        logger.exception("Submit to judge failed for submission %s", submission.id)
        submission.verdict = SubmissionVerdict.rejected
        await session.commit()
        raise AppError(f"Failed to submit to judge: {exc}", 502) from exc

    submission.external_submission_id = external_id
    submission.verdict = SubmissionVerdict.running
    await session.commit()
    await session.refresh(submission)
    return submission


def _check_contest_open(contest: Contest) -> None:
    if contest.status == ContestStatus.finished:
        raise AppError("Contest is finished", 400)
    if contest.status == ContestStatus.draft:
        raise AppError("Contest has not started yet", 400)


async def get_submission(session: AsyncSession, submission_id: int) -> Submission:
    submission = await SubmissionRepository(session).get(submission_id)
    if not submission:
        raise AppError("Submission not found", 404)
    return submission


async def list_for_contest(
    session: AsyncSession, contest_id: int, user_id: int | None = None
) -> list[Submission]:
    return await SubmissionRepository(session).list_for_contest(contest_id, user_id)


async def poll_pending_verdicts() -> None:
    """Фоновое обновление вердиктов для всех pending/running сабмитов.

    Вызывается APScheduler-ом. Открывает собственную сессию БД, чтобы не
    зависеть от запроса.
    """
    async with AsyncSessionFactory() as session:
        repo = SubmissionRepository(session)
        pending = await repo.list_pending()
        if not pending:
            return

        for sub in pending:
            if not sub.external_submission_id:
                continue
            problem = await ProblemRepository(session).get(sub.problem_id)
            if not problem:
                continue
            try:
                adapter = registry.get(problem.external_source)
            except KeyError:
                logger.warning(
                    "No adapter for %s while polling submission %s",
                    problem.external_source,
                    sub.id,
                )
                continue

            try:
                result: SubmissionResult = await adapter.poll_verdict(
                    sub.external_submission_id
                )
            except Exception:
                logger.exception(
                    "Failed to poll verdict for submission %s", sub.id
                )
                continue

            sub.verdict = result.verdict
            if result.time_ms is not None:
                sub.time_ms = result.time_ms
            if result.memory_mb is not None:
                sub.memory_mb = result.memory_mb

        await session.commit()
