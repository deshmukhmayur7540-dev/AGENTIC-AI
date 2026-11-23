"""Persistent Audit Service for CourseAgentAI (Bug 7 repair and governance recording)."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.data.db import get_db_connection

logger = logging.getLogger(__name__)


class AuditService:
    """Thread-safe persistent audit logging service recording all academic mutations in SQLite."""

    def log_event(
        self,
        event_type: str,
        actor: str,
        actor_role: str,
        resource: str,
        action: str,
        outcome: str,
        details: Any = None,
        trace_id: Optional[str] = None,
        connection: Optional[sqlite3.Connection] = None,
    ) -> dict[str, Any]:
        """Record an immutable event into the persistent audit log."""
        trace = trace_id or f"trace-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        details_str = json.dumps(details) if details is not None else None

        if connection is not None:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (event_type, actor, actor_role, resource, action, outcome, details, trace_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_type, actor, actor_role, resource, action, outcome, details_str, trace, now_iso),
            )
            return {
                "id": cursor.lastrowid,
                "event_type": event_type,
                "actor": actor,
                "actor_role": actor_role,
                "resource": resource,
                "action": action,
                "outcome": outcome,
                "details": details,
                "trace_id": trace,
                "timestamp": now_iso,
                "persisted": True,
            }

        try:
            with get_db_connection(immediate=True) as conn:
                result = self.log_event(
                    event_type=event_type,
                    actor=actor,
                    actor_role=actor_role,
                    resource=resource,
                    action=action,
                    outcome=outcome,
                    details=details,
                    trace_id=trace,
                    connection=conn,
                )
                event_id = result["id"]
        except Exception as exc:
            logger.error("Failed to persist audit event (%s, %s): %s", event_type, action, exc)
            return {
                "id": None,
                "event_type": event_type,
                "actor": actor,
                "actor_role": actor_role,
                "resource": resource,
                "action": action,
                "outcome": outcome,
                "details": details,
                "trace_id": trace,
                "timestamp": now_iso,
                "persisted": False,
            }

        return {
            "id": event_id,
            "event_type": event_type,
            "actor": actor,
            "actor_role": actor_role,
            "resource": resource,
            "action": action,
            "outcome": outcome,
            "details": details,
            "trace_id": trace,
            "timestamp": now_iso,
            "persisted": True,
        }

    def list_events(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Retrieve filtered audit history sorted by descending timestamp."""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: list[Any] = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if actor:
            query += " AND actor LIKE ?"
            params.append(f"%{actor}%")
        if resource:
            query += " AND resource LIKE ?"
            params.append(f"%{resource}%")
        if outcome:
            query += " AND outcome = ?"
            params.append(outcome)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        events = []
        for r in rows:
            data = dict(r)
            if data.get("details"):
                try:
                    data["details"] = json.loads(data["details"])
                except Exception:
                    pass
            events.append(data)
        return events

    def get_event_count(self) -> int:
        """Count total recorded audit events."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM audit_events")
            return cursor.fetchone()["cnt"]


audit_service = AuditService()
