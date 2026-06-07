"""
viko/conversation.py

Conversation persistence using SQLite.
DB: ~/.viko/viko_memory.db

Tables:
  sessions   — one row per conversation session
  messages   — individual chat turns
  summaries  — LLM-generated session summaries (queryable)

All public operations are exposed via module-level convenience functions that
delegate to a module-level singleton (get_db()).
"""

import os
import sys
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent

DB_PATH: Path = _base_dir() / "memory" / "viko_memory.db"

RETENTION_DAYS: int = int(os.environ.get("VIKO_MEMORY_RETENTION_DAYS", "365"))
SUMMARY_RETENTION_DAYS: int = 730

# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------

class ConversationDB:
    """Thread-safe SQLite-backed conversation store."""

    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        self._cleanup_retention()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id            INTEGER PRIMARY KEY,
                    started_at    TEXT,
                    ended_at      TEXT,
                    summary       TEXT,
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY,
                    session_id INTEGER,
                    timestamp  TEXT,
                    role       TEXT,
                    content    TEXT
                );

                CREATE TABLE IF NOT EXISTS summaries (
                    id         INTEGER PRIMARY KEY,
                    session_id INTEGER,
                    created_at TEXT,
                    content    TEXT
                );
            """)
            self._conn.commit()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self) -> int:
        """Insert a new session row and return its id."""
        now = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO sessions (started_at) VALUES (?)",
                (now,),
            )
            self._conn.commit()
            return cur.lastrowid

    def end_session(self, session_id: int) -> None:
        """Mark session as ended and update message_count."""
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                """
                UPDATE sessions
                SET ended_at      = ?,
                    message_count = (
                        SELECT COUNT(*) FROM messages WHERE session_id = ?
                    )
                WHERE id = ?
                """,
                (now, session_id, session_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def save_message(self, session_id: int, role: str, content: str) -> int:
        """Insert a message row and return its id."""
        now = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO messages (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
                (session_id, now, role, content),
            )
            self._conn.commit()
            return cur.lastrowid

    def get_recent_messages(self, n: int = 20) -> list[dict]:
        """
        Return the last *n* messages across all sessions in chronological order
        (oldest first within the returned slice).
        """
        rows = self._conn.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (n,),
        ).fetchall()
        # rows are newest-first; reverse to get chronological order
        return [
            {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
            for row in reversed(rows)
        ]

    # ------------------------------------------------------------------
    # Summary management
    # ------------------------------------------------------------------

    def get_recent_summaries(self, n: int = 5) -> list[str]:
        """Return the *n* most recent summary strings, newest first."""
        rows = self._conn.execute(
            "SELECT content FROM summaries ORDER BY created_at DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [row["content"] for row in rows]

    def save_summary(self, session_id: int, content: str) -> None:
        """Insert into summaries and update sessions.summary."""
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO summaries (session_id, created_at, content) VALUES (?, ?, ?)",
                (session_id, now, content),
            )
            self._conn.execute(
                "UPDATE sessions SET summary = ? WHERE id = ?",
                (content, session_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Retention cleanup
    # ------------------------------------------------------------------

    def _cleanup_retention(self) -> None:
        """
        Delete messages older than RETENTION_DAYS.
        Delete summaries older than SUMMARY_RETENTION_DAYS.
        """
        msg_cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()
        sum_cutoff = (datetime.now() - timedelta(days=SUMMARY_RETENTION_DAYS)).isoformat()
        with self._lock:
            self._conn.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (msg_cutoff,),
            )
            self._conn.execute(
                "DELETE FROM summaries WHERE created_at < ?",
                (sum_cutoff,),
            )
            self._conn.commit()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_db_instance: ConversationDB | None = None
_db_lock = threading.Lock()


def get_db() -> ConversationDB:
    """Return the module-level ConversationDB singleton (lazy, thread-safe init)."""
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = ConversationDB()
    return _db_instance


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def start_session() -> int:
    return get_db().start_session()


def end_session(session_id: int) -> None:
    get_db().end_session(session_id)


def save_message(session_id: int, role: str, content: str) -> int:
    return get_db().save_message(session_id, role, content)


def get_recent_messages(n: int = 20) -> list[dict]:
    return get_db().get_recent_messages(n)


def get_recent_summaries(n: int = 5) -> list[str]:
    return get_db().get_recent_summaries(n)


def save_summary(session_id: int, content: str) -> None:
    get_db().save_summary(session_id, content)


# ---------------------------------------------------------------------------
# Background summarizer
# ---------------------------------------------------------------------------

def summarize_session_async(session_id: int, messages: list[dict]) -> None:
    """Run in a daemon thread. Calls the LLM client to summarize the session, saves result."""

    def _run() -> None:
        try:
            from viko.self_engineer.llm import generate_text
            if not messages:
                return
            convo_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in messages[-30:]
            )
            summary = generate_text(
                f"Summarize this conversation in 3-5 sentences. Focus on what was discussed, "
                f"decided, or accomplished. Be factual and concise.\n\nConversation:\n{convo_text}",
                system="You are a memory summarizer. Return a factual summary in 3-5 sentences.",
                max_tokens=300,
            )
            if summary and summary.strip():
                save_summary(session_id, summary.strip())
                print(f"[Conversation] Session {session_id} summarized.")
        except Exception as e:
            print(f"[Conversation] Summarize failed: {e}")

    threading.Thread(target=_run, daemon=True).start()
