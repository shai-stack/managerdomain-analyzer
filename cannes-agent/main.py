import asyncio
import logging
import os

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

import agent
from gcal import build_calendar_client

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")

app = FastAPI()

try:
    cal_client = build_calendar_client()
except Exception:
    log.warning("Google Calendar client failed to initialize, calendar features disabled")
    cal_client = None

# Build the Telegram bot application
_telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


async def handle_message(update: Update, context) -> None:
    """Handle incoming Telegram messages."""
    if not update.message or not update.message.text:
        return
    phone = str(update.message.chat_id)
    user_message = update.message.text
    reply = await asyncio.to_thread(agent.run, phone, user_message, cal_client)
    await update.message.reply_text(reply)


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


@app.on_event("shutdown")
async def shutdown():
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
