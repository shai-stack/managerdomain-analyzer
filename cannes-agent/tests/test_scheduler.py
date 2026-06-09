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
