import requests

TOKEN = 'YOUR_TELEGRAM_TOKEN'
WEBHOOK_URL = f'https://tkc-telegram-bot.onrender.com/webhook'

url = f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}'

response = requests.get(url)
print(response.json())
