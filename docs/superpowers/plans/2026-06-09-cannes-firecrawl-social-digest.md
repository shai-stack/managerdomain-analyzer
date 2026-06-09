# Cannes Social Buzz Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Firecrawl-powered LinkedIn/X trending search and a scheduled daily digest to the existing Cannes Lions Telegram bot.

**Architecture:** A new `firecrawl.py` module calls Firecrawl's REST API to search for trending Cannes Lions content on LinkedIn and X. A new `scheduler.py` sets up APScheduler to fire 9 times per day (CST), generate a digest via Claude, and push it to Telegram. `agent.py` detects trending-intent keywords and injects Firecrawl results into the Claude context before responding.

**Tech Stack:** Python 3.12, APScheduler 3.10.4, requests 2.32.3, Firecrawl REST API (`/v1/search`), python-telegram-bot 21.5, existing Anthropic + FastAPI stack.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `cannes-agent/firecrawl.py` | Firecrawl REST API calls, returns text block |
| Create | `cannes-agent/scheduler.py` | APScheduler setup, digest trigger, Telegram push |
| Modify | `cannes-agent/agent.py` | Keyword detection, inject Firecrawl results into system prompt |
| Modify | `cannes-agent/main.py` | Start/stop scheduler in FastAPI lifespan events |
| Modify | `cannes-agent/requirements.txt` | Add apscheduler, requests |
| Create | `cannes-agent/tests/test_firecrawl.py` | Unit tests for firecrawl module |
| Create | `cannes-agent/tests/test_scheduler.py` | Unit tests for scheduler module |
| Create | `cannes-agent/tests/test_agent_trending.py` | Unit tests for keyword detection + prompt injection |

---

### Task 1: Firecrawl Module

**Files:**
- Create: `cannes-agent/firecrawl.py`
- Create: `cannes-agent/tests/test_firecrawl.py`
- Modify: `cannes-agent/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Open `cannes-agent/requirements.txt` and add:
```
apscheduler==3.10.4
requests==2.32.3
```

- [ ] **Step 2: Write the failing tests**

Create `cannes-agent/tests/test_firecrawl.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import firecrawl


def _make_response(items):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"data": items}
    return mock


def test_get_trending_content_combines_results():
    linkedin_item = {"title": "LinkedIn post", "description": "Big news at Cannes", "url": "https://linkedin.com/a"}
    twitter_item = {"title": "X post", "description": "Trending at Cannes", "url": "https://x.com/b"}

    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = [
            _make_response([linkedin_item]),
            _make_response([twitter_item]),
        ]
        result = firecrawl.get_trending_content("fake-key")

    assert "LinkedIn post" in result
    assert "X post" in result


def test_get_trending_content_one_source_fails():
    twitter_item = {"title": "X post", "description": "Trending at Cannes", "url": "https://x.com/b"}

    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = [
            Exception("network error"),
            _make_response([twitter_item]),
        ]
        result = firecrawl.get_trending_content("fake-key")

    assert "X post" in result


def test_get_trending_content_both_fail():
    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = Exception("network error")
        result = firecrawl.get_trending_content("fake-key")

    assert result == ""


def test_get_trending_content_empty_data():
    with patch("firecrawl.requests.post") as mock_post:
        mock_post.return_value = _make_response([])
        result = firecrawl.get_trending_content("fake-key")

    assert result == ""
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd cannes-agent && python -m pytest tests/test_firecrawl.py -v
```
Expected: `ModuleNotFoundError: No module named 'firecrawl'`

- [ ] **Step 4: Create `cannes-agent/firecrawl.py`**

```python
import logging
import os

import requests

log = logging.getLogger(__name__)

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/search"
SEARCHES = [
    "Cannes Lions 2026 site:linkedin.com",
    "Cannes Lions 2026 site:twitter.com OR site:x.com",
]


def _search(query: str, api_key: str, limit: int = 5) -> list[dict]:
    """Run a single Firecrawl search. Returns list of result dicts."""
    response = requests.post(
        FIRECRAWL_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "limit": limit},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def _format_results(results: list[dict]) -> str:
    """Convert a list of Firecrawl result dicts into readable text."""
    lines = []
    for item in results:
        title = item.get("title", "").strip()
        description = item.get("description", "").strip()
        url = item.get("url", "").strip()
        if title or description:
            lines.append(f"- {title}: {description} ({url})")
    return "\n".join(lines)


def get_trending_content(api_key: str | None = None) -> str:
    """
    Search LinkedIn and X/Twitter for trending Cannes Lions 2026 content.
    Returns a plain-text block of results, or empty string if both searches fail.
    """
    if api_key is None:
        api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        log.warning("FIRECRAWL_API_KEY not set — skipping trending search")
        return ""

    blocks = []
    labels = ["LinkedIn", "X/Twitter"]
    for label, query in zip(labels, SEARCHES):
        try:
            results = _search(query, api_key)
            text = _format_results(results)
            if text:
                blocks.append(f"{label}:\n{text}")
        except Exception:
            log.warning("Firecrawl search failed for %s", label, exc_info=True)

    return "\n\n".join(blocks)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd cannes-agent && python -m pytest tests/test_firecrawl.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 6: Commit**

```bash
cd cannes-agent && git add firecrawl.py tests/test_firecrawl.py requirements.txt
git commit -m "feat: add firecrawl module for trending Cannes Lions search"
```

---

### Task 2: Scheduler Module

**Files:**
- Create: `cannes-agent/scheduler.py`
- Create: `cannes-agent/tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

Create `cannes-agent/tests/test_scheduler.py`:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import scheduler


def test_build_jobs_returns_nine_triggers():
    """Should return exactly 9 cron triggers for the daily schedule."""
    jobs = scheduler._build_cron_times()
    assert len(jobs) == 9


def test_build_jobs_includes_7am():
    jobs = scheduler._build_cron_times()
    assert (7, 0) in jobs


def test_build_jobs_includes_10pm():
    jobs = scheduler._build_cron_times()
    assert (22, 0) in jobs


def test_build_jobs_even_hours_8am_to_10pm():
    jobs = scheduler._build_cron_times()
    for hour in range(8, 23, 2):
        assert (hour, 0) in jobs


def test_format_digest_prompt_contains_results():
    content = "LinkedIn:\n- Big news at Cannes"
    prompt = scheduler._format_digest_prompt(content)
    assert "Big news at Cannes" in prompt
    assert "5 bullets" in prompt or "five" in prompt.lower() or "bullet" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd cannes-agent && python -m pytest tests/test_scheduler.py -v
```
Expected: `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: Create `cannes-agent/scheduler.py`**

```python
import logging
import os

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

    try:
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(bot.send_message(chat_id=chat_id, text=digest))
        loop.close()
    except Exception:
        log.exception("Failed to send digest to Telegram")


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

    _scheduler.start()
    log.info("Digest scheduler started with %d jobs", len(_build_cron_times()))


def stop_scheduler() -> None:
    """Stop APScheduler. Called from FastAPI shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Digest scheduler stopped")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd cannes-agent && python -m pytest tests/test_scheduler.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add cannes-agent/scheduler.py cannes-agent/tests/test_scheduler.py
git commit -m "feat: add APScheduler digest module for Cannes social buzz"
```

---

### Task 3: Keyword Detection and Prompt Injection in agent.py

**Files:**
- Modify: `cannes-agent/agent.py`
- Create: `cannes-agent/tests/test_agent_trending.py`

- [ ] **Step 1: Write failing tests**

Create `cannes-agent/tests/test_agent_trending.py`:

```python
import pytest
import agent


@pytest.mark.parametrize("msg", [
    "what's trending at Cannes?",
    "what's the buzz today?",
    "what are people saying about Cannes?",
    "any LinkedIn posts about Cannes?",
    "what's happening on twitter?",
    "what's people talking about",
    "show me social updates",
])
def test_is_trending_query_detects_keywords(msg):
    assert agent._is_trending_query(msg) is True


@pytest.mark.parametrize("msg", [
    "what sessions are on today?",
    "do I have any meetings tomorrow?",
    "recommend events for adtech",
    "what time does the morning keynote start?",
])
def test_is_trending_query_ignores_non_trending(msg):
    assert agent._is_trending_query(msg) is False


def test_inject_trending_appends_to_system_prompt():
    base = "You are a Cannes assistant."
    content = "LinkedIn:\n- Big news"
    result = agent._inject_trending(base, content)
    assert "Big news" in result
    assert base in result


def test_inject_trending_skips_empty_content():
    base = "You are a Cannes assistant."
    result = agent._inject_trending(base, "")
    assert result == base
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd cannes-agent && python -m pytest tests/test_agent_trending.py -v
```
Expected: `ImportError` — `_is_trending_query` and `_inject_trending` don't exist yet

- [ ] **Step 3: Add keyword detection and injection helpers to `agent.py`**

Add these two functions to `cannes-agent/agent.py` after the `build_system_prompt` function:

```python
_TRENDING_KEYWORDS = [
    "trending", "buzz", "what's people saying", "what are people",
    "social", "linkedin", "twitter", "x.com", "what's happening",
    "talk about", "talking about", "people saying",
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
```

- [ ] **Step 4: Update the `run()` function in `agent.py` to use the new helpers**

Find the `run()` function and update it to call Firecrawl when a trending query is detected. Replace the existing `run()` function with:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd cannes-agent && python -m pytest tests/test_agent_trending.py -v
```
Expected: all 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add cannes-agent/agent.py cannes-agent/tests/test_agent_trending.py
git commit -m "feat: detect trending queries and inject Firecrawl results into agent context"
```

---

### Task 4: Wire Scheduler into FastAPI and Set Env Vars

**Files:**
- Modify: `cannes-agent/main.py`

- [ ] **Step 1: Update `main.py` to import and start/stop the scheduler**

Replace the `startup` and `shutdown` event handlers in `cannes-agent/main.py` with:

```python
import scheduler as digest_scheduler

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

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
        anthropic_client=agent._client,
        model=agent.MODEL,
    )


@app.on_event("shutdown")
async def shutdown():
    digest_scheduler.stop_scheduler()
    await _telegram_app.shutdown()
```

Also add the import at the top of the file alongside the other imports:
```python
import scheduler as digest_scheduler
```

- [ ] **Step 2: Install new dependencies locally to verify**

```bash
cd cannes-agent && pip install apscheduler==3.10.4 requests==2.32.3
```
Expected: installs without errors

- [ ] **Step 3: Get your Telegram chat ID**

Message `@userinfobot` on Telegram. It will reply with your user ID (a number like `123456789`). Copy it.

- [ ] **Step 4: Set Railway environment variables**

```bash
railway variables --set "FIRECRAWL_API_KEY=your_firecrawl_key_here" --service cannes-agent
railway variables --set "TELEGRAM_CHAT_ID=your_telegram_user_id_here" --service cannes-agent
```

Replace `your_firecrawl_key_here` with your key from https://firecrawl.dev and `your_telegram_user_id_here` with the ID from @userinfobot.

- [ ] **Step 5: Commit**

```bash
git add cannes-agent/main.py
git commit -m "feat: wire digest scheduler into FastAPI startup/shutdown"
```

---

### Task 5: Deploy and Smoke Test

**Files:** none (deploy only)

- [ ] **Step 1: Deploy to Railway**

```bash
cd cannes-agent && railway up
```
Expected: build succeeds, deployment live

- [ ] **Step 2: Check logs for scheduler startup**

```bash
railway logs --service cannes-agent | grep -i scheduler
```
Expected output contains: `Digest scheduler started with 9 jobs`

- [ ] **Step 3: Smoke test on-demand trending query**

Open Telegram and message `@cannes_shai_bot`:
```
What's trending at Cannes right now?
```
Expected: bot replies with a summary of LinkedIn/X content (or graceful "nothing found" message if Cannes hasn't started yet and results are sparse)

- [ ] **Step 4: Trigger a manual digest to verify the push flow**

In a Python shell on your local machine (with env vars set):
```python
import os
os.environ["FIRECRAWL_API_KEY"] = "your_key"
import firecrawl
print(firecrawl.get_trending_content())
```
Expected: prints some text with LinkedIn/X results (or empty string if no results indexed yet)

- [ ] **Step 5: Verify scheduler times in logs**

```bash
railway logs --service cannes-agent | grep "digest_"
```
Expected: log entries showing the 9 scheduled job IDs (`digest_0700`, `digest_0800`, etc.)

- [ ] **Step 6: Final commit (if any last-minute fixes)**

```bash
git add -p  # stage only what changed
git commit -m "fix: post-deploy corrections"
```

---

## Environment Variables Summary

| Variable | Where to get it |
|---|---|
| `FIRECRAWL_API_KEY` | https://firecrawl.dev — sign up and copy API key |
| `TELEGRAM_CHAT_ID` | Message `@userinfobot` on Telegram — copy the numeric ID it returns |
