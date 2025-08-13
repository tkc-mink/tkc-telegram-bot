# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Persistent Memory Store using SQLite (Final Version)
- Stores permanent profiles for users (including location).
- Stores conversation history.
- Stores user reviews.
- Stores user favorites.
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

# --- Private Helper Functions ---

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

# --- Initialization ---

def init_db():
    """Initializes the database and creates/upgrades all necessary tables."""
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()

            # Table 1: Users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT,
                    username TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                    summary TEXT DEFAULT '', latitude REAL, longitude REAL
                )
            """)
            _add_column_if_not_exists(cursor, 'users', 'latitude', 'REAL')
            _add_column_if_not_exists(cursor, 'users', 'longitude', 'REAL')

            # Table 2: Messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, timestamp INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id_timestamp ON messages (user_id, timestamp);")

            # ✅ Table 3: Reviews
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL, comment TEXT, timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # ✅ Table 4: Favorites
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    favorite_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    content TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
            print("[Memory] Database initialized successfully (Final Version with all features).")
    except sqlite3.Error as e:
        print(f"[Memory] Database error during initialization: {e}")

# --- User Profile & Location Functions ---

def get_or_create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # (โค้ดส่วนนี้เหมือนเดิม)
    user_id, first_name, last_name, username = user_data.id, user_data.first_name, user_data.last_name, user_data.username
    now_iso = datetime.datetime.now().isoformat()
    try:
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if user is None:
                cursor.execute("INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?)",
                               (user_id, first_name, last_name, username, now_iso, now_iso))
                status = "new_user"
            else:
                cursor.execute("UPDATE users SET last_seen = ?, first_name = ?, last_name = ?, username = ? WHERE user_id = ?",
                               (now_iso, first_name, last_name, username, user_id))
                status = "returning_user"
            conn.commit()
            updated_user_profile = dict(cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())
            return {"status": status, "profile": updated_user_profile}
    except sqlite3.Error as e:
        print(f"[Memory] DB error in get_or_create_user: {e}")
        return None

def update_user_location(user_id: int, lat: float, lon: float) -> bool:
    # (โค้ดส่วนนี้เหมือนเดิม)
    try:
        with _get_db_connection() as conn:
            conn.execute("UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?", (lat, lon, user_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] DB error updating location: {e}")
        return False

# --- Chat History & Summary Functions ---

def append_message(user_id: int, role: str, content: str) -> None:
    # (โค้ดส่วนนี้เหมือนเดิม)
    try:
        with _get_db_connection() as conn:
            ts = int(datetime.datetime.now().timestamp())
            conn.execute("INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (user_id, role, (content or "").strip(), ts))
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Memory] DB error appending message: {e}")

# (ฟังก์ชัน get_summary, set_summary, get_recent_context, prune_and_maybe_summarize ให้คงไว้เหมือนเดิม)

# --- ✅ Review Functions ---

def add_review(user_id: int, rating: int, comment: Optional[str] = None) -> bool:
    """Adds a new review to the database."""
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            conn.execute("INSERT INTO reviews (user_id, rating, comment, timestamp) VALUES (?, ?, ?, ?)",
                           (user_id, rating, comment, now_iso))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] DB error adding review: {e}")
        return False

def get_last_review_timestamp(user_id: int) -> Optional[str]:
    """Gets the timestamp of the last review from a user."""
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT timestamp FROM reviews WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,)).fetchone()
            return res['timestamp'] if res else None
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting last review ts: {e}")
        return None

# --- ✅ Favorite Functions ---

def add_favorite(user_id: int, content: str) -> bool:
    """Adds a new favorite item to the database."""
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            conn.execute("INSERT INTO favorites (user_id, content, timestamp) VALUES (?, ?, ?)",
                           (user_id, content, now_iso))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] DB error adding favorite: {e}")
        return False

def get_favorites_by_user(user_id: int, limit: int = 10) -> List[Dict]:
    """Gets a list of favorite items for a user."""
    try:
        with _get_db_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT favorite_id, content FROM favorites WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()]
    except sqlite3.Error:
        return []

def remove_favorite_by_id(favorite_id: int, user_id: int) -> bool:
    """Removes a favorite item by its ID, ensuring user ownership."""
    try:
        with _get_db_connection() as conn:
            res = conn.execute("DELETE FROM favorites WHERE favorite_id = ? AND user_id = ?", (favorite_id, user_id))
            conn.commit()
            return res.rowcount > 0
    except sqlite3.Error:
        return False
