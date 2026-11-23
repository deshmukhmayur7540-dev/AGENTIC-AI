import json
import os
from pathlib import Path
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional
from config import settings
from app.labs.lab5.sources.base_source import BaseDataSource
from app.models.lab5_models import ConnectorOperation, ConnectorRole


class SqliteDataSource(BaseDataSource):
    """Governed SQLite database connector managing assignments, rubrics, students, and submissions."""

    source_id = "sqlite_source"
    name = "Academic SQLite Database"
    source_type = "SQLITE"
    description = (
        "Governed relational store for assignments, grading rubrics, students, and assignment submissions. "
        "Enforces strict authorization: Student and TA roles cannot modify course structure or other students' records."
    )
    supported_operations = [
        ConnectorOperation.READ,
        ConnectorOperation.WRITE,
        ConnectorOperation.SEARCH,
        ConnectorOperation.LIST,
        ConnectorOperation.DELETE,
    ]
    is_read_only = False
    requires_auth = True

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._lock = threading.Lock()
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = Path(settings.database_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._init_db()

    def close(self) -> None:
        """Close the SQLite connection owned by this data source."""
        with self._lock:
            self._conn.close()

    def _init_db(self) -> None:
        """Create initial schema, execute non-destructive migrations, and seed foundational records."""
        with self._lock:
            cur = self._conn.cursor()

            # 1. Assignments Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id TEXT PRIMARY KEY,
                    course_id TEXT,
                    title TEXT,
                    max_points INTEGER,
                    weight_percentage REAL,
                    due_week INTEGER
                )
            """)

            # Non-destructive column migrations for assignments
            cur.execute("PRAGMA table_info(assignments)")
            existing_cols = {row[1] for row in cur.fetchall()}
            
            if "description" not in existing_cols:
                cur.execute("ALTER TABLE assignments ADD COLUMN description TEXT")
            if "due_date" not in existing_cols:
                cur.execute("ALTER TABLE assignments ADD COLUMN due_date TEXT")
            if "submission_rules" not in existing_cols:
                cur.execute("ALTER TABLE assignments ADD COLUMN submission_rules TEXT")
            if "late_policy" not in existing_cols:
                cur.execute("ALTER TABLE assignments ADD COLUMN late_policy TEXT")
            if "status" not in existing_cols:
                cur.execute("ALTER TABLE assignments ADD COLUMN status TEXT DEFAULT 'OPEN'")

            # 2. Rubrics Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rubrics (
                    id TEXT PRIMARY KEY,
                    assignment_id TEXT,
                    criterion TEXT,
                    max_points INTEGER,
                    description TEXT
                )
            """)

            # 3. Students Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    course_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # 4. Submissions Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    assignment_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    repository_url TEXT NOT NULL,
                    normalized_url TEXT NOT NULL,
                    repo_owner TEXT NOT NULL,
                    repo_name TEXT NOT NULL,
                    submission_timestamp TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    validation_details TEXT,
                    is_latest INTEGER NOT NULL DEFAULT 1,
                    review_status TEXT DEFAULT 'PENDING',
                    review_feedback TEXT,
                    review_score REAL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    notes TEXT,
                    audit_trace_id TEXT,
                    FOREIGN KEY (assignment_id) REFERENCES assignments(id),
                    FOREIGN KEY (student_id) REFERENCES students(id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS submission_audit_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_id TEXT,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    review_score REAL,
                    review_feedback TEXT,
                    occurred_at TEXT NOT NULL,
                    trace_id TEXT
                )
            """)

            cur.execute("PRAGMA table_info(submissions)")
            submission_cols = {row[1] for row in cur.fetchall()}
            if "approved_at" not in submission_cols:
                cur.execute("ALTER TABLE submissions ADD COLUMN approved_at TEXT")
            if "approved_by" not in submission_cols:
                cur.execute("ALTER TABLE submissions ADD COLUMN approved_by TEXT")

            # Indexes for optimal querying
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sub_student_asgn ON submissions (student_id, assignment_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sub_asgn ON submissions (assignment_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sub_status ON submissions (status)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_submission_audit_submission "
                "ON submission_audit_events(submission_id, event_id)"
            )

            # Seed 26ECAC401 default assignments
            cur.execute("""
                INSERT OR IGNORE INTO assignments (id, course_id, title, max_points, weight_percentage, due_week) VALUES 
                ('lab1', '26ECAC401', 'Lab 1: Clarify-Plan-Revise Agent', 100, 10.0, 3),
                ('lab2', '26ECAC401', 'Lab 2: Tool-Using Agent with Trace', 100, 15.0, 5),
                ('lab3', '26ECAC401', 'Lab 3: Reusable Skills Registry', 100, 15.0, 7),
                ('lab4', '26ECAC401', 'Lab 4: Memory & Retrieval Architecture', 100, 15.0, 9),
                ('final_capstone', '26ECAC401', 'Agentic AI Final Capstone Project', 100, 25.0, 14)
            """)

            # Populate metadata fields on assignments if currently NULL
            cur.execute("""
                UPDATE assignments SET 
                    description = COALESCE(description, 'Implement an Agentic AI Workspace Planner with gap analysis and immutable revision diffs.'),
                    due_date = COALESCE(due_date, '2026-10-31T23:59:59Z'),
                    submission_rules = COALESCE(submission_rules, 'HTTPS GitHub repository link containing complete solution code and documentation.'),
                    late_policy = COALESCE(late_policy, '5% penalty per day up to 3 days late; submissions beyond 3 days receive 0.'),
                    status = COALESCE(status, 'OPEN')
                WHERE id = 'lab1'
            """)
            cur.execute("""
                UPDATE assignments SET 
                    description = COALESCE(description, 'Develop a deterministic ReAct tool-using agent with auditable zero-private-token trace.'),
                    due_date = COALESCE(due_date, '2026-11-14T23:59:59Z'),
                    submission_rules = COALESCE(submission_rules, 'HTTPS GitHub repository link with Pydantic tool schemas and execution history.'),
                    late_policy = COALESCE(late_policy, '5% penalty per day up to 3 days late.'),
                    status = COALESCE(status, 'OPEN')
                WHERE id = 'lab2'
            """)
            cur.execute("""
                UPDATE assignments SET 
                    description = COALESCE(description, 'Stateless Pydantic-typed reusable skill modules for planning, research, and formatting.'),
                    due_date = COALESCE(due_date, '2026-11-28T23:59:59Z'),
                    submission_rules = COALESCE(submission_rules, 'HTTPS GitHub repository link.'),
                    late_policy = COALESCE(late_policy, '5% penalty per day up to 3 days late.'),
                    status = COALESCE(status, 'OPEN')
                WHERE id = 'lab3'
            """)
            cur.execute("""
                UPDATE assignments SET 
                    description = COALESCE(description, 'Session store and long-term inverted index with anti-hallucination guardrails.'),
                    due_date = COALESCE(due_date, '2026-12-12T23:59:59Z'),
                    submission_rules = COALESCE(submission_rules, 'HTTPS GitHub repository link.'),
                    late_policy = COALESCE(late_policy, '5% penalty per day up to 3 days late.'),
                    status = COALESCE(status, 'OPEN')
                WHERE id = 'lab4'
            """)
            cur.execute("""
                UPDATE assignments SET 
                    description = COALESCE(description, 'Comprehensive end-to-end multi-agent orchestration and governed runtime system.'),
                    due_date = COALESCE(due_date, '2026-12-24T23:59:59Z'),
                    submission_rules = COALESCE(submission_rules, 'Public or faculty-accessible GitHub repository containing full capstone solution.'),
                    late_policy = COALESCE(late_policy, 'Strict deadline: No late submissions accepted for final capstone.'),
                    status = COALESCE(status, 'OPEN')
                WHERE id = 'final_capstone'
            """)

            # Seed rubrics
            cur.execute("""
                INSERT OR IGNORE INTO rubrics (id, assignment_id, criterion, max_points, description) VALUES
                ('rub-1-1', 'lab1', 'Intent Extraction & Clarification', 40, 'Detects missing requirements and asks >= 2 questions'),
                ('rub-1-2', 'lab1', 'Immutability & Diffs', 60, 'Preserves v1.0 and generates exact field diffs'),
                ('rub-2-1', 'lab2', 'Typed Schema Validation', 50, 'Enforces strict Pydantic input/output schemas'),
                ('rub-2-2', 'lab2', 'Auditable Trace', 50, 'Zero private chain-of-thought tokens exposed')
            """)

            # Seed default students
            cur.execute("""
                INSERT OR IGNORE INTO students VALUES
                ('std-001', 'Alice Chen', 'alice.chen@university.edu', '26ECAC401', '2026-09-01T00:00:00Z'),
                ('std-002', 'Bob Smith', 'bob.smith@university.edu', '26ECAC401', '2026-09-01T00:00:00Z'),
                ('std-003', 'Charlie Patel', 'charlie.patel@university.edu', '26ECAC401', '2026-09-01T00:00:00Z')
            """)

            self._conn.commit()

    @staticmethod
    def _course_scope(parameters: dict[str, Any], alias: str) -> tuple[str, list[str]]:
        """Build a mandatory course predicate for sensitive submission records."""
        course_ids = parameters.get("authorized_course_ids")
        if course_ids is None:
            course_id = parameters.get("course_id")
            course_ids = [course_id] if course_id else []
        if not isinstance(course_ids, (list, tuple, set)):
            raise PermissionError("Course-scoped access is required for submission records.")
        normalized_ids = sorted({str(course_id).strip() for course_id in course_ids if str(course_id).strip()})
        if not normalized_ids:
            raise PermissionError("Course-scoped access is required for submission records.")
        placeholders = ", ".join("?" for _ in normalized_ids)
        return f"{alias}.course_id IN ({placeholders})", normalized_ids

    @staticmethod
    def _student_scope(parameters: dict[str, Any], role: ConnectorRole) -> tuple[str, list[str]]:
        if role != ConnectorRole.STUDENT:
            return "", []
        student_id = parameters.get("student_id")
        if not isinstance(student_id, str) or not student_id.strip():
            raise PermissionError("Student-scoped access requires the authenticated student ID.")
        return " AND s.student_id = ?", [student_id.strip()]

    @staticmethod
    @contextmanager
    def _savepoint(connection: sqlite3.Connection, name: str) -> Iterator[None]:
        connection.execute(f"SAVEPOINT {name}")
        try:
            yield
        except Exception:
            connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
            connection.execute(f"RELEASE SAVEPOINT {name}")
            raise
        else:
            connection.execute(f"RELEASE SAVEPOINT {name}")

    def _write_submission(self, cursor: sqlite3.Cursor, parameters: dict[str, Any]) -> None:
        with self._savepoint(self._conn, "submission_write"):
            sub_id = parameters.get("id")
            if not sub_id:
                raise ValueError("WRITE operation on 'submissions' requires 'id'.")
            details = parameters.get("validation_details", {})
            details_json = json.dumps(details) if isinstance(details, dict) else str(details or "{}")
            previous = cursor.execute(
                "SELECT status FROM submissions WHERE id = ?",
                (sub_id,),
            ).fetchone()
            if previous is None:
                cursor.execute(
                    """
                    UPDATE submissions SET is_latest = 0
                    WHERE student_id = ? AND assignment_id = ? AND is_latest = 1
                    """,
                    (parameters.get("student_id"), parameters.get("assignment_id")),
                )

            cursor.execute(
                """
                INSERT OR REPLACE INTO submissions (
                    id, assignment_id, student_id, course_id,
                    repository_url, normalized_url, repo_owner, repo_name,
                    submission_timestamp, attempt_number, status,
                    validation_status, validation_details, is_latest,
                    review_status, review_feedback, review_score,
                    reviewed_by, reviewed_at, notes, audit_trace_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub_id,
                    parameters.get("assignment_id"),
                    parameters.get("student_id"),
                    parameters.get("course_id", "26ECAC401"),
                    parameters.get("repository_url"),
                    parameters.get("normalized_url"),
                    parameters.get("repo_owner"),
                    parameters.get("repo_name"),
                    parameters.get("submission_timestamp"),
                    parameters.get("attempt_number", 1),
                    parameters.get("status", "SUBMITTED"),
                    parameters.get("validation_status", "PASSED"),
                    details_json,
                    1 if parameters.get("is_latest", True) else 0,
                    parameters.get("review_status", "PENDING"),
                    parameters.get("review_feedback"),
                    parameters.get("review_score"),
                    parameters.get("reviewed_by"),
                    parameters.get("reviewed_at"),
                    parameters.get("notes"),
                    parameters.get("audit_trace_id"),
                ),
            )
            if previous is None:
                action = "SUBMITTED"
            elif parameters.get("review_status") == "REVIEWED":
                action = "REVIEWED"
            else:
                action = "REVIEW_STATUS_CHANGED"
            cursor.execute(
                """
                INSERT INTO submission_audit_events(
                    submission_id, action, actor_id, from_status, to_status,
                    review_score, review_feedback, occurred_at, trace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sub_id,
                    action,
                    parameters.get("reviewed_by") or parameters.get("student_id"),
                    previous[0] if previous is not None else None,
                    parameters.get("status", "SUBMITTED"),
                    parameters.get("review_score"),
                    parameters.get("review_feedback"),
                    parameters.get("reviewed_at") or parameters.get("submission_timestamp"),
                    parameters.get("audit_trace_id"),
                ),
            )

    def execute(
        self,
        operation: ConnectorOperation,
        resource_path: str,
        parameters: dict[str, Any],
        role: ConnectorRole,
    ) -> tuple[Any, str]:
        table = resource_path or parameters.get("table", "assignments")
        valid_tables = (
            "assignments",
            "rubrics",
            "students",
            "submissions",
            "submission_audit_events",
        )
        if table not in valid_tables:
            raise ValueError(f"Unknown table '{table}' in SqliteDataSource. Allowed: {valid_tables}")

        # Role-based authorization enforcement
        if operation in (ConnectorOperation.WRITE, ConnectorOperation.DELETE):
            if table == "submission_audit_events":
                raise PermissionError("Submission audit events are append-only and cannot be modified or deleted.")
            if operation == ConnectorOperation.DELETE and table == "submissions":
                raise PermissionError("Submission lifecycle changes must use the authorized review and grading APIs.")
            if role in (ConnectorRole.STUDENT, ConnectorRole.TA):
                # Student can ONLY write to submissions table (for their own submission)
                if operation == ConnectorOperation.WRITE and table == "submissions":
                    pass
                else:
                    raise PermissionError(
                        f"Access Denied: Role '{role.value}' is unauthorized to perform '{operation.value}' "
                        f"on relational store '{self.source_id}'. Consequential database modifications require FACULTY or SYSTEM authority."
                    )

        with self._lock:
            cur = self._conn.cursor()

            # -----------------------------------------------------------------
            # LIST
            # -----------------------------------------------------------------
            if operation == ConnectorOperation.LIST:
                if table == "submissions":
                    course_filter, q_args = self._course_scope(parameters, "s")
                    student_filter, student_args = self._student_scope(parameters, role)
                    query = f"SELECT s.* FROM submissions s WHERE {course_filter}{student_filter}"
                    q_args.extend(student_args)
                    if "student_id" in parameters:
                        query += " AND s.student_id = ?"
                        q_args.append(parameters["student_id"])
                    if "assignment_id" in parameters:
                        query += " AND s.assignment_id = ?"
                        q_args.append(parameters["assignment_id"])
                    if "is_latest" in parameters:
                        query += " AND s.is_latest = ?"
                        q_args.append(1 if parameters["is_latest"] else 0)
                    if "status" in parameters:
                        query += " AND s.status = ?"
                        q_args.append(parameters["status"])
                    query += " ORDER BY s.submission_timestamp DESC"
                    cur.execute(query, tuple(q_args))
                elif table == "submission_audit_events":
                    course_filter, q_args = self._course_scope(parameters, "s")
                    student_filter, student_args = self._student_scope(parameters, role)
                    query = (
                        "SELECT e.* FROM submission_audit_events e "
                        "JOIN submissions s ON s.id = e.submission_id "
                        f"WHERE {course_filter}{student_filter}"
                    )
                    q_args.extend(student_args)
                    if "submission_id" in parameters:
                        query += " AND e.submission_id = ?"
                        q_args.append(parameters["submission_id"])
                    query += " ORDER BY e.event_id"
                    cur.execute(query, tuple(q_args))
                elif table == "assignments" and "course_id" in parameters:
                    cur.execute("SELECT * FROM assignments WHERE course_id = ? ORDER BY due_week ASC", (parameters["course_id"],))
                else:
                    cur.execute(f"SELECT * FROM {table}")

                cols = [desc[0] for desc in cur.description]
                rows = [dict(zip(cols, row)) for row in cur.fetchall()]
                # Unpack json fields if submissions
                if table == "submissions":
                    for r in rows:
                        if isinstance(r.get("validation_details"), str):
                            try:
                                r["validation_details"] = json.loads(r["validation_details"])
                            except Exception:
                                pass
                        r["is_latest"] = bool(r.get("is_latest", 1))
                return rows, f"SQLite Table '{table}' (Full Record Scan)"

            # -----------------------------------------------------------------
            # READ
            # -----------------------------------------------------------------
            elif operation == ConnectorOperation.READ:
                item_id = parameters.get("id")
                if not item_id:
                    raise ValueError(f"READ operation requires parameter 'id'.")
                if table == "submissions":
                    course_filter, q_args = self._course_scope(parameters, "s")
                    student_filter, student_args = self._student_scope(parameters, role)
                    cur.execute(
                        f"SELECT s.* FROM submissions s WHERE s.id = ? AND {course_filter}{student_filter}",
                        (item_id, *q_args, *student_args),
                    )
                elif table == "submission_audit_events":
                    course_filter, q_args = self._course_scope(parameters, "s")
                    student_filter, student_args = self._student_scope(parameters, role)
                    cur.execute(
                        "SELECT e.* FROM submission_audit_events e "
                        "JOIN submissions s ON s.id = e.submission_id "
                        f"WHERE e.event_id = ? AND {course_filter}{student_filter}",
                        (item_id, *q_args, *student_args),
                    )
                else:
                    primary_key = "event_id" if table == "submission_audit_events" else "id"
                    cur.execute(f"SELECT * FROM {table} WHERE {primary_key} = ?", (item_id,))
                cols = [desc[0] for desc in cur.description]
                row = cur.fetchone()
                if not row:
                    return None, f"SQLite Table '{table}' (Record Not Found)"
                res = dict(zip(cols, row))
                if table == "submissions":
                    if isinstance(res.get("validation_details"), str):
                        try:
                            res["validation_details"] = json.loads(res["validation_details"])
                        except Exception:
                            pass
                    res["is_latest"] = bool(res.get("is_latest", 1))
                return res, f"SQLite Table '{table}' WHERE id='{item_id}'"

            # -----------------------------------------------------------------
            # SEARCH
            # -----------------------------------------------------------------
            elif operation == ConnectorOperation.SEARCH:
                kw = f"%{parameters.get('query', '')}%"
                if table == "assignments":
                    cur.execute("SELECT * FROM assignments WHERE title LIKE ? OR course_id LIKE ?", (kw, kw))
                elif table == "rubrics":
                    cur.execute("SELECT * FROM rubrics WHERE criterion LIKE ? OR description LIKE ?", (kw, kw))
                elif table == "students":
                    cur.execute("SELECT * FROM students WHERE name LIKE ? OR email LIKE ? OR id LIKE ?", (kw, kw, kw))
                elif table == "submissions":
                    course_filter, q_args = self._course_scope(parameters, "s")
                    student_filter, student_args = self._student_scope(parameters, role)
                    cur.execute(
                        "SELECT s.* FROM submissions s "
                        f"WHERE {course_filter}{student_filter} AND "
                        "(s.repository_url LIKE ? OR s.repo_owner LIKE ? OR s.repo_name LIKE ? OR s.student_id LIKE ?)",
                        (*q_args, *student_args, kw, kw, kw, kw),
                    )
                cols = [desc[0] for desc in cur.description]
                rows = [dict(zip(cols, row)) for row in cur.fetchall()]
                return rows, f"SQLite Table '{table}' (Filtered Search)"

            # -----------------------------------------------------------------
            # WRITE
            # -----------------------------------------------------------------
            elif operation == ConnectorOperation.WRITE:
                if table == "assignments":
                    asgn_id = parameters.get("id", f"asgn-{parameters.get('due_week', 1)}")
                    cur.execute("""
                        INSERT OR REPLACE INTO assignments (
                            id, course_id, title, max_points, weight_percentage, due_week,
                            description, due_date, submission_rules, late_policy, status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        asgn_id,
                        parameters.get("course_id", "26ECAC401"),
                        parameters.get("title", "New Assignment"),
                        parameters.get("max_points", 100),
                        parameters.get("weight_percentage", 10.0),
                        parameters.get("due_week", 1),
                        parameters.get("description"),
                        parameters.get("due_date"),
                        parameters.get("submission_rules"),
                        parameters.get("late_policy"),
                        parameters.get("status", "OPEN"),
                    ))
                elif table == "rubrics":
                    rub_id = parameters.get("id", "rub-custom")
                    cur.execute("""
                        INSERT OR REPLACE INTO rubrics (id, assignment_id, criterion, max_points, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        rub_id,
                        parameters.get("assignment_id", "lab1"),
                        parameters.get("criterion", "Quality Metric"),
                        parameters.get("max_points", 50),
                        parameters.get("description", "Evaluation criterion"),
                    ))
                elif table == "students":
                    std_id = parameters.get("id")
                    if not std_id:
                        raise ValueError("WRITE operation on 'students' requires 'id'.")
                    cur.execute("""
                        INSERT OR REPLACE INTO students (id, name, email, course_id, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        std_id,
                        parameters.get("name", "Student"),
                        parameters.get("email", f"{std_id}@university.edu"),
                        parameters.get("course_id", "26ECAC401"),
                        parameters.get("created_at", "2026-09-01T00:00:00Z"),
                    ))
                elif table == "submissions":
                    self._write_submission(cur, parameters)

                self._conn.commit()
                return {"status": "RECORD_WRITTEN", "id": parameters.get("id")}, f"SQLite Commit: Table '{table}'"

            # -----------------------------------------------------------------
            # DELETE
            # -----------------------------------------------------------------
            elif operation == ConnectorOperation.DELETE:
                item_id = parameters.get("id")
                if not item_id:
                    raise ValueError("DELETE operation requires parameter 'id'.")
                cur.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
                if cur.rowcount == 0:
                    raise ValueError(f"Record with id '{item_id}' not found in table '{table}'. Deletion aborted.")
                self._conn.commit()
                return {"status": "RECORD_DELETED", "id": item_id}, f"SQLite Delete: Table '{table}' id='{item_id}'"

        raise ValueError(f"Operation '{operation}' not supported.")
