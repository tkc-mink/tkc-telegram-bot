# handlers/news.py
# -*- coding: utf-8 -*-
"""
Handler for fetching and displaying the latest news (Thai/any topic).
Stable version:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo)
- parse_mode=HTML พร้อม escape ทุกข้อความจากภายนอก
- รองรับผลลัพธ์จาก utils.news_utils.get_news() ทั้ง str / dict / list[dict]
- ฟอร์แมตหัวข้อ, แหล่งข่าว, เวลาเผยแพร่, และลิงก์ให้อ่านง่าย
"""
from __future__ import annotations
from typing import Dict, Any, List, Iterable
import re

from utils.message_utils import send_message, send_typing_action
from utils.news_utils import get_news


# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _looks_html(s: str) -> bool:
    if not s:
        return False
    return ("</" in s) or ("<b>" in s) or ("<i>" in s) or ("<code>" in s) or ("<a " in s) or ("<br" in s)

def _parse_topic_and_limit(user_text: str) -> tuple[str, int]:
    """
    แยก topic และ limit แบบยืดหยุ่น:
    - "/news" → ("ข่าวล่าสุด", 8)
    - "/news เศรษฐกิจไทย" → ("เศรษฐกิจไทย", 8)
    - "/news AI 5" → ("AI", 5)
    - ถ้า limit ไม่ใช่ตัวเลขหรือ <=0 → ใช้ 8
    """
    default_topic = "ข่าวล่าสุด"
    default_limit = 8

    text = (user_text or "").strip()
    if not text:
        return (default_topic, default_limit)

    parts = text.split(maxsplit=1)
    if not parts:
        return (default_topic, default_limit)

    # ตัดคำสั่ง /news ออก
    if parts[0].lower().startswith("/news"):
        rest = parts[1].strip() if len(parts) > 1 else ""
    else:
        rest = text

    if not rest:
        return (default_topic, default_limit)

    # จับกรณีลงท้ายด้วยเลข เช่น "AI 5"
    m = re.match(r"^(.*\S)\s+(\d{1,2})$", rest)
    if m:
        topic = m.group(1).strip()
        try:
            lim = int(m.group(2))
            if lim <= 0:
                lim = default_limit
        except Exception:
            lim = default_limit
        return (topic or default_topic, min(lim, 12))  # กันยาวเกิน

    return (rest, default_limit)

def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _format_article_item(item: Dict[str, Any]) -> str:
    """
    แปลงข่าว 1 ชิ้นเป็นสตริง HTML สวย ๆ:
    รองรับคีย์ยอดนิยม: title, url, link, source, publisher, published_at, time, summary
    """
    title = _first_present(item, ("title", "headline", "name")) or "-"
    url   = _first_present(item, ("url", "link"))
    src   = _first_present(item, ("source", "publisher", "site"))
    when  = _first_present(item, ("published_at", "published", "date", "time"))
    summ  = _first_present(item, ("summary", "description"))

    title_html = _html_escape(str(title))
    if url:
        url_s = str(url).strip()
        # Telegram HTML link
        title_html = f'<a href="{_html_escape(url_s)}">{title_html}</a>'

    lines = [f"• {title_html}"]
    meta_bits: List[str] = []
    if src:
        meta_bits.append(_html_escape(str(src)))
    if when:
        meta_bits.append(_html_escape(str(when)))
    if meta_bits:
        lines.append("   " + " · ".join(meta_bits))
    if summ:
        lines.append("   " + _html_escape(str(summ)))
    return "\n".join(lines)

def _format_list_payload(items: List[Dict[str, Any]], topic_label: str) -> str:
    if not items:
        return f"🗞️ <b>ไม่พบข่าวในหัวข้อ</b> <code>{_html_escape(topic_label)}</code> ครับ"

    header = f"🗞️ <b>สรุปข่าวล่าสุด</b> — <code>{_html_escape(topic_label)}</code>\n"
    body_lines: List[str] = []
    for it in items:
        try:
            body_lines.append(_format_article_item(it))
        except Exception:
            # Fallback: dump key:value แบบสั้น
            kv = " ".join(f"<code>{_html_escape(str(k))}</code>={_html_escape(str(v))}" for k, v in list(it.items())[:6])
            body_lines.append(f"• {kv}")
    return header + "\n".join(body_lines)

def _to_item_list(payload: Any) -> List[Dict[str, Any]] | None:
    """
    พยายามแปลงผลลัพธ์ให้เป็น list[dict] ถ้าเป็นไปได้:
    - list[dict] → OK
    - dict{ 'items': list } → OK
    - อื่น ๆ → None
    """
    if isinstance(payload, list):
        # ยอมรับเฉพาะที่เป็น list ของ dict
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return None


# ===== Main Handler =====
def handle_news(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Parses the news topic from user text, fetches news via utils.news_utils.get_news, and sends.
    รองรับ:
    - /news
    - /news เศรษฐกิจไทย
    - /news AI 5   (จำกัดจำนวนข่าว 5 ชิ้น)
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        # 1) วิเคราะห์ topic + limit
        topic, limit = _parse_topic_and_limit(user_text)

        # 2) แจ้งสถานะกำลังค้นหา
        send_typing_action(chat_id, "typing")
        send_message(chat_id, f"🔎 กำลังค้นหาข่าวในหัวข้อ <code>{_html_escape(topic)}</code> สักครู่ครับ…", parse_mode="HTML")

        # 3) เรียก utility — รองรับทั้ง signature ใหม่/เก่า
        try:
            data = get_news(topic, limit=limit)  # type: ignore[arg-type]
        except TypeError:
            # ถ้าเวอร์ชันเดิมรับแค่ topic
            data = get_news(topic)

        # 4) ฟอร์แมตผลลัพธ์
        # 4.1 ถ้าเป็น list/dict (รายการข่าว)
        items = _to_item_list(data)
        if items is not None:
            # จำกัดจำนวนเพื่อกันยาวเกิน (เผื่อ util ส่งมาเยอะ)
            items = items[:max(1, min(limit, 12))]
            msg = _format_list_payload(items, topic_label=topic)
            send_message(chat_id, msg, parse_mode="HTML")
            return

        # 4.2 ถ้าเป็นข้อความ
        if isinstance(data, str):
            s = data.strip()
            if not s:
                send_message(chat_id, "ขออภัยครับ ไม่พบข่าวในขณะนี้", parse_mode="HTML")
                return
            if _looks_html(s):
                send_message(chat_id, s, parse_mode="HTML")
            else:
                send_message(
                    chat_id,
                    f"🗞️ <b>สรุปข่าวล่าสุด</b> — <code>{_html_escape(topic)}</code>\n\n{_html_escape(s)}",
                    parse_mode="HTML",
                )
            return

        # 4.3 ไม่เข้าเคสที่รู้จัก
        send_message(chat_id, "ขออภัยครับ ไม่พบข่าวที่จะแสดงในขณะนี้", parse_mode="HTML")

    except Exception as e:
        print(f"[handle_news] ERROR: {e}")
        send_message(chat_id, f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการค้นหาข่าวครับ", parse_mode="HTML")
