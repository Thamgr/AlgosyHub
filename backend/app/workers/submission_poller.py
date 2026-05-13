import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import submission_service

logger = logging.getLogger(__name__)

# Раз в 15 секунд достаточно — `user.status` живёт публично, и мы не хотим
# словить rate limit от CF при росте числа активных юзеров.
POLL_INTERVAL_SEC = 15


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        submission_service.poll_external_submissions,
        "interval",
        seconds=POLL_INTERVAL_SEC,
        id="submission_poller",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
