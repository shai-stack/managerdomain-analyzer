import pytest
from unittest.mock import patch, MagicMock
import firecrawl


def _make_response(items):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"data": items}
    return mock


def test_get_trending_content_combines_results():
    linkedin_item = {"title": "LinkedIn post", "description": "Big news at Cannes", "url": "https://linkedin.com/a"}
    twitter_item = {"title": "X post", "description": "Trending at Cannes", "url": "https://x.com/b"}

    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = [
            _make_response([linkedin_item]),
            _make_response([twitter_item]),
        ]
        result = firecrawl.get_trending_content("fake-key")

    assert "LinkedIn post" in result
    assert "X post" in result


def test_get_trending_content_one_source_fails():
    twitter_item = {"title": "X post", "description": "Trending at Cannes", "url": "https://x.com/b"}

    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = [
            Exception("network error"),
            _make_response([twitter_item]),
        ]
        result = firecrawl.get_trending_content("fake-key")

    assert "X post" in result


def test_get_trending_content_both_fail():
    with patch("firecrawl.requests.post") as mock_post:
        mock_post.side_effect = Exception("network error")
        result = firecrawl.get_trending_content("fake-key")

    assert result == ""


def test_get_trending_content_empty_data():
    with patch("firecrawl.requests.post") as mock_post:
        mock_post.return_value = _make_response([])
        result = firecrawl.get_trending_content("fake-key")

    assert result == ""


def test_get_trending_content_no_api_key(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    with patch("firecrawl.requests.post") as mock_post:
        result = firecrawl.get_trending_content()
    mock_post.assert_not_called()
    assert result == ""
