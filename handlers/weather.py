# handlers/weather.py
from utils.weather_utils import get_weather_forecast
from utils.message_utils import send_message, ask_for_location
from utils.context_utils import get_context  # ถ้าไม่ได้ใช้ก็ลบได้
from utils.json_utils import load_json_safe  # ถ้าไม่ได้ใช้ก็ลบได้

def handle_weather(chat_id: int, user_text: str):
    """
    ดึงพยากรณ์อากาศจาก lat/lon ที่เราเก็บไว้
    """
    # สมมติคุณเก็บโลเคชันไว้ในไฟล์ location_logs.json
    from utils.context_utils import get_user_location  # ถ้ามีฟังก์ชันใน context_utils
    # ถ้ายังอยู่ไฟล์เดิม ก็ import ให้ถูก เช่น from utils.history_utils import get_user_location

    loc = get_user_location(str(chat_id)) if 'get_user_location' in dir() else None
    if loc and loc.get("lat") and loc.get("lon"):
        reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
        send_message(chat_id, reply)
    else:
        ask_for_location(chat_id, "กรุณาส่งตำแหน่งก่อนใช้คำสั่งอากาศ /weather")
