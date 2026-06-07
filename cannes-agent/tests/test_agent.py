from unittest.mock import patch, MagicMock
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
