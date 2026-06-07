from collections import defaultdict, deque


class ConversationHistory:
    def __init__(self, max_messages: int = 10):
        self._max = max_messages
        self._store: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._max))

    def add(self, phone: str, role: str, content: str) -> None:
        self._store[phone].append({"role": role, "content": content})

    def get(self, phone: str) -> list[dict]:
        return list(self._store[phone])
