"""SQLite-backed short-term session state with a bounded lifetime."""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.data.db import get_db_connection
from app.models.lab4_models import DialogueTurn, SessionState


class ShortTermSessionStore:
    """Persist transient run state for recovery without promoting it to knowledge."""

    def __init__(self, session_ttl_seconds: int = 24 * 60 * 60) -> None:
        if session_ttl_seconds <= 0:
            raise ValueError("Session lifetime must be a positive number of seconds.")
        self._lock = threading.RLock()
        self._session_ttl_seconds = session_ttl_seconds

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _load_state(conn, row) -> SessionState:
        turns = conn.execute(
            """
            SELECT turn_id, role, content, timestamp, metadata_json
            FROM lab4_session_turns
            WHERE session_id = ?
            ORDER BY timestamp, rowid
            """,
            (row["session_id"],),
        ).fetchall()
        return SessionState(
            session_id=row["session_id"],
            user_id=row["user_id"],
            course_id=row["course_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
            current_request=row["current_request"],
            active_plan_id=row["active_plan_id"],
            clarification_answers=json.loads(row["clarification_answers_json"]),
            scratchpad=json.loads(row["scratchpad_json"]),
            dialogue_turns=[
                DialogueTurn(
                    turn_id=turn["turn_id"],
                    role=turn["role"],
                    content=turn["content"],
                    timestamp=turn["timestamp"],
                    metadata=json.loads(turn["metadata_json"]),
                )
                for turn in turns
            ],
        )

    @staticmethod
    def _cleanup_expired(conn, now: str) -> int:
        cursor = conn.execute("DELETE FROM lab4_sessions WHERE expires_at <= ?", (now,))
        return cursor.rowcount

    def cleanup_expired(self) -> int:
        """Remove expired short-term state and its turns."""
        with self._lock, get_db_connection(immediate=True) as conn:
            return self._cleanup_expired(conn, self._now().isoformat())

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: str = "faculty_reviewer",
        course_id: str = "26ECAC401",
    ) -> SessionState:
        """Create a durable, owner-scoped short-term session."""
        sid = session_id or f"sess-{uuid.uuid4().hex[:12]}"
        now = self._now()
        now_iso = now.isoformat()
        expires_at = (now + timedelta(seconds=self._session_ttl_seconds)).isoformat()
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now_iso)
            try:
                conn.execute(
                    """
                    INSERT INTO lab4_sessions (
                        session_id, user_id, course_id, created_at, updated_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sid, user_id, course_id, now_iso, now_iso, expires_at),
                )
            except sqlite3.IntegrityError as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("Session already exists.") from exc
                raise
            row = conn.execute(
                "SELECT * FROM lab4_sessions WHERE session_id = ?",
                (sid,),
            ).fetchone()
            return self._load_state(conn, row)

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve an unexpired session or None if absent/expired."""
        now = self._now().isoformat()
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            row = conn.execute(
                "SELECT * FROM lab4_sessions WHERE session_id = ? AND expires_at > ?",
                (session_id, now),
            ).fetchone()
            return self._load_state(conn, row) if row else None

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: str = "faculty_reviewer",
        course_id: str = "26ECAC401",
    ) -> SessionState:
        """Get a matching owner/course session or create a new transient session."""
        if session_id:
            existing = self.get_session(session_id)
            if existing:
                if existing.user_id != user_id or existing.course_id != course_id:
                    raise KeyError("Session not found.")
                return existing
        try:
            return self.create_session(session_id=session_id, user_id=user_id, course_id=course_id)
        except ValueError:
            existing = self.get_session(session_id) if session_id else None
            if existing and existing.user_id == user_id and existing.course_id == course_id:
                return existing
            raise KeyError("Session not found.")

    def append_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        expected_user_id: Optional[str] = None,
    ) -> DialogueTurn:
        """Append a dialogue turn to the short-term session buffer."""
        now = self._now().isoformat()
        turn = DialogueTurn(
            turn_id=f"turn-{uuid.uuid4().hex[:12]}",
            role=role,
            content=content,
            metadata=metadata or {},
            timestamp=now,
        )
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            session = conn.execute(
                "SELECT user_id FROM lab4_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not session or (expected_user_id is not None and session["user_id"] != expected_user_id):
                raise KeyError("Session not found.")
            conn.execute(
                """
                INSERT INTO lab4_session_turns (
                    turn_id, session_id, role, content, timestamp, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (turn.turn_id, session_id, role, content, now, json.dumps(turn.metadata)),
            )
            conn.execute(
                "UPDATE lab4_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        return turn

    def set_scratchpad_variable(
        self,
        session_id: str,
        key: str,
        value: Any,
        expected_user_id: Optional[str] = None,
    ) -> None:
        """Update transient scratchpad variables in the active session."""
        now = self._now().isoformat()
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            row = conn.execute(
                "SELECT user_id, scratchpad_json FROM lab4_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row or (expected_user_id is not None and row["user_id"] != expected_user_id):
                raise KeyError("Session not found.")
            scratchpad = json.loads(row["scratchpad_json"])
            scratchpad[key] = value
            conn.execute(
                "UPDATE lab4_sessions SET scratchpad_json = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps(scratchpad), now, session_id),
            )

    def set_current_request(
        self,
        session_id: str,
        request_text: str,
        expected_user_id: Optional[str] = None,
    ) -> None:
        """Record the active request in the short-term session."""
        now = self._now().isoformat()
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            cursor = conn.execute(
                """
                UPDATE lab4_sessions SET current_request = ?, updated_at = ?
                WHERE session_id = ? AND (? IS NULL OR user_id = ?)
                """,
                (request_text, now, session_id, expected_user_id, expected_user_id),
            )
            if cursor.rowcount == 0:
                raise KeyError("Session not found.")

    def clear_session(self, session_id: str, expected_user_id: Optional[str] = None) -> bool:
        """Clear short-term state while retaining its session identity and expiry."""
        now = self._now().isoformat()
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            row = conn.execute(
                "SELECT user_id FROM lab4_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row or (expected_user_id is not None and row["user_id"] != expected_user_id):
                return False
            conn.execute("DELETE FROM lab4_session_turns WHERE session_id = ?", (session_id,))
            conn.execute(
                """
                UPDATE lab4_sessions SET current_request = NULL, active_plan_id = NULL,
                    clarification_answers_json = '[]', scratchpad_json = '{}', updated_at = ?
                WHERE session_id = ?
                """,
                (now, session_id),
            )
            return True

    def delete_session(self, session_id: str, expected_user_id: Optional[str] = None) -> bool:
        """Completely remove an owned session and its dialogue turns."""
        with self._lock, get_db_connection(immediate=True) as conn:
            cursor = conn.execute(
                "DELETE FROM lab4_sessions WHERE session_id = ? AND (? IS NULL OR user_id = ?)",
                (session_id, expected_user_id, expected_user_id),
            )
            return cursor.rowcount > 0

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        course_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List summaries of unexpired sessions within the requested scope."""
        now = self._now().isoformat()
        clauses = ["expires_at > ?"]
        params: list[Any] = [now]
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if course_id is not None:
            clauses.append("course_id = ?")
            params.append(course_id)
        with self._lock, get_db_connection(immediate=True) as conn:
            self._cleanup_expired(conn, now)
            rows = conn.execute(
                f"""
                SELECT s.session_id, s.user_id, s.course_id, s.created_at, s.updated_at,
                    s.expires_at, s.current_request,
                    (SELECT COUNT(*) FROM lab4_session_turns t WHERE t.session_id = s.session_id) AS turn_count
                FROM lab4_sessions s
                WHERE {' AND '.join(clause.replace('user_id', 's.user_id').replace('course_id', 's.course_id').replace('expires_at', 's.expires_at') for clause in clauses)}
                ORDER BY s.updated_at DESC
                """,
                params,
            ).fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "user_id": row["user_id"],
                    "course_id": row["course_id"],
                    "turn_count": row["turn_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "expires_at": row["expires_at"],
                    "has_active_request": row["current_request"] is not None,
                }
                for row in rows
            ]


# Global singleton instance
short_term_store = ShortTermSessionStore()
