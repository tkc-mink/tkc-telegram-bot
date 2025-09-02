# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Persistent Memory Store using SQLite (Master Version)
- Stores permanent profiles for users (including location, status, and role).
- Stores conversation history, reviews, favorites, and FAQs.
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

def _add_column_if_not_exists(cursor: sqlite3.Cursor, table: str, column: str, col_type: str, default_val: str = "NULL"):
    """Helper function to add a column to a table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row['name'] for row in cursor.fetchall()]
    if column not in columns:
        print(f"[Memory] Upgrading table '{table}', adding column '{column}'...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default_val}")

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
            _add_column_if_not_exists(cursor, 'users', 'status', 'TEXT', "'pending'")
            _add_column_if_not_exists(cursor, 'users', 'role', 'TEXT', "'employee'")
            
            # Table 2: Messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, timestamp INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id_timestamp ON messages (user_id, timestamp);")
            
            # Table 3: Reviews
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL, comment TEXT, timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table 4: Favorites
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    favorite_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    content TEXT NOT NULL, timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Table 5: FAQ
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq (
                    faq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL UNIQUE,
                    answer TEXT NOT NULL,
                    added_by INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
            print("[Memory] Database initialized successfully (Master Version with all features).")
    except sqlite3.Error as e:
        print(f"[Memory] Database error during initialization: {e}")

# --- User Profile, Status & Location Functions ---

def get_or_create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Gets a user profile from the DB or creates one with 'pending' status."""
    try:
        user_id = user_data['id']
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        username = user_data.get('username', '')
        now_iso = datetime.datetime.now().isoformat()
        
        with _get_db_connection() as conn:
            cursor = conn.cursor()
            user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if user is None:
                cursor.execute(
                    "INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen, status, role) VALUES (?, ?, ?, ?, ?, ?, 'pending', 'employee')",
                    (user_id, first_name, last_name, username, now_iso, now_iso)
                )
                status = "new_user_pending"
            else:
                cursor.execute("UPDATE users SET last_seen = ?, first_name = ?, last_name = ?, username = ? WHERE user_id = ?",
                               (now_iso, first_name, last_name, username, user_id))
                status = "returning_user"
            conn.commit()
            updated_user_profile = dict(cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())
            return {"status": status, "profile": updated_user_profile}
    except KeyError as e:
        print(f"[Memory] Key error processing user_data: {e}. Data received: {user_data}")
        return None
    except sqlite3.Error as e:
        print(f"[Memory] DB error in get_or_create_user: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a user's full profile by their ID."""
    try:
        with _get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(user) if user else None
    except sqlite3.Error:
        return None

def get_all_users() -> List[Dict]:
    """Retrieves a list of all users with key information."""
    try:
        with _get_db_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT user_id, first_name, username, status, role FROM users ORDER BY first_seen DESC").fetchall()]
    except sqlite3.Error:
        return []

def update_user_status(user_id: int, status: str) -> bool:
    """Updates a user's status (e.g., 'approved', 'removed')."""
    try:
        with _get_db_connection() as conn:
            res = conn.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            conn.commit()
            return res.rowcount > 0
    except sqlite3.Error:
        return False

def update_user_location(user_id: int, lat: float, lon: float) -> bool:
    try:
        with _get_db_connection() as conn:
            conn.execute("UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?", (lat, lon, user_id))
            conn.commit()
            return True
    except sqlite3.Error:
        return False

# --- Chat History & Context Functions ---

def append_message(user_id: int, role: str, content: str) -> None:
    try:
        with _get_db_connection() as conn:
            ts = int(datetime.datetime.now().timestamp())
            conn.execute("INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (user_id, role, (content or "").strip(), ts))
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Memory] DB error appending message: {e}")

def get_recent_context(user_id: int, max_items: int = CTX_MAX_ITEMS, max_chars: int = CTX_MAX_CHARS) -> List[Dict[str, str]]:
    try:
        with _get_db_connection() as conn:
            msgs = conn.execute("SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, max_items)).fetchall()
            out, total_chars = [], 0
            for m in msgs:
                content = m["content"]
                total_chars += len(content)
                if total_chars > max_chars: break
                out.append({"role": m["role"], "content": content})
            return list(reversed(out))
    except sqlite3.Error:
        return []

def get_user_chat_history(user_id: int, limit: int = 10) -> List[Dict]:
    try:
        with _get_db_connection() as conn:
            history = []
            for row in conn.execute("SELECT role, content, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)).fetchall():
                row_dict = dict(row)
                row_dict['timestamp'] = datetime.datetime.fromtimestamp(row_dict['timestamp']).isoformat()
                history.append(row_dict)
            return history
    except sqlite3.Error:
        return []

# --- Summarization Functions ---

def get_summary(user_id: int) -> str:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT summary FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return res['summary'] if res else ""
    except sqlite3.Error:
        return ""

def set_summary(user_id: int, summary: str) -> None:
    try:
        with _get_db_connection() as conn:
            conn.execute("UPDATE users SET summary = ? WHERE user_id = ?", ((summary or "").strip(), user_id))
            conn.commit()
    except sqlite3.Error:
        pass

def prune_and_maybe_summarize(user_id: int, summarize_func: Callable[[str], str]) -> None:
    try:
        with _get_db_connection() as conn:
            msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)).fetchone()[0]
            if msg_count <= MAX_HISTORY_ITEMS: return
            limit = msg_count - KEEP_TAIL_AFTER_SUM
            part_to_summarize = conn.execute("SELECT role, content, message_id FROM messages WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?", (user_id, limit)).fetchall()
            if not part_to_summarize: return
            text_to_summarize = "\n".join(f"[{m['role']}] {m['content']}" for m in part_to_summarize)
            previous_summary = get_summary(user_id)
            prompt = f"{('[สรุปเดิม] ' + previous_summary) if previous_summary else ''}\n[เนื้อหาใหม่ที่จะสรุปต่อ] {text_to_summarize}"
            new_summary = summarize_func(prompt)
            set_summary(user_id, new_summary)
            ids_to_delete = tuple(m['message_id'] for m in part_to_summarize)
            conn.execute(f"DELETE FROM messages WHERE message_id IN ({','.join('?' for _ in ids_to_delete)})", ids_to_delete)
            conn.commit()
    except sqlite3.Error:
        pass

# --- Review Functions ---

def add_review(user_id: int, rating: int, comment: Optional[str] = None) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            conn.execute("INSERT INTO reviews (user_id, rating, comment, timestamp) VALUES (?, ?, ?, ?)", (user_id, rating, comment, now_iso))
            conn.commit()
            return True
    except sqlite3.Error:
        return False

def get_last_review_timestamp(user_id: int) -> Optional[str]:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT timestamp FROM reviews WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,)).fetchone()
            return res['timestamp'] if res else None
    except sqlite3.Error:
        return None

# --- Favorite Functions ---

def add_favorite(user_id: int, content: str) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            conn.execute("INSERT INTO favorites (user_id, content, timestamp) VALUES (?, ?, ?)", (user_id, content, now_iso))
            conn.commit()
            return True
    except sqlite3.Error:
        return False

def get_favorites_by_user(user_id: int, limit: int = 10) -> List[Dict]:
    try:
        with _get_db_connection() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT favorite_id, content FROM favorites WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit)
            ).fetchall()]
    except sqlite3.Error:
        return []

def remove_favorite_by_id(favorite_id: int, user_id: int) -> bool:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("DELETE FROM favorites WHERE favorite_id = ? AND user_id = ?", (favorite_id, user_id))
            conn.commit()
            return res.rowcount > 0
    except sqlite3.Error:
        return False

# --- FAQ Functions ---
def add_or_update_faq(keyword: str, answer: str, user_id: int) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            # Use INSERT ... ON CONFLICT to handle both add and update in one step
            conn.execute(
                """
                INSERT INTO faq (keyword, answer, added_by, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    answer = excluded.answer,
                    added_by = excluded.added_by,
                    timestamp = excluded.timestamp
                """,
                (keyword.lower(), answer, user_id, now_iso)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] DB error adding/updating FAQ: {e}")
        return False

def get_faq_answer(keyword: str) -> Optional[str]:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT answer FROM faq WHERE keyword = ?", (keyword.lower(),)).fetchone()
            return res['answer'] if res else None
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting FAQ answer: {e}")
        return None

def get_all_faqs() -> List[Dict]:
    try:
        with _get_db_connection() as conn:
            return [dict(row) for row in conn.execute("SELECT keyword, answer FROM faq ORDER BY keyword ASC").fetchall()]
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting all FAQs: {e}")
        return []
