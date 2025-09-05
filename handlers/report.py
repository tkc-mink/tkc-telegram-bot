# handlers/report.py
# -*- coding: utf-8 -*-
"""
Handler for generating system reports using utils.report_utils.get_system_report.
Stable + safe:
- ใช้ utils.message_utils (retry/auto-chunk/no-echo) และ typing action
- parse_mode=HTML พร้อม escape ทุกข้อความที่มาจากภายนอก
- รองรับผลลัพธ์ทั้ง str / dict / list[dict]
- ฟอร์แมตหัวข้อ/ช่วงเวลา/สรุปสถิติ/ตาราง key:value ให้สวยและอ่านง่าย
"""
from __future__ import annotations
from typing import Dict, Any, List, Iterable

from utils.message_utils import send_message, send_typing_action
from utils.report_utils import get_system_report  # ✅ เครื่องมือใหม่

# ===== Helpers =====
def _html_escape(s: str) -> str:
    s = s or ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _first_present(d: Dict[str, Any], keys: Iterable[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None

def _fmt_kv_block(d: Dict[str, Any], allow_keys: Iterable[str] | None = None, title: str | None = None) -> str:
    """
    แสดง key:value เป็นบล็อกอ่านง่าย
    - ถ้าระบุ allow_keys จะเรียงตามนั้นและแสดงเฉพาะคีย์ที่มีจริง
    - ถ้าไม่ระบุ จะ dump ทุกคีย์ที่ค่ามีความหมาย
    """
    lines: List[str] = []
    if title:
        lines.append(f"<b>{_html_escape(title)}</b>")
    if allow_keys:
        for k in allow_keys:
            if k in d and d[k] not in (None, ""):
                lines.append(f"• <code>{_html_escape(str(k))}</code>: {_html_escape(str(d[k]))}")
    else:
        for k, v in d.items():
            if v not in (None, ""):
                lines.append(f"• <code>{_html_escape(str(k))}</code>: {_html_escape(str(v))}")
    return "\n".join(lines) if lines else ""

def _fmt_list_of_dicts(items: List[Dict[str, Any]], title: str) -> str:
    """
    แสดง list ของ dict เป็นหัวข้อย่อยทีละรายการ:
    • #1 key1=val1 · key2=val2 ...
    """
    if not items:
        return ""
    lines = [f"<b>{_html_escape(title)}</b>"]
    for i, it in enumerate(items, start=1):
        # เอา key สำคัญขึ้นก่อนถ้ามี
        primary = []
        for k in ("name", "user", "command", "keyword", "title"):
            if k in it and it[k] not in (None, ""):
                primary.append(f"{_html_escape(str(it[k]))}")
        head = " / ".join(primary) if primary else None

        # ส่วนรายละเอียดที่เหลือ
        kvs = []
        for k, v in it.items():
            if k in ("name", "user", "command", "keyword", "title"):
                continue
            if v in (None, ""):
                continue
            kvs.append(f"<code>{_html_escape(str(k))}</code>=<_>{_html_escape(str(v))}</_>")

        # แท็ก <_> เป็นตัวช่วยกัน “=” ใน value; แล้วค่อยแทนกลับ
        meta = " · ".join(kvs).replace("=<_>", "= ").replace("</_>", "")
        if head and meta:
            lines.append(f"• #{i} <b>{head}</b> — {meta}")
        elif head:
            lines.append(f"• #{i} <b>{head}</b>")
        else:
            # ไม่มีคีย์เด่นเลย → dump สั้น ๆ
            short = " · ".join(kvs[:6]).replace("=<_>", "= ").replace("</_>", "")
            lines.append(f"• #{i} {short}" if short else f"• #{i}")
    return "\n".join(lines)

def _format_report_dict(d: Dict[str, Any]) -> str:
    """
    ฟอร์แมตรายงานจาก dict แบบยืดหยุ่น:
    รองรับคีย์ยอมรับได้ เช่น:
    - title / report_title
    - since / start / period_start
    - until / end / period_end
    - generated_at / generated / as_of
    - summary / stats (dict)
    - top_commands / top_users / errors / notes / items (list[dict] หรือ list[str])
    """
    if not d:
        return "⚠️ ไม่พบข้อมูลรายงาน"

    title = _first_present(d, ("title", "report_title")) or "รายงานระบบ"
    since = _first_present(d, ("since", "start", "period_start"))
    until = _first_present(d, ("until", "end", "period_end"))
    genat = _first_present(d, ("generated_at", "generated", "as_of"))

    header_lines: List[str] = [f"📊 <b>{_html_escape(str(title))}</b>"]
    period_bits = []
    if since: period_bits.append(f"ตั้งแต่ <code>{_html_escape(str(since))}</code>")
    if until: period_bits.append(f"ถึง <code>{_html_escape(str(until))}</code>")
    if period_bits:
        header_lines.append("🗓️ " + " — ".join(period_bits))
    if genat:
        header_lines.append(f"🕒 สร้างเมื่อ: <code>{_html_escape(str(genat))}</code>")

    # Summary/Stats
    blocks: List[str] = []
    summary = _first_present(d, ("summary", "stats", "metrics"))
    if isinstance(summary, dict):
        blocks.append(_fmt_kv_block(
            summary,
            allow_keys=("total_messages", "total_users", "active_users", "images", "tokens", "success_rate", "errors", "latency_avg_ms"),
            title="สรุปตัวเลขสำคัญ",
        ))

    # รายการยอดนิยม / ข้อผิดพลาด / บันทึก
    for key, label in (
        ("top_commands", "คำสั่งที่ถูกใช้บ่อย"),
        ("top_users", "ผู้ใช้ที่ใช้งานมากสุด"),
        ("errors", "เหตุการณ์ผิดพลาดที่น่าสนใจ"),
        ("items", "รายละเอียดรายการ"),
        ("notes", "บันทึกเพิ่มเติม"),
    ):
        val = d.get(key)
        if isinstance(val, list) and val and isinstance(val[0], dict):
            blocks.append(_fmt_list_of_dicts(val, label))
        elif isinstance(val, list) and val:
            # เป็นลิสต์สตริง
            safe = "\n".join(f"• {_html_escape(str(x))}" for x in val)
            blocks.append(f"<b>{label}</b>\n{safe}")
        elif isinstance(val, dict):
            blocks.append(_fmt_kv_block(val, title=label))

    # อื่น ๆ ที่ยังเหลือ
    leftovers = {k: v for k, v in d.items() if k not in {
        "title", "report_title", "since", "start", "period_start", "until", "end", "period_end",
        "generated_at", "generated", "as_of", "summary", "stats", "metrics",
        "top_commands", "top_users", "errors", "items", "notes"
    } and v not in (None, "")}
    if leftovers:
        blocks.append(_fmt_kv_block(leftovers, title="ข้อมูลอื่น ๆ"))

    body = "\n\n".join(b for b in blocks if b)
    return "\n".join(header_lines) + ("\n\n" + body if body else "")

def _format_report_payload(payload: Any) -> str:
    # dict
    if isinstance(payload, dict):
        return _format_report_dict(payload)
    # list[dict]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        # รวมเป็นรายการย่อยภายใต้หัวข้อเดียว
        return _fmt_list_of_dicts(payload, "รายการในรายงาน")
    # str
    if isinstance(payload, str):
        s = payload.strip()
        return s if s else "⚠️ ไม่พบข้อมูลรายงาน"
    # unknown
    return "⚠️ ไม่พบข้อมูลรายงาน"

# ===== Main Handler =====
def handle_report(user_info: Dict[str, Any], user_text: str) -> None:
    """
    Handles /report (สรุประบบแบบคร่าว ๆ จาก report_utils)
    - แสดง typing action ระหว่างรวบรวมข้อมูล
    - รองรับผลลัพธ์หลายรูปแบบ และฟอร์แมตเป็น HTML ที่อ่านง่าย
    """
    chat_id = user_info["profile"]["user_id"]
    user_name = user_info["profile"].get("first_name") or ""

    try:
        # แจ้งสถานะกำลังรวบรวมข้อมูล
        send_typing_action(chat_id, "typing")
        send_message(chat_id, "🔎 กำลังรวบรวมข้อมูลเพื่อสร้างรายงานสักครู่ครับ…", parse_mode="HTML")

        # เรียก utility (ปล่อยให้ util ตัดสินใจช่วงเวลาเอง เช่น วันนี้/ล่าสุด)
        data = get_system_report()

        # ฟอร์แมตและส่งกลับ (wrapper จะจัดการแบ่ง ≤4096 อัตโนมัติ)
        msg = _format_report_payload(data)
        send_message(chat_id, msg, parse_mode="HTML")

    except Exception as e:
        print(f"[handle_report] ERROR: {e}")
        send_message(
            chat_id,
            f"❌ ขออภัยครับคุณ {_html_escape(user_name)}, เกิดข้อผิดพลาดในการสร้างรายงานครับ",
            parse_mode="HTML",
        )
