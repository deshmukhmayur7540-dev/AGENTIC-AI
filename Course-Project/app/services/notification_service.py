"""Persistence helpers for in-app notifications."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


def insert_notification(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    user_role: str,
    title: str,
    message: str,
    category: str,
    link: str | None = None,
) -> None:
    """Insert a notification using the caller's existing transaction."""
    conn.execute(
        """
        INSERT INTO notifications
            (id, user_id, user_role, title, message, category, is_read, link, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            f"notif-{uuid.uuid4().hex}",
            user_id,
            user_role,
            title,
            message,
            category,
            link,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
