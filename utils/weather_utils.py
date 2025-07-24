import os
import requests

def get_weather_forecast(text=None, lat=None, lon=None):
    """
    ดึงข้อมูลพยากรณ์อากาศปัจจุบัน (วันนี้) ตามพิกัด lat/lon จาก OpenWeather API
    """
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    if not OPENWEATHER_API_KEY:
        return "❌ ไม่พบ API Key สำหรับ OpenWeather"
    if lat is None or lon is None:
        return "❌ ไม่พบพิกัด location กรุณาแชร์ตำแหน่งก่อนถามอากาศ"

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=th"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            # ดึงข้อมูลที่สำคัญ
            weather = data.get("weather", [{}])[0]
            desc = weather.get("description", "ไม่ทราบ")
            main = data.get("main", {})
            temp = main.get("temp", "-")
            temp_min = main.get("temp_min", "-")
            temp_max = main.get("temp_max", "-")
            humidity = main.get("humidity", "-")
            wind = data.get("wind", {})
            wind_speed = wind.get("speed", "-")
            city = data.get("name", "ไม่ทราบตำแหน่ง")
            # ข้อความภาษาไทย
            return (
                f"📍 สภาพอากาศวันนี้ ({city})\n"
                f"สภาพอากาศ: {desc.capitalize()}\n"
                f"อุณหภูมิ: {temp}°C (สูงสุด {temp_max}°C / ต่ำสุด {temp_min}°C)\n"
                f"ความชื้น: {humidity}%\n"
                f"ลม: {wind_speed} กม./ชม."
            )
        elif resp.status_code == 401:
            return "❌ API Key ของ OpenWeather ไม่ถูกต้องหรือหมดอายุ"
        else:
            return f"❌ ไม่สามารถดึงข้อมูลอากาศได้ (status: {resp.status_code})"
    except Exception as e:
        print(f"[weather_utils] ERROR: {e}")
        return "❌ ไม่สามารถดึงข้อมูลอากาศได้ในขณะนี้"
