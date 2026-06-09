import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional


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
        from google.oauth2 import service_account as _sa
        from googleapiclient.discovery import build as _build
        info = json.loads(credentials_json)
        creds = _sa.Credentials.from_service_account_info(info, scopes=SCOPES)
        self._service = _build("calendar", "v3", credentials=creds)
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
            if not start_raw or not end_raw:
                continue  # skip all-day events (use "date" not "dateTime") and malformed entries
            start = datetime.fromisoformat(start_raw).strftime("%H:%M")
            end = datetime.fromisoformat(end_raw).strftime("%H:%M")
            events.append(CalendarEvent(title=item.get("summary", "Untitled"), start=start, end=end))
        return events


def build_calendar_client() -> Optional[CalendarClient]:
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        return None
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    try:
        return CalendarClient(creds_json, calendar_id=calendar_id)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Calendar client init failed: %s", exc)
        return None
