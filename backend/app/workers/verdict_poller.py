import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import submission_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 5


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        submission_service.poll_pending_verdicts,
        "interval",
        seconds=POLL_INTERVAL_SEC,
        id="verdict_poller",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
