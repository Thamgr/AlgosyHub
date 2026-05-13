"""Submission-сервис.

Платформа сама не сдаёт решения за пользователя: студент сдаёт код в нативном
UI судьи (`/contest/.../submit`), а здесь мы только наблюдаем за его посылками
через публичные API судей и собираем их в единую таблицу.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory
from app.core.exceptions import AppError
from app.integrations.judges import registry
from app.integrations.judges.base import ExternalSubmission
from app.models.contest import Contest, contest_problems
from app.models.enums import ContestStatus, ExternalSource, SubmissionVerdict
from app.models.group import group_members
from app.models.judge_account import JudgeAccount
from app.models.problem import Problem
from app.models.submission import Submission
from app.repositories.submission_repo import SubmissionRepository

logger = logging.getLogger(__name__)


# Сколько последних посылок пользователя забираем за один проход поллера.
# CF user.status поддерживает paging, но обычно достаточно последних 50.
POLL_SUBMISSIONS_PER_USER = 50


async def get_submission(session: AsyncSession, submission_id: int) -> Submission:
    submission = await SubmissionRepository(session).get(submission_id)
    if not submission:
        raise AppError("Submission not found", 404)
    return submission


async def list_for_contest(
    session: AsyncSession, contest_id: int, user_id: int | None = None
) -> list[Submission]:
    return await SubmissionRepository(session).list_for_contest(contest_id, user_id)


async def poll_external_submissions() -> None:
    """Опрашивает посылки пользователей у внешних судей и синхронит с нашей БД.

    Алгоритм:
      1. Берём все (user_id, source) у которых:
         - подключён JudgeAccount(source)
         - есть доступ к хотя бы одному (active/finished) контесту с задачей на этом source
      2. Для каждого такого юзера фетчим его последние посылки на судье.
      3. Для каждой посылки, чья (source, external_problem_id) совпадает с
         задачей в одном из доступных юзеру контестов — вставляем или
         обновляем строку в submissions.
    """
    async with AsyncSessionFactory() as session:
        targets = await _collect_polling_targets(session)
        if not targets:
            return

        for (user_id, source), info in targets.items():
            try:
                adapter = registry.get(source)
            except KeyError:
                logger.warning("No adapter registered for source=%s", source)
                continue

            try:
                rows = await adapter.fetch_user_submissions(
                    info.handle, count=POLL_SUBMISSIONS_PER_USER
                )
            except Exception:
                logger.exception(
                    "Failed to fetch submissions for user=%s handle=%s source=%s",
                    user_id,
                    info.handle,
                    source,
                )
                continue

            await _sync_user_submissions(session, user_id, info, rows)

        await session.commit()


class _UserPollingInfo:
    """Что поллеру нужно знать про конкретного (user, source)."""

    __slots__ = ("handle", "problem_by_external_id", "contest_id_by_problem_id")

    def __init__(self, handle: str) -> None:
        self.handle = handle
        # ключ — external_id задачи на судье ("1900F2")
        self.problem_by_external_id: dict[str, Problem] = {}
        # к какому контесту прикреплять посылки по этой задаче
        # (выбираем самый "поздний" контест, в который входит задача и
        # к которому у юзера есть доступ — см. _pick_contest_id)
        self.contest_id_by_problem_id: dict[int, int] = {}


async def _collect_polling_targets(
    session: AsyncSession,
) -> dict[tuple[int, ExternalSource], _UserPollingInfo]:
    """Строит карту (user_id, source) → инфа для поллинга."""
    # Все интересные связки достаём одним запросом:
    # user в группе → группа имеет контест → контест содержит задачу с source X
    # И этот user имеет JudgeAccount(source=X)
    stmt = (
        select(
            group_members.c.user_id,
            JudgeAccount.handle,
            Contest.id.label("contest_id"),
            Contest.status,
            Problem.id.label("problem_id"),
            Problem.external_source,
            Problem.external_id,
        )
        .select_from(group_members)
        .join(Contest, Contest.group_id == group_members.c.group_id)
        .join(contest_problems, contest_problems.c.contest_id == Contest.id)
        .join(Problem, Problem.id == contest_problems.c.problem_id)
        .join(
            JudgeAccount,
            (JudgeAccount.user_id == group_members.c.user_id)
            & (JudgeAccount.source == Problem.external_source),
        )
        .where(Contest.status != ContestStatus.draft)
    )
    rows = (await session.execute(stmt)).all()

    targets: dict[tuple[int, ExternalSource], _UserPollingInfo] = {}
    # Чтобы не делать N+1, грузим Problem-ы пакетно по id.
    problem_ids = {r.problem_id for r in rows}
    if not problem_ids:
        return {}

    problems_map = {
        p.id: p
        for p in (
            await session.execute(select(Problem).where(Problem.id.in_(problem_ids)))
        )
        .scalars()
        .all()
    }

    # Для выбора "лучшего" контеста для задачи (если задача в нескольких) —
    # предпочтём running, затем самый поздний по starts_at.
    contest_order: dict[int, tuple[int, datetime]] = {}
    contests_rows = (
        await session.execute(
            select(Contest.id, Contest.status, Contest.starts_at).where(
                Contest.id.in_({r.contest_id for r in rows})
            )
        )
    ).all()
    EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
    for cid, status, starts_at in contests_rows:
        # running = 1 (приоритетнее), finished = 0
        priority = 1 if status == ContestStatus.running else 0
        contest_order[cid] = (priority, starts_at or EPOCH)

    for r in rows:
        key = (r.user_id, r.external_source)
        info = targets.setdefault(key, _UserPollingInfo(handle=r.handle))
        problem = problems_map.get(r.problem_id)
        if problem is None:
            continue
        info.problem_by_external_id[problem.external_id] = problem

        current_cid = info.contest_id_by_problem_id.get(problem.id)
        if current_cid is None or contest_order[r.contest_id] > contest_order.get(
            current_cid, (-1, EPOCH)
        ):
            info.contest_id_by_problem_id[problem.id] = r.contest_id

    return targets


async def _sync_user_submissions(
    session: AsyncSession,
    user_id: int,
    info: _UserPollingInfo,
    rows: list[ExternalSubmission],
) -> None:
    relevant = [
        row for row in rows if row.external_problem_id in info.problem_by_external_id
    ]
    if not relevant:
        return

    repo = SubmissionRepository(session)
    existing = await repo.find_by_external_ids(
        user_id, [row.external_id for row in relevant]
    )

    for row in relevant:
        problem = info.problem_by_external_id[row.external_problem_id]
        contest_id = info.contest_id_by_problem_id.get(problem.id)

        sub = existing.get(row.external_id)
        if sub is None:
            sub = Submission(
                user_id=user_id,
                problem_id=problem.id,
                contest_id=contest_id,
                language=row.language,
                source_code=None,
                verdict=row.verdict,
                external_submission_id=row.external_id,
                time_ms=row.time_ms,
                memory_mb=row.memory_mb,
                created_at=row.submitted_at,
            )
            session.add(sub)
        else:
            # Обновляем только волатильные поля — created_at и contest_id
            # фиксируются при первом наблюдении.
            sub.verdict = row.verdict
            if row.time_ms is not None:
                sub.time_ms = row.time_ms
            if row.memory_mb is not None:
                sub.memory_mb = row.memory_mb
            sub.language = row.language
