"""
Conversation Memory System for WhatsApp Sales Agent
Handles user conversation history and context-aware responses.

Storage is SQLite (``data/agent.db`` by default). The previous implementation
rewrote a whole JSON file per message from an in-process cache, so two messages
from the same user arriving concurrently would each write the state they had
read, and one of them would be lost. Every write here is a single SQL statement
inside one transaction, and counters are incremented in SQL rather than in
Python, so concurrent writers cannot clobber each other.

The public interface (``get_or_create_session``, ``add_message``,
``get_conversation_context``, ``update_user_preferences``, ``add_user_interest``,
``get_user_summary``, ``cleanup_old_sessions``, ``get_all_users_summary``) is
unchanged. Existing JSON sessions are imported by
``scripts/migrate_json_to_sqlite.py``.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join("data", "agent.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    phone_number       TEXT PRIMARY KEY,
    name               TEXT,
    preferred_currency TEXT    NOT NULL DEFAULT 'USD',
    interests          TEXT    NOT NULL DEFAULT '[]',
    last_interaction   TEXT,
    total_interactions INTEGER NOT NULL DEFAULT 0,
    session_summary    TEXT,
    created_at         TEXT    NOT NULL,
    updated_at         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    timestamp    TEXT NOT NULL,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    metadata     TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (phone_number) REFERENCES users(phone_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_phone_id ON messages(phone_number, id);
"""

# Columns a caller is allowed to set through update_user_preferences().
_UPDATABLE_COLUMNS = {
    "name",
    "preferred_currency",
    "interests",
    "last_interaction",
    "total_interactions",
    "session_summary",
}


@dataclass
class ConversationMessage:
    """Single message in conversation"""
    timestamp: str
    role: str  # 'user' or 'assistant'
    content: str
    message_type: str = "text"  # text, currency_conversion, product_inquiry
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class UserProfile:
    """User profile and preferences"""
    phone_number: str
    name: Optional[str] = None
    preferred_currency: str = "USD"
    interests: List[str] = None
    last_interaction: Optional[str] = None
    total_interactions: int = 0

    def __post_init__(self):
        if self.interests is None:
            self.interests = []


@dataclass
class ConversationSession:
    """Complete conversation session for a user"""
    user_profile: UserProfile
    messages: List[ConversationMessage]
    session_summary: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


def _now() -> str:
    return datetime.now().isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection configured for concurrent writers."""
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db(db_path: str) -> None:
    """Create the schema if it does not exist. Safe to call repeatedly."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


class ConversationMemory:
    """Manages conversation memory and context, backed by SQLite."""

    def __init__(self, storage_dir: str = "data/conversations",
                 db_path: Optional[str] = None):
        # storage_dir is retained for backwards compatibility: it is the
        # location the JSON migration reads from, not a live write path.
        self.storage_dir = storage_dir
        self.db_path = db_path or os.getenv("AGENT_DB_PATH", DEFAULT_DB_PATH)
        self.max_messages_per_session = 50  # Keep last 50 messages
        self.session_timeout_hours = 24  # Reset context after 24 hours

        self._local = threading.local()
        init_db(self.db_path)

    # ------------------------------------------------------------------
    # connection handling
    # ------------------------------------------------------------------
    @property
    def conn(self) -> sqlite3.Connection:
        """One connection per thread; SQLite connections are not shareable."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = connect(self.db_path)
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # reads
    # ------------------------------------------------------------------
    def _row_to_profile(self, row: sqlite3.Row) -> UserProfile:
        try:
            interests = json.loads(row["interests"]) or []
        except (json.JSONDecodeError, TypeError):
            interests = []
        return UserProfile(
            phone_number=row["phone_number"],
            name=row["name"],
            preferred_currency=row["preferred_currency"] or "USD",
            interests=interests,
            last_interaction=row["last_interaction"],
            total_interactions=row["total_interactions"] or 0,
        )

    def _row_to_message(self, row: sqlite3.Row) -> ConversationMessage:
        try:
            metadata = json.loads(row["metadata"]) or {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return ConversationMessage(
            timestamp=row["timestamp"],
            role=row["role"],
            content=row["content"],
            message_type=row["message_type"],
            metadata=metadata,
        )

    def _ensure_user(self, phone_number: str) -> None:
        now = _now()
        with self.conn:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO users "
                "(phone_number, preferred_currency, interests, total_interactions,"
                " created_at, updated_at) VALUES (?, 'USD', '[]', 0, ?, ?)",
                (phone_number, now, now),
            )
        if cursor.rowcount:
            logger.info(f"Created new session for {phone_number}")

    def get_or_create_session(self, phone_number: str) -> ConversationSession:
        """Get existing session or create new one"""
        self._ensure_user(phone_number)

        user_row = self.conn.execute(
            "SELECT * FROM users WHERE phone_number = ?", (phone_number,)
        ).fetchone()

        message_rows = self.conn.execute(
            "SELECT * FROM messages WHERE phone_number = ? ORDER BY id ASC",
            (phone_number,),
        ).fetchall()

        return ConversationSession(
            user_profile=self._row_to_profile(user_row),
            messages=[self._row_to_message(row) for row in message_rows],
            session_summary=user_row["session_summary"],
            created_at=user_row["created_at"],
            updated_at=user_row["updated_at"],
        )

    def get_conversation_context(self, phone_number: str,
                                 last_n_messages: int = 10) -> str:
        """Get conversation context for AI prompt"""
        session = self.get_or_create_session(phone_number)

        if not session.messages:
            return "This is a new conversation with the user."

        recent_messages = session.messages[-last_n_messages:]

        profile = session.user_profile
        context_parts = [
            f"User Profile: {profile.name or 'Unknown'} ({phone_number})",
            f"Preferred Currency: {profile.preferred_currency}",
            f"Total Interactions: {profile.total_interactions}",
            f"Interests: {', '.join(profile.interests) if profile.interests else 'None yet'}",
            "",
            "Recent Conversation History:"
        ]

        for msg in recent_messages:
            try:
                timestamp = datetime.fromisoformat(msg.timestamp).strftime("%H:%M")
            except (ValueError, TypeError):
                timestamp = "--:--"
            context_parts.append(f"[{timestamp}] {msg.role.upper()}: {msg.content}")

        return "\n".join(context_parts)

    def get_user_summary(self, phone_number: str) -> Dict[str, Any]:
        """Get user summary for analytics"""
        self._ensure_user(phone_number)
        row = self.conn.execute(
            "SELECT u.*, (SELECT COUNT(*) FROM messages m "
            "             WHERE m.phone_number = u.phone_number) AS total_messages "
            "FROM users u WHERE u.phone_number = ?",
            (phone_number,),
        ).fetchone()
        profile = self._row_to_profile(row)

        return {
            "phone_number": phone_number,
            "name": profile.name,
            "total_interactions": profile.total_interactions,
            "preferred_currency": profile.preferred_currency,
            "interests": profile.interests,
            "last_interaction": profile.last_interaction,
            "total_messages": row["total_messages"],
            "session_created": row["created_at"],
        }

    def get_all_users_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all users"""
        rows = self.conn.execute(
            "SELECT u.*, (SELECT COUNT(*) FROM messages m "
            "             WHERE m.phone_number = u.phone_number) AS total_messages "
            "FROM users u ORDER BY u.phone_number"
        ).fetchall()

        summaries = []
        for row in rows:
            profile = self._row_to_profile(row)
            summaries.append({
                "phone_number": profile.phone_number,
                "name": profile.name,
                "total_interactions": profile.total_interactions,
                "preferred_currency": profile.preferred_currency,
                "interests": profile.interests,
                "last_interaction": profile.last_interaction,
                "total_messages": row["total_messages"],
                "session_created": row["created_at"],
            })
        return summaries

    # ------------------------------------------------------------------
    # writes
    # ------------------------------------------------------------------
    def add_message(self, phone_number: str, role: str, content: str,
                    message_type: str = "text", metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        self._ensure_user(phone_number)
        timestamp = _now()

        with self.conn:
            self.conn.execute(
                "INSERT INTO messages "
                "(phone_number, timestamp, role, content, message_type, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (phone_number, timestamp, role, content, message_type,
                 json.dumps(metadata or {}, ensure_ascii=False)),
            )
            # Counter is incremented in SQL, so two concurrent turns for the
            # same user both count instead of one overwriting the other.
            self.conn.execute(
                "UPDATE users SET total_interactions = total_interactions + 1, "
                "last_interaction = ?, updated_at = ? WHERE phone_number = ?",
                (timestamp, timestamp, phone_number),
            )
            # Keep only the most recent N messages for this user.
            self.conn.execute(
                "DELETE FROM messages WHERE phone_number = ? AND id NOT IN "
                "(SELECT id FROM messages WHERE phone_number = ? "
                " ORDER BY id DESC LIMIT ?)",
                (phone_number, phone_number, self.max_messages_per_session),
            )

        logger.debug(f"Added {role} message for {phone_number}: {content[:50]}...")

    def update_user_preferences(self, phone_number: str, **kwargs):
        """Update user preferences"""
        self._ensure_user(phone_number)

        assignments = []
        values = []
        for key, value in kwargs.items():
            if key not in _UPDATABLE_COLUMNS:
                continue
            assignments.append(f"{key} = ?")
            values.append(json.dumps(value) if key == "interests" else value)
            logger.info(f"Updated {key} for {phone_number}: {value}")

        if not assignments:
            return

        assignments.append("updated_at = ?")
        values.extend([_now(), phone_number])

        with self.conn:
            self.conn.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE phone_number = ?",
                values,
            )

    def add_user_interest(self, phone_number: str, interest: str):
        """Add user interest"""
        self._ensure_user(phone_number)

        # Append and de-duplicate in one statement. A read-modify-write in
        # Python would let two concurrent calls each read the same list and
        # write back a version missing the other's interest.
        with self.conn:
            cursor = self.conn.execute(
                "UPDATE users "
                "SET interests = json_insert(interests, '$[#]', ?), updated_at = ? "
                "WHERE phone_number = ? AND NOT EXISTS ("
                "  SELECT 1 FROM json_each(users.interests) "
                "  WHERE lower(json_each.value) = lower(?))",
                (interest, _now(), phone_number, interest),
            )

        if cursor.rowcount:
            logger.info(f"Added interest '{interest}' for {phone_number}")

    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up old inactive sessions"""
        cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()

        rows = self.conn.execute(
            "SELECT phone_number FROM users "
            "WHERE last_interaction IS NOT NULL AND last_interaction < ?",
            (cutoff,),
        ).fetchall()

        if not rows:
            return

        with self.conn:
            for row in rows:
                phone_number = row["phone_number"]
                self.conn.execute(
                    "DELETE FROM messages WHERE phone_number = ?", (phone_number,)
                )
                self.conn.execute(
                    "DELETE FROM users WHERE phone_number = ?", (phone_number,)
                )
                logger.info(f"Cleaned up old session for {phone_number}")
