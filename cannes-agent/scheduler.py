import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import firecrawl

log = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="America/Chicago")


def _build_cron_times() -> list[tuple[int, int]]:
    """Return (hour, minute) tuples for all 9 daily digest times (CST)."""
    times = [(7, 0)]
    for hour in range(8, 23, 2):
        times.append((hour, 0))
    return times


def _format_digest_prompt(content: str) -> str:
    return (
        "Write a short, punchy Cannes Lions social buzz digest (5 bullets max) "
        "based on the following trending content from LinkedIn and X/Twitter. "
        "Plain text only, no markdown, no headers.\n\n"
        f"{content}"
    )


def _send_digest(bot, chat_id: str, anthropic_client, model: str) -> None:
    """Fetch trending content, generate digest, send to Telegram."""
    content = firecrawl.get_trending_content()
    if not content:
        log.info("No trending content found — skipping digest")
        return

    try:
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=512,
            messages=[{"role": "user", "content": _format_digest_prompt(content)}],
        )
        digest = response.content[0].text.strip()
    except Exception:
        log.exception("Claude digest generation failed")
        digest = "Couldn't fetch the Cannes buzz right now — try asking me directly."

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(bot.send_message(chat_id=chat_id, text=digest))
    except Exception:
        log.exception("Failed to send digest to Telegram")
    finally:
        loop.close()


def start_scheduler(bot, chat_id: str, anthropic_client, model: str) -> None:
    """Start APScheduler with all digest triggers. Called from FastAPI startup."""
    if not chat_id:
        log.warning("TELEGRAM_CHAT_ID not set — digest scheduler disabled")
        return

    for hour, minute in _build_cron_times():
        _scheduler.add_job(
            _send_digest,
            trigger=CronTrigger(hour=hour, minute=minute, timezone="America/Chicago"),
            args=[bot, chat_id, anthropic_client, model],
            id=f"digest_{hour:02d}{minute:02d}",
            replace_existing=True,
        )

    if not _scheduler.running:
        _scheduler.start()
    log.info("Digest scheduler started with %d jobs", len(_build_cron_times()))


def stop_scheduler() -> None:
    """Stop APScheduler. Called from FastAPI shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Digest scheduler stopped")
