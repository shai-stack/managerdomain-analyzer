import asyncio
import os
import xml.sax.saxutils as saxutils
from typing import Annotated

from fastapi import FastAPI, Form, Request, Response
from twilio.request_validator import RequestValidator

import agent
from gcal import build_calendar_client

app = FastAPI()

try:
    cal_client = build_calendar_client()
except Exception:
    import logging as _log
    _log.getLogger(__name__).warning("Google Calendar client failed to initialize, calendar features disabled")
    cal_client = None

_twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
if not _twilio_auth_token:
    import logging as _log
    _log.getLogger(__name__).warning("TWILIO_AUTH_TOKEN is not set — signature validation will fail")
_validator = RequestValidator(_twilio_auth_token or "")


def validate_twilio_signature(request: Request, form_data: dict) -> bool:
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")
    return _validator.validate(url, form_data, signature)


def twiml_response(message: str) -> Response:
    safe = saxutils.escape(message)
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{safe}</Message>
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

    reply = await asyncio.to_thread(agent.run, From, Body, cal_client)
    return twiml_response(reply)
