# Cannes Lions WhatsApp Personal Assistant — Design Spec

**Date:** 2026-06-07
**Author:** Shai Almagor-Kueez
**Status:** Approved

---

## Overview

A personal WhatsApp assistant that helps Shai navigate Cannes Lions 2026. It understands his role (adtech), knows the full Cannes schedule via MCP, and is aware of his Google Calendar so it can give conflict-free, personalized recommendations.

---

## Architecture

```
Shai (WhatsApp)
     ↕  Twilio WhatsApp API
FastAPI webhook (Python, Railway free tier)
     ↕  Anthropic SDK (claude-sonnet-4-6) with MCP tool use
     ↕  Cannes Lions MCP  (https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp)
     ↕  Google Calendar API (read-only)
```

**Request flow:**
1. Shai sends a WhatsApp message
2. Twilio POSTs it to the Railway webhook
3. Webhook validates Twilio signature, extracts message
4. Agent runs: Claude + Cannes MCP tools + Google Calendar data
5. Claude returns a WhatsApp-friendly reply (plain text, ≤1,500 chars)
6. Webhook sends reply via Twilio TwiML

---

## Components

### `main.py`
FastAPI app with a single `POST /webhook` endpoint.
- Validates Twilio request signature on every call
- Extracts sender number + message body
- Calls `agent.run()`
- Returns TwiML XML with Claude's reply

### `agent.py`
Claude agent using the Anthropic SDK with MCP tool use.
- Connects to Cannes Lions MCP server via HTTP
- Available MCP tools: `search_schedule`, `recommend_events`, `filter_events`, `list_schedule_by_day`, `list_schedule_by_host`, `get_event_details`, `list_registrations`, `find_registration`
- Calls `calendar.get_today_events()` or `calendar.get_events_for_day()` when the user asks about their schedule or when checking for conflicts
- System prompt establishes: user is Shai, role is adtech, keep replies concise and plain text
- Runs tool loop until final answer is ready

### `conversation.py`
In-memory conversation history keyed by WhatsApp phone number.
- Stores last 10 messages per number
- Provides context to Claude across a conversation thread
- Resets on server restart (acceptable for Cannes week)

### `calendar.py`
Google Calendar integration (read-only).
- Authenticates via OAuth2 using service account or user credentials
- `get_events_for_day(date)` — returns list of events with title, start, end times
- Claude uses this to surface conflicts and build full-day views

---

## Example Interactions

| User message | Agent behavior |
|---|---|
| "What adtech events are on Tuesday?" | `recommend_events(role=adtech)` + `list_schedule_by_day(tuesday)` + calendar conflict check |
| "What does my Wednesday look like?" | Google Calendar events + Cannes schedule merged and summarized |
| "Any AI or programmatic panels?" | `search_schedule(query="AI programmatic")` |
| "Am I registered for anything?" | `list_registrations()` |
| "Who's hosting at the Palais tomorrow?" | `list_schedule_by_host` + `filter_events` |

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Cannes MCP unreachable | "I'm having trouble reaching the Cannes schedule right now, try again in a moment." |
| Google Calendar auth failure | Gracefully skips calendar data, notes it in response |
| Reply too long | Claude summarizes top 5 results, offers to send more |
| Unknown Twilio sender | Silently ignore (Twilio signature validation handles spoofing) |

---

## Environment Variables

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | Your Twilio WhatsApp sender number |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CANNES_MCP_URL` | `https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp` |
| `GOOGLE_CREDENTIALS_JSON` | Google OAuth2 credentials JSON (as string) |

---

## Hosting

- **Platform:** Railway (free tier)
- **Runtime:** Python 3.11
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Config:** `railway.toml`

---

## Setup Steps (high level)

1. Create Twilio account → enable WhatsApp sandbox → point webhook to Railway URL
2. Create Google Cloud project → enable Calendar API → download OAuth credentials
3. Deploy to Railway → set environment variables
4. Send first WhatsApp message to Twilio sandbox number

---

## Out of Scope

- Writing to Google Calendar (read-only)
- Persistent conversation storage (in-memory is sufficient for Cannes week)
- Multi-user support
- Push notifications / proactive messages
