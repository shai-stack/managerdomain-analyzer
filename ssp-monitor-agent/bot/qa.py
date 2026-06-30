import anthropic

from bot.context import build_daily_context

_FULL_LIST = "full list"
_YESTERDAY = "yesterday"


def answer(question, data, history, api_key):
    """Answer a natural-language question about SSP performance."""
    client = anthropic.Anthropic(api_key=api_key)
    context = build_daily_context(data)

    system_prompt = (
        "You are an SSP performance analyst assistant. "
        "Answer questions clearly and concisely. Use tables when helpful. "
        "Be precise with numbers. "
        "If a question cannot be answered from the data, say so.\n\n"
        + context
    )

    messages = list(history[-10:]) + [{"role": "user", "content": question}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def get_full_list(data):
    """Return formatted full client list for the latest day, ranked by revenue."""
    latest = sorted(data["latest_day"], key=lambda r: r.get("revenue", 0), reverse=True)
    lines = [u"📋 Full Client List — {}\n".format(data["latest_date"])]
    for i, r in enumerate(latest, 1):
        lines.append(
            u"{}. {} ({}) — ${:.2f} | Fill: {:.4f} | RPM: ${:.4f}".format(
                i,
                r.get("seller", ""),
                r.get("ad_type", ""),
                r.get("revenue", 0),
                r.get("fill_rate", 0),
                r.get("rpm", 0),
            )
        )
    return "\n".join(lines)


def is_full_list_request(text):
    return _FULL_LIST in text.lower()


def is_yesterday_request(text):
    return _YESTERDAY in text.lower()
