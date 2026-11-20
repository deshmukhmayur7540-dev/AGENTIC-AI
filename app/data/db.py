"""Unified database access, initialization, and migration module for CourseAgentAI."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from config import settings

_db_lock = threading.RLock()


def get_db_path() -> Path:
    """Return the resolved Path to the SQLite database file."""
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_db_connection(immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Provide a thread-safe context manager for SQLite connection with Row factory and FK enforcement."""
    conn = sqlite3.connect(str(get_db_path()), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        if immediate:
            conn.execute("BEGIN IMMEDIATE;")
        with conn:
            yield conn
    finally:
        conn.close()


def init_database() -> None:
    """Run non-destructive schema initialization and migration for all application tables."""
    with _db_lock, get_db_connection(immediate=True) as conn:
        cursor = conn.cursor()

        # 1. Assignments
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                max_points REAL DEFAULT 100.0,
                weight_percentage REAL DEFAULT 10.0,
                due_week INTEGER DEFAULT 1,
                description TEXT,
                due_date TEXT,
                submission_rules TEXT,
                late_policy TEXT,
                status TEXT DEFAULT 'OPEN',
                created_at TEXT,
                updated_at TEXT
            );
            """
        )

        cursor.execute("PRAGMA table_info(assignments)")
        assignment_cols = {row["name"] for row in cursor.fetchall()}
        if "description" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN description TEXT")
        if "due_date" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN due_date TEXT")
        if "submission_rules" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN submission_rules TEXT")
        if "late_policy" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN late_policy TEXT")
        if "status" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN status TEXT DEFAULT 'OPEN'")
        if "created_at" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN created_at TEXT")
        if "updated_at" not in assignment_cols:
            cursor.execute("ALTER TABLE assignments ADD COLUMN updated_at TEXT")

        # 2. Rubrics
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rubrics (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                criterion TEXT NOT NULL,
                max_points REAL NOT NULL,
                description TEXT,
                weight_percentage REAL DEFAULT 20.0,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
            );
            """
        )

        cursor.execute("PRAGMA table_info(rubrics)")
        rubric_cols = {row["name"] for row in cursor.fetchall()}
        if "weight_percentage" not in rubric_cols:
            cursor.execute("ALTER TABLE rubrics ADD COLUMN weight_percentage REAL DEFAULT 20.0")

        # 3. Students
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                course_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )

        # 4. Submissions
        cursor.execute(
            """
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
                rubric_scores TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                published_at TEXT,
                published_by TEXT,
                file_attachment_path TEXT,
                notes TEXT,
                audit_trace_id TEXT,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            """
        )

        cursor.execute("PRAGMA table_info(submissions)")
        sub_cols = {row["name"] for row in cursor.fetchall()}
        if "rubric_scores" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN rubric_scores TEXT")
        if "published_at" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN published_at TEXT")
        if "published_by" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN published_by TEXT")
        if "approved_at" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN approved_at TEXT")
        if "approved_by" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN approved_by TEXT")
        if "file_attachment_path" not in sub_cols:
            cursor.execute("ALTER TABLE submissions ADD COLUMN file_attachment_path TEXT")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_student_asgn ON submissions (student_id, assignment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_asgn ON submissions (assignment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_status ON submissions (status);")

        # 5. Submission Audit Events (legacy table kept compatible)
        cursor.execute(
            """
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
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_submission_audit_submission ON submission_audit_events(submission_id, event_id);"
        )

        # 6. Unified System-Wide Audit Log (NEW - Bug 7 repair)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                details TEXT,
                trace_id TEXT,
                timestamp TEXT NOT NULL
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);")

        # 7. Course Projects (PART 7)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_projects (
                id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                project_type TEXT DEFAULT 'GROUP',
                status TEXT DEFAULT 'IN_PROGRESS',
                progress_percentage REAL DEFAULT 0.0,
                repository_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # 8. Project Members (PART 7)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_members (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                role TEXT DEFAULT 'MEMBER',
                responsibilities TEXT,
                FOREIGN KEY (project_id) REFERENCES course_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            """
        )

        # 9. Project Milestones (PART 7)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_milestones (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT NOT NULL,
                weight_percentage REAL DEFAULT 25.0,
                status TEXT DEFAULT 'NOT_STARTED',
                deliverable_name TEXT,
                deliverable_url TEXT,
                completed_at TEXT,
                comments TEXT,
                FOREIGN KEY (project_id) REFERENCES course_projects(id) ON DELETE CASCADE
            );
            """
        )

        # 10. Project Activity Timeline (PART 7)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES course_projects(id) ON DELETE CASCADE
            );
            """
        )

        # 11. Similarity Reports (PART 6)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS similarity_reports (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                generated_by TEXT NOT NULL,
                status TEXT NOT NULL,
                total_submissions_compared INTEGER NOT NULL,
                highest_similarity_score REAL NOT NULL,
                pairs_json TEXT NOT NULL,
                flagged_count INTEGER NOT NULL,
                summary TEXT NOT NULL
            );
            """
        )

        # 12. Announcements (PART 12)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS announcements (
                id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                posted_by TEXT NOT NULL,
                priority TEXT DEFAULT 'NORMAL',
                created_at TEXT NOT NULL
            );
            """
        )

        # 13. Notifications (PART 12)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_role TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                category TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                link TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);")

        # 14. Governance Tables (Lab 12 - Bug 5 repair)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS governance_resources (
                resource_id TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
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
            """
        )
        cursor.execute(
            """
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
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('STUDENT', 'FACULTY', 'ADMIN')),
                student_id TEXT UNIQUE,
                course_scopes TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at);")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_login_limits (
                address_hash TEXT PRIMARY KEY,
                window_started_at TEXT NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab4_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                current_request TEXT,
                active_plan_id TEXT,
                clarification_answers_json TEXT NOT NULL DEFAULT '[]',
                scratchpad_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab4_sessions_owner_course_expiry "
            "ON lab4_sessions(user_id, course_id, expires_at)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab4_session_turns (
                turn_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES lab4_sessions(session_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab4_turns_session_timestamp "
            "ON lab4_session_turns(session_id, timestamp)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab4_memory_records (
                memory_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab4_memory_owner_course "
            "ON lab4_memory_records(user_id, course_id, created_at)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab4_memory_embeddings (
                memory_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                embedding_dimension INTEGER NOT NULL,
                text_hash TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES lab4_memory_records(memory_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab4_memory_embeddings_scope "
            "ON lab4_memory_embeddings(owner_id, course_id, model_id, model_revision)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab4_submission_embeddings (
                submission_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_revision TEXT NOT NULL,
                embedding_dimension INTEGER NOT NULL,
                text_hash TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab4_submission_embeddings_scope "
            "ON lab4_submission_embeddings(owner_id, course_id, model_id, model_revision)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab6_runtime_runs (
                run_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                owner_role TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab6_runtime_owner_course "
            "ON lab6_runtime_runs(owner_user_id, course_id, updated_at)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab6_runtime_checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                checkpoint_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES lab6_runtime_runs(run_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab6_runtime_checkpoints_run "
            "ON lab6_runtime_checkpoints(run_id, step_index)"
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS lab6_runtime_audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                actor_user_id TEXT,
                actor_role TEXT,
                actor_agent TEXT NOT NULL,
                action TEXT NOT NULL,
                input_summary TEXT NOT NULL,
                output_summary TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                error TEXT,
                occurred_at TEXT NOT NULL,
                UNIQUE(run_id, step_id),
                FOREIGN KEY (run_id) REFERENCES lab6_runtime_runs(run_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab6_runtime_audit_run "
            "ON lab6_runtime_audit_events(run_id, event_id)"
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS material_categories (
                category_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS material_folders (
                folder_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                parent_folder_id TEXT,
                name TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES material_categories(category_id),
                FOREIGN KEY (parent_folder_id) REFERENCES material_folders(folder_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_materials (
                material_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category_id TEXT NOT NULL,
                folder_id TEXT,
                chapter INTEGER,
                lab INTEGER,
                storage_key TEXT NOT NULL UNIQUE,
                original_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
                checksum_sha256 TEXT NOT NULL,
                uploader_id TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES material_categories(category_id),
                FOREIGN KEY (folder_id) REFERENCES material_folders(folder_id) ON DELETE SET NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_workspace_runs (
                run_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                assignment_id TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                request_text TEXT NOT NULL,
                status TEXT NOT NULL,
                package_json TEXT NOT NULL,
                validation_json TEXT NOT NULL,
                approval_user_id TEXT,
                approval_comment TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_workspace_releases (
                release_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                package_json TEXT NOT NULL,
                published_by TEXT NOT NULL,
                published_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                rolled_back INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES course_workspace_runs(run_id),
                UNIQUE (course_id, version)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS course_workspace_audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                actor_user_id TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                details_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES course_workspace_runs(run_id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_workspace_runs_course ON course_workspace_runs(course_id, created_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_workspace_audit_run ON course_workspace_audit_events(run_id, event_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_course_category ON course_materials(course_id, category_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_folder ON course_materials(folder_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_materials_search ON course_materials(course_id, title, description)"
        )

        for category_id, name, sort_order in (
            ("notes", "Notes", 1),
            ("lab-manuals", "Lab Manuals", 2),
            ("lesson-plans", "Lesson Plans", 3),
            ("presentations", "Presentations", 4),
            ("assignments", "Assignments", 5),
            ("question-banks", "Question Banks", 6),
            ("reference-materials", "Reference Materials", 7),
            ("syllabus", "Syllabus and Course Outline", 8),
        ):
            cursor.execute(
                "INSERT OR IGNORE INTO material_categories (category_id, name, sort_order) VALUES (?, ?, ?)",
                (category_id, name, sort_order),
            )

        # Seed initial data if tables are empty
        _seed_foundational_data(conn)


def _seed_foundational_data(conn: sqlite3.Connection) -> None:
    """Populate default enrolled students, assignments, rubrics, announcements, and a sample project if absent."""
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Seed Students
    students_data = [
        ("std-001", "Alice Chen", "alice.chen@university.edu", "26ECAC401", now_iso),
        ("std-002", "Bob Smith", "bob.smith@university.edu", "26ECAC401", now_iso),
        ("std-003", "Charlie Patel", "charlie.patel@university.edu", "26ECAC401", now_iso),
        ("std-004", "Diana Prince", "diana.prince@university.edu", "26ECAC401", now_iso),
    ]
    for sid, name, email, cid, cat in students_data:
        cursor.execute(
            "INSERT OR IGNORE INTO students (id, name, email, course_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (sid, name, email, cid, cat),
        )

    # Seed All 12 Course Labs as assignments in DB
    assignments_data = [
        ("lab1", "26ECAC401", "Lab 1: Clarify-Plan-Revise Agent", 100.0, 8.0, 2, "Implement an Agentic AI Workspace Planner with gap analysis and immutable revision diffs.", "2026-11-20T23:59:59Z", "HTTPS GitHub repository link containing complete solution code and tests.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab2", "26ECAC401", "Lab 2: Tool-Using Agent with Trace", 100.0, 8.0, 3, "Develop a deterministic ReAct tool-using agent with auditable zero-private-token trace.", "2026-11-27T23:59:59Z", "HTTPS GitHub repository link with Pydantic tool schemas and execution history.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab3", "26ECAC401", "Lab 3: Reusable Skills Registry", 100.0, 8.0, 5, "Stateless Pydantic-typed reusable skill modules for planning, research, and formatting.", "2026-12-04T23:59:59Z", "HTTPS GitHub repository link with unit tests.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab4", "26ECAC401", "Lab 4: Memory & Retrieval Architecture", 100.0, 8.0, 7, "Session store and long-term inverted index with anti-hallucination guardrails.", "2026-12-11T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab5", "26ECAC401", "Lab 5: Governed Academic Connector", 100.0, 8.0, 8, "Model Context Protocol style connector with strict role-based access control.", "2026-12-18T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab6", "26ECAC401", "Lab 6: Controlled Agent Runtime", 100.0, 8.0, 9, "Resilient agent execution loop with step budgeting, state checkpointing, and faculty gates.", "2026-12-25T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab7", "26ECAC401", "Lab 7: Agentic Specialist Node Graph", 100.0, 8.0, 10, "10-node Directed Acyclic Graph with explicit state transitions and bounded retries.", "2027-01-01T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab8", "26ECAC401", "Lab 8: Parallel Swarm & Dynamic Fan-Out", 100.0, 8.0, 11, "Concurrent specialist worker dispatch with async fan-out and deterministic fan-in.", "2027-01-08T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab9", "26ECAC401", "Lab 9: Deep Research Agent", 100.0, 8.0, 12, "Deep research evidence verification distinguishing lexical matching from semantic entailment.", "2027-01-15T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab10", "26ECAC401", "Lab 10: Cloud Operations Agent", 100.0, 8.0, 13, "Automated infrastructure health monitoring, failure diagnosis, and gated remediation.", "2027-01-22T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab11", "26ECAC401", "Lab 11: Agentic SDLC Factory", 100.0, 8.0, 14, "Autonomous requirement-to-code synthesis, automated test generation, and test execution.", "2027-01-29T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("lab12", "26ECAC401", "Lab 12: Safety, Governance & Alignment", 100.0, 8.0, 15, "Governed change proposals, multi-factor approval gates, immutable audit trail, and rollback.", "2027-02-05T23:59:59Z", "HTTPS GitHub repository link.", "5% deduction per day up to 3 days late.", "OPEN", now_iso, now_iso),
        ("final_capstone", "26ECAC401", "Agentic AI Capstone Project: CourseAgentAI", 100.0, 20.0, 16, "Comprehensive full-stack course operations multi-agent platform connecting notes, assignments, and projects.", "2027-02-15T23:59:59Z", "Full repository submission with documentation, test reports, and live demonstration.", "Late submissions not permitted for final capstone.", "OPEN", now_iso, now_iso),
    ]

    for row in assignments_data:
        cursor.execute(
            """
            INSERT INTO assignments (id, course_id, title, max_points, weight_percentage, due_week, description, due_date, submission_rules, late_policy, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                description = COALESCE(assignments.description, excluded.description),
                due_date = COALESCE(assignments.due_date, excluded.due_date),
                submission_rules = COALESCE(assignments.submission_rules, excluded.submission_rules),
                late_policy = COALESCE(assignments.late_policy, excluded.late_policy),
                status = COALESCE(assignments.status, excluded.status)
            """,
            row,
        )

    # Seed Rubrics for Assignments
    rubrics_seed = [
        ("rub-l1-1", "lab1", "Ambiguity & Gap Detection", 25.0, "Accurately identifies unestablished constraints and prompts for clarification.", 25.0),
        ("rub-l1-2", "lab1", "Structured Plan Synthesis", 35.0, "Generates modular weekly schedule with topics, assignments, and exam weights.", 35.0),
        ("rub-l1-3", "lab1", "Deterministic Revision Engine", 25.0, "Applies edits without losing existing configuration, computing clean diffs.", 25.0),
        ("rub-l1-4", "lab1", "Test Coverage & Provenance", 15.0, "Full test suite pass rate with traceable version history.", 15.0),

        ("rub-l2-1", "lab2", "Typed Tool Schemas", 30.0, "Strict Pydantic schemas validating inputs and outputs with boundaries.", 30.0),
        ("rub-l2-2", "lab2", "Observable ReAct Loop", 40.0, "Step-by-step Thought -> Action -> Observation with zero hidden tokens.", 40.0),
        ("rub-l2-3", "lab2", "Domain Math Correctness", 30.0, "Exact calculation of grade totals, rubric sums, and workload hours.", 30.0),

        ("rub-cap-1", "final_capstone", "Multi-Agent Architecture", 30.0, "Clean separation of Coordinator, Repository, Distribution, Grading, and Milestone agents.", 30.0),
        ("rub-cap-2", "final_capstone", "Knowledge Management & RAG", 25.0, "Hierarchical folder structure, multi-format text extraction, and grounded search.", 25.0),
        ("rub-cap-3", "final_capstone", "Submissions & Transparent Grading", 25.0, "Verifiable submission validation, similarity checks, and faculty review gates.", 25.0),
        ("rub-cap-4", "final_capstone", "UI/UX & Engineering Polish", 20.0, "Apple-inspired Cupertino UI, full test suite pass, and comprehensive documentation.", 20.0),
    ]
    for rid, aid, crit, pts, desc, wt in rubrics_seed:
        cursor.execute(
            """
            INSERT OR IGNORE INTO rubrics (id, assignment_id, criterion, max_points, description, weight_percentage)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rid, aid, crit, pts, desc, wt),
        )

    # Seed Announcements
    cursor.execute("SELECT COUNT(*) AS cnt FROM announcements")
    if cursor.fetchone()["cnt"] == 0:
        announcements_seed = [
            ("ann-001", "26ECAC401", "Welcome to 26ECAC401: Agentic AI Semester", "Welcome students! All lecture notes (Chapters 1-7), lab specifications (Labs 1-12), and project guidelines are now accessible in the Knowledge Repository. Please inspect the syllabus and initial lab assignments.", "Prof. Course Coordinator", "HIGH", now_iso),
            ("ann-002", "26ECAC401", "Lab 1 Submission Portal Open", "Lab 1 (Clarify-Plan-Revise Agent) is open for GitHub repository submissions. Ensure your repository is public and includes complete test cases.", "Teaching Assistant", "NORMAL", now_iso),
            ("ann-003", "26ECAC401", "Course Project Teams & Milestone 1 Announced", "Course project milestone schedules have been published. Team leads must confirm their member assignments and repository links before Milestone 1 deadline.", "Faculty Reviewer", "URGENT", now_iso),
        ]
        for aid, cid, title, content, author, prio, cat in announcements_seed:
            cursor.execute(
                "INSERT INTO announcements (id, course_id, title, content, posted_by, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (aid, cid, title, content, author, prio, cat),
            )

    # Seed Notifications
    cursor.execute("SELECT COUNT(*) AS cnt FROM notifications")
    if cursor.fetchone()["cnt"] == 0:
        notifs_seed = [
            ("notif-001", "std-001", "STUDENT", "New Assignment Published", "Lab 1: Clarify-Plan-Revise Agent is now available for submission.", "ASSIGNMENT", 0, "/#assignments", now_iso),
            ("notif-002", "std-001", "STUDENT", "Project Milestone Approaching", "Milestone 1: Project Architecture Sign-off is due in 5 days.", "PROJECT", 0, "/#projects", now_iso),
            ("notif-003", "prof_faculty", "FACULTY", "New Student Submissions Pending Review", "3 new student submissions are queued in the Faculty Review Portal.", "SUBMISSION", 0, "/#faculty-review", now_iso),
        ]
        for nid, uid, urole, title, msg, cat, is_r, lnk, cat_at in notifs_seed:
            cursor.execute(
                "INSERT INTO notifications (id, user_id, user_role, title, message, category, is_read, link, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (nid, uid, urole, title, msg, cat, is_r, lnk, cat_at),
            )

    # Seed Sample Course Project (PART 7)
    cursor.execute("SELECT COUNT(*) AS cnt FROM course_projects")
    if cursor.fetchone()["cnt"] == 0:
        proj_id = "proj-team-alpha"
        cursor.execute(
            """
            INSERT INTO course_projects (id, course_id, title, description, project_type, status, progress_percentage, repository_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proj_id,
                "26ECAC401",
                "CourseAgentAI: Autonomous Multi-Agent Academic Operations Suite",
                "Flagship course management agentic system integrating course knowledge, assignment evaluation, similarity review, and milestone tracking.",
                "GROUP",
                "IN_PROGRESS",
                65.0,
                "https://github.com/CourseAgentAI/CourseAgentAI",
                now_iso,
                now_iso,
            ),
        )

        members = [
            ("mem-001", proj_id, "std-001", "Alice Chen", "LEAD", "Multi-agent coordination, node graph architecture, and testing"),
            ("mem-002", proj_id, "std-002", "Bob Smith", "DEVELOPER", "Backend REST APIs, SQLite persistent schema, and GitHub validator"),
            ("mem-003", proj_id, "std-003", "Charlie Patel", "RESEARCHER", "Knowledge extraction, BM25 indexing, and AI Assistant RAG"),
            ("mem-004", proj_id, "std-004", "Diana Prince", "TESTER", "Regression testing, similarity evaluation, and documentation"),
        ]
        for mid, pid, sid, sname, role, resp in members:
            cursor.execute(
                "INSERT INTO project_members (id, project_id, student_id, student_name, role, responsibilities) VALUES (?, ?, ?, ?, ?, ?)",
                (mid, pid, sid, sname, role, resp),
            )

        milestones = [
            ("ms-001", proj_id, "Milestone 1: Problem Statement & Architecture Design", "System specification, agent role breakdown, and database entity models.", "2026-11-25T23:59:59Z", 25.0, "COMPLETED", "Architecture Specification Document", "https://github.com/CourseAgentAI/CourseAgentAI/blob/main/ARCHITECTURE.md", now_iso, "Approved with high commendation for modular structure."),
            ("ms-002", proj_id, "Milestone 2: Knowledge RAG & ReAct Tools Implementation", "Hierarchical file discovery, BM25 retriever, and 9 deterministic Pydantic tools.", "2026-12-15T23:59:59Z", 25.0, "COMPLETED", "Working Knowledge & Tool Engine", "https://github.com/CourseAgentAI/CourseAgentAI/tree/main/app/knowledge", now_iso, "Passed all 250 unit and integration tests."),
            ("ms-003", proj_id, "Milestone 3: Node Graph, Swarm & Submissions Workflow", "Stateful 10-node DAG, parallel swarm fan-out, and verified GitHub submission portal.", "2027-01-10T23:59:59Z", 25.0, "IN_PROGRESS", "Submissions & Orchestration Engine", "https://github.com/CourseAgentAI/CourseAgentAI", None, "Currently undergoing final regression checks."),
            ("ms-004", proj_id, "Milestone 4: Final Capstone Defense & Complete Submission Package", "Full submission package, final report, user manual, and live evaluation.", "2027-02-15T23:59:59Z", 25.0, "NOT_STARTED", "Final Report & Video Demo", None, None, "Scheduled for final semester defense."),
        ]
        for ms_id, pid, title, desc, due, wt, status, dname, durl, comp_at, comm in milestones:
            cursor.execute(
                """
                INSERT INTO project_milestones (id, project_id, title, description, due_date, weight_percentage, status, deliverable_name, deliverable_url, completed_at, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ms_id, pid, title, desc, due, wt, status, dname, durl, comp_at, comm),
            )

        activities = [
            (proj_id, "Alice Chen", "INITIALIZED_PROJECT", "Created project repository and team workspace", now_iso),
            (proj_id, "Bob Smith", "SUBMITTED_MILESTONE_1", "Completed Milestone 1 architecture design", now_iso),
            (proj_id, "Charlie Patel", "SUBMITTED_MILESTONE_2", "Integrated BM25 course knowledge indexer", now_iso),
            (proj_id, "Prof. Evaluator", "APPROVED_MILESTONE", "Approved Milestone 1 & 2 with distinction", now_iso),
        ]
        for pid, actor, action, details, ts in activities:
            cursor.execute(
                "INSERT INTO project_activity (project_id, actor, action, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                (pid, actor, action, details, ts),
            )
