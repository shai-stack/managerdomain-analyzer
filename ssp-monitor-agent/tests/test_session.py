from bot.session import append, clear, clear_all, get_history


def test_empty_history():
    assert get_history(999) == []


def test_append_and_get():
    append(1, "user", "hello")
    append(1, "assistant", "hi")
    h = get_history(1)
    assert len(h) == 2
    assert h[0] == {"role": "user", "content": "hello"}


def test_clear_single():
    append(2, "user", "q")
    clear(2)
    assert get_history(2) == []


def test_clear_all():
    append(10, "user", "a")
    append(11, "user", "b")
    clear_all()
    assert get_history(10) == []
    assert get_history(11) == []
