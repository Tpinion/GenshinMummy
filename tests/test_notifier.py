from genshin_mummy.tools.notifier import notify, notify_countdown


def test_notify():
    notify('你好')


def test_notify_countdown():
    notify_countdown(5)
