from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def send_telegram(
    bot_token: str,
    chat_id: str,
    message: str,
    opener: Callable = urlopen,
) -> bool:
    if not message.strip():
        return False
    if not bot_token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    payload = urlencode({"chat_id": chat_id, "text": message, "disable_web_page_preview": "true"}).encode()
    request = Request(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=payload, method="POST")
    with opener(request, timeout=30) as response:
        result = json.loads(response.read())
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API rejected the message: {result}")
    return True


def main() -> int:
    message_path = Path(os.environ.get("TELEGRAM_MESSAGE_FILE", ".out/telegram.txt"))
    message = message_path.read_text(encoding="utf-8") if message_path.exists() else ""
    sent = send_telegram(
        os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        os.environ.get("TELEGRAM_CHAT_ID", ""),
        message,
    )
    print("Telegram notification sent" if sent else "No new jobs; Telegram notification skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
