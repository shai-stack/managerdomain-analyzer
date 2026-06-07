import os
from typing import Annotated

from fastapi import FastAPI, Form, Request, Response
from twilio.request_validator import RequestValidator

import agent
from gcal import build_calendar_client

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
