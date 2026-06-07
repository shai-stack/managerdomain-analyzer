# Cannes Lions WhatsApp Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal WhatsApp assistant for Shai that uses the Cannes Lions MCP and Google Calendar to give personalized, conflict-aware event recommendations.

**Architecture:** FastAPI webhook on Railway receives WhatsApp messages via Twilio, passes them through a Claude agent that calls the Cannes Lions MCP tools and Google Calendar API, then returns a plain-text reply via Twilio TwiML.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Anthropic SDK (claude-sonnet-4-6), `anthropic` MCP client, `google-api-python-client`, `twilio`, Railway hosting.

---

## File Structure

```
cannes-agent/
├── main.py              # FastAPI app + /webhook endpoint
├── agent.py             # Claude agent with MCP tool loop
├── conversation.py      # In-memory conversation history
├── calendar.py          # Google Calendar read-only integration
├── requirements.txt     # Python dependencies
├── railway.toml         # Railway deployment config
├── .env.example         # Template for required env vars
└── tests/
    ├── test_conversation.py
    ├── test_calendar.py
    ├── test_agent.py
    └── test_main.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `cannes-agent/requirements.txt`
- Create: `cannes-agent/railway.toml`
- Create: `cannes-agent/.env.example`
- Create: `cannes-agent/tests/__init__.py`

- [ ] **Step 1: Create the project directory**

```bash
mkdir -p cannes-agent/tests
cd cannes-agent
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.6
anthropic==0.34.0
twilio==9.3.2
google-api-python-client==2.143.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
```

- [ ] **Step 3: Create `railway.toml`**

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 4: Create `.env.example`**

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ANTHROPIC_API_KEY=sk-ant-...
CANNES_MCP_URL=https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

- [ ] **Step 5: Create `tests/__init__.py`**

```python
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: scaffold cannes-agent project structure"
```

---

## Task 2: Conversation History

**Files:**
- Create: `cannes-agent/conversation.py`
- Create: `cannes-agent/tests/test_conversation.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_conversation.py
from conversation import ConversationHistory

def test_add_and_get_messages():
    history = ConversationHistory(max_messages=4)
    history.add("whatsapp:+972501234567", "user", "Hello")
    history.add("whatsapp:+972501234567", "assistant", "Hi Shai!")
    messages = history.get("whatsapp:+972501234567")
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi Shai!"}

def test_max_messages_enforced():
    history = ConversationHistory(max_messages=4)
    for i in range(6):
        history.add("whatsapp:+972501234567", "user", f"msg {i}")
    messages = history.get("whatsapp:+972501234567")
    assert len(messages) == 4
    assert messages[0]["content"] == "msg 2"

def test_different_numbers_isolated():
    history = ConversationHistory()
    history.add("whatsapp:+1111", "user", "Hello from 1111")
    history.add("whatsapp:+2222", "user", "Hello from 2222")
    assert history.get("whatsapp:+1111")[0]["content"] == "Hello from 1111"
    assert history.get("whatsapp:+2222")[0]["content"] == "Hello from 2222"

def test_empty_history_returns_empty_list():
    history = ConversationHistory()
    assert history.get("whatsapp:+unknown") == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd cannes-agent
pytest tests/test_conversation.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `conversation` not yet defined.

- [ ] **Step 3: Implement `conversation.py`**

```python
from collections import defaultdict, deque

class ConversationHistory:
    def __init__(self, max_messages: int = 10):
        self._max = max_messages
        self._store: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._max))

    def add(self, phone: str, role: str, content: str) -> None:
        self._store[phone].append({"role": role, "content": content})

    def get(self, phone: str) -> list[dict]:
        return list(self._store[phone])
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_conversation.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add conversation.py tests/test_conversation.py
git commit -m "feat: add in-memory conversation history"
```

---

## Task 3: Google Calendar Integration

**Files:**
- Create: `cannes-agent/calendar.py`
- Create: `cannes-agent/tests/test_calendar.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_calendar.py
import json
from unittest.mock import patch, MagicMock
from datetime import date
from calendar import CalendarClient, CalendarEvent

def make_mock_event(summary, start_time, end_time):
    return {
        "summary": summary,
        "start": {"dateTime": start_time, "timeZone": "Europe/Paris"},
        "end": {"dateTime": end_time, "timeZone": "Europe/Paris"},
    }

def test_get_events_for_day_returns_events():
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {
        "items": [
            make_mock_event("Lunch with Alex", "2026-06-17T12:00:00+02:00", "2026-06-17T13:00:00+02:00"),
            make_mock_event("Cannes panel", "2026-06-17T15:00:00+02:00", "2026-06-17T16:00:00+02:00"),
        ]
    }
    client = CalendarClient.__new__(CalendarClient)
    client._service = mock_service
    events = client.get_events_for_day(date(2026, 6, 17))
    assert len(events) == 2
    assert events[0].title == "Lunch with Alex"
    assert events[0].start == "12:00"
    assert events[0].end == "13:00"

def test_get_events_for_day_empty():
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": []}
    client = CalendarClient.__new__(CalendarClient)
    client._service = mock_service
    events = client.get_events_for_day(date(2026, 6, 17))
    assert events == []

def test_calendar_event_str():
    event = CalendarEvent(title="Meeting", start="14:00", end="15:00")
    assert str(event) == "14:00-15:00 Meeting"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_calendar.py -v
```

Expected: `ImportError` — `calendar` module not yet defined.

- [ ] **Step 3: Implement `calendar.py`**

```python
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

@dataclass
class CalendarEvent:
    title: str
    start: str  # HH:MM
    end: str    # HH:MM

    def __str__(self) -> str:
        return f"{self.start}-{self.end} {self.title}"


class CalendarClient:
    def __init__(self, credentials_json: str, calendar_id: str = "primary"):
        info = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        self._service = build("calendar", "v3", credentials=creds)
        self._calendar_id = calendar_id

    def get_events_for_day(self, day: date) -> list[CalendarEvent]:
        time_min = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
        time_max = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()
        result = self._service.events().list(
            calendarId=self._calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for item in result.get("items", []):
            start_raw = item.get("start", {}).get("dateTime", "")
            end_raw = item.get("end", {}).get("dateTime", "")
            if not start_raw:
                continue
            start = datetime.fromisoformat(start_raw).strftime("%H:%M")
            end = datetime.fromisoformat(end_raw).strftime("%H:%M")
            events.append(CalendarEvent(title=item.get("summary", "Untitled"), start=start, end=end))
        return events


def build_calendar_client() -> Optional[CalendarClient]:
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        return None
    try:
        return CalendarClient(creds_json)
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_calendar.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add calendar.py tests/test_calendar.py
git commit -m "feat: add Google Calendar read-only integration"
```

---

## Task 4: Claude Agent with MCP Tool Loop

**Files:**
- Create: `cannes-agent/agent.py`
- Create: `cannes-agent/tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent.py
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from agent import build_system_prompt, truncate_for_whatsapp

def test_system_prompt_contains_role():
    prompt = build_system_prompt(calendar_summary=None)
    assert "adtech" in prompt.lower()
    assert "Shai" in prompt

def test_system_prompt_includes_calendar_when_provided():
    prompt = build_system_prompt(calendar_summary="12:00-13:00 Lunch")
    assert "12:00-13:00 Lunch" in prompt

def test_truncate_short_message_unchanged():
    msg = "Hello Shai!"
    assert truncate_for_whatsapp(msg) == msg

def test_truncate_long_message():
    msg = "x" * 2000
    result = truncate_for_whatsapp(msg)
    assert len(result) <= 1500
    assert result.endswith("...")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent.py -v
```

Expected: `ImportError` — `agent` not defined.

- [ ] **Step 3: Implement `agent.py`**

```python
import os
from datetime import date, timedelta
from typing import Optional

import anthropic

from calendar import CalendarClient, CalendarEvent
from conversation import ConversationHistory

CANNES_MCP_URL = os.getenv("CANNES_MCP_URL", "https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp")
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
WHATSAPP_LIMIT = 1500

_history = ConversationHistory(max_messages=10)
_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


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
        with _client.messages.stream(
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
        ) as stream:
            response = stream.get_final_message()

        reply = ""
        for block in response.content:
            if hasattr(block, "text"):
                reply = block.text
                break

        if not reply:
            reply = "Sorry, I couldn't get a response. Please try again."

    except Exception as e:
        reply = "I'm having trouble right now. Please try again in a moment."

    reply = truncate_for_whatsapp(reply)
    _history.add(phone, "assistant", reply)
    return reply
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: add Claude agent with Cannes MCP tool loop"
```

---

## Task 5: FastAPI Webhook

**Files:**
- Create: `cannes-agent/main.py`
- Create: `cannes-agent/tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_main.py
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    with patch("main.cal_client", None):
        from main import app
        return TestClient(app)

def test_webhook_returns_twiml(client):
    with patch("main.agent.run", return_value="Here are your adtech events!"):
        with patch("main.validate_twilio_signature", return_value=True):
            resp = client.post(
                "/webhook",
                data={"From": "whatsapp:+972501234567", "Body": "What events are on Tuesday?"},
                headers={"X-Twilio-Signature": "fake"},
            )
    assert resp.status_code == 200
    assert "Here are your adtech events!" in resp.text
    assert "<?xml" in resp.text or "<Response>" in resp.text

def test_webhook_missing_body_returns_400(client):
    with patch("main.validate_twilio_signature", return_value=True):
        resp = client.post("/webhook", data={"From": "whatsapp:+972501234567"})
    assert resp.status_code == 422 or "Body" in resp.text or resp.status_code in (400, 422)

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py -v
```

Expected: `ImportError` — `main` not defined.

- [ ] **Step 3: Implement `main.py`**

```python
import os
from typing import Annotated

from fastapi import FastAPI, Form, Request, Response
from twilio.request_validator import RequestValidator

import agent
from calendar import build_calendar_client

app = FastAPI()
cal_client = build_calendar_client()
_validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN", ""))


def validate_twilio_signature(request: Request, form_data: dict) -> bool:
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")
    return _validator.validate(url, form_data, signature)


def twiml_response(message: str) -> Response:
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""
    return Response(content=body, media_type="application/xml")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    From: Annotated[str, Form()],
    Body: Annotated[str, Form()],
):
    form_data = dict(await request.form())
    if not validate_twilio_signature(request, form_data):
        return Response(status_code=403)

    reply = agent.run(phone=From, user_message=Body, cal_client=cal_client)
    return twiml_response(reply)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "feat: add FastAPI webhook with Twilio signature validation"
```

---

## Task 6: Local Smoke Test

**Files:** None (runtime verification only)

- [ ] **Step 1: Create a local `.env` file**

Copy `.env.example` to `.env` and fill in your real values:
```bash
cp .env.example .env
# Edit .env with actual keys
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Start the server**

```bash
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

- [ ] **Step 4: Test the health endpoint**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Test the agent locally (bypass Twilio validation)**

Temporarily comment out the `validate_twilio_signature` check in `main.py`, then:

```bash
curl -X POST http://localhost:8000/webhook \
  -d "From=whatsapp:+972501234567&Body=What adtech events are on Tuesday?"
```

Expected: TwiML XML response with event recommendations.

- [ ] **Step 6: Restore signature validation**

Uncomment the signature check in `main.py`.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "chore: verify local smoke test passes"
```

---

## Task 7: Deploy to Railway

**Files:** None (deployment steps)

- [ ] **Step 1: Install Railway CLI**

```bash
npm install -g @railway/cli
railway login
```

- [ ] **Step 2: Create a new Railway project**

```bash
cd cannes-agent
railway init
```

Select "Empty project", name it `cannes-agent`.

- [ ] **Step 3: Set environment variables on Railway**

```bash
railway variables set TWILIO_ACCOUNT_SID=ACxxx
railway variables set TWILIO_AUTH_TOKEN=your_token
railway variables set TWILIO_WHATSAPP_NUMBER="whatsapp:+14155238886"
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set CANNES_MCP_URL=https://mimmopalm--cannes-lions-mcp-web.modal.run/mcp
railway variables set GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
```

- [ ] **Step 4: Deploy**

```bash
railway up
```

Expected: Railway builds and deploys. Note the public URL (e.g. `https://cannes-agent-production.up.railway.app`).

- [ ] **Step 5: Verify deployment**

```bash
curl https://cannes-agent-production.up.railway.app/health
```

Expected: `{"status":"ok"}`

---

## Task 8: Twilio WhatsApp Setup

**Steps (done in Twilio Console — no code)**

- [ ] **Step 1: Create a Twilio account**

Go to [twilio.com](https://twilio.com) → Sign up for free.

- [ ] **Step 2: Enable WhatsApp Sandbox**

Twilio Console → Messaging → Try it out → Send a WhatsApp message.
Follow instructions to join the sandbox by sending a code from your WhatsApp.

- [ ] **Step 3: Point the sandbox webhook to Railway**

In the sandbox settings, set "When a message comes in" to:
```
https://cannes-agent-production.up.railway.app/webhook
```
Method: `HTTP POST`

- [ ] **Step 4: Send a test message**

From your WhatsApp, send: `What adtech events are on Tuesday?`

Expected: Claude replies with Cannes Lions schedule for Tuesday filtered to adtech-relevant events.

---

## Task 9: Google Calendar Setup

**Steps (done in Google Cloud Console — no code)**

- [ ] **Step 1: Create a Google Cloud project**

Go to [console.cloud.google.com](https://console.cloud.google.com) → New Project → name it `cannes-agent`.

- [ ] **Step 2: Enable Google Calendar API**

APIs & Services → Library → search "Google Calendar API" → Enable.

- [ ] **Step 3: Create a Service Account**

APIs & Services → Credentials → Create Credentials → Service Account.
Name: `cannes-agent`, Role: Viewer.

- [ ] **Step 4: Download credentials JSON**

In the service account, Keys → Add Key → JSON. Download the file.

- [ ] **Step 5: Share your calendar with the service account**

In Google Calendar → Settings → Share with specific people → paste the service account email (looks like `cannes-agent@your-project.iam.gserviceaccount.com`) → give "See all event details" permission.

- [ ] **Step 6: Update Railway env var**

```bash
railway variables set GOOGLE_CREDENTIALS_JSON="$(cat path/to/credentials.json)"
railway up
```

- [ ] **Step 7: Test calendar-aware query**

From WhatsApp: `What does my Tuesday look like?`

Expected: Claude replies with a merged view of your Google Calendar meetings and Cannes Lions events for Tuesday, flagging any conflicts.
