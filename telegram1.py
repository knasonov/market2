import requests
import os

def send_telegram_message(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    message = "Hello from your Python script!"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"

    response = requests.get(url)

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")
        print(response.text)