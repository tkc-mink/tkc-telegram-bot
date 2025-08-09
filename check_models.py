# check_models.py
# -*- coding: utf-8 -*-
"""
สคริปต์ทดสอบการเชื่อมต่อ OpenAI SDK v1.x
- แสดงรายการโมเดลที่เข้าถึงได้
- ทดสอบแชทสั้น ๆ ว่าตอบกลับได้จริง
รัน: python check_models.py
"""

import os
from utils.openai_client import client, chat_completion

def list_models():
    try:
        resp = client.models.list()
        ids = [m.id for m in getattr(resp, "data", [])]
        print("🔍 โมเดลที่ API key นี้เรียกได้:")
        for mid in ids:
            print("-", mid)
    except Exception as e:
        print(f"❌ ดึงรายการโมเดลไม่สำเร็จ: {e}")

def quick_chat_test():
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        reply = chat_completion([
            {"role": "system", "content": "You are a helpful assistant that replies in Thai."},
            {"role": "user", "content": "ทดสอบตอบสั้น ๆ คำว่า 'pong' หน่อย"},
        ], model=model)
        print(f"💬 Chat test ({model}):", reply)
    except Exception as e:
        print(f"❌ ทดสอบแชทไม่สำเร็จ: {e}")

if __name__ == "__main__":
    list_models()
    quick_chat_test()
