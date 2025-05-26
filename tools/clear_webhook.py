import requests
from config.tokens import BOT_TOKENS

for name, token in BOT_TOKENS.items():
    print(f"🔧 ล้าง webhook สำหรับบอท: {name}")
    resp = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
    print(resp.text)
