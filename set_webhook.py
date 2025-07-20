import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL in environment variables")

url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
response = requests.post(url, data={"url": WEBHOOK_URL})

if response.status_code == 200:
    print("Webhook set successfully ✅")
else:
    print(f"Failed to set webhook ❌\n{response.text}")
