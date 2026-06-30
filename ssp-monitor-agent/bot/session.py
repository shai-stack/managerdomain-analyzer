_histories = {}


def get_history(chat_id):
    return list(_histories.get(chat_id, []))


def append(chat_id, role, content):
    _histories.setdefault(chat_id, []).append({"role": role, "content": content})


def clear(chat_id):
    _histories[chat_id] = []


def clear_all():
    _histories.clear()
