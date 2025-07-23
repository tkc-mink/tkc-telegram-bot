# handlers/weather.py
from utils.weather_utils import get_weather_forecast
from utils.context_utils import get_user_location, ask_for_location
from utils.message_utils import send_message

def handle_weather(chat_id, user_text):
    user_id = str(chat_id)
    loc = get_user_location(user_id)
    if loc and loc.get("lat") and loc.get("lon"):
        reply = get_weather_forecast(text=None, lat=loc["lat"], lon=loc["lon"])
        send_message(chat_id, reply)
    else:
        ask_for_location(chat_id)
