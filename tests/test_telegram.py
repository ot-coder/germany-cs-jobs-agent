import unittest
from urllib.parse import parse_qs

from jobs_agent.telegram import send_telegram


class TelegramTests(unittest.TestCase):
    def test_send_telegram_posts_message_to_configured_chat(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b'{"ok": true}'

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["data"] = parse_qs(request.data.decode())
            captured["timeout"] = timeout
            return Response()

        send_telegram("token123", "chat456", "New job!", opener=opener)
        self.assertEqual(captured["url"], "https://api.telegram.org/bottoken123/sendMessage")
        self.assertEqual(captured["data"]["chat_id"], ["chat456"])
        self.assertEqual(captured["data"]["text"], ["New job!"])

    def test_send_telegram_skips_empty_message(self):
        called = False

        def opener(*args, **kwargs):
            nonlocal called
            called = True

        self.assertFalse(send_telegram("token", "chat", "", opener=opener))
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
