# utils/report_utils.py
# -*- coding: utf-8 -*-
"""
Utility for generating system usage reports by querying the persistent database.
This replaces the old file-based logging system.
"""
from __future__ import annotations
import datetime

# ✅ เราจะ import _get_db_connection โดยตรงเพื่อทำการ query ฐานข้อมูล
from utils.memory_store import _get_db_connection

def get_system_report() -> str:
    """
    Generates a comprehensive system report based on data from the last 7 days.
    """
    print("[Report_Utils] Generating system-wide report from database...")
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            # --- 1. สถิติผู้ใช้งานและข้อความ ---
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE timestamp >= ?", (int(seven_days_ago.timestamp()),))
            active_users_7d = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM messages WHERE timestamp >= ?", (int(seven_days_ago.timestamp()),))
            messages_7d = cursor.fetchone()[0]

            # --- 2. 5 รีวิวล่าสุด ---
            cursor.execute("""
                SELECT u.first_name, r.rating 
                FROM reviews r JOIN users u ON r.user_id = u.user_id 
                ORDER BY r.timestamp DESC LIMIT 5
            """)
            recent_reviews = cursor.fetchall()

            # --- 3. 5 ผู้ใช้ที่ใช้งานบ่อยที่สุดใน 7 วัน ---
            cursor.execute("""
                SELECT u.first_name, COUNT(m.message_id) as msg_count
                FROM messages m JOIN users u ON m.user_id = u.user_id
                WHERE m.timestamp >= ?
                GROUP BY m.user_id
                ORDER BY msg_count DESC
                LIMIT 5
            """, (int(seven_days_ago.timestamp()),))
            top_users = cursor.fetchall()
            
            # --- สร้างข้อความรายงาน ---
            report_lines = ["📊 **รายงานสรุปภาพรวมระบบ (7 วันล่าสุด)**"]
            report_lines.append("---------------------------------")
            
            report_lines.append(f"👥 **ผู้ใช้งานทั้งหมด:** {total_users} คน")
            report_lines.append(f" সক্রিয় **ผู้ใช้งานล่าสุด:** {active_users_7d} คน")
            report_lines.append(f"💬 **ข้อความทั้งหมด:** {messages_7d} ข้อความ")
            report_lines.append("---------------------------------")

            report_lines.append("🏆 **ผู้ใช้งานสูงสุด 5 อันดับ:**")
            if top_users:
                for i, user in enumerate(top_users, 1):
                    report_lines.append(f"{i}. คุณ {user['first_name']} ({user['msg_count']} ข้อความ)")
            else:
                report_lines.append("- ไม่มีข้อมูล")
            report_lines.append("---------------------------------")

            report_lines.append("🌟 **5 รีวิวล่าสุด:**")
            if recent_reviews:
                for review in recent_reviews:
                    rating_stars = "⭐" * review['rating']
                    report_lines.append(f"- {rating_stars} โดยคุณ {review['first_name']}")
            else:
                report_lines.append("- ยังไม่มีรีวิว")
            
            return "\n".join(report_lines)

    except Exception as e:
        print(f"[Report_Utils] An error occurred while generating the report: {e}")
        return "❌ ขออภัยครับ เกิดข้อผิดพลาดในการสร้างรายงานจากฐานข้อมูล"
