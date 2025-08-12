# handlers/search.py

# ... (โค้ดเดิมของคุณอยู่ด้านบน) ...

# ===== ส่วนที่เพิ่มเข้ามาใหม่สำหรับ Gemini =====
# import client ใหม่ของเรา
try:
    from utils.gemini_client import generate_text as gemini_ask
except ImportError:
    # Fallback เผื่อไฟล์ยังไม่ได้สร้าง
    def gemini_ask(prompt: str, prefer_strong: bool = False) -> str:
        return "❌ ไม่สามารถเชื่อมต่อ Gemini Client ได้ โปรดตรวจสอบไฟล์ utils/gemini_client.py"

def handle_gemini_search(chat_id, user_text):
    """
    Handler สำหรับการค้นหาและสรุปข้อมูลด้วย Gemini (อัปเกรด)
    """
    # จัดการกับคำค้นหา (เหมือนโค้ดเดิมของคุณ)
    prefix = "/search"
    query = user_text
    if user_text.lower().startswith(prefix):
        query = user_text[len(prefix):].strip()
    elif user_text.startswith("ค้นหา"):
        query = user_text[3:].strip()
    
    if not query:
        send_message(chat_id, "❗️ พิมพ์ /search คำค้นหา เช่น /search ยางรถยนต์ไฟฟ้า OTANI")
        return

    # สร้าง Prompt ที่ชัดเจนสำหรับ Gemini
    # การใส่คำว่า "ข้อมูลล่าสุด" จะช่วยกระตุ้นให้ Gemini ค้นหาข้อมูลที่เป็นปัจจุบันมากขึ้น
    prompt_for_gemini = f"ช่วยค้นหาและสรุปข้อมูลล่าสุดเกี่ยวกับ '{query}' ให้หน่อย"
    
    # แจ้งให้ผู้ใช้ทราบว่ากำลังทำงาน
    send_message(chat_id, "🔎 กำลังค้นหาและสรุปข้อมูลด้วย Gemini...")

    # เรียกใช้ Gemini!
    result = gemini_ask(prompt_for_gemini)

    # ส่งผลลัพธ์ที่ Gemini สรุปมาให้แล้วกลับไป
    send_message(chat_id, result, parse_mode="Markdown")

# หมายเหตุ: เราจะยังเก็บ handle_Google Search และ handle_google_image ของเดิมไว้ก่อน
# เพื่อให้สามารถสลับกลับไปใช้ได้หากต้องการ
