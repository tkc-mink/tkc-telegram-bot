# handlers/weather.py
from utils.message_utils import send_message, ask_for_location
from utils.context_utils import get_user_location  # ถ้าย้ายฟังก์ชันนี้ไว้ที่อื่น ปรับ path ให้ถูก
from weather_utils import get_weather_forecast

def handle_weather(chat_id: int, user_text: str):
    """
    ตอบสภาพอากาศจาก lat/lon ที่เคยบันทึกไว้
    """
    loc = get_user_location(str(chat_id))
    if loc and loc.get("lat") and loc.get("lon"):
        reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
        send_message(chat_id, reply)
    else:
        ask_for_location(chat_id, "ยังไม่มีตำแหน่งของคุณ กรุณาแชร์ตำแหน่งก่อนครับ")
