import logging
import os
import anthropic

from datetime import date
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
    cal_section = ""
    if calendar_summary:
        cal_section = f"\n\nShai's Google Calendar for today:\n{calendar_summary}"
    return (
        "You are a personal assistant for Shai, helping him navigate Cannes Lions 2026. "
        "Shai's role is adtech. He is attending as an adtech professional. "
        "Use the Cannes schedule tools to answer questions about events, panels, and registrations. "
        "Keep all replies concise, plain text, no markdown — WhatsApp renders it poorly. "
        "If listing events, show at most 5 and offer to send more. "
        "When recommending events, check for calendar conflicts and flag them."
        f"{cal_section}"
    )


def truncate_for_whatsapp(text: str) -> str:
    if len(text) <= WHATSAPP_LIMIT:
        return text
    return text[: WHATSAPP_LIMIT - 3] + "..."


def _get_calendar_summary(cal_client: Optional[CalendarClient]) -> Optional[str]:
    if cal_client is None:
        return None
    try:
        today = date.today()
        events = cal_client.get_events_for_day(today)
        if not events:
            return None
        return "\n".join(str(e) for e in events)
    except Exception:
        return None


def run(phone: str, user_message: str, cal_client: Optional[CalendarClient] = None) -> str:
    calendar_summary = _get_calendar_summary(cal_client)
    system_prompt = build_system_prompt(calendar_summary)

    _history.add(phone, "user", user_message)
    messages = _history.get(phone)

    try:
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
