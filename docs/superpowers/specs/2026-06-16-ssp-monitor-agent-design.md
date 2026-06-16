# SSP Performance Monitor Agent — Design Spec
**Date:** 2026-06-16  
**Status:** Approved

## Overview

A Telegram bot that ingests a daily SSP performance CSV report (sent by Airflow), analyzes it with Claude, and delivers a morning digest. Stays available all day for natural-language Q&A about client performance.

---

## Architecture

```
Airflow → sends email to kueez.ssp.report@gmail.com (7am UTC / 10am Israel)

Railway Python server (~$5/mo)
  ├── Scheduled job at 7:05am UTC
  │     ├── Connects to Gmail via IMAP
  │     ├── Downloads CSV attachment from airflow@kueez.com
  │     ├── Parses 30-day rolling data into memory + saves to latest_report.json
  │     ├── Calls Claude API → generates morning digest
  │     └── Sends digest to Telegram
  │
  └── Telegram Bot (always-on, python-telegram-bot)
        ├── Loads data from latest_report.json on startup
        ├── Handles Q&A via Claude API
        └── Maintains conversation history per session (resets on new digest)
```

**No database required.** Each daily CSV contains the full 30-day rolling window (~200 rows/day × 30 days). Data persisted to a local JSON file on Railway for bot restarts.

---

## Data Source

- **From:** `airflow@kueez.com`
- **To:** `kueez.ssp.report@gmail.com` (dedicated Gmail, created for this agent)
- **Subject:** `[BEUI Alert]: SSP Last 30 days - New 2026`
- **Attachment:** CSV with ~200 rows/day, 30-day rolling window

### CSV Columns
| Column | Description |
|---|---|
| SSP Adapter Connection Primary Seller | Client/publisher name |
| Day | Date (YYYY-MM-DD) |
| SSP Adapter Advertiser Type (Internal) | web_display, web_video, apps_display, apps_video |
| SSP Adapter Auctions | Auction volume |
| SSP Adapter Auctions (Previous) | Previous day auction volume |
| Diff | Auction change vs previous |
| SSP Handled Auction Rate | % of auctions handled |
| SSP Adapter Publisher Net Revenue | Revenue in USD |
| SSP Adapter Fill Rate % | Fill rate |
| SSP Adapter Publisher Share (Gross) | Publisher revenue share |
| SSP Adapter - Gross RPM | RPM in USD |

---

## Components

### 1. Email Watcher (scheduled, 7:05am UTC daily)
- Connects to Gmail via IMAP (`imap.gmail.com`)
- Searches for unread email from `airflow@kueez.com` with subject matching `SSP Last 30 days`
- Downloads and decodes CSV attachment
- Parses into a pandas DataFrame
- Saves to `latest_report.json` (flat records format)
- Marks email as read
- Triggers digest generation

### 2. Digest Generator
Calls Claude API (`claude-sonnet-4-6`) with the full dataset and produces a 3-part message:

**Part 1 — Summary**
- Total net revenue for latest day
- % change vs previous day (using the Diff and Auctions Previous columns)
- Top earning client
- Count of active clients and ad types

**Part 2 — Anomalies**
- Revenue drop >25% vs previous day
- SSP Handled Auction Rate below 50%
- Unusual auction volume spikes (>2x previous)
- Flagged with ⬇ / ⬆ emoji and brief explanation

**Part 3 — Full Breakdown**
- All clients for latest day, ranked by net revenue
- Columns: rank, client, ad type, revenue, fill rate, RPM
- Truncated to top 20 in the message; full list available on request

Telegram's 4096 char limit handled by splitting into multiple messages.

### 3. Telegram Bot (always-on)
- Framework: `python-telegram-bot` (webhook mode on Railway)
- Conversation history stored in memory per `chat_id`, reset on each new daily digest
- Each user message → Claude API call with:
  - System prompt: role + full 30-day dataset as context
  - Conversation history (last 10 exchanges)
  - User's message
- Response sent back to Telegram

**Special commands:**
| Command | Action |
|---|---|
| `full list` | Send complete client breakdown for latest day |
| `refresh` | Manually re-check Gmail and reprocess |
| `yesterday` | Show previous day's data for comparison |

### 4. Claude API Usage
- Model: `claude-sonnet-4-6`
- Digest generation: one call per day, full dataset as input (~6000 rows × ~10 columns)
- Q&A: one call per user message, dataset passed each time as system context
- Context strategy: full 30-day CSV in system prompt (fits within 200k context window)

---

## Infrastructure

| Component | Service | Cost |
|---|---|---|
| Python bot + scheduler | Railway | ~$5/mo |
| Email receiving | Gmail (dedicated free account) | Free |
| LLM | Claude API (Anthropic) | Pay per use |
| Telegram bot | Telegram BotFather | Free |

**Required setup steps:**
1. Create `kueez.ssp.report@gmail.com`
2. Ask Airflow team to add this address as a recipient on the daily report
3. Create Telegram bot via @BotFather
4. Deploy Python server to Railway
5. Set env vars: `GMAIL_EMAIL`, `GMAIL_APP_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`

---

## Morning Digest Example

```
📊 SSP Daily Report — June 16, 2026

💰 SUMMARY
Total Revenue: $1,247.83 (+3.2% vs yesterday)
Top Earner: Yahoo — $512.23
Active Clients: 87 | Ad Types: web_display, web_video, apps_display

🚨 ANOMALIES
⬇ Dailymotion — revenue down 38% vs yesterday
⬇ Smart News — SSP Auction Rate only 47% (below threshold)
⬆ EightPoint — auctions up 300% (87K vs 29K prev)

📋 TOP 20 BY REVENUE
1. Yahoo (web_display) — $512.23 | Fill: 0.75% | RPM: $0.0075
2. Publift (web_display) — $133.67 | Fill: 1.19% | RPM: $0.0080
3. First Media — $78.08 | Fill: 2.85% | RPM: $0.0290
...
[type "full list" for all clients]
```

---

## Q&A Capabilities

The bot handles natural-language queries against the full 30-day dataset:

- Trend analysis: *"How's Yahoo trending over the last 2 weeks?"*
- Filtering: *"Which clients have fill rate above 3%?"*
- Comparison: *"Compare Publift vs First Media RPM over 30 days"*
- Anomaly investigation: *"Why did Dailymotion drop?"*
- Segment analysis: *"Which web_video clients are underperforming?"*

---

## Error Handling

- **Email not found by 7:30am UTC:** bot sends Telegram alert "⚠️ Report not received yet. Will retry in 30 min."
- **Claude API failure:** retry once; if still failing, send raw top-10 table without analysis
- **Railway restart:** bot reloads from `latest_report.json` on startup
- **Telegram message too long:** auto-split at 4096 chars between logical sections
