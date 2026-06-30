from unittest.mock import MagicMock, patch

from bot.digest import generate_digest, split_for_telegram

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        }
    ],
    "thirty_day_summary": {
        "Yahoo|web_display": {
            "seller": "Yahoo", "ad_type": "web_display",
            "total_revenue": 14500.23, "avg_fill_rate": 0.0075, "avg_rpm": 0.0075,
            "revenue_by_date": {"2026-06-16": 512.23},
        }
    },
}


def _mock_claude(text: str):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=text)]
    )
    return mock_client


def test_generate_digest_returns_list():
    mock_client = _mock_claude("Part1\n---SPLIT---\nPart2\n---SPLIT---\nPart3")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        result = generate_digest(SAMPLE_DATA, "fake-key")
    assert isinstance(result, list)
    assert len(result) == 3


def test_generate_digest_all_under_4096():
    mock_client = _mock_claude("Part1\n---SPLIT---\nPart2\n---SPLIT---\nPart3")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        result = generate_digest(SAMPLE_DATA, "fake-key")
    assert all(len(m) <= 4096 for m in result)


def test_split_for_telegram_short_message():
    assert split_for_telegram("hello") == ["hello"]


def test_split_for_telegram_long_message():
    long = "x\n" * 3000  # 6000 chars
    parts = split_for_telegram(long)
    assert len(parts) > 1
    assert all(len(p) <= 4096 for p in parts)


def test_generate_digest_calls_claude():
    mock_client = _mock_claude("a\n---SPLIT---\nb\n---SPLIT---\nc")
    with patch("bot.digest.anthropic.Anthropic", return_value=mock_client):
        generate_digest(SAMPLE_DATA, "fake-key")
    mock_client.messages.create.assert_called_once()
