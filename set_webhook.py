import requests

TOKEN = '8113563670:AAEzvfUChu4TeRsSTtuTouc6IPfXWs4FnCk'  # <- ของจริง (คุณใส่มาแล้ว ใช้ได้เลย)
WEBHOOK_URL = 'https://tkc-telegram-bot.onrender.com/webhook'  # <- ไม่มีจุดต่อท้าย

url = f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}'

response = requests.get(url)
print(response.json())
