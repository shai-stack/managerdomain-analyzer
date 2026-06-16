# SSP Performance Monitor Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that ingests a daily SSP CSV report via Gmail IMAP, analyzes it with Claude, delivers a morning digest, and answers natural-language Q&A about client performance.

**Architecture:** A persistent Python server on Railway runs two things in parallel: an APScheduler cron job that checks Gmail at 7:05am UTC, parses the CSV, calls Claude to generate a digest, and sends it to Telegram; and a python-telegram-bot instance that handles Q&A throughout the day using Claude with the full 30-day dataset as context.

**Tech Stack:** Python 3.11, python-telegram-bot 20.7, anthropic 0.26.0, pandas 2.2.0, apscheduler 3.10.4, pytest 8.0, Railway (deployment)

---

## File Structure

```
ssp-monitor-agent/
├── bot/
│   ├── __init__.py          # empty, marks package
│   ├── data_store.py        # parse CSV, save/load latest_report.json
│   ├── context.py           # format structured data as Claude prompt context
│   ├── email_watcher.py     # Gmail IMAP connection, CSV extraction
│   ├── digest.py            # call Claude to generate morning digest messages
│   ├── qa.py                # Claude Q&A handler, full-list formatter
│   ├── session.py           # in-memory conversation history per chat_id
│   ├── telegram_bot.py      # Telegram Application, command/message handlers
│   ├── ingest.py            # orchestrates email→parse→digest→send
│   └── main.py              # entry point: starts scheduler + bot
├── tests/
│   ├── __init__.py
│   ├── test_data_store.py
│   ├── test_context.py
│   ├── test_email_watcher.py
│   ├── test_digest.py
│   ├── test_qa.py
│   └── test_session.py
├── requirements.txt
├── pytest.ini
├── Procfile
├── railway.toml
└── .env.example
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `ssp-monitor-agent/requirements.txt`
- Create: `ssp-monitor-agent/pytest.ini`
- Create: `ssp-monitor-agent/.env.example`
- Create: `ssp-monitor-agent/bot/__init__.py`
- Create: `ssp-monitor-agent/tests/__init__.py`

- [ ] **Step 1: Create project directory and package files**

```bash
mkdir -p ssp-monitor-agent/bot ssp-monitor-agent/tests
touch ssp-monitor-agent/bot/__init__.py ssp-monitor-agent/tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
# ssp-monitor-agent/requirements.txt
python-telegram-bot==20.7
anthropic==0.26.0
pandas==2.2.0
apscheduler==3.10.4
pytest==8.0.0
pytest-asyncio==0.23.0
python-dotenv==1.0.0
```

- [ ] **Step 3: Write pytest.ini**

```ini
# ssp-monitor-agent/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4: Write .env.example**

```bash
# ssp-monitor-agent/.env.example
GMAIL_EMAIL=kueez.ssp.report@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-GHI
TELEGRAM_CHAT_ID=123456789
ANTHROPIC_API_KEY=sk-ant-api03-...
```

- [ ] **Step 5: Install dependencies**

```bash
cd ssp-monitor-agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add ssp-monitor-agent/
git commit -m "chore: scaffold ssp-monitor-agent project"
```

---

## Task 2: Data Store

Parses raw CSV content into structured data and persists it to `latest_report.json`.

**Files:**
- Create: `ssp-monitor-agent/bot/data_store.py`
- Create: `ssp-monitor-agent/tests/test_data_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# ssp-monitor-agent/tests/test_data_store.py
import pytest
from pathlib import Path
from bot.data_store import parse_csv, save, load

SAMPLE_CSV = (
    "SSP Adapter Connection Primary Seller,Day,"
    "SSP Adapter Advertiser Type (Internal),SSP Adapter Auctions,"
    "SSP Adapter Auctions (Previous),Diff,SSP Handled Auction Rate,"
    "SSP Adapter Publisher Net Revenue,SSP Adapter Fill Rate %,"
    "SSP Adapter Publisher Share (Gross),SSP Adapter - Gross RPM\n"
    'Yahoo,2026-06-16,web_display,"81,266,000","106,053,000","-24,787,000",'
    '76.77%,$512.23,0.75%,95.00%,$0.0075\n'
    'Publift,2026-06-16,web_display,"22,278,000","19,824,000","2,454,000",'
    '89.38%,$133.67,1.19%,82.27%,$0.0080\n'
    'Yahoo,2026-06-15,web_display,"90,000,000","85,000,000","5,000,000",'
    '80.00%,$480.00,0.80%,95.00%,$0.0070\n'
)


def test_parse_csv_latest_date():
    result = parse_csv(SAMPLE_CSV)
    assert result["latest_date"] == "2026-06-16"


def test_parse_csv_latest_day_has_two_rows():
    result = parse_csv(SAMPLE_CSV)
    assert len(result["latest_day"]) == 2


def test_parse_csv_revenue_is_float():
    result = parse_csv(SAMPLE_CSV)
    yahoo = next(r for r in result["latest_day"] if r["seller"] == "Yahoo")
    assert yahoo["revenue"] == pytest.approx(512.23)


def test_parse_csv_auctions_are_int():
    result = parse_csv(SAMPLE_CSV)
    yahoo = next(r for r in result["latest_day"] if r["seller"] == "Yahoo")
    assert yahoo["auctions"] == 81266000


def test_parse_csv_thirty_day_summary_keys():
    result = parse_csv(SAMPLE_CSV)
    assert "Yahoo|web_display" in result["thirty_day_summary"]


def test_parse_csv_thirty_day_total_revenue():
    result = parse_csv(SAMPLE_CSV)
    total = result["thirty_day_summary"]["Yahoo|web_display"]["total_revenue"]
    assert total == pytest.approx(992.23)


def test_save_and_load(tmp_path, monkeypatch):
    import bot.data_store as ds
    monkeypatch.setattr(ds, "DATA_FILE", tmp_path / "report.json")
    data = {"latest_date": "2026-06-16", "latest_day": [], "thirty_day_summary": {}}
    save(data)
    loaded = load()
    assert loaded["latest_date"] == "2026-06-16"


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    import bot.data_store as ds
    monkeypatch.setattr(ds, "DATA_FILE", tmp_path / "missing.json")
    assert load() is None
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd ssp-monitor-agent
pytest tests/test_data_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.data_store'`

- [ ] **Step 3: Write data_store.py**

```python
# ssp-monitor-agent/bot/data_store.py
import io
import json
from pathlib import Path

import pandas as pd

DATA_FILE = Path("latest_report.json")

_COL_MAP = {
    "SSP Adapter Connection Primary Seller": "seller",
    "Day": "date",
    "SSP Adapter Advertiser Type (Internal)": "ad_type",
    "SSP Adapter Auctions": "auctions",
    "SSP Adapter Auctions (Previous)": "auctions_prev",
    "Diff": "auctions_diff",
    "SSP Handled Auction Rate": "auction_rate",
    "SSP Adapter Publisher Net Revenue": "revenue",
    "SSP Adapter Fill Rate %": "fill_rate",
    "SSP Adapter Publisher Share (Gross)": "pub_share",
    "SSP Adapter - Gross RPM": "rpm",
}


def parse_csv(csv_content: str) -> dict:
    df = pd.read_csv(io.StringIO(csv_content))
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in _COL_MAP.items() if k in df.columns})

    for col in ("revenue", "fill_rate", "pub_share", "rpm", "auction_rate"):
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.replace(r"[$%,]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ("auctions", "auctions_prev", "auctions_diff"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "")
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].copy()

    summary: dict = {}
    for (seller, ad_type), group in df.groupby(["seller", "ad_type"]):
        key = f"{seller}|{ad_type}"
        revenue_by_date = group.set_index("date")["revenue"].to_dict()
        summary[key] = {
            "seller": seller,
            "ad_type": ad_type,
            "total_revenue": round(float(group["revenue"].sum()), 2),
            "avg_fill_rate": round(float(group["fill_rate"].mean()), 4),
            "avg_rpm": round(float(group["rpm"].mean()), 4),
            "revenue_by_date": {str(k): round(float(v), 2) for k, v in revenue_by_date.items()},
        }

    return {
        "latest_date": latest_date,
        "latest_day": latest.to_dict(orient="records"),
        "thirty_day_summary": summary,
    }


def save(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, default=str))


def load() -> dict | None:
    if not DATA_FILE.exists():
        return None
    return json.loads(DATA_FILE.read_text())
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_data_store.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add bot/data_store.py tests/test_data_store.py
git commit -m "feat: add data_store — CSV parsing and JSON persistence"
```

---

## Task 3: Context Builder

Formats the structured data into a compact text block for Claude prompts.

**Files:**
- Create: `ssp-monitor-agent/bot/context.py`
- Create: `ssp-monitor-agent/tests/test_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# ssp-monitor-agent/tests/test_context.py
from bot.context import build_daily_context

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        },
        {
            "seller": "Publift", "ad_type": "web_display", "revenue": 133.67,
            "fill_rate": 0.0119, "rpm": 0.0080, "auction_rate": 0.8938,
            "auctions": 22278000, "auctions_prev": 19824000, "auctions_diff": 2454000,
        },
    ],
    "thirty_day_summary": {
        "Yahoo|web_display": {
            "seller": "Yahoo", "ad_type": "web_display",
            "total_revenue": 14500.23, "avg_fill_rate": 0.0075, "avg_rpm": 0.0075,
            "revenue_by_date": {"2026-06-16": 512.23, "2026-06-15": 480.00},
        },
    },
}


def test_contains_latest_date():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "2026-06-16" in ctx


def test_contains_seller_name():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "Yahoo" in ctx


def test_contains_revenue():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "512.23" in ctx


def test_yahoo_before_publift_in_today_section():
    ctx = build_daily_context(SAMPLE_DATA)
    today_section = ctx.split("30-Day Summary")[0]
    assert today_section.index("Yahoo") < today_section.index("Publift")


def test_contains_thirty_day_total():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "14500.23" in ctx


def test_contains_daily_revenue_trend():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "2026-06-15" in ctx
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_context.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.context'`

- [ ] **Step 3: Write context.py**

```python
# ssp-monitor-agent/bot/context.py


def build_daily_context(data: dict) -> str:
    latest_date = data["latest_date"]
    latest_day = sorted(data["latest_day"], key=lambda r: r.get("revenue", 0), reverse=True)
    summary = data["thirty_day_summary"]

    lines = [f"# SSP Performance Data — Latest: {latest_date}\n"]

    lines.append("## Today's Performance (ranked by revenue)")
    lines.append(
        "Seller | Ad Type | Revenue | Fill Rate | RPM | Auction Rate | "
        "Auctions | Auctions Prev | Diff"
    )
    for r in latest_day:
        lines.append(
            f"{r.get('seller', '')} | {r.get('ad_type', '')} | "
            f"${r.get('revenue', 0):.2f} | {r.get('fill_rate', 0):.4f} | "
            f"${r.get('rpm', 0):.4f} | {r.get('auction_rate', 0):.4f} | "
            f"{r.get('auctions', 0):,} | {r.get('auctions_prev', 0):,} | "
            f"{r.get('auctions_diff', 0):,}"
        )

    lines.append("\n## 30-Day Summary (per seller/ad_type)")
    lines.append("Seller | Ad Type | 30d Total Revenue | Avg Fill Rate | Avg RPM")
    for key, s in sorted(summary.items(), key=lambda x: x[1]["total_revenue"], reverse=True):
        lines.append(
            f"{s['seller']} | {s['ad_type']} | ${s['total_revenue']:.2f} | "
            f"{s['avg_fill_rate']:.4f} | ${s['avg_rpm']:.4f}"
        )

    lines.append("\n## Daily Revenue Trends (top 30 sellers, last 30 days)")
    top30 = sorted(summary.items(), key=lambda x: x[1]["total_revenue"], reverse=True)[:30]
    for _, s in top30:
        dates = ", ".join(
            f"{d}: ${v}" for d, v in sorted(s["revenue_by_date"].items())
        )
        lines.append(f"{s['seller']} ({s['ad_type']}): {dates}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_context.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add bot/context.py tests/test_context.py
git commit -m "feat: add context builder for Claude prompts"
```

---

## Task 4: Email Watcher

Connects to Gmail via IMAP, finds the latest report email, and returns the CSV content.

**Files:**
- Create: `ssp-monitor-agent/bot/email_watcher.py`
- Create: `ssp-monitor-agent/tests/test_email_watcher.py`

- [ ] **Step 1: Write the failing tests**

```python
# ssp-monitor-agent/tests/test_email_watcher.py
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

from bot.email_watcher import fetch_latest_csv


def _make_email_bytes(csv_content: str) -> bytes:
    msg = MIMEMultipart()
    msg["From"] = "airflow@kueez.com"
    msg["Subject"] = "[BEUI Alert]: SSP Last 30 days - New 2026"
    part = MIMEBase("text", "csv")
    part.set_payload(csv_content.encode())
    part.add_header("Content-Disposition", "attachment", filename="report.csv")
    msg.attach(part)
    return msg.as_bytes()


def _mock_imap(raw_email_bytes: bytes, has_unseen: bool = True):
    mock_mail = MagicMock()
    mock_mail.login.return_value = ("OK", [])
    mock_mail.select.return_value = ("OK", [])
    if has_unseen:
        mock_mail.search.return_value = ("OK", [b"1"])
    else:
        mock_mail.search.return_value = ("OK", [b""])
    mock_mail.fetch.return_value = ("OK", [(b"1 (RFC822 {100})", raw_email_bytes)])
    mock_mail.store.return_value = ("OK", [])

    mock_class = MagicMock()
    mock_class.return_value.__enter__ = MagicMock(return_value=mock_mail)
    mock_class.return_value.__exit__ = MagicMock(return_value=False)
    return mock_class, mock_mail


def test_fetch_returns_csv_content():
    raw = _make_email_bytes("col1,col2\nval1,val2")
    mock_class, _ = _mock_imap(raw)
    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        result = fetch_latest_csv("test@gmail.com", "apppass")
    assert "col1,col2" in result


def test_fetch_marks_email_as_read():
    raw = _make_email_bytes("a,b\n1,2")
    mock_class, mock_mail = _mock_imap(raw)
    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        fetch_latest_csv("test@gmail.com", "apppass")
    mock_mail.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


def test_fetch_returns_none_when_no_email():
    mock_mail = MagicMock()
    mock_mail.login.return_value = ("OK", [])
    mock_mail.select.return_value = ("OK", [])
    mock_mail.search.return_value = ("OK", [b""])

    mock_class = MagicMock()
    mock_class.return_value.__enter__ = MagicMock(return_value=mock_mail)
    mock_class.return_value.__exit__ = MagicMock(return_value=False)

    with patch("bot.email_watcher.imaplib.IMAP4_SSL", mock_class):
        result = fetch_latest_csv("test@gmail.com", "apppass")
    assert result is None
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_email_watcher.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.email_watcher'`

- [ ] **Step 3: Write email_watcher.py**

```python
# ssp-monitor-agent/bot/email_watcher.py
import email
import imaplib

_IMAP_HOST = "imap.gmail.com"
_SENDER = "airflow@kueez.com"


def fetch_latest_csv(gmail_email: str, app_password: str) -> str | None:
    """Return CSV string from the latest SSP report email, or None if not found."""
    with imaplib.IMAP4_SSL(_IMAP_HOST) as mail:
        mail.login(gmail_email, app_password)
        mail.select("INBOX")

        # Try unseen first, fall back to most recent from sender
        _, msg_ids = mail.search(None, f'FROM "{_SENDER}" UNSEEN')
        ids = msg_ids[0].split()

        if not ids:
            _, msg_ids = mail.search(None, f'FROM "{_SENDER}"')
            ids = msg_ids[0].split()
            if not ids:
                return None
            ids = [ids[-1]]

        _, msg_data = mail.fetch(ids[-1], "(RFC822)")
        raw = msg_data[0][1]
        mail.store(ids[-1], "+FLAGS", "\\Seen")

        msg = email.message_from_bytes(raw)
        for part in msg.walk():
            if part.get_content_type() == "text/csv" or (
                part.get_content_disposition() == "attachment"
                and (part.get_filename() or "").endswith(".csv")
            ):
                payload = part.get_payload(decode=True)
                return payload.decode("utf-8", errors="replace")

    return None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_email_watcher.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add bot/email_watcher.py tests/test_email_watcher.py
git commit -m "feat: add Gmail IMAP email watcher"
```

---

## Task 5: Digest Generator

Calls Claude to generate the 3-part morning digest and splits it into Telegram-sized messages.

**Files:**
- Create: `ssp-monitor-agent/bot/digest.py`
- Create: `ssp-monitor-agent/tests/test_digest.py`

- [ ] **Step 1: Write the failing tests**

```python
# ssp-monitor-agent/tests/test_digest.py
from unittest.mock import MagicMock, patch

from bot.digest import generate_digest, split_for_telegram

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        }
    ],
    "thirty_day_summary": {
        "Yahoo|web_display": {
            "seller": "Yahoo", "ad_type": "web_display",
            "total_revenue": 14500.23, "avg_fill_rate": 0.0075, "avg_rpm": 0.0075,
            "revenue_by_date": {"2026-06-16": 512.23},
        }
    },
}


def _mock_claude(text: str):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=text)]
    )
    return mock_client


def test_generate_digest_returns_list():
    mock_client = _mock_claude("Part1\n---SPLIT---\nPart2\n---SPLIT---\nPart3")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        result = generate_digest(SAMPLE_DATA, "fake-key")
    assert isinstance(result, list)
    assert len(result) == 3


def test_generate_digest_all_under_4096():
    mock_client = _mock_claude("Part1\n---SPLIT---\nPart2\n---SPLIT---\nPart3")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        result = generate_digest(SAMPLE_DATA, "fake-key")
    assert all(len(m) <= 4096 for m in result)


def test_split_for_telegram_short_message():
    assert split_for_telegram("hello") == ["hello"]


def test_split_for_telegram_long_message():
    long = "x\n" * 3000  # 6000 chars
    parts = split_for_telegram(long)
    assert len(parts) > 1
    assert all(len(p) <= 4096 for p in parts)


def test_generate_digest_calls_claude():
    mock_client = _mock_claude("a\n---SPLIT---\nb\n---SPLIT---\nc")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        generate_digest(SAMPLE_DATA, "fake-key")
    mock_client.messages.create.assert_called_once()
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_digest.py -v
```

Expected: `ModuleNotFoundError: No module named 'bot.digest'`

- [ ] **Step 3: Write digest.py**

```python
# ssp-monitor-agent/bot/digest.py
import anthropic

from bot.context import build_daily_context


def split_for_telegram(text: str) -> list[str]:
    """Split text into chunks of ≤4096 chars, breaking at newlines."""
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


def generate_digest(data: dict, api_key: str) -> list[str]:
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
Use ⬇ for drops, ⬆ for unexpected spikes (auctions > 2× auctions_prev).
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

    messages: list[str] = []
    for part in parts:
        messages.extend(split_for_telegram(part))
    return messages
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_digest.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add bot/digest.py tests/test_digest.py
git commit -m "feat: add Claude digest generator"
```

---

## Task 6: Session Store + Q&A Handler

**Files:**
- Create: `ssp-monitor-agent/bot/session.py`
- Create: `ssp-monitor-agent/bot/qa.py`
- Create: `ssp-monitor-agent/tests/test_session.py`
- Create: `ssp-monitor-agent/tests/test_qa.py`

- [ ] **Step 1: Write the failing tests**

```python
# ssp-monitor-agent/tests/test_session.py
from bot.session import append, clear, clear_all, get_history


def test_empty_history():
    assert get_history(999) == []


def test_append_and_get():
    append(1, "user", "hello")
    append(1, "assistant", "hi")
    h = get_history(1)
    assert len(h) == 2
    assert h[0] == {"role": "user", "content": "hello"}


def test_clear_single():
    append(2, "user", "q")
    clear(2)
    assert get_history(2) == []


def test_clear_all():
    append(10, "user", "a")
    append(11, "user", "b")
    clear_all()
    assert get_history(10) == []
    assert get_history(11) == []
```

```python
# ssp-monitor-agent/tests/test_qa.py
from unittest.mock import MagicMock, patch

from bot.qa import answer, get_full_list, is_full_list_request, is_yesterday_request

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        },
        {
            "seller": "Publift", "ad_type": "web_display", "revenue": 133.67,
            "fill_rate": 0.0119, "rpm": 0.0080, "auction_rate": 0.8938,
            "auctions": 22278000, "auctions_prev": 19824000, "auctions_diff": 2454000,
        },
    ],
    "thirty_day_summary": {},
}


def _mock_claude(text: str):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=text)]
    )
    return mock_client


def test_answer_returns_claude_text():
    with patch("bot.qa.anthropic.Anthropic", return_value=_mock_claude("Yahoo is up.")):
        result = answer("How is Yahoo?", SAMPLE_DATA, [], "fake-key")
    assert result == "Yahoo is up."


def test_answer_passes_history():
    mock_client = _mock_claude("ok")
    history = [
        {"role": "user", "content": "prev"},
        {"role": "assistant", "content": "resp"},
    ]
    with patch("bot.qa.anthropic.Anthropic", return_value=mock_client):
        answer("follow up", SAMPLE_DATA, history, "fake-key")
    call_msgs = mock_client.messages.create.call_args[1]["messages"]
    assert any(m["content"] == "prev" for m in call_msgs)


def test_get_full_list_yahoo_first():
    result = get_full_list(SAMPLE_DATA)
    assert result.index("Yahoo") < result.index("Publift")


def test_get_full_list_contains_revenue():
    result = get_full_list(SAMPLE_DATA)
    assert "512.23" in result


def test_is_full_list_request_true():
    assert is_full_list_request("show full list please") is True


def test_is_full_list_request_false():
    assert is_full_list_request("how is yahoo") is False


def test_is_yesterday_request_true():
    assert is_yesterday_request("show me yesterday") is True


def test_is_yesterday_request_false():
    assert is_yesterday_request("today's data") is False
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_session.py tests/test_qa.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write session.py**

```python
# ssp-monitor-agent/bot/session.py
_histories: dict[int, list[dict]] = {}


def get_history(chat_id: int) -> list[dict]:
    return list(_histories.get(chat_id, []))


def append(chat_id: int, role: str, content: str) -> None:
    _histories.setdefault(chat_id, []).append({"role": role, "content": content})


def clear(chat_id: int) -> None:
    _histories[chat_id] = []


def clear_all() -> None:
    _histories.clear()
```

- [ ] **Step 4: Write qa.py**

```python
# ssp-monitor-agent/bot/qa.py
import anthropic

from bot.context import build_daily_context

_FULL_LIST = "full list"
_YESTERDAY = "yesterday"


def answer(question: str, data: dict, history: list[dict], api_key: str) -> str:
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


def get_full_list(data: dict) -> str:
    """Return formatted full client list for the latest day, ranked by revenue."""
    latest = sorted(data["latest_day"], key=lambda r: r.get("revenue", 0), reverse=True)
    lines = [f"📋 Full Client List — {data['latest_date']}\n"]
    for i, r in enumerate(latest, 1):
        lines.append(
            f"{i}. {r.get('seller', '')} ({r.get('ad_type', '')}) — "
            f"${r.get('revenue', 0):.2f} | Fill: {r.get('fill_rate', 0):.4f} | "
            f"RPM: ${r.get('rpm', 0):.4f}"
        )
    return "\n".join(lines)


def is_full_list_request(text: str) -> bool:
    return _FULL_LIST in text.lower()


def is_yesterday_request(text: str) -> bool:
    return _YESTERDAY in text.lower()
```

- [ ] **Step 5: Run tests — expect pass**

```bash
pytest tests/test_session.py tests/test_qa.py -v
```

Expected: 11 passed.

- [ ] **Step 6: Commit**

```bash
git add bot/session.py bot/qa.py tests/test_session.py tests/test_qa.py
git commit -m "feat: add session store and Q&A handler"
```

---

## Task 7: Ingest Orchestrator

Ties email watcher → data store → digest → Telegram send into one callable coroutine.

**Files:**
- Create: `ssp-monitor-agent/bot/ingest.py`

- [ ] **Step 1: Write ingest.py**

No unit tests for this module — it is pure orchestration of already-tested units. Integration is verified in Task 9.

```python
# ssp-monitor-agent/bot/ingest.py
import logging
import os

from telegram import Bot

from bot import data_store, digest, email_watcher, session

logger = logging.getLogger(__name__)


async def run_ingest() -> bool:
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
```

- [ ] **Step 2: Commit**

```bash
git add bot/ingest.py
git commit -m "feat: add ingest orchestrator"
```

---

## Task 8: Telegram Bot

Handles /start, /status, /refresh commands and routes free-text messages to Q&A.

**Files:**
- Create: `ssp-monitor-agent/bot/telegram_bot.py`

- [ ] **Step 1: Write telegram_bot.py**

No unit tests for Telegram handlers (the library's async context makes mocking expensive). Tested end-to-end in Task 9.

```python
# ssp-monitor-agent/bot/telegram_bot.py
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
        "👋 SSP Monitor active. Ask me anything about your client performance.\n\n"
        "Commands:\n"
        "/status — show loaded report date\n"
        "/refresh — manually re-check Gmail\n\n"
        "Say 'full list' for all clients, 'yesterday' for previous day data."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = data_store.load()
    if data:
        await update.message.reply_text(f"✅ Latest report: {data['latest_date']}")
    else:
        await update.message.reply_text("⚠️ No report loaded. Try /refresh.")


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🔄 Checking Gmail for latest report...")
    from bot.ingest import run_ingest
    success = await run_ingest()
    if success:
        data = data_store.load()
        await update.message.reply_text(f"✅ Report refreshed: {data['latest_date']}")
    else:
        await update.message.reply_text("❌ No new report found in inbox.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    api_key = os.environ["ANTHROPIC_API_KEY"]

    data = data_store.load()
    if not data:
        await update.message.reply_text("⚠️ No report data yet. Try /refresh.")
        return

    if qa.is_full_list_request(text):
        full = qa.get_full_list(data)
        for i in range(0, len(full), 4096):
            await update.message.reply_text(full[i : i + 4096])
        return

    await update.effective_chat.send_action("typing")
    history = session.get_history(chat_id)
    response = qa.answer(text, data, history, api_key)
    session.append(chat_id, "user", text)
    session.append(chat_id, "assistant", response)

    for i in range(0, len(response), 4096):
        await update.message.reply_text(response[i : i + 4096])


def build_app(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("refresh", cmd_refresh))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
```

- [ ] **Step 2: Commit**

```bash
git add bot/telegram_bot.py
git commit -m "feat: add Telegram bot handlers"
```

---

## Task 9: Main Entry Point + Scheduler

**Files:**
- Create: `ssp-monitor-agent/bot/main.py`

- [ ] **Step 1: Write main.py**

```python
# ssp-monitor-agent/bot/main.py
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
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _scheduled_ingest() -> None:
    success = await run_ingest()
    if not success:
        logger.warning("Report not found at 07:05 UTC. Retrying in 30 min...")
        await asyncio.sleep(1800)
        await run_ingest()


async def _run() -> None:
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


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests to confirm everything still passes**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Smoke test locally**

Copy `.env.example` to `.env`, fill in real values, then:

```bash
python -m bot.main
```

Expected:
- `Scheduler started. Daily ingest at 07:05 UTC.`
- `Telegram bot polling started.`

Send `/start` to your bot in Telegram. Expected reply: the welcome message.
Send `/status` — should say "No report loaded" if no email has arrived yet.
Send `/refresh` — should attempt Gmail fetch.

- [ ] **Step 4: Commit**

```bash
git add bot/main.py
git commit -m "feat: add main entry point with APScheduler"
```

---

## Task 10: Railway Deployment

**Files:**
- Create: `ssp-monitor-agent/Procfile`
- Create: `ssp-monitor-agent/railway.toml`
- Modify: `ssp-monitor-agent/requirements.txt` (already done)

- [ ] **Step 1: Write Procfile**

```
worker: python -m bot.main
```

- [ ] **Step 2: Write railway.toml**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python -m bot.main"
restartPolicyType = "always"
```

- [ ] **Step 3: Deploy to Railway**

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# From ssp-monitor-agent/ directory
railway login
railway init          # creates new project named ssp-monitor-agent
railway up            # deploys
```

- [ ] **Step 4: Set environment variables in Railway dashboard**

Go to Railway dashboard → your project → Variables tab. Add:

```
GMAIL_EMAIL=kueez.ssp.report@gmail.com
GMAIL_APP_PASSWORD=<16-char app password from Google Account settings>
TELEGRAM_BOT_TOKEN=<from @BotFather>
TELEGRAM_CHAT_ID=<your chat ID — send /start to @userinfobot to get it>
ANTHROPIC_API_KEY=<from console.anthropic.com>
```

- [ ] **Step 5: Verify deployment**

In Railway dashboard → Deployments → click your deploy → view logs.

Expected:
```
Scheduler started. Daily ingest at 07:05 UTC.
Telegram bot polling started.
```

Send `/status` to your Telegram bot. Expected: "No report loaded. Try /refresh."
Send `/refresh`. Expected: either a fetched report or "No new report found in inbox."

- [ ] **Step 6: Final commit**

```bash
git add Procfile railway.toml
git commit -m "chore: add Railway deployment config"
```

---

## Pre-launch Checklist

Before the first automated digest:

- [ ] Gmail account `kueez.ssp.report@gmail.com` created
- [ ] Gmail App Password generated (Google Account → Security → 2-Step Verification → App passwords)
- [ ] Airflow team has added `kueez.ssp.report@gmail.com` as a recipient on the daily report
- [ ] Telegram bot created via @BotFather, token saved
- [ ] Your Telegram chat ID confirmed (use @userinfobot)
- [ ] All 5 env vars set in Railway
- [ ] `/refresh` tested manually with a forwarded copy of the report email
