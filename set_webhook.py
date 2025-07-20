import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not URL:
    print("Missing BOT_TOKEN or WEBHOOK_URL")
else:
    webhook_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={URL}/webhook"
    r = requests.get(webhook_url)
    print(r.json())