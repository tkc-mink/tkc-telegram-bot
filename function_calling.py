import json
from weather_utils import get_weather_forecast
from gold_utils import get_gold_price
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FUNCTIONS = [
    {
        "name": "get_weather_forecast",
        "description": "ดูพยากรณ์อากาศวันนี้หรือล่วงหน้าในไทย",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "ข้อความที่ผู้ใช้พิมพ์ เช่น อากาศที่โคราช หรือ พยากรณ์วันนี้"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "get_gold_price",
        "description": "ดูราคาทองคำประจำวัน",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]

SYSTEM_PROMPT = (
    "คุณคือผู้ช่วย AI ภาษาไทยขององค์กรกลุ่มตระกูลชัย "
    "ให้ตอบคำถามทั่วไปอย่างสุภาพ จริงใจ และเป็นประโยชน์ "
    "หากพบคำถามเกี่ยวกับอากาศหรือราคาทอง ให้เรียกฟังก์ชันที่ระบบมีให้ "
    "ห้ามตอบแทนถ้าฟังก์ชันสามารถจัดการได้"
)

def process_with_function_calling(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            functions=FUNCTIONS,
            function_call="auto"
        )
        msg = response.choices[0].message

        if msg.function_call:
            fname = msg.function_call.name
            args = json.loads(msg.function_call.arguments or "{}")
            if fname == "get_weather_forecast":
                return get_weather_forecast(text=args.get("text", ""))
            elif fname == "get_gold_price":
                return get_gold_price()

        return msg.content.strip()

    except Exception as e:
        print(f"[function_calling] {e}")
        return "❌ ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งครับ"
