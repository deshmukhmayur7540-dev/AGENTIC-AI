"""Course Project Management Service for CourseAgentAI (Part 7)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.data.db import get_db_connection
from app.services.audit_service import audit_service
from app.services.notification_service import insert_notification

logger = logging.getLogger(__name__)


def _notify_project_members(
    conn,
    project_id: str,
    *,
    actor_student_id: str | None,
    title: str,
    message: str,
) -> None:
    members = conn.execute(
        "SELECT DISTINCT student_id FROM project_members WHERE project_id = ?",
        (project_id,),
    ).fetchall()
    for member in members:
        student_id = member["student_id"]
        if student_id == actor_student_id:
            continue
        insert_notification(
            conn,
            user_id=student_id,
            user_role="STUDENT",
            title=title,
            message=message,
            category="PROJECT",
            link="/#projects",
        )


class ProjectService:
    """Manages course projects, team allocations, milestones, deliverables, and progress tracking."""

    def list_projects(self, course_id: str = "26ECAC401") -> list[dict[str, Any]]:
        """Retrieve all course projects with summary statistics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.*,
                       (SELECT COUNT(*) FROM project_members m WHERE m.project_id = p.id) AS member_count,
                       (SELECT COUNT(*) FROM project_milestones ms WHERE ms.project_id = p.id) AS total_milestones,
                       (SELECT COUNT(*) FROM project_milestones ms WHERE ms.project_id = p.id AND ms.status = 'COMPLETED') AS completed_milestones
                FROM course_projects p
                WHERE p.course_id = ?
                ORDER BY p.created_at DESC
                """,
                (course_id,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        """Retrieve full project details with members, milestones, and timeline activity."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM course_projects WHERE id = ?", (project_id,))
            proj_row = cursor.fetchone()
            if not proj_row:
                return None

            project = dict(proj_row)

            # Members
            cursor.execute("SELECT * FROM project_members WHERE project_id = ? ORDER BY id ASC", (project_id,))
            project["members"] = [dict(r) for r in cursor.fetchall()]

            # Milestones
            cursor.execute("SELECT * FROM project_milestones WHERE project_id = ? ORDER BY due_date ASC", (project_id,))
            project["milestones"] = [dict(r) for r in cursor.fetchall()]

            # Activity
            cursor.execute("SELECT * FROM project_activity WHERE project_id = ? ORDER BY timestamp DESC LIMIT 20", (project_id,))
            project["activity"] = [dict(r) for r in cursor.fetchall()]

            # Determine next required action
            pending_ms = [m for m in project["milestones"] if m["status"] != "COMPLETED"]
            project["next_action"] = (
                f"Work on '{pending_ms[0]['title']}' (Due {pending_ms[0]['due_date'][:10]})"
                if pending_ms
                else "All milestones completed! Prepare final project defense."
            )

            return project

    def create_project(
        self,
        title: str,
        description: str,
        course_id: str = "26ECAC401",
        project_type: str = "GROUP",
        repository_url: Optional[str] = None,
        members: Optional[list[dict[str, Any]]] = None,
        milestones: Optional[list[dict[str, Any]]] = None,
        actor: str = "faculty",
        actor_role: str = "FACULTY",
    ) -> dict[str, Any]:
        """Create a new course project with assigned members and milestones."""
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db_connection(immediate=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO course_projects (id, course_id, title, description, project_type, status, progress_percentage, repository_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, course_id, title, description, project_type, "IN_PROGRESS", 0.0, repository_url, now_iso, now_iso),
            )

            # Add Members
            if members:
                for m in members:
                    mid = f"mem-{uuid.uuid4().hex[:6]}"
                    cursor.execute(
                        """
                        INSERT INTO project_members (id, project_id, student_id, student_name, role, responsibilities)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (mid, project_id, m["student_id"], m.get("student_name", "Student"), m.get("role", "MEMBER"), m.get("responsibilities", "")),
                    )

            # Add Milestones
            if milestones:
                for idx, ms in enumerate(milestones):
                    ms_id = f"ms-{project_id}-{idx+1}"
                    cursor.execute(
                        """
                        INSERT INTO project_milestones (id, project_id, title, description, due_date, weight_percentage, status, deliverable_name, deliverable_url, completed_at, comments)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            ms_id,
                            project_id,
                            ms.get("title", f"Milestone {idx+1}"),
                            ms.get("description", ""),
                            ms.get("due_date", now_iso),
                            float(ms.get("weight_percentage", 25.0)),
                            ms.get("status", "NOT_STARTED"),
                            ms.get("deliverable_name"),
                            ms.get("deliverable_url"),
                            None,
                            None,
                        ),
                    )

            # Log Activity
            cursor.execute(
                """
                INSERT INTO project_activity (project_id, actor, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, actor, "CREATED_PROJECT", f"Created project '{title}'", now_iso),
            )

        audit_service.log_event(
            event_type="PROJECT_CREATED",
            actor=actor,
            actor_role=actor_role,
            resource=f"project:{project_id}",
            action="CREATE_PROJECT",
            outcome="SUCCESS",
            details={"title": title, "type": project_type},
        )

        return self.get_project(project_id) or {"id": project_id, "title": title}

    def update_milestone(
        self,
        project_id: str,
        milestone_id: str,
        status: Optional[str] = None,
        deliverable_name: Optional[str] = None,
        deliverable_url: Optional[str] = None,
        comments: Optional[str] = None,
        actor: str = "faculty",
        actor_role: str = "FACULTY",
        actor_student_id: str | None = None,
    ) -> dict[str, Any]:
        """Update milestone status, record deliverables, and recalculate team progress."""
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db_connection(immediate=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM project_milestones WHERE id = ? AND project_id = ?", (milestone_id, project_id))
            ms_row = cursor.fetchone()
            if not ms_row:
                raise ValueError(f"Milestone '{milestone_id}' not found for project '{project_id}'.")

            current_status = status or ms_row["status"]
            completed_at = now_iso if current_status == "COMPLETED" else ms_row["completed_at"]

            cursor.execute(
                """
                UPDATE project_milestones SET
                    status = COALESCE(?, status),
                    deliverable_name = COALESCE(?, deliverable_name),
                    deliverable_url = COALESCE(?, deliverable_url),
                    comments = COALESCE(?, comments),
                    completed_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (status, deliverable_name, deliverable_url, comments, completed_at, milestone_id, project_id),
            )

            # Recalculate overall project progress
            cursor.execute("SELECT weight_percentage, status FROM project_milestones WHERE project_id = ?", (project_id,))
            all_ms = cursor.fetchall()
            total_weight = sum(r["weight_percentage"] for r in all_ms) or 100.0
            completed_weight = sum(r["weight_percentage"] for r in all_ms if r["status"] == "COMPLETED")
            progress_pct = round((completed_weight / total_weight) * 100.0, 1) if total_weight > 0 else 0.0

            cursor.execute(
                "UPDATE course_projects SET progress_percentage = ?, updated_at = ? WHERE id = ?",
                (progress_pct, now_iso, project_id),
            )

            cursor.execute(
                """
                INSERT INTO project_activity (project_id, actor, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, actor, f"MILESTONE_{current_status}", f"Milestone '{ms_row['title']}' updated to {current_status}", now_iso),
            )
            project_row = cursor.execute(
                "SELECT title FROM course_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            _notify_project_members(
                conn,
                project_id,
                actor_student_id=actor_student_id,
                title="Project milestone updated",
                message=f"Milestone '{ms_row['title']}' was updated to {current_status} in project '{project_row['title']}'.",
            )

        audit_service.log_event(
            event_type="PROJECT_MILESTONE_UPDATED",
            actor=actor,
            actor_role=actor_role,
            resource=f"project:{project_id}:milestone:{milestone_id}",
            action="UPDATE_MILESTONE",
            outcome=current_status,
            details={"milestone_id": milestone_id, "new_status": current_status, "progress": progress_pct},
        )

        return self.get_project(project_id) or {"project_id": project_id, "progress": progress_pct}

    def add_milestone_comment(
        self,
        project_id: str,
        milestone_id: str,
        comment: str,
        actor: str = "faculty",
        actor_student_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a review comment or guidance to a milestone."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(immediate=True) as conn:
            cursor = conn.cursor()
            milestone = cursor.execute(
                "SELECT title FROM project_milestones WHERE id = ? AND project_id = ?",
                (milestone_id, project_id),
            ).fetchone()
            if milestone is None:
                raise ValueError(f"Milestone '{milestone_id}' not found for project '{project_id}'.")
            cursor.execute(
                """
                UPDATE project_milestones SET
                    comments = CASE WHEN comments IS NULL OR comments = '' THEN ? ELSE comments || '\n[' || ? || ' - ' || ? || ']: ' || ? END
                WHERE id = ? AND project_id = ?
                """,
                (f"[{actor} - {now_iso[:16]}]: {comment}", actor, now_iso[:16], comment, milestone_id, project_id),
            )
            cursor.execute(
                """
                INSERT INTO project_activity (project_id, actor, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, actor, "COMMENT_POSTED", f"Comment on milestone: {comment[:80]}", now_iso),
            )
            project_row = cursor.execute(
                "SELECT title FROM course_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            _notify_project_members(
                conn,
                project_id,
                actor_student_id=actor_student_id,
                title="New project milestone comment",
                message=f"A new comment was posted on milestone '{milestone['title']}' in project '{project_row['title']}'.",
            )
        return self.get_project(project_id) or {}

    def get_dashboard_summary(self, course_id: str = "26ECAC401") -> dict[str, Any]:
        """Aggregate course-wide project health metrics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM course_projects WHERE course_id = ?", (course_id,))
            total_projects = cursor.fetchone()["total"]

            cursor.execute("SELECT AVG(progress_percentage) AS avg_prog FROM course_projects WHERE course_id = ?", (course_id,))
            avg_prog = cursor.fetchone()["avg_prog"] or 0.0

            cursor.execute(
                """
                SELECT COUNT(*) AS overdue FROM project_milestones ms
                JOIN course_projects p ON ms.project_id = p.id
                WHERE p.course_id = ? AND ms.status != 'COMPLETED' AND ms.due_date < datetime('now')
                """,
                (course_id,),
            )
            overdue_ms = cursor.fetchone()["overdue"]

            cursor.execute(
                """
                SELECT ms.title, ms.due_date, ms.status, p.title as project_title, p.id as project_id
                FROM project_milestones ms
                JOIN course_projects p ON ms.project_id = p.id
                WHERE p.course_id = ? AND ms.status != 'COMPLETED'
                ORDER BY ms.due_date ASC LIMIT 5
                """,
                (course_id,),
            )
            upcoming = [dict(r) for r in cursor.fetchall()]

            return {
                "course_id": course_id,
                "total_projects": total_projects,
                "average_progress": round(avg_prog, 1),
                "overdue_milestones_count": overdue_ms,
                "upcoming_milestones": upcoming,
            }


project_service = ProjectService()
