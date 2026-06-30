import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from bot.ingest import run_ingest
from bot.telegram_bot import build_app

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _scheduled_ingest():
    success = await run_ingest()
    if not success:
        logger.warning("Report not found at 07:05 UTC. Retrying in 30 min...")
        await asyncio.sleep(1800)
        await run_ingest()


async def _run():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = build_app(token)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_scheduled_ingest, "cron", hour=7, minute=5, timezone="UTC")
    scheduler.start()
    logger.info("Scheduler started. Daily ingest at 07:05 UTC.")

    async with app:
        await app.start()
        await app.updater.start_polling()
        logger.info("Telegram bot polling started.")
        await asyncio.Event().wait()


def main():
    asyncio.run(_run())


if __name__ == "__main__":
    main()
