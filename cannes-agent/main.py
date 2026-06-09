import asyncio
import logging
import os

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

import agent
import scheduler as digest_scheduler
from gcal import build_calendar_client

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

app = FastAPI()

try:
    cal_client = build_calendar_client()
    if cal_client:
        log.info("Google Calendar client initialized OK (calendar_id=%s)", os.getenv("GOOGLE_CALENDAR_ID", "primary"))
    else:
        log.warning("Google Calendar client is None — GOOGLE_CREDENTIALS_JSON may not be set")
except Exception as e:
    log.warning("Google Calendar client failed to initialize: %s", e)
    cal_client = None

# Build the Telegram bot application
_telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


async def handle_message(update: Update, context) -> None:
    """Handle incoming Telegram messages."""
    if not update.message or not update.message.text:
        return
    phone = str(update.message.chat_id)
    user_message = update.message.text
    log.info("Received message from %s: %s", phone, user_message)
    try:
        reply = await asyncio.to_thread(agent.run, phone, user_message, cal_client)
        log.info("Sending reply to %s: %s", phone, reply[:80])
        await update.message.reply_text(reply)
    except Exception as e:
        log.exception("Failed to handle message: %s", e)
        await update.message.reply_text("Sorry, something went wrong. Please try again.")


_telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@app.on_event("startup")
async def startup():
    await _telegram_app.initialize()
    if WEBHOOK_URL:
        webhook = f"https://{WEBHOOK_URL}/telegram"
        await _telegram_app.bot.set_webhook(webhook)
        log.info("Telegram webhook set to %s", webhook)
    else:
        log.warning("RAILWAY_PUBLIC_DOMAIN not set — webhook not registered")

    digest_scheduler.start_scheduler(
        bot=_telegram_app.bot,
        chat_id=TELEGRAM_CHAT_ID,
        anthropic_client=agent.anthropic_client,
        model=agent.MODEL,
    )


@app.on_event("shutdown")
async def shutdown():
    digest_scheduler.stop_scheduler()
    await _telegram_app.shutdown()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, _telegram_app.bot)
    await _telegram_app.process_update(update)
    return Response(status_code=200)
