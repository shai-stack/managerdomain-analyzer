from conversation import ConversationHistory

def test_add_and_get_messages():
    history = ConversationHistory(max_messages=4)
    history.add("whatsapp:+972501234567", "user", "Hello")
    history.add("whatsapp:+972501234567", "assistant", "Hi Shai!")
    messages = history.get("whatsapp:+972501234567")
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi Shai!"}

def test_max_messages_enforced():
    history = ConversationHistory(max_messages=4)
    for i in range(6):
        history.add("whatsapp:+972501234567", "user", f"msg {i}")
    messages = history.get("whatsapp:+972501234567")
    assert len(messages) == 4
    assert messages[0]["content"] == "msg 2"

def test_different_numbers_isolated():
    history = ConversationHistory()
    history.add("whatsapp:+1111", "user", "Hello from 1111")
    history.add("whatsapp:+2222", "user", "Hello from 2222")
    assert history.get("whatsapp:+1111")[0]["content"] == "Hello from 1111"
    assert history.get("whatsapp:+2222")[0]["content"] == "Hello from 2222"

def test_empty_history_returns_empty_list():
    history = ConversationHistory()
    assert history.get("whatsapp:+unknown") == []
