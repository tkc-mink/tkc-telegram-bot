
import openai
import os

# อ่าน API Key จาก Environment Variable
openai.api_key = os.getenv("OPENAI_API_KEY")

models = openai.models.list()

print("🔍 รายการโมเดลที่เรียกได้ด้วย API Key นี้:")
for m in models.data:
    print("-", m.id)
