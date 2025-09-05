# utils/report_utils.py
# -*- coding: utf-8 -*-
"""
Utility สร้างรายงานการใช้งานระบบจากฐานข้อมูล (เสถียร/พร้อมใช้งาน)
- ใช้ _get_db_connection() จาก utils.memory_store
- ตั้ง row_factory = sqlite3.Row เพื่ออ่านค่าแบบ dict ได้
- ครอบ try/fallback กรณี schema แตกต่าง (JOIN ไม่สำเร็จ → ใช้ fallback แบบไม่ JOIN)
- จัดรูปข้อความ Markdown ปลอดภัยกับ Telegram (Markdown v1)

Sections ที่รายงาน:
1) ผู้ใช้งานทั้งหมด / ผู้ใช้งานใน 7 วันที่ผ่านมา / จำนวนข้อความ 7 วัน / ค่าเฉลี่ยรีวิว 7 วัน
2) ผู้ใช้งานสูงสุด 5 อันดับ (ตามจำนวนข้อความ 7 วัน) — มี fallback ถ้าไม่มีตาราง users
3) รีวิวล่าสุด 5 รายการ — มี fallback ถ้าไม่มีตาราง users

ปรับช่วงวันได้ด้วย argument days (ดีฟอลต์ 7)
"""

from __future__ import annotations
from typing import Any, List, Tuple
import datetime
import sqlite3

# ✅ ใช้คอนเนคชันจาก memory_store
from utils.memory_store import _get_db_connection


# ---------- Helpers ----------
def _now_ts() -> int:
    return int(datetime.datetime.now().timestamp())

def _ts_days_ago(days: int) -> int:
    return int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())

def _fmt_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _fmt_float(v: Any, digits: int = 2) -> str:
    try:
        if v is None:
            return "-"
        return f"{float(v):.{digits}f}"
    except Exception:
        return "-"

def _stars(n: Any) -> str:
    try:
        i = max(0, min(5, int(n)))
        return "⭐" * i if i > 0 else "—"
    except Exception:
        return "—"


# ---------- Core builder ----------
def get_system_report(days: int = 7) -> str:
    """
    ดึงสถิติช่วง N วันล่าสุด (ดีฟอลต์ 7 วัน) และคืน string ที่พร้อมส่งใน Telegram (Markdown)
    """
    since_ts = _ts_days_ago(days)
    until_ts = _now_ts()
    range_text = (
        f"{datetime.datetime.fromtimestamp(since_ts).strftime('%Y-%m-%d')} "
        f"ถึง {datetime.datetime.fromtimestamp(until_ts).strftime('%Y-%m-%d')}"
    )

    try:
        with _get_db_connection() as conn:
            # ให้ดึงคอลัมน์ด้วยชื่อได้ (row["col"])
            try:
                conn.row_factory = sqlite3.Row
            except Exception:
                pass
            cur = conn.cursor()

            # ---------- 1) Users / Messages / Avg rating ----------
            total_users = 0
            try:
                cur.execute("SELECT COUNT(*) AS c FROM users")
                row = cur.fetchone()
                total_users = _fmt_int(row["c"] if row and "c" in row.keys() else (row[0] if row else 0), 0)
            except Exception:
                # ไม่มีตาราง users ก็ให้เป็น 0 ไป
                total_users = 0

            active_users_7d = 0
            try:
                cur.execute(
                    "SELECT COUNT(DISTINCT user_id) AS c FROM messages WHERE timestamp >= ?",
                    (since_ts,),
                )
                row = cur.fetchone()
                active_users_7d = _fmt_int(row["c"] if row and "c" in row.keys() else (row[0] if row else 0), 0)
            except Exception:
                active_users_7d = 0

            messages_7d = 0
            try:
                cur.execute(
                    "SELECT COUNT(*) AS c FROM messages WHERE timestamp >= ?",
                    (since_ts,),
                )
                row = cur.fetchone()
                messages_7d = _fmt_int(row["c"] if row and "c" in row.keys() else (row[0] if row else 0), 0)
            except Exception:
                messages_7d = 0

            avg_rating_7d = "-"
            try:
                cur.execute(
                    "SELECT AVG(rating) AS avg_r FROM reviews WHERE timestamp >= ?",
                    (since_ts,),
                )
                row = cur.fetchone()
                avg_rating_7d = _fmt_float(row["avg_r"] if row and "avg_r" in row.keys() else (row[0] if row else None), 2)
            except Exception:
                avg_rating_7d = "-"

            # ---------- 2) Top users (7 วัน) ----------
            top_users: List[sqlite3.Row] = []
            try:
                cur.execute(
                    """
                    SELECT u.first_name AS first_name,
                           COUNT(m.message_id) AS msg_count
                    FROM messages m
                    JOIN users u ON m.user_id = u.user_id
                    WHERE m.timestamp >= ?
                    GROUP BY m.user_id
                    ORDER BY msg_count DESC
                    LIMIT 5
                    """,
                    (since_ts,),
                )
                top_users = cur.fetchall() or []
            except Exception:
                # Fallback: ไม่มีตาราง users → ดึงเฉพาะ user_id ล้วน
                try:
                    cur.execute(
                        """
                        SELECT m.user_id AS user_id,
                               COUNT(m.message_id) AS msg_count
                        FROM messages m
                        WHERE m.timestamp >= ?
                        GROUP BY m.user_id
                        ORDER BY msg_count DESC
                        LIMIT 5
                        """,
                        (since_ts,),
                    )
                    rows = cur.fetchall() or []
                    # สร้างโครงสร้างให้คล้ายเดิม
                    top_users = []
                    for r in rows:
                        # จำลอง Row ด้วย dict (รองรับ row["first_name"])
                        first_name = f"UID {r['user_id']}" if isinstance(r, sqlite3.Row) else f"UID {r[0]}"
                        msg_count = (r["msg_count"] if isinstance(r, sqlite3.Row) else r[1])
                        top_users.append({"first_name": first_name, "msg_count": msg_count})  # type: ignore
                except Exception:
                    top_users = []

            # ---------- 3) Recent reviews ----------
            recent_reviews: List[sqlite3.Row] = []
            try:
                cur.execute(
                    """
                    SELECT u.first_name AS first_name,
                           r.rating       AS rating
                    FROM reviews r
                    JOIN users   u ON r.user_id = u.user_id
                    ORDER BY r.timestamp DESC
                    LIMIT 5
                    """
                )
                recent_reviews = cur.fetchall() or []
            except Exception:
                # Fallback: ไม่มี users → เอา user_id มาแสดงแทน
                try:
                    cur.execute(
                        """
                        SELECT user_id, rating
                        FROM reviews
                        ORDER BY timestamp DESC
                        LIMIT 5
                        """
                    )
                    rows = cur.fetchall() or []
                    recent_reviews = []
                    for r in rows:
                        if isinstance(r, sqlite3.Row):
                            recent_reviews.append({"first_name": f"UID {r['user_id']}", "rating": r["rating"]})  # type: ignore
                        else:
                            recent_reviews.append({"first_name": f"UID {r[0]}", "rating": r[1]})  # type: ignore
                except Exception:
                    recent_reviews = []

            # ---------- Compose Markdown ----------
            lines: List[str] = []
            lines.append("📊 **รายงานสรุปภาพรวมระบบ**")
            lines.append(f"_ช่วงข้อมูล_: {range_text}")
            lines.append("---------------------------------")
            lines.append(f"👥 **ผู้ใช้งานทั้งหมด:** {total_users} คน")
            lines.append(f"🟢 **ผู้ใช้งานใน {days} วันล่าสุด:** {active_users_7d} คน")
            lines.append(f"💬 **จำนวนข้อความ {days} วันล่าสุด:** {messages_7d} ข้อความ")
            lines.append(f"🌟 **ค่าเฉลี่ยรีวิว {days} วันล่าสุด:** {avg_rating_7d}")
            lines.append("---------------------------------")

            lines.append("🏆 **ผู้ใช้งานสูงสุด 5 อันดับ (ตามจำนวนข้อความในช่วง)**")
            if top_users:
                for i, row in enumerate(top_users, 1):
                    # รองรับทั้ง sqlite3.Row และ dict fallback
                    if isinstance(row, sqlite3.Row):
                        name = row["first_name"] if "first_name" in row.keys() else (row["user_id"] if "user_id" in row.keys() else "—")
                        cnt  = row["msg_count"] if "msg_count" in row.keys() else 0
                    else:
                        name = row.get("first_name") if isinstance(row, dict) else "—"  # type: ignore
                        cnt  = row.get("msg_count", 0) if isinstance(row, dict) else 0  # type: ignore
                    lines.append(f"{i}. คุณ {name} ({_fmt_int(cnt)} ข้อความ)")
            else:
                lines.append("- ไม่มีข้อมูล")
            lines.append("---------------------------------")

            lines.append("📝 **รีวิวล่าสุด 5 รายการ**")
            if recent_reviews:
                for r in recent_reviews:
                    if isinstance(r, sqlite3.Row):
                        name = r["first_name"] if "first_name" in r.keys() else (r["user_id"] if "user_id" in r.keys() else "—")
                        rating = r["rating"] if "rating" in r.keys() else None
                    else:
                        name = r.get("first_name", "—") if isinstance(r, dict) else "—"  # type: ignore
                        rating = r.get("rating") if isinstance(r, dict) else None      # type: ignore
                    lines.append(f"- {_stars(rating)} โดยคุณ {name}")
            else:
                lines.append("- ยังไม่มีรีวิว")

            return "\n".join(lines)

    except Exception as e:
        print(f"[Report_Utils] error: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดในการสร้างรายงานจากฐานข้อมูล"
