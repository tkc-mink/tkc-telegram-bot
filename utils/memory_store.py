# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Persistent Memory Store using SQLite (Version 2)
- Stores a permanent profile for each user, including last known location.
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

os.makedirs(DATA_DIR, exist_ok=True)

def _get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def _add_column_if_not_exists(cursor: sqlite3.Cursor, table: str, column: str, col_type: str):
    """Helper function to add a column to a table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row['name'] for row in cursor.fetchall()]
    if column not in columns:
        print(f"[Memory] Upgrading table '{table}', adding column '{column}'...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

def init_db():
    """Initializes the database and creates/upgrades tables."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. สร้างตาราง 'users' พร้อมคอลัมน์พื้นฐาน
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
            
            # ✅ **ส่วนที่อัปเกรด:** เพิ่มคอลัมน์สำหรับเก็บ Location อย่างปลอดภัย
            _add_column_if_not_exists(cursor, 'users', 'latitude', 'REAL')
            _add_column_if_not_exists(cursor, 'users', 'longitude', 'REAL')

            # 2. สร้างตาราง 'messages' (เหมือนเดิม)
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id_timestamp ON messages (user_id, timestamp);")
            
            conn.commit()
            print("[Memory] Database initialized successfully (v2 with location support).")
    except sqlite3.Error as e:
        print(f"[Memory] Database error during initialization: {e}")

def get_or_create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Gets a user profile from the DB or creates one if it doesn't exist."""
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
                # New user
                print(f"[Memory] New user detected: {first_name} (ID: {user_id})")
                cursor.execute(
                    "INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, first_name, last_name, username, now_iso, now_iso)
                )
                status = "new_user"
            else:
                # Returning user
                print(f"[Memory] Returning user: {user['first_name']} (ID: {user['user_id']})")
                cursor.execute(
                    "UPDATE users SET last_seen = ?, first_name = ?, last_name = ?, username = ? WHERE user_id = ?",
                    (now_iso, first_name, last_name, username, user_id)
                )
                status = "returning_user"
            
            conn.commit()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            updated_user_profile = dict(cursor.fetchone())

            return {"status": status, "profile": updated_user_profile}
    except sqlite3.Error as e:
        print(f"[Memory] Database error in get_or_create_user: {e}")
        return None

# --- ✅ ฟังก์ชันใหม่สำหรับจัดการ Location ---

def update_user_location(user_id: int, lat: float, lon: float) -> bool:
    """อัปเดตตำแหน่งล่าสุดของผู้ใช้ลงในฐานข้อมูล"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?", (lat, lon, user_id))
            conn.commit()
            print(f"[Memory] Updated location for user {user_id} to (Lat: {lat}, Lon: {lon})")
            return True
    except sqlite3.Error as e:
        print(f"[Memory] Failed to update location for user {user_id}: {e}")
        return False

def get_user_location(user_id: int) -> Optional[Dict[str, float]]:
    """ดึงตำแหน่งล่าสุดของผู้ใช้จากฐานข้อมูล"""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT latitude, longitude FROM users WHERE user_id = ?", (user_id,))
            loc = cursor.fetchone()
            if loc and loc['latitude'] is not None and loc['longitude'] is not None:
                return {"lat": loc['latitude'], "lon": loc['longitude']}
            return None
    except sqlite3.Error as e:
        print(f"[Memory] Failed to get location for user {user_id}: {e}")
        return None

# --- (ฟังก์ชันอื่นๆ ที่เหลือให้คงไว้เหมือนเดิม) ---
# append_message, get_summary, set_summary, get_recent_context, prune_and_maybe_summarize
# (เพื่อความกระชับ ผมขอละโค้ดส่วนนี้ แต่ในไฟล์จริงของคุณต้องมีอยู่นะครับ)
