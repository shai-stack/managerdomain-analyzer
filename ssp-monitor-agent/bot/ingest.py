import logging
import os

from telegram import Bot

from bot import data_store, digest, email_watcher, session

logger = logging.getLogger(__name__)


async def run_ingest():
    """Fetch email, parse CSV, generate digest, send to Telegram.
    Returns True if a new report was found and processed.
    """
    gmail_email = os.environ["GMAIL_EMAIL"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    api_key = os.environ["ANTHROPIC_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = int(os.environ["TELEGRAM_CHAT_ID"])

    logger.info("Checking Gmail for SSP report...")
    csv_content = email_watcher.fetch_latest_csv(gmail_email, app_password)
    if not csv_content:
        logger.warning("No report email found.")
        return False

    logger.info("Parsing CSV...")
    data = data_store.parse_csv(csv_content)
    data_store.save(data)

    session.clear_all()

    logger.info("Generating digest with Claude...")
    messages = digest.generate_digest(data, api_key)

    logger.info("Sending digest to Telegram...")
    bot = Bot(token=bot_token)
    async with bot:
        for msg in messages:
            await bot.send_message(chat_id=chat_id, text=msg)

    logger.info("Digest sent for %s.", data["latest_date"])
    return True
