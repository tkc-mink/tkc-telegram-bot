# location_handler.py - TKC Assistant Bot Module

from telegram import Update
from telegram.ext import ContextTypes
import os
import json
import requests
from datetime import datetime

LOCATION_FOLDER = "data/locations"

def ensure_folder():
    if not os.path.exists(LOCATION_FOLDER):
        os.makedirs(LOCATION_FOLDER)

def get_location_file(user_id):
    return os.path.join(LOCATION_FOLDER, f"{user_id}.json")

def reverse_geocode(lat, lon):
    try:
        response = requests.get(
            f"https://nominatim.openstreetmap.org/reverse",
            params={
                "format": "json",
                "lat": lat,
                "lon": lon,
                "zoom": 10,
                "addressdetails": 1
            },
            headers={"User-Agent": "tkc-bot"}
        )
        data = response.json()
        address = data.get("address", {})
        return {
            "district": address.get("county") or address.get("district") or "",
            "province": address.get("state") or address.get("region") or "",
            "full": data.get("display_name", "")
        }
    except Exception as e:
        return {
            "district": "",
            "province": "",
            "full": "ไม่สามารถระบุพิกัดได้"
        }

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    ensure_folder()

    lat = update.message.location.latitude
    lon = update.message.location.longitude
    timestamp = datetime.now().isoformat()

    address_info = reverse_geocode(lat, lon)

    location_data = {
        "user_id": user_id,
        "latitude": lat,
        "longitude": lon,
        "timestamp": timestamp,
        "district": address_info["district"],
        "province": address_info["province"],
        "display_name": address_info["full"]
    }

    with open(get_location_file(user_id), "w", encoding="utf-8") as f:
        json.dump(location_data, f, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        f"📍 บันทึกตำแหน่งเรียบร้อยแล้ว\nอำเภอ: {address_info['district']}\nจังหวัด: {address_info['province']}"
    )
