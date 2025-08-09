# handlers/weather.py
# -*- coding: utf-8 -*-

from utils.message_utils import send_message, ask_for_location
from utils.context_utils import get_user_location
from utils.weather_utils import get_weather_forecast


def handle_weather(chat_id: int, user_text: str) -> None:
    """
    ส่งสภาพอากาศล่าสุดกลับไปยังผู้ใช้
    - ถ้ามี location (lat/lon) ในระบบ => ตอบทันที
    - ถ้ายังไม่มี => ขอให้ผู้ใช้แชร์ตำแหน่ง
    """
    try:
        loc = get_user_location(str(chat_id))
        # ตรวจสอบว่า loc มีข้อมูลที่จำเป็นครบ
        if (
            loc
            and isinstance(loc, dict)
            and loc.get("lat") is not None
            and loc.get("lon") is not None
        ):
            reply = get_weather_forecast(
                text=None,
                lat=loc["lat"],
                lon=loc["lon"]
            )
            send_message(chat_id, reply, parse_mode="HTML")
        else:
            ask_for_location(
                chat_id,
                "📍 กรุณาแชร์โลเคชั่นครั้งแรกเพื่อให้ผมส่งพยากรณ์อากาศตรงพื้นที่คุณนะครับ แล้วพิมพ์ /weather อีกครั้ง"
            )

    except Exception as e:
        send_message(chat_id, f"❌ เกิดข้อผิดพลาดในการดึงข้อมูลอากาศ: {e}")
