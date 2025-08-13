# -*- coding: utf-8 -*-
"""
Persistent Memory Store using SQLite
- Stores a permanent profile for each user.
- Stores conversation history for each user.
- Handles context retrieval and history pruning.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import os
import sqlite3
import datetime

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
DB_PATH = os.path.join(DATA_DIR, 'bot_memory.db')
MAX_HISTORY_ITEMS = int(os.getenv("MEMORY_MAX_HISTORY_ITEMS", "40"))
KEEP_TAIL_AFTER_SUM = int(os.getenv("MEMORY_KEEP_TAIL_AFTER_SUM", "8"))
CTX_MAX_ITEMS = int(os.getenv("MEMORY_CTX_MAX_ITEMS", "12"))
CTX_MAX_CHARS = int(os.getenv("MEMORY_CTX_MAX_CHARS", "6000"))

# สร้างโฟลเดอร์ data ถ้ายังไม่มี
os.makedirs(DATA_DIR, exist_ok=True)

# --- Private Helper Functions ---

def _get_db_connection() -> sqlite3.Connection:
    """สร้างการเชื่อมต่อกับฐานข้อมูล SQLite"""
    conn = sqlite3.connect(DB_PATH)
    # ทำให้ผลลัพธ์จากการ query เป็น dictionary เพื่อให้ใช้ง่าย
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialization ---

def init_db():
    """
    ฟังก์ชันสำหรับสร้างฐานข้อมูลและตารางที่จำเป็นทั้งหมด ถ้ายังไม่มี
    จะถูกเรียกใช้แค่ครั้งเดียวตอนที่บอทเริ่มทำงาน
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. สร้างตาราง 'users' สำหรับเก็บโปรไฟล์ถาวร
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    summary TEXT DEFAULT ''
                )
            """)

            # 2. สร้างตาราง 'messages' สำหรับเก็บประวัติการสนทนา
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # 3. สร้าง Index เพื่อเพิ่มความเร็วในการค้นหา
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id_timestamp ON messages (user_id, timestamp);")

            conn.commit()
            print("[Memory] Database initialized successfully. Tables 'users' and 'messages' are ready.")

    except sqlite3.Error as e:
        print(f"[Memory] Database error during initialization: {e}")

# --- Public API Functions ---

def get_or_create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    ฟังก์ชันหัวใจหลัก: ตรวจสอบโปรไฟล์ผู้ใช้, สร้างใหม่ถ้าไม่มี, หรืออัปเดตถ้ามีอยู่แล้ว
    user_data คือ object ที่ได้จาก Telegram (update.effective_user)
    """
    user_id = user_data.id
    first_name = user_data.first_name
    last_name = user_data.last_name
    username = user_data.username
    now_iso = datetime.datetime.now().isoformat()
    
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user is None:
                # กรณีเป็นผู้ใช้ใหม่: สร้างโปรไฟล์
                print(f"[Memory] New user detected: {first_name} (ID: {user_id})")
                cursor.execute("""
                    INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, first_name, last_name, username, now_iso, now_iso, ''))
                status = "new_user"
            else:
                # กรณีเป็นผู้ใช้เก่า: อัปเดตข้อมูลล่าสุด
                print(f"[Memory] Returning user: {user['first_name']} (ID: {user['user_id']})")
                cursor.execute("""
                    UPDATE users SET last_seen = ?, first_name = ?, last_name = ?, username = ?
                    WHERE user_id = ?
                """, (now_iso, first_name, last_name, username, user_id))
                status = "returning_user"
            
            conn.commit()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            updated_user_profile = dict(cursor.fetchone())

            return {"status": status, "profile": updated_user_profile}

    except sqlite3.Error as e:
        print(f"[Memory] Database error in get_or_create_user: {e}")
        return None

def append_message(user_id: int, role: str, content: str) -> None:
    """เพิ่มข้อความใหม่ลงในประวัติการสนทนาของผู้ใช้"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            timestamp = int(datetime.datetime.now().timestamp())
            cursor.execute(
                "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, role, (content or "").strip(), timestamp)
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Memory] Failed to append message for user {user_id}: {e}")

def get_summary(user_id: int) -> str:
    """ดึงข้อมูลสรุป (summary) ของผู้ใช้"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT summary FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result['summary'] if result else ""
    except sqlite3.Error as e:
        print(f"[Memory] Failed to get summary for user {user_id}: {e}")
        return ""

def set_summary(user_id: int, summary: str) -> None:
    """ตั้งค่าข้อมูลสรุป (summary) ของผู้ใช้"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET summary = ? WHERE user_id = ?", ((summary or "").strip(), user_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Memory] Failed to set summary for user {user_id}: {e}")

def get_recent_context(user_id: int, max_items: int = CTX_MAX_ITEMS, max_chars: int = CTX_MAX_CHARS) -> List[Dict[str, str]]:
    """ดึงประวัติการสนทนาล่าสุดเพื่อใช้เป็น context"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, max_items)
            )
            msgs = cursor.fetchall()

            out: List[Dict[str, str]] = []
            total_chars = 0
            for m in msgs:
                content = m["content"]
                total_chars += len(content)
                if total_chars > max_chars:
                    break
                out.append({"role": m["role"], "content": content})
            return list(reversed(out))
    except sqlite3.Error as e:
        print(f"[Memory] Failed to get recent context for user {user_id}: {e}")
        return []

def prune_and_maybe_summarize(user_id: int, summarize_func: Callable[[str], str]) -> None:
    """
    หากประวัติการสนทนายาวเกินไป จะทำการสรุปส่วนเก่าและเก็บไว้เฉพาะส่วนล่าสุด
    """
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,))
            msg_count = cursor.fetchone()[0]

            if msg_count <= MAX_HISTORY_ITEMS:
                return

            print(f"[Memory] User {user_id} has {msg_count} messages, pruning...")

            # 1. ดึงข้อความส่วนที่จะสรุป (ส่วนที่เก่าที่สุด)
            limit = msg_count - KEEP_TAIL_AFTER_SUM
            cursor.execute(
                "SELECT role, content, message_id FROM messages WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
                (user_id, limit)
            )
            part_to_summarize = cursor.fetchall()
            
            if not part_to_summarize:
                return

            text_to_summarize = "\n".join(f"[{m['role']}] {m['content']}" for m in part_to_summarize)
            
            # 2. สร้าง summary ใหม่
            previous_summary = get_summary(user_id)
            prompt_for_summary = (
                f"{('[สรุปเดิม] ' + previous_summary) if previous_summary else ''}\n"
                f"[เนื้อหาใหม่ที่จะสรุปต่อ] {text_to_summarize}"
            )
            new_summary = summarize_func(prompt_for_summary)
            set_summary(user_id, new_summary)
            
            # 3. ลบข้อความเก่าที่สรุปไปแล้วออกจากฐานข้อมูล
            ids_to_delete = tuple(m['message_id'] for m in part_to_summarize)
            # ใช้ 'IN' clause เพื่อลบหลายรายการพร้อมกัน
            cursor.execute(f"DELETE FROM messages WHERE message_id IN ({','.join('?' for _ in ids_to_delete)})", ids_to_delete)
            
            conn.commit()
            print(f"[Memory] User {user_id} pruned. New summary saved. {len(ids_to_delete)} messages deleted.")
            
    except sqlite3.Error as e:
        print(f"[Memory] Error during prune/summarize for user {user_id}: {e}")
