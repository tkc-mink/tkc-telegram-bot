# handlers/favorite.py
# -*- coding: utf-8 -*-

from utils.message_utils import send_message
from utils.favorite_utils import add_favorite, get_favorites, remove_favorite


def handle_favorite(chat_id: int, user_text: str) -> None:
    """
    คำสั่ง:
    - /favorite_add <ข้อความ>   -> บันทึกเป็นรายการโปรด
    - /favorite_list             -> ดูรายการโปรด 10 รายการล่าสุด
    - /favorite_remove <ลำดับ>  -> ลบตามลำดับ (เช่น 1,2,... จากหน้ารายการ)
    """
    try:
        text = (user_text or "").strip()
        if text.startswith("/favorite_add"):
            content = text.replace("/favorite_add", "", 1).strip()
            if not content:
                send_message(chat_id, "พิมพ์สิ่งที่ต้องการบันทึกต่อท้าย เช่น /favorite_add วิธีเช็คสภาพอากาศ")
                return
            ok = add_favorite(str(chat_id), content)
            send_message(chat_id, "✅ บันทึกรายการโปรดแล้ว" if ok else "❌ บันทึกรายการโปรดไม่สำเร็จ")
            return

        if text.startswith("/favorite_list"):
            favs = get_favorites(str(chat_id), limit=10)
            if not favs:
                send_message(chat_id, "🤔 คุณยังไม่มีรายการโปรด")
                return
            lines = []
            for i, item in enumerate(favs, start=1):
                lines.append(f"{i}. {item.get('text','')}")
            msg = "⭐ <b>รายการโปรดของคุณ</b>:\n" + "\n".join(lines)
            send_message(chat_id, msg, parse_mode="HTML")
            return

        if text.startswith("/favorite_remove"):
            idx_text = text.replace("/favorite_remove", "", 1).strip()
            if not idx_text.isdigit():
                send_message(chat_id, "โปรดระบุดัชนี (ตัวเลข) ที่ต้องการลบ เช่น /favorite_remove 2")
                return
            idx = int(idx_text)
            ok = remove_favorite(str(chat_id), index=idx)
            send_message(chat_id, "🗑️ ลบรายการเรียบร้อย" if ok else "❌ ไม่พบรายการตามลำดับที่ระบุ")
            return

        # ถ้าไม่ได้ใช้คำสั่งด้านบน ให้แนะนำการใช้งาน
        send_message(
            chat_id,
            "คำสั่งรายการโปรด:\n"
            "• /favorite_add ข้อความ\n"
            "• /favorite_list\n"
            "• /favorite_remove ลำดับ",
        )
    except Exception as e:
        send_message(chat_id, f"❌ จัดการรายการโปรดไม่สำเร็จ: {e}")
