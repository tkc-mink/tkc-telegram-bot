# utils/memory_store.py
# -*- coding: utf-8 -*-
"""
Persistent Memory Store using SQLite (Master Version, hardened+)
- โปรไฟล์ผู้ใช้ (สถานะ, role, location) + ประวัติสนทนา/สรุป
- รีวิว รายการโปรด FAQ ใบลา
- เสถียร: WAL, foreign_keys, busy_timeout, retry on locked, UPSERT users
- Backward-compatible กับโค้ดเดิมและ handler ที่มีอยู่
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable, Tuple
import os
import sqlite3
import datetime
import time
import math

# --------------------- Config ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DB_PATH = os.path.join(DATA_DIR, os.getenv("BOT_MEMORY_DB_FILE", "bot_memory.db"))

os.makedirs(DATA_DIR, exist_ok=True)

# Context / History caps
MAX_HISTORY_ITEMS   = int(os.getenv("MEMORY_MAX_HISTORY_ITEMS", "40"))
KEEP_TAIL_AFTER_SUM = int(os.getenv("MEMORY_KEEP_TAIL_AFTER_SUM", "8"))
CTX_MAX_ITEMS       = int(os.getenv("MEMORY_CTX_MAX_ITEMS", "12"))
CTX_MAX_CHARS       = int(os.getenv("MEMORY_CTX_MAX_CHARS", "6000"))
MAX_MESSAGE_CHARS   = int(os.getenv("MEMORY_MAX_MESSAGE_CHARS", "4000"))   # cap ต่อข้อความที่บันทึก
SUMMARIZE_MAX_CHARS = int(os.getenv("MEMORY_SUMMARIZE_MAX_CHARS", "12000"))

# allowed values
_ALLOWED_STATUS = {"pending", "approved", "removed"}
_ALLOWED_ROLES  = {"employee", "admin", "super_admin"}

# message roles สำหรับตาราง messages
_MSG_ROLES = {"user", "assistant", "system"}

# retry settings
SQLITE_LOCK_RETRY = int(os.getenv("SQLITE_LOCK_RETRY", "1"))
SQLITE_LOCK_SLEEP = float(os.getenv("SQLITE_LOCK_SLEEP", "0.15"))

def _parse_super_admin_ids() -> set[int]:
    """
    รองรับ:
      SUPER_ADMIN_IDS="604990227,123456789" (หรือ ;)
      SUPER_ADMIN_ID="604990227" (legacy)
    """
    ids: set[int] = set()
    env = (os.getenv("SUPER_ADMIN_IDS") or "").strip()
    if env:
        for tok in env.replace(";", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                ids.add(int(tok))
            except ValueError:
                pass
    legacy = os.getenv("SUPER_ADMIN_ID")
    if legacy:
        try:
            ids.add(int(legacy.strip()))
        except Exception:
            pass
    return ids

SUPER_ADMIN_IDS: set[int] = _parse_super_admin_ids()

# --------------------- DB helpers ---------------------

def _ts_now() -> int:
    return int(time.time())

def _norm_role(role: str) -> str:
    r = (role or "").strip().lower()
    return r if r in _MSG_ROLES else "user"

def _norm_text(s: str, max_len: int = MAX_MESSAGE_CHARS) -> str:
    if s is None:
        return ""
    s = str(s).replace("\x00", "")  # กัน null byte
    if len(s) > max_len:
        return s[:max_len]
    return s

def _execute_retry(conn: sqlite3.Connection, sql: str, params: Tuple | List | None = None):
    """
    เรียก execute พร้อม retry เบา ๆ เฉพาะกรณี database is locked
    """
    params = params or ()
    tries = SQLITE_LOCK_RETRY + 1
    for i in range(tries):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "locked" in msg and i < tries - 1:
                time.sleep(SQLITE_LOCK_SLEEP)
                continue
            raise

def _executemany_retry(conn: sqlite3.Connection, sql: str, seq_params: List[Tuple]):
    tries = SQLITE_LOCK_RETRY + 1
    for i in range(tries):
        try:
            return conn.executemany(sql, seq_params)
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "locked" in msg and i < tries - 1:
                time.sleep(SQLITE_LOCK_SLEEP)
                continue
            raise

def _get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with sane PRAGMAs for server use."""
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # concurrency / safety
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")  # milliseconds
    # เพิ่มเติมเล็กน้อยเพื่อประสิทธิภาพ (ไม่บังคับทุกเวอร์ชัน)
    try:
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA mmap_size=134217728;")  # 128MB ถ้ารองรับ
    except Exception:
        pass
    return conn

# ให้ app.py ใช้ใน /healthz
__all__ = [
    "_get_db_connection",
    "init_db",
    "get_or_create_user",
    "get_user_by_id",
    "get_all_users",
    "update_user_status",
    "set_user_status",
    "update_user_role",
    "update_user_location",
    "append_message",
    "get_recent_context",
    "get_user_chat_history",
    "get_summary",
    "set_summary",
    "prune_and_maybe_summarize",
    "add_review",
    "get_last_review_timestamp",
    "add_favorite",
    "get_favorites_by_user",
    "remove_favorite_by_id",
    "add_or_update_faq",
    "get_faq_answer",
    "get_all_faqs",
    "add_leave_request",
    "is_super_admin",
]

def _add_column_if_not_exists(cursor: sqlite3.Cursor, table: str, column: str, col_type: str, default_val: str = "NULL") -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row["name"] for row in cursor.fetchall()]
    if column not in columns:
        print(f"[Memory] Upgrading table '{table}', adding column '{column}'...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default_val}")

# --------------------- Initialization ---------------------

def init_db() -> None:
    """Create/upgrade schema; safe to call multiple times."""
    try:
        with _get_db_connection() as conn:
            c = conn.cursor()

            # Table: users
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id    INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name  TEXT,
                    username   TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen  TEXT NOT NULL,
                    summary    TEXT DEFAULT '',
                    latitude   REAL,
                    longitude  REAL
                )
                """
            )
            _add_column_if_not_exists(c, "users", "status", "TEXT", "'pending'")
            _add_column_if_not_exists(c, "users", "role", "TEXT", "'employee'")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users (status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users (last_seen)")

            # Backfill status/role ให้ถูกเซ็ต
            placeholders = ",".join("?" for _ in _ALLOWED_STATUS)
            c.execute(
                f"UPDATE users SET status='pending' WHERE status IS NULL OR status NOT IN ({placeholders})",
                tuple(_ALLOWED_STATUS),
            )
            placeholders_role = ",".join("?" for _ in _ALLOWED_ROLES)
            c.execute(
                f"UPDATE users SET role='employee' WHERE role IS NULL OR role NOT IN ({placeholders_role})",
                tuple(_ALLOWED_ROLES),
            )

            # Table: messages
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    timestamp  INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_time ON messages (user_id, timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)")

            # Table: reviews
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   INTEGER NOT NULL,
                    rating    INTEGER NOT NULL,
                    comment   TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews (user_id, timestamp)")

            # Table: favorites
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    favorite_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    content     TEXT NOT NULL,
                    timestamp   TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id, timestamp)")

            # Table: faq
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS faq (
                    faq_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword  TEXT NOT NULL UNIQUE,
                    answer   TEXT NOT NULL,
                    added_by INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_faq_keyword ON faq (keyword)")

            # Table: leave_requests
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS leave_requests (
                    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    leave_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date   TEXT NOT NULL,
                    reason     TEXT,
                    status     TEXT DEFAULT 'pending',
                    timestamp  TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_leave_user ON leave_requests (user_id, timestamp)")

            conn.commit()
            print("[Memory] Database initialized (WAL mode, indices, backfill ok).")
    except sqlite3.Error as e:
        print(f"[Memory] Database error during initialization: {e}")

# เรียก init_db เมื่อโมดูลถูกโหลด ( idempotent )
init_db()

# --------------------- User Profile / Status / Location ---------------------

def is_super_admin(user_id: int) -> bool:
    return int(user_id) in SUPER_ADMIN_IDS

def get_or_create_user(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    ดึงโปรไฟล์; ถ้าไม่มีจะสร้างใหม่
    - ผู้ใช้ใหม่ default: status='pending', role='employee'
    - ถ้าอยู่ใน SUPER_ADMIN_IDS: default status='approved', role='super_admin' (และ report เป็น returning_user)
    - ใช้ UPSERT ป้องกัน race
    """
    try:
        user_id    = int(user_data["id"])
        first_name = user_data.get("first_name", "") or ""
        last_name  = user_data.get("last_name", "") or ""
        username   = user_data.get("username", "") or ""
        now_iso    = datetime.datetime.now().isoformat()

        if is_super_admin(user_id):
            default_status = "approved"
            default_role   = "super_admin"
            status_report  = "returning_user"
        else:
            default_status = "pending"
            default_role   = "employee"
            status_report  = "new_user_pending"

        with _get_db_connection() as conn:
            # ถ้ายังไม่มี -> insert; ถ้ามี -> update เฉพาะ metadata
            _execute_retry(conn,
                """
                INSERT INTO users (user_id, first_name, last_name, username, first_seen, last_seen, status, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name =excluded.last_name,
                    username  =excluded.username,
                    last_seen =excluded.last_seen
                """,
                (user_id, first_name, last_name, username, now_iso, now_iso, default_status, default_role),
            )
            conn.commit()

            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            profile = dict(row) if row else None

        # ถ้าเป็นผู้ใช้เก่าอยู่แล้ว ให้ปรับ report เป็น returning_user
        if profile and profile.get("first_seen") != now_iso:
            status_report = "returning_user"

        return {"status": status_report, "profile": profile} if profile else None

    except KeyError as e:
        print(f"[Memory] Key error processing user_data: {e}. Data received: {user_data}")
        return None
    except sqlite3.Error as e:
        print(f"[Memory] DB error in get_or_create_user: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        with _get_db_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None

def get_all_users() -> List[Dict[str, Any]]:
    try:
        with _get_db_connection() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT user_id, first_name, username, status, role, first_seen, last_seen FROM users ORDER BY first_seen DESC"
                ).fetchall()
            ]
    except sqlite3.Error:
        return []

def update_user_status(user_id: int, status: str) -> bool:
    status = (status or "").strip().lower()
    if status not in _ALLOWED_STATUS:
        print(f"[Memory] Reject invalid status '{status}' for user {user_id}")
        return False
    try:
        with _get_db_connection() as conn:
            res = _execute_retry(conn, "UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
            conn.commit()
            return (res.rowcount if res else 0) > 0
    except sqlite3.Error:
        return False

# alias เดิม
def set_user_status(user_id: int, status: str) -> bool:
    return update_user_status(user_id, status)

def update_user_role(user_id: int, role: str) -> bool:
    role = (role or "").strip().lower()
    if role not in _ALLOWED_ROLES:
        print(f"[Memory] Reject invalid role '{role}' for user {user_id}")
        return False
    try:
        with _get_db_connection() as conn:
            res = _execute_retry(conn, "UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
            conn.commit()
            return (res.rowcount if res else 0) > 0
    except sqlite3.Error:
        return False

def update_user_location(user_id: int, lat: float, lon: float) -> bool:
    try:
        with _get_db_connection() as conn:
            _execute_retry(conn, "UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?", (lat, lon, user_id))
            conn.commit()
            return True
    except sqlite3.Error:
        return False

# --------------------- Chat History & Context ---------------------

def append_message(user_id: int, role: str, content: str) -> None:
    """
    บันทึกข้อความ โดย normalize role และ cap ความยาว content
    """
    try:
        with _get_db_connection() as conn:
            ts = _ts_now()
            _execute_retry(
                conn,
                "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, _norm_role(role), _norm_text(content), ts),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"[Memory] DB error appending message: {e}")

def get_recent_context(user_id: int, max_items: int = CTX_MAX_ITEMS, max_chars: int = CTX_MAX_CHARS) -> List[Dict[str, str]]:
    """
    คืนค่า messages ล่าสุด (role/content) สำหรับ LLM
    - จำกัดจำนวนชิ้น และจำนวนตัวอักษรรวม
    """
    try:
        with _get_db_connection() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, max_items),
            ).fetchall()
            out: List[Dict[str, str]] = []
            total = 0
            for r in rows:
                content = r["content"] or ""
                # รวมจากท้ายกลับไปต้น (เราดึง DESC)
                if total + len(content) > max_chars and out:
                    break
                out.append({"role": r["role"], "content": content})
                total += len(content)
            out.reverse()
            return out
    except sqlite3.Error:
        return []

def get_user_chat_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        with _get_db_connection() as conn:
            history: List[Dict[str, Any]] = []
            for row in conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            ).fetchall():
                d = dict(row)
                d["timestamp"] = datetime.datetime.fromtimestamp(d["timestamp"]).isoformat()
                history.append(d)
            return history
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting user chat history: {e}")
        return []

def count_messages(user_id: int) -> int:
    try:
        with _get_db_connection() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM messages WHERE user_id = ?", (user_id,)).fetchone()
            return int(row["c"]) if row else 0
    except sqlite3.Error:
        return 0

def delete_messages_by_ids(ids: List[int]) -> int:
    """
    ลบข้อความตาม message_id เป็นชุด (คืนจำนวนที่ลบได้)
    """
    if not ids:
        return 0
    try:
        with _get_db_connection() as conn:
            deleted = 0
            CHUNK = 500
            for i in range(0, len(ids), CHUNK):
                sub = ids[i:i+CHUNK]
                res = _execute_retry(conn, f"DELETE FROM messages WHERE message_id IN ({','.join('?' for _ in sub)})", tuple(sub))
                deleted += (res.rowcount if res else 0)
            conn.commit()
            return deleted
    except sqlite3.Error:
        return 0

# --------------------- Summarization ---------------------

def get_summary(user_id: int) -> str:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT summary FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return res["summary"] if res else ""
    except sqlite3.Error:
        return ""

def set_summary(user_id: int, summary: str) -> None:
    try:
        with _get_db_connection() as conn:
            _execute_retry(conn, "UPDATE users SET summary = ? WHERE user_id = ?", (_norm_text(summary, 20000), user_id))
            conn.commit()
    except sqlite3.Error:
        pass

def prune_and_maybe_summarize(user_id: int, summarize_func: Callable[[str], str]) -> None:
    """
    - ถ้าจำนวนข้อความเกิน MAX_HISTORY_ITEMS → รวบรวมส่วนต้น (เก่า) เพื่อสรุป
    - แนบสรุปเดิม + ข้อความใหม่ แล้วเรียก summarize_func
    - ลบข้อความเก่าที่ถูกสรุปออก เหลือท้ายไว้ KEEP_TAIL_AFTER_SUM
    - จำกัดขนาดอินพุตที่ส่งให้ summarize_func ด้วย SUMMARIZE_MAX_CHARS
    """
    try:
        with _get_db_connection() as conn:
            msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)).fetchone()[0]
            if msg_count <= MAX_HISTORY_ITEMS:
                return

            limit = msg_count - KEEP_TAIL_AFTER_SUM
            part = conn.execute(
                "SELECT role, content, message_id FROM messages WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            if not part:
                return

            # รวมข้อความที่จะสรุป + cap ขนาด
            text_parts: List[str] = []
            total = 0
            for m in part:
                seg = f"[{m['role']}] {m['content']}"
                if total + len(seg) > SUMMARIZE_MAX_CHARS and text_parts:
                    break
                text_parts.append(seg)
                total += len(seg)
            text = "\n".join(text_parts)

            prev = get_summary(user_id)
            header = f"[สรุปเดิม] {prev}\n" if prev else ""
            prompt = f"{header}[เนื้อหาใหม่ที่จะสรุปต่อ]\n{text}"

            # เรียกสรุป (กัน error)
            try:
                new_sum = summarize_func(prompt) or prev
            except Exception:
                new_sum = prev

            set_summary(user_id, new_sum)

            # ลบแบบ chunk กันชน 999 placeholders
            ids = [m["message_id"] for m in part]
            CHUNK = 500
            for i in range(0, len(ids), CHUNK):
                sub = ids[i : i + CHUNK]
                _execute_retry(conn, f"DELETE FROM messages WHERE message_id IN ({','.join('?' for _ in sub)})", tuple(sub))
            conn.commit()
    except sqlite3.Error:
        pass

# --------------------- Reviews ---------------------

def add_review(user_id: int, rating: int, comment: Optional[str] = None) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            _execute_retry(
                conn,
                "INSERT INTO reviews (user_id, rating, comment, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, int(rating), _norm_text(comment, 2000), now_iso),
            )
            conn.commit()
            return True
    except sqlite3.Error:
        return False

def get_last_review_timestamp(user_id: int) -> Optional[str]:
    try:
        with _get_db_connection() as conn:
            res = conn.execute(
                "SELECT timestamp FROM reviews WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user_id,)
            ).fetchone()
            return res["timestamp"] if res else None
    except sqlite3.Error:
        return None

# --------------------- Favorites ---------------------

def add_favorite(user_id: int, content: str) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            _execute_retry(
                conn,
                "INSERT INTO favorites (user_id, content, timestamp) VALUES (?, ?, ?)",
                (user_id, _norm_text(content, 4000), now_iso),
            )
            conn.commit()
            return True
    except sqlite3.Error:
        return False

def get_favorites_by_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        with _get_db_connection() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT favorite_id, content FROM favorites WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            ]
    except sqlite3.Error:
        return []

def remove_favorite_by_id(favorite_id: int, user_id: int) -> bool:
    try:
        with _get_db_connection() as conn:
            res = _execute_retry(
                conn,
                "DELETE FROM favorites WHERE favorite_id = ? AND user_id = ?",
                (favorite_id, user_id),
            )
            conn.commit()
            return (res.rowcount if res else 0) > 0
    except sqlite3.Error:
        return False

# --------------------- FAQ ---------------------

def add_or_update_faq(keyword: str, answer: str, user_id: int) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            _execute_retry(
                conn,
                """
                INSERT INTO faq (keyword, answer, added_by, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    answer    = excluded.answer,
                    added_by  = excluded.added_by,
                    timestamp = excluded.timestamp
                """,
                ((keyword or "").lower(), _norm_text(answer, 8000), user_id, now_iso),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] DB error adding/updating FAQ: {e}")
        return False

def get_faq_answer(keyword: str) -> Optional[str]:
    try:
        with _get_db_connection() as conn:
            res = conn.execute("SELECT answer FROM faq WHERE keyword = ?", ((keyword or "").lower(),)).fetchone()
            return res["answer"] if res else None
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting FAQ answer: {e}")
        return None

def get_all_faqs() -> List[Dict[str, Any]]:
    try:
        with _get_db_connection() as conn:
            return [
                dict(row)
                for row in conn.execute("SELECT keyword, answer FROM faq ORDER BY keyword ASC").fetchall()
            ]
    except sqlite3.Error as e:
        print(f"[Memory] DB error getting all FAQs: {e}")
        return []

# --------------------- Leave Requests ---------------------

def add_leave_request(user_id: int, leave_type: str, start_date: str, end_date: str, reason: str) -> bool:
    try:
        with _get_db_connection() as conn:
            now_iso = datetime.datetime.now().isoformat()
            _execute_retry(
                conn,
                """
                INSERT INTO leave_requests (user_id, leave_type, start_date, end_date, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, _norm_text(leave_type, 64), _norm_text(start_date, 32), _norm_text(end_date, 32), _norm_text(reason, 2000), now_iso),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"[Memory] Failed to add leave request for user {user_id}: {e}")
        return False
