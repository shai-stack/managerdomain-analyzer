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
    client._calendar_id = "primary"
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
    client._calendar_id = "primary"
    events = client.get_events_for_day(date(2026, 6, 17))
    assert events == []

def test_calendar_event_str():
    event = CalendarEvent(title="Meeting", start="14:00", end="15:00")
    assert str(event) == "14:00-15:00 Meeting"
