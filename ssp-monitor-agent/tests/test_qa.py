from unittest.mock import MagicMock, patch

from bot.qa import answer, get_full_list, is_full_list_request, is_yesterday_request

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        },
        {
            "seller": "Publift", "ad_type": "web_display", "revenue": 133.67,
            "fill_rate": 0.0119, "rpm": 0.0080, "auction_rate": 0.8938,
            "auctions": 22278000, "auctions_prev": 19824000, "auctions_diff": 2454000,
        },
    ],
    "thirty_day_summary": {},
}


def _mock_claude(text):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=text)]
    )
    return mock_client


def test_answer_returns_claude_text():
    with patch("bot.qa.anthropic.Anthropic", return_value=_mock_claude("Yahoo is up.")):
        result = answer("How is Yahoo?", SAMPLE_DATA, [], "fake-key")
    assert result == "Yahoo is up."


def test_answer_passes_history():
    mock_client = _mock_claude("ok")
    history = [
        {"role": "user", "content": "prev"},
        {"role": "assistant", "content": "resp"},
    ]
    with patch("bot.qa.anthropic.Anthropic", return_value=mock_client):
        answer("follow up", SAMPLE_DATA, history, "fake-key")
    call_msgs = mock_client.messages.create.call_args[1]["messages"]
    assert any(m["content"] == "prev" for m in call_msgs)


def test_get_full_list_yahoo_first():
    result = get_full_list(SAMPLE_DATA)
    assert result.index("Yahoo") < result.index("Publift")


def test_get_full_list_contains_revenue():
    result = get_full_list(SAMPLE_DATA)
    assert "512.23" in result


def test_is_full_list_request_true():
    assert is_full_list_request("show full list please") is True


def test_is_full_list_request_false():
    assert is_full_list_request("how is yahoo") is False


def test_is_yesterday_request_true():
    assert is_yesterday_request("show me yesterday") is True


def test_is_yesterday_request_false():
    assert is_yesterday_request("today's data") is False
