from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.core.api import Scraper
from bot.core.logger import log_function
from bot.core.models.application import ApplicationModel
from bot.core.notificator import notify_subscribers
from bot.core.utils import process_status_update

JOB_ID = "status_check"
scheduler_ref: AsyncIOScheduler | None = None


def set_scheduler(scheduler: AsyncIOScheduler) -> None:
    global scheduler_ref
    scheduler_ref = scheduler


def update_scheduler_interval(minutes: int) -> bool:
    if not scheduler_ref:
        return False
    job = scheduler_ref.get_job(JOB_ID)
    if not job:
        return False
    scheduler_ref.reschedule_job(JOB_ID, trigger="interval", minutes=minutes)
    return True


def get_scheduler_interval_minutes() -> int | None:
    if not scheduler_ref:
        return None
    job = scheduler_ref.get_job(JOB_ID)
    if not job:
        return None
    try:
        interval = getattr(job.trigger, "interval", None)
        if not interval:
            return None
        return int(interval.total_seconds() // 60)
    except Exception:
        return None


@log_function("scheduler_job")
async def scheduler_job() -> None:
    applications = await ApplicationModel.find({}).to_list()
    scraper = Scraper()

    for application in applications:
        try:
            await process_status_update(application, scraper, notify_subscribers)
        except Exception as e:
            # Log error but continue processing other applications
            from bot.core.logger import log_error

            log_error(
                f"Failed to process status update for session {application.session_id}",
                exception=e,
            )
