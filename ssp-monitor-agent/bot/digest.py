import anthropic

from bot.context import build_daily_context


def split_for_telegram(text):
    """Split text into chunks of <=4096 chars, breaking at newlines."""
    if len(text) <= 4096:
        return [text]
    parts = []
    while len(text) > 4096:
        split_at = text.rfind("\n", 0, 4096)
        if split_at == -1:
            split_at = 4096
        parts.append(text[:split_at])
        text = text[split_at:].strip()
    if text:
        parts.append(text)
    return parts


def generate_digest(data, api_key):
    """Call Claude to produce a 3-part morning digest. Returns list of Telegram messages."""
    client = anthropic.Anthropic(api_key=api_key)
    context = build_daily_context(data)
    latest_date = data["latest_date"]

    prompt = f"""You are an SSP performance analyst. Based on the data below, produce a morning digest with exactly 3 parts separated by the literal string ---SPLIT--- (on its own line).

{context}

PART 1 — SUMMARY (use these emojis exactly):
📊 SSP Daily Report — {latest_date}

💰 SUMMARY
Total Revenue: $[sum all revenue for {latest_date}]
Top Earner: [highest revenue seller] — $[amount]
Active Clients: [count unique sellers] | Ad Types: [list unique ad_types]

---SPLIT---

PART 2 — ANOMALIES:
🚨 ANOMALIES
Flag clients where auction_rate < 0.50, or auctions_diff is a large negative (>25% drop).
Use ⬇ for drops, ⬆ for unexpected spikes (auctions > 2x auctions_prev).
One line per anomaly: [emoji] [Seller] — [reason with numbers]
If none qualify, write: ✅ No major anomalies today.

---SPLIT---

PART 3 — TOP 20:
📋 TOP 20 BY REVENUE
[rank]. [Seller] ([ad_type]) — $[revenue] | Fill: [fill_rate] | RPM: $[rpm]
(list top 20 sellers for {latest_date}, ranked by revenue)

[type "full list" for all clients]

Keep each part under 1500 characters. Be precise with the numbers from the data."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    parts = [p.strip() for p in raw.split("---SPLIT---") if p.strip()]

    messages = []
    for part in parts:
        messages.extend(split_for_telegram(part))
    return messages
