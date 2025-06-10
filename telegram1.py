import os
import requests


def send_telegram_message(message: str) -> None:
    """Send *message* to the configured Telegram chat."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.get(url, params={"chat_id": chat_id, "text": message})
    if resp.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")
        print(resp.text)
