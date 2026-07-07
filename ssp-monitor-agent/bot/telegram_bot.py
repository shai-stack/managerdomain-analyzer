import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import data_store, qa, session

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        u"👋 SSP Monitor active. Ask me anything about your client performance.\n\n"
        "Commands:\n"
        "/status — show loaded report date\n"
        "/refresh — manually re-check Gmail\n\n"
        "Say 'full list' for all clients, 'yesterday' for previous day data."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = data_store.load()
    if data:
        await update.message.reply_text(u"✅ Latest report: {}".format(data["latest_date"]))
    else:
        await update.message.reply_text(u"⚠️ No report loaded. Try /refresh.")


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(u"🔄 Checking Gmail for latest report...")
    from bot.ingest import run_ingest
    success = await run_ingest()
    if success:
        data = data_store.load()
        await update.message.reply_text(u"✅ Report refreshed: {}".format(data["latest_date"]))
    else:
        await update.message.reply_text(u"❌ No new report found in inbox.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    if not doc.file_name.endswith(".csv"):
        await update.message.reply_text(u"⚠️ Please send a .csv file.")
        return
    await update.message.reply_text(u"📂 Loading CSV...")
    file = await doc.get_file()
    csv_bytes = await file.download_as_bytearray()
    csv_content = csv_bytes.decode("utf-8", errors="replace")
    try:
        data = data_store.parse_csv(csv_content)
        data_store.save(data)
        session.clear_all()
        await update.message.reply_text(u"✅ Report loaded: {}. Ask me anything!".format(data["latest_date"]))
    except Exception as e:
        await update.message.reply_text(u"❌ Failed to parse CSV: {}".format(str(e)))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    api_key = os.environ["ANTHROPIC_API_KEY"]

    data = data_store.load()
    if not data:
        await update.message.reply_text(u"⚠️ No report data yet. Try /refresh.")
        return

    if qa.is_full_list_request(text):
        full = qa.get_full_list(data)
        for i in range(0, len(full), 4096):
            await update.message.reply_text(full[i: i + 4096])
        return

    await update.effective_chat.send_action("typing")
    history = session.get_history(chat_id)
    response = qa.answer(text, data, history, api_key)
    session.append(chat_id, "user", text)
    session.append(chat_id, "assistant", response)

    for i in range(0, len(response), 4096):
        await update.message.reply_text(response[i: i + 4096])


def build_app(token):
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    return app
