"""Course-scoped persistent preparation, validation, approval, release, and rollback."""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.data.db import get_db_connection
from app.knowledge.service import knowledge_service
from app.services.course_materials import list_materials
from app.services.project_service import project_service
from app.services.similarity_service import similarity_service
from app.services.submission_service import submission_service


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_run(row: Any) -> dict[str, Any]:
    result = dict(row)
    result["package"] = json.loads(result.pop("package_json"))
    result["validation"] = json.loads(result.pop("validation_json"))
    return result


class CourseCapstoneService:
    """Coordinates existing course services without bypassing their authorization APIs."""

    def create_run(
        self,
        *,
        course_id: str,
        assignment_id: str,
        request_text: str,
        actor_user_id: str,
        actor_role: str,
    ) -> dict[str, Any]:
        assignments = submission_service.list_assignments(course_id=course_id)
        assignment = next((item for item in assignments if item.id == assignment_id), None)
        if assignment is None:
            raise LookupError("Assignment was not found in the authorized course.")

        materials = list_materials(course_id=course_id, limit=200)["items"]
        evidence_result = knowledge_service.search(
            request_text,
            course_id=course_id,
            top_k=5,
        )
        evidence = [
            {
                "chunk_id": match.chunk_id,
                "source_document": match.source_document,
                "source_location": match.source_location,
                "citation": match.source,
                "material_id": match.material_id,
                "category": match.category,
                "folder_path": match.folder_path,
                "excerpt": match.matched_text[:700],
            }
            for match in evidence_result.matches
        ]
        projects = project_service.list_projects(course_id=course_id)

        with get_db_connection() as conn:
            rubric_rows = conn.execute(
                "SELECT criterion, max_points, weight_percentage FROM rubrics WHERE assignment_id = ? ORDER BY id",
                (assignment_id,),
            ).fetchall()
            submissions = conn.execute(
                """
                SELECT s.id, s.student_id, s.status, s.validation_status,
                       s.validation_details, s.submission_timestamp,
                       s.review_status, s.review_score, s.approved_by,
                       s.approved_at, s.published_by, s.published_at,
                       a.max_points, a.due_date
                FROM submissions s
                JOIN assignments a ON a.id = s.assignment_id
                WHERE s.assignment_id = ? AND s.course_id = ? AND s.is_latest = 1
                ORDER BY s.submission_timestamp, s.id
                """,
                (assignment_id, course_id),
            ).fetchall()
            milestones_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM project_milestones m
                JOIN course_projects p ON p.id = m.project_id
                WHERE p.course_id = ?
                """,
                (course_id,),
            ).fetchone()["count"]

        similarity_report = None
        if len(submissions) >= 2:
            similarity_report = similarity_service.run_similarity_check(
                assignment_id=assignment_id,
                actor=actor_user_id,
                actor_role=actor_role,
            )

        late_checks = []
        grade_checks = []
        published_grade_checks = []
        for submission in submissions:
            try:
                details = json.loads(submission["validation_details"] or "{}")
            except (TypeError, json.JSONDecodeError):
                details = {}
            due_date = submission["due_date"]
            if due_date:
                try:
                    due_at = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    submitted_at = datetime.fromisoformat(
                        submission["submission_timestamp"].replace("Z", "+00:00")
                    )
                    if due_at.tzinfo is None:
                        due_at = due_at.replace(tzinfo=timezone.utc)
                    if submitted_at.tzinfo is None:
                        submitted_at = submitted_at.replace(tzinfo=timezone.utc)
                    expected_late = submitted_at > due_at
                    marked_late = submission["status"] == "LATE"
                    declared_late = details.get("is_late")
                    late_checks.append(
                        marked_late == expected_late
                        and (declared_late is None or bool(declared_late) == expected_late)
                    )
                except (TypeError, ValueError):
                    late_checks.append(False)
            else:
                late_checks.append(
                    submission["status"] != "LATE"
                    and details.get("is_late") is not True
                )
            grade = submission["review_score"]
            grade_checks.append(
                grade is None
                or 0 <= float(grade) <= float(submission["max_points"])
            )
            if submission["published_at"]:
                published_grade_checks.append(
                    bool(submission["approved_by"] and submission["approved_at"] and submission["published_by"])
                )

        project_summaries = [
            {
                "project_id": project["id"],
                "title": project["title"],
                "status": project["status"],
                "total_milestones": project["total_milestones"],
                "completed_milestones": project["completed_milestones"],
            }
            for project in projects
        ]
        checks = [
            {
                "check_id": "authorized_course_evidence",
                "passed": bool(evidence),
                "observed": len(evidence),
                "required": "at least one cited source from the authorized course index",
            },
            {
                "check_id": "organized_course_materials",
                "passed": bool(materials),
                "observed": len(materials),
                "required": "at least one database-backed material in the course library",
            },
            {
                "check_id": "assignment_and_rubric",
                "passed": bool(rubric_rows)
                and abs(sum(float(row["max_points"]) for row in rubric_rows) - float(assignment.max_points)) < 0.01
                and abs(sum(float(row["weight_percentage"] or 0) for row in rubric_rows) - 100.0) < 0.01,
                "observed": {
                    "assignment_id": assignment.id,
                    "rubric_criteria": len(rubric_rows),
                    "rubric_points": sum(float(row["max_points"]) for row in rubric_rows),
                    "rubric_weight_percentage": sum(float(row["weight_percentage"] or 0) for row in rubric_rows),
                    "assignment_max_points": float(assignment.max_points),
                },
                "required": "rubric criteria sum to assignment maximum points and 100% weight",
            },
            {
                "check_id": "project_checkpoints",
                "passed": int(milestones_count) >= 2,
                "observed": int(milestones_count),
                "required": "at least two course project milestones",
            },
            {
                "check_id": "submission_cycle_and_similarity",
                "passed": len(submissions) >= 2 and similarity_report is not None,
                "observed": {
                    "latest_submissions": len(submissions),
                    "similarity_status": similarity_report.get("status") if similarity_report else "NOT_RUN",
                },
                "required": "at least two latest submissions and a persisted similarity comparison",
            },
            {
                "check_id": "late_flags_consistent",
                "passed": all(late_checks),
                "observed": len(late_checks),
                "required": "every latest submission's late flag agrees with its status",
            },
            {
                "check_id": "grades_within_maximum",
                "passed": all(grade_checks),
                "observed": len(grade_checks),
                "required": "no recorded grade exceeds its assignment maximum",
            },
            {
                "check_id": "published_grades_approved",
                "passed": all(published_grade_checks),
                "observed": len(published_grade_checks),
                "required": "every published grade has approval and publisher attribution",
            },
        ]
        ready = all(check["passed"] for check in checks)
        run_id = f"cap-{uuid.uuid4().hex[:12]}"
        occurred_at = _now()
        package = {
            "course_id": course_id,
            "request": request_text,
            "assignment": assignment.model_dump(),
            "rubric": [dict(row) for row in rubric_rows],
            "materials": [
                {
                    "material_id": item["material_id"],
                    "title": item["title"],
                    "category_id": item["category_id"],
                    "folder_id": item["folder_id"],
                    "file_type": item["extension"],
                }
                for item in materials
            ],
            "evidence": evidence,
            "submissions": [
                {
                    "submission_id": row["id"],
                    "status": row["status"],
                    "validation_status": row["validation_status"],
                    "review_status": row["review_status"],
                    "review_score": row["review_score"],
                    "approved": bool(row["approved_by"] and row["approved_at"]),
                    "published": bool(row["published_at"] and row["published_by"]),
                }
                for row in submissions
            ],
            "similarity": similarity_report,
            "projects": project_summaries,
            "disclosure": {
                "similarity_is_candidate_review_evidence": True,
                "repository_source_code_was_fetched": False,
                "external_services_contacted": False,
                "automated_grading_performed": False,
            },
            "governance": {
                "release_policy": "Only authenticated course faculty can publish a validation-passing run.",
                "student_view": "Individual submissions, grades, and similarity pairs are redacted from student release reads.",
                "risk_register": [
                    {
                        "risk": "Lexical similarity can over- or under-estimate overlap and does not inspect repository contents.",
                        "mitigation": "Use the report only as candidate evidence for faculty review.",
                    },
                    {
                        "risk": "Retrieved citations may be relevant candidates without proving a claim.",
                        "mitigation": "Retain source locations and require human review; no entailment is asserted.",
                    },
                    {
                        "risk": "Course submissions contain private academic records.",
                        "mitigation": "Course authorization is enforced and student-facing release data omits individual submissions and scores.",
                    },
                ],
                "evaluation_metrics": {
                    "checks_total": len(checks),
                    "checks_passed": sum(check["passed"] for check in checks),
                    "checks_failed": sum(not check["passed"] for check in checks),
                    "evidence_citations": len(evidence),
                },
            },
        }
        status = "READY_FOR_FACULTY_APPROVAL" if ready else "VALIDATION_FAILED"

        with get_db_connection(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO course_workspace_runs(
                    run_id, course_id, assignment_id, owner_user_id, request_text,
                    status, package_json, validation_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    course_id,
                    assignment_id,
                    actor_user_id,
                    request_text,
                    status,
                    json.dumps(package, sort_keys=True),
                    json.dumps({"passed": ready, "checks": checks}, sort_keys=True),
                    occurred_at,
                    occurred_at,
                ),
            )
            self._audit(
                conn,
                run_id,
                course_id,
                actor_user_id,
                actor_role,
                "RUN_CREATED",
                {"status": status, "validation_passed": ready},
                occurred_at,
            )
        return self.get_run(run_id)

    @staticmethod
    def _audit(
        conn,
        run_id: str,
        course_id: str,
        actor_user_id: str,
        actor_role: str,
        action: str,
        details: dict[str, Any],
        occurred_at: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO course_workspace_audit_events(
                run_id, course_id, actor_user_id, actor_role, action, details_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                course_id,
                actor_user_id,
                actor_role,
                action,
                json.dumps(details, sort_keys=True),
                occurred_at,
            ),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM course_workspace_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _decode_run(row) if row else None

    def list_audit(self, run_id: str) -> list[dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT event_id, actor_user_id, actor_role, action, details_json, occurred_at
                FROM course_workspace_audit_events WHERE run_id = ? ORDER BY event_id
                """,
                (run_id,),
            ).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["details"] = json.loads(event.pop("details_json"))
        return events

    def approve(self, run_id: str, actor_user_id: str, comment: str = "") -> dict[str, Any]:
        now = _now()
        with get_db_connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM course_workspace_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Course workspace run was not found.")
            run = _decode_run(row)
            if run["status"] != "READY_FOR_FACULTY_APPROVAL" or not run["validation"]["passed"]:
                raise ValueError("A failed validation run cannot be approved or published.")
            version_row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM course_workspace_releases WHERE course_id = ?",
                (run["course_id"],),
            ).fetchone()
            version = int(version_row["version"]) + 1
            release_id = f"release-{uuid.uuid4().hex[:12]}"
            conn.execute(
                "UPDATE course_workspace_releases SET is_active = 0 WHERE course_id = ? AND is_active = 1",
                (run["course_id"],),
            )
            conn.execute(
                """
                INSERT INTO course_workspace_releases(
                    release_id, course_id, run_id, version, package_json,
                    published_by, published_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    release_id,
                    run["course_id"],
                    run_id,
                    version,
                    json.dumps(run["package"], sort_keys=True),
                    actor_user_id,
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE course_workspace_runs
                SET status = 'PUBLISHED', approval_user_id = ?, approval_comment = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (actor_user_id, comment, now, run_id),
            )
            self._audit(
                conn,
                run_id,
                run["course_id"],
                actor_user_id,
                "FACULTY",
                "RELEASE_PUBLISHED",
                {"release_id": release_id, "version": version, "comment": comment},
                now,
            )
        return self.get_release(release_id)

    def reject(self, run_id: str, actor_user_id: str, comment: str = "") -> dict[str, Any]:
        now = _now()
        with get_db_connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM course_workspace_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Course workspace run was not found.")
            run = _decode_run(row)
            if run["status"] != "READY_FOR_FACULTY_APPROVAL":
                raise ValueError("Only a validated run can be rejected from faculty review.")
            conn.execute(
                """
                UPDATE course_workspace_runs
                SET status = 'REJECTED', approval_user_id = ?, approval_comment = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (actor_user_id, comment, now, run_id),
            )
            self._audit(
                conn,
                run_id,
                run["course_id"],
                actor_user_id,
                "FACULTY",
                "RELEASE_REJECTED",
                {"comment": comment},
                now,
            )
        return self.get_run(run_id)

    def get_release(self, release_id: str) -> dict[str, Any] | None:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM course_workspace_releases WHERE release_id = ?",
                (release_id,),
            ).fetchone()
        if row is None:
            return None
        release = dict(row)
        release["package"] = json.loads(release.pop("package_json"))
        return release

    def current_release(
        self,
        course_id: str,
        *,
        public_view: bool = False,
    ) -> dict[str, Any] | None:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM course_workspace_releases
                WHERE course_id = ? AND is_active = 1
                ORDER BY version DESC LIMIT 1
                """,
                (course_id,),
            ).fetchone()
        if row is None:
            return None
        release = dict(row)
        release["package"] = json.loads(release.pop("package_json"))
        if public_view:
            package = deepcopy(release["package"])
            submission_records = package.pop("submissions", [])
            package["submission_summary"] = {
                "count": len(submission_records),
                "notice": "Individual submissions, grades, and review details are private to the student and authorized faculty.",
            }
            similarity = package.get("similarity")
            package["similarity"] = (
                {
                    "status": similarity.get("status"),
                    "flagged_count": similarity.get("flagged_count"),
                    "notice": "Similarity details are faculty-only candidate evidence, not a finding of misconduct.",
                }
                if similarity
                else None
            )
            release["package"] = package
        return release

    def rollback(self, release_id: str, actor_user_id: str) -> dict[str, Any] | None:
        now = _now()
        with get_db_connection(immediate=True) as conn:
            row = conn.execute(
                "SELECT * FROM course_workspace_releases WHERE release_id = ?",
                (release_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Course workspace release was not found.")
            release = dict(row)
            if not release["is_active"] or release["rolled_back"]:
                raise ValueError("Only the current active release can be rolled back.")
            conn.execute(
                """
                UPDATE course_workspace_releases
                SET is_active = 0, rolled_back = 1
                WHERE release_id = ?
                """,
                (release_id,),
            )
            previous = conn.execute(
                """
                SELECT release_id FROM course_workspace_releases
                WHERE course_id = ? AND version < ? AND rolled_back = 0
                ORDER BY version DESC LIMIT 1
                """,
                (release["course_id"], release["version"]),
            ).fetchone()
            if previous:
                conn.execute(
                    "UPDATE course_workspace_releases SET is_active = 1 WHERE release_id = ?",
                    (previous["release_id"],),
                )
            self._audit(
                conn,
                release["run_id"],
                release["course_id"],
                actor_user_id,
                "FACULTY",
                "RELEASE_ROLLED_BACK",
                {
                    "release_id": release_id,
                    "version": release["version"],
                    "restored_release_id": previous["release_id"] if previous else None,
                },
                now,
            )
        return self.current_release(release["course_id"])


capstone_service = CourseCapstoneService()
