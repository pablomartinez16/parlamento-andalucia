import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.database import AsyncSessionLocal
from app.services.ingesta import IngestaService

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_sync_job():
    logger.info("Executing scheduled RSS sync job...")
    async with AsyncSessionLocal() as session:
        try:
            service = IngestaService(session)
            count = await service.sync_from_rss()
            logger.info(f"Scheduled sync completed: {count} initiatives processed.")
        except Exception as e:
            logger.error(f"Error during scheduled sync: {e}")


def start_scheduler():
    if settings.ENABLE_SCHEDULER:
        scheduler.add_job(
            scheduled_sync_job,
            "interval",
            minutes=settings.SYNC_INTERVAL_MINUTES,
            id="sync_parliament_rss",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduler started: running sync every {settings.SYNC_INTERVAL_MINUTES} minutes.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
