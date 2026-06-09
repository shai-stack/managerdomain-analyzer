# Cannes Lions Social Buzz Feature — Design Spec

**Date:** 2026-06-09  
**Project:** cannes-agent  
**Status:** Approved

---

## Overview

Add real-time social media trending search and a scheduled digest to the existing Cannes Lions Telegram bot. When Shai asks about what's buzzing at Cannes, the bot searches LinkedIn and X/Twitter via Firecrawl and summarizes the results. The bot also proactively sends digests throughout the day on a fixed schedule.

---

## Architecture

Three additions to the existing app, no changes to Railway infra:

| File | Responsibility |
|---|---|
| `cannes-agent/firecrawl.py` | Calls Firecrawl REST API, returns summarizable text |
| `cannes-agent/scheduler.py` | APScheduler setup, digest trigger, Telegram push |
| `cannes-agent/agent.py` | Updated to detect trending queries and inject Firecrawl results |

One new env var: `FIRECRAWL_API_KEY`  
One new env var: `TELEGRAM_CHAT_ID` (Shai's personal Telegram user ID)

---

## Firecrawl Search (`firecrawl.py`)

**Inputs:** none (searches are hardcoded for Cannes Lions 2026)  
**Output:** plain-text block of top search results, ready to pass to Claude

Two searches are run:
1. `"Cannes Lions 2026 site:linkedin.com"` — top 5 results
2. `"Cannes Lions 2026 site:twitter.com OR site:x.com"` — top 5 results

Both use Firecrawl's `/v1/search` REST endpoint with the `FIRECRAWL_API_KEY`.

Results are concatenated into a single text block. If a search fails or returns nothing, that source is silently skipped — the other source still runs.

**Interface:**
```python
def get_trending_content() -> str:
    """Returns a text block of trending Cannes Lions content from LinkedIn and X.
    Returns empty string if both searches fail."""
```

---

## Scheduled Digest (`scheduler.py`)

Uses `APScheduler` (`BackgroundScheduler` with timezone `America/Chicago` for CST).

**Schedule:** 9 daily triggers during Cannes week (June 21–26) and on-demand outside Cannes:
- 07:00 CST — morning brief
- 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 CST — daytime updates

Each trigger:
1. Calls `firecrawl.get_trending_content()`
2. Calls Claude with prompt: *"Write a short, punchy Cannes Lions social buzz digest (5 bullets max) based on these results. Plain text, no markdown."*
3. Sends the result to `TELEGRAM_CHAT_ID` via the Telegram bot

If Firecrawl returns empty, the digest is skipped (no message sent).  
If Claude fails, a fallback message is sent: *"Couldn't fetch the Cannes buzz right now — try asking me directly."*

**Interface:**
```python
def start_scheduler(bot, chat_id: str) -> None:
    """Start APScheduler. Called from FastAPI startup."""

def stop_scheduler() -> None:
    """Stop APScheduler. Called from FastAPI shutdown."""
```

Scheduler is started in `main.py`'s `startup` event alongside webhook registration, and stopped in `shutdown`.

---

## On-Demand Trigger (`agent.py`)

`agent.py` gets a keyword detection step before the Claude API call. If the user message contains any of these signals:

> "trending", "buzz", "what's people saying", "what's happening", "social", "linkedin", "twitter", "x.com", "what are people", "talk about"

...then `firecrawl.get_trending_content()` is called and the results are appended to the system prompt:

```
Current Cannes Lions social buzz (LinkedIn + X):
<firecrawl results>
```

Claude then answers the user's question using both the Cannes MCP tools and the injected social content.

If Firecrawl returns empty, the system prompt is unchanged and Claude answers from its own knowledge.

---

## Dependencies

Add to `requirements.txt`:
- `apscheduler==3.10.4`
- `requests==2.32.3` (for Firecrawl REST calls — already likely present, pin explicitly)

---

## Environment Variables

| Variable | Description |
|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl API key from firecrawl.dev |
| `TELEGRAM_CHAT_ID` | Shai's personal Telegram user ID (get from @userinfobot) |

---

## Error Handling

- Firecrawl API errors: log warning, return empty string, don't crash
- Claude API errors in digest: send fallback Telegram message
- Scheduler startup failure: log error, app still starts (bot works without digest)
- Missing env vars: log warning at startup, scheduler disabled gracefully

---

## Out of Scope

- Scraping private LinkedIn feeds or authenticated X timelines
- Storing or caching search results between runs
- Configuring the schedule dynamically via the bot
- Sources beyond LinkedIn and X (can add later)
