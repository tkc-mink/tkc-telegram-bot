import requests
from config.tokens import BOT_TOKENS

for name, token in BOT_TOKENS.items():
    url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    response = requests.post(url)
    if response.status_code == 200:
        print(f"[{name}] ✅ ล้าง webhook สำเร็จ")
    else:
        print(f"[{name}] ❌ ล้มเหลวในการล้าง webhook: {response.text}")
