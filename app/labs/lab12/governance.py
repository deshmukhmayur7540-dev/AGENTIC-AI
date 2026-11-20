"""SQLite-backed approval and rollback state for the Lab 12 demo."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config import settings


class GovernedChangeStore:
    """Persist proposals, decisions, resource values, and append-only audit events."""

    def __init__(self, db_path: str | Path | None = None, *, initialize: bool = True) -> None:
        self._db_path = Path(db_path or settings.database_path)
        self._lock = threading.RLock()
        if initialize:
            self.initialize()

    def initialize(self) -> None:
        """Create the governance schema when explicitly requested."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _transaction(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self._db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            if immediate:
                connection.execute("BEGIN IMMEDIATE")
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS governance_resources (
                    resource_id TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS governance_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    resource_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    before_json TEXT NOT NULL,
                    proposed_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_by TEXT,
                    decision_comment TEXT,
                    decided_at TEXT,
                    applied INTEGER NOT NULL DEFAULT 0,
                    rolled_back INTEGER NOT NULL DEFAULT 0,
                    rolled_back_by TEXT,
                    rolled_back_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_governance_proposals_resource
                    ON governance_proposals(resource_id, created_at);
                CREATE TABLE IF NOT EXISTS governance_audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT,
                    comment TEXT,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(proposal_id) REFERENCES governance_proposals(proposal_id)
                );
                CREATE INDEX IF NOT EXISTS idx_governance_audit_proposal
                    ON governance_audit_events(proposal_id, event_id);
                """
            )

    @staticmethod
    def _decode_proposal(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        proposal = dict(row)
        proposal["before"] = json.loads(proposal.pop("before_json"))
        proposal["proposed"] = json.loads(proposal.pop("proposed_json"))
        proposal["applied"] = bool(proposal["applied"])
        proposal["rolled_back"] = bool(proposal["rolled_back"])
        return proposal

    @staticmethod
    def _current_resource(connection: sqlite3.Connection, resource_id: str) -> dict[str, Any] | None:
        row = connection.execute(
            "SELECT value_json FROM governance_resources WHERE resource_id = ?",
            (resource_id,),
        ).fetchone()
        return json.loads(row["value_json"]) if row else None

    @staticmethod
    def _set_resource(
        connection: sqlite3.Connection,
        resource_id: str,
        value: dict[str, Any],
        occurred_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO governance_resources(resource_id, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(resource_id) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (resource_id, json.dumps(value, sort_keys=True), occurred_at),
        )

    @staticmethod
    def _record_event(
        connection: sqlite3.Connection,
        proposal_id: str,
        action: str,
        actor: str | None,
        comment: str | None,
        from_status: str | None,
        to_status: str,
        occurred_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO governance_audit_events(
                proposal_id, action, actor, comment, from_status, to_status, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (proposal_id, action, actor, comment, from_status, to_status, occurred_at),
        )

    def propose(
        self,
        resource_id: str,
        current_value: dict[str, Any],
        proposed_value: dict[str, Any],
        summary: str,
        actor: str | None = None,
    ) -> dict[str, Any]:
        with self._lock, self._transaction(immediate=True) as connection:
            known = self._current_resource(connection, resource_id)
            before = known if known is not None else current_value
            if known is not None and known != current_value:
                raise ValueError("current_value does not match the latest governed resource state")

            proposal_id = f"chg-{uuid.uuid4().hex[:12]}"
            occurred_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                """
                INSERT INTO governance_proposals(
                    proposal_id, resource_id, summary, before_json, proposed_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?)
                """,
                (
                    proposal_id,
                    resource_id,
                    summary,
                    json.dumps(before, sort_keys=True),
                    json.dumps(proposed_value, sort_keys=True),
                    occurred_at,
                ),
            )
            self._record_event(
                connection,
                proposal_id,
                "PROPOSED",
                actor,
                summary,
                None,
                "PENDING_APPROVAL",
                occurred_at,
            )
            proposal = self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )
            if proposal is None:
                raise RuntimeError("New governance proposal could not be read after insertion.")
            return proposal

    def decide(
        self,
        proposal_id: str,
        approved: bool,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        with self._lock, self._transaction(immediate=True) as connection:
            proposal = self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )
            if proposal is None:
                raise KeyError("Governance proposal was not found")
            if proposal["status"] != "PENDING_APPROVAL":
                raise ValueError(f"Proposal is already {proposal['status']}")

            current = self._current_resource(connection, proposal["resource_id"])
            if current is not None and current != proposal["before"]:
                raise ValueError(
                    "Resource changed after this proposal was created; create a new proposal from the latest state"
                )

            occurred_at = datetime.now(timezone.utc).isoformat()
            status = "APPROVED_APPLIED" if approved else "REJECTED"
            connection.execute(
                """
                UPDATE governance_proposals
                SET status = ?, decided_by = ?, decision_comment = ?, decided_at = ?, applied = ?
                WHERE proposal_id = ?
                """,
                (status, actor, comment, occurred_at, int(approved), proposal_id),
            )
            if approved:
                self._set_resource(
                    connection,
                    proposal["resource_id"],
                    proposal["proposed"],
                    occurred_at,
                )
            self._record_event(
                connection,
                proposal_id,
                "APPROVED" if approved else "REJECTED",
                actor,
                comment,
                "PENDING_APPROVAL",
                status,
                occurred_at,
            )
            result = self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )
            if result is None:
                raise RuntimeError("Governance proposal could not be read after its decision.")
            return result

    def rollback(self, proposal_id: str, actor: str) -> dict[str, Any]:
        with self._lock, self._transaction(immediate=True) as connection:
            proposal = self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )
            if proposal is None:
                raise KeyError("Governance proposal was not found")
            if not proposal["applied"] or proposal["rolled_back"]:
                raise ValueError("Only an applied change can be rolled back once")
            if self._current_resource(connection, proposal["resource_id"]) != proposal["proposed"]:
                raise ValueError("Resource changed after approval; rollback would overwrite a newer value")

            occurred_at = datetime.now(timezone.utc).isoformat()
            self._set_resource(
                connection,
                proposal["resource_id"],
                proposal["before"],
                occurred_at,
            )
            connection.execute(
                """
                UPDATE governance_proposals
                SET status = 'ROLLED_BACK', rolled_back = 1,
                    rolled_back_by = ?, rolled_back_at = ?
                WHERE proposal_id = ?
                """,
                (actor, occurred_at, proposal_id),
            )
            self._record_event(
                connection,
                proposal_id,
                "ROLLED_BACK",
                actor,
                None,
                "APPROVED_APPLIED",
                "ROLLED_BACK",
                occurred_at,
            )
            result = self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )
            if result is None:
                raise RuntimeError("Governance proposal could not be read after rollback.")
            return result

    def get(self, proposal_id: str) -> dict[str, Any] | None:
        with self._lock, self._transaction() as connection:
            return self._decode_proposal(
                connection.execute(
                    "SELECT * FROM governance_proposals WHERE proposal_id = ?",
                    (proposal_id,),
                ).fetchone()
            )

    def list(self) -> list[dict[str, Any]]:
        with self._lock, self._transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM governance_proposals ORDER BY created_at, rowid"
            ).fetchall()
            proposals = [self._decode_proposal(row) for row in rows]
            return [proposal for proposal in proposals if proposal is not None]

    def get_resource(self, resource_id: str) -> dict[str, Any] | None:
        with self._lock, self._transaction() as connection:
            return self._current_resource(connection, resource_id)

    def get_audit_history(self, proposal_id: str) -> list[dict[str, Any]]:
        with self._lock, self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT event_id, proposal_id, action, actor, comment,
                       from_status, to_status, occurred_at
                FROM governance_audit_events
                WHERE proposal_id = ?
                ORDER BY event_id
                """,
                (proposal_id,),
            ).fetchall()
            return [dict(row) for row in rows]


governed_change_store = GovernedChangeStore(initialize=False)
