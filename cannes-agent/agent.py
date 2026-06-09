import logging
import os
import anthropic

from datetime import date, timedelta
from typing import Optional

from gcal import CalendarClient, CalendarEvent
from conversation import ConversationHistory

CANNES_MCP_URL = os.getenv("CANNES_MCP_URL", "https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp")
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048
WHATSAPP_LIMIT = 1500

_history = ConversationHistory(max_messages=10)
_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
if not os.getenv("ANTHROPIC_API_KEY"):
    import logging as _log
    _log.getLogger(__name__).warning("ANTHROPIC_API_KEY is not set — agent calls will fail")


def build_system_prompt(calendar_summary: Optional[str]) -> str:
    today = date.today()
    day_name = today.strftime("%A")  # e.g. "Sunday"
    date_str = today.strftime("%B %d, %Y")  # e.g. "June 09, 2026"
    cal_section = ""
    if calendar_summary:
        cal_section = f"\n\nShai's Google Calendar (today + Cannes week June 21-26):\n{calendar_summary}"
    return (
        f"You are a personal assistant for Shai, helping him navigate Cannes Lions 2026. "
        f"Today is {day_name}, {date_str}. Cannes Lions 2026 runs June 21-26. "
        "Shai's role is adtech. He is attending as an adtech professional. "
        "Use the Cannes schedule tools to answer questions about events, panels, and registrations. "
        "Keep all replies concise, plain text, no markdown — Telegram renders markdown differently. "
        "If listing events, show at most 5 and offer to send more. "
        "When recommending events, check for calendar conflicts and flag them."
        f"{cal_section}"
    )


_TRENDING_KEYWORDS = [
    "trending", "buzz", "what's people saying", "what are people",
    "social media", "social posts", "social buzz",
    "linkedin", "twitter", "x.com", "what's happening",
    "talking about", "people saying",
]


def _is_trending_query(message: str) -> bool:
    """Return True if the message is asking about social/trending Cannes content."""
    lower = message.lower()
    return any(kw in lower for kw in _TRENDING_KEYWORDS)


def _inject_trending(system_prompt: str, trending_content: str) -> str:
    """Append trending content block to system prompt if content is non-empty."""
    if not trending_content:
        return system_prompt
    return (
        system_prompt
        + f"\n\nCurrent Cannes Lions social buzz (LinkedIn + X):\n{trending_content}"
    )


def truncate_for_whatsapp(text: str) -> str:
    if len(text) <= WHATSAPP_LIMIT:
        return text
    return text[: WHATSAPP_LIMIT - 3] + "..."


def _get_calendar_summary(cal_client: Optional[CalendarClient]) -> Optional[str]:
    """Fetch calendar events for Cannes week (June 21-26) plus today."""
    if cal_client is None:
        return None
    try:
        cannes_start = date(2026, 6, 21)
        cannes_end = date(2026, 6, 26)
        today = date.today()
        # Collect unique dates: today + all of Cannes week
        dates_to_fetch = set()
        dates_to_fetch.add(today)
        d = cannes_start
        while d <= cannes_end:
            dates_to_fetch.add(d)
            d += timedelta(days=1)
        lines = []
        for d in sorted(dates_to_fetch):
            events = cal_client.get_events_for_day(d)
            if events:
                label = d.strftime("%A %B %d")
                lines.append(f"{label}:")
                lines.extend(f"  {e}" for e in events)
        return "\n".join(lines) if lines else None
    except Exception:
        return None


def run(phone: str, user_message: str, cal_client: Optional[CalendarClient] = None) -> str:
    calendar_summary = _get_calendar_summary(cal_client)
    system_prompt = build_system_prompt(calendar_summary)

    if _is_trending_query(user_message):
        import firecrawl
        trending = firecrawl.get_trending_content()
        system_prompt = _inject_trending(system_prompt, trending)

    _history.add(phone, "user", user_message)
    messages = _history.get(phone)

    try:
        logging.getLogger(__name__).info("Calling Claude API for phone %s: %s", phone, user_message)
        response = _client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
            mcp_servers=[
                {
                    "type": "url",
                    "url": CANNES_MCP_URL,
                    "name": "cannes-lions",
                }
            ],
            betas=["mcp-client-2025-04-04"],
        )

        logging.getLogger(__name__).info("Claude API response received, stop_reason=%s", response.stop_reason)
        reply = " ".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        if not reply:
            reply = "Sorry, I couldn't get a response. Please try again."

    except Exception:
        logging.getLogger(__name__).exception("Agent call failed for phone %s", phone)
        reply = "I'm having trouble right now. Please try again in a moment."

    reply = truncate_for_whatsapp(reply)
    _history.add(phone, "assistant", reply)
    return reply
