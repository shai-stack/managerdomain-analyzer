import pytest
import agent


@pytest.mark.parametrize("msg", [
    "what's trending at Cannes?",
    "what's the buzz today?",
    "what are people saying about Cannes?",
    "any LinkedIn posts about Cannes?",
    "what's happening on twitter?",
    "what's people talking about",
    "show me social media updates",
])
def test_is_trending_query_detects_keywords(msg):
    assert agent._is_trending_query(msg) is True


@pytest.mark.parametrize("msg", [
    "what sessions are on today?",
    "do I have any meetings tomorrow?",
    "recommend events for adtech",
    "what time does the morning keynote start?",
])
def test_is_trending_query_ignores_non_trending(msg):
    assert agent._is_trending_query(msg) is False


def test_inject_trending_appends_to_system_prompt():
    base = "You are a Cannes assistant."
    content = "LinkedIn:\n- Big news"
    result = agent._inject_trending(base, content)
    assert "Big news" in result
    assert base in result


def test_inject_trending_skips_empty_content():
    base = "You are a Cannes assistant."
    result = agent._inject_trending(base, "")
    assert result == base
