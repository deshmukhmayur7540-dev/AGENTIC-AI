"""SubmissionService: Mediates all student GitHub submissions and faculty reviews.

Enforces:
- Defense-in-depth URL structure validation
- Student enrollment and assignment eligibility verification
- Resubmission versioning (attempt counting and latest submission pointer)
- Deadline and faculty late policy calculation
- Remote GitHub reachability check with safe error handling and zero token leakage
- Role-based isolation (students can only see their own work; faculty review rights)
- Persistent SQLite storage mediated by the Governed Connector
"""

from datetime import datetime, timezone
import json
import logging
import uuid
from typing import Any, Optional
from config import settings
from app.data.db import get_db_connection
from app.labs.lab5.governed_connector import governed_connector
from app.models.lab5_models import ConnectorOperation, ConnectorRequest, ConnectorRole
from app.models.submission_models import (
    AssignmentOut,
    GitHubSubmissionRequest,
    StudentOut,
    SubmissionRecord,
    SubmissionReviewRequest,
    SubmissionStatus,
)
from app.services.github_validator import (
    check_remote_repository_access,
    validate_github_url,
)
from app.services.audit_service import audit_service
from app.services.notification_service import insert_notification

logger = logging.getLogger(__name__)

LEGACY_REVIEW_STATUS_MAP = {
    "PENDING": "PENDING",
    "REVIEWED": "DRAFT_GRADED",
    "RESUBMISSION_REQUESTED": "RETURNED_FOR_REVISION",
}


class SubmissionTransitionError(ValueError):
    """Raised when a submission review or publication transition is not allowed."""


class SubmissionService:
    """Core domain service for assignment submissions and review workflows."""

    def __init__(self) -> None:
        self._connector = governed_connector

    def list_assignments(self, course_id: str = "26ECAC401") -> list[AssignmentOut]:
        """Retrieve all assignments for a course."""
        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="assignments",
            parameters={"course_id": course_id},
            client_role=ConnectorRole.STUDENT,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return []
        
        assignments = []
        for row in res.data:
            assignments.append(AssignmentOut(
                id=row["id"],
                course_id=row.get("course_id", course_id),
                title=row.get("title", ""),
                max_points=row.get("max_points", 100),
                weight_percentage=float(row.get("weight_percentage", 10.0)),
                due_week=row.get("due_week", 1),
                description=row.get("description"),
                due_date=row.get("due_date"),
                submission_rules=row.get("submission_rules"),
                late_policy=row.get("late_policy"),
                status=row.get("status", "OPEN"),
            ))
        return assignments

    def get_assignment(self, assignment_id: str) -> Optional[AssignmentOut]:
        """Retrieve details of a single assignment by ID."""
        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.READ,
            resource_path="assignments",
            parameters={"id": assignment_id},
            client_role=ConnectorRole.STUDENT,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return None
        row = res.data
        return AssignmentOut(
            id=row["id"],
            course_id=row.get("course_id", "26ECAC401"),
            title=row.get("title", ""),
            max_points=row.get("max_points", 100),
            weight_percentage=float(row.get("weight_percentage", 10.0)),
            due_week=row.get("due_week", 1),
            description=row.get("description"),
            due_date=row.get("due_date"),
            submission_rules=row.get("submission_rules"),
            late_policy=row.get("late_policy"),
            status=row.get("status", "OPEN"),
        )

    def list_students(self, course_id: str = "26ECAC401") -> list[StudentOut]:
        """Retrieve enrolled students."""
        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="students",
            parameters={"course_id": course_id},
            client_role=ConnectorRole.STUDENT,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return []
        return [
            StudentOut(
                id=r["id"],
                name=r["name"],
                email=r["email"],
                course_id=r["course_id"],
                created_at=r["created_at"],
            )
            for r in res.data
        ]

    def get_student(self, student_id: str) -> Optional[StudentOut]:
        """Retrieve student record by ID."""
        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.READ,
            resource_path="students",
            parameters={"id": student_id},
            client_role=ConnectorRole.STUDENT,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return None
        r = res.data
        return StudentOut(
            id=r["id"],
            name=r["name"],
            email=r["email"],
            course_id=r["course_id"],
            created_at=r["created_at"],
        )

    async def submit_assignment(
        self,
        request: GitHubSubmissionRequest,
        actor_role: str = "STUDENT",
    ) -> SubmissionRecord:
        """Submit a student solution repository URL for an assignment."""
        # 1. Verify student exists
        student = self.get_student(request.student_id)
        if not student:
            raise ValueError(f"Student ID '{request.student_id}' is not enrolled in the course.")

        # 2. Verify assignment exists and is open
        assignment = self.get_assignment(request.assignment_id)
        if not assignment:
            raise ValueError(f"Assignment '{request.assignment_id}' not found.")
        if assignment.status.upper() != "OPEN":
            raise ValueError(f"Assignment '{assignment.title}' is closed for submissions.")

        # 3. Validate GitHub repository URL
        validation_res = validate_github_url(request.repository_url)
        if not validation_res.is_valid:
            raise ValueError(validation_res.error_message)

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        # 4. Check deadline & late-submission policy
        status = SubmissionStatus.SUBMITTED.value
        validation_details = dict(validation_res.details)
        
        if assignment.due_date:
            try:
                # Parse ISO timestamp
                due_dt = datetime.fromisoformat(assignment.due_date.replace("Z", "+00:00"))
                if now_dt > due_dt:
                    status = SubmissionStatus.LATE.value
                    validation_details["is_late"] = True
                    validation_details["deadline"] = assignment.due_date
                    validation_details["submitted_at"] = now_iso
                    validation_details["late_policy"] = assignment.late_policy or "Late submission policy unestablished"
                else:
                    validation_details["is_late"] = False
                    validation_details["deadline"] = assignment.due_date
            except Exception as exc:
                logger.warning("Could not parse due_date '%s': %s", assignment.due_date, exc)
                validation_details["due_date_unparseable"] = str(exc)
        else:
            validation_details["deadline_status"] = "UNESTABLISHED"

        # 5. Remote reachability check (non-blocking / safe)
        reach_status, reach_details = await check_remote_repository_access(
            owner=validation_res.owner,
            repo=validation_res.repo,
            token=settings.github_token or None,
            timeout_seconds=3.0,
        )
        validation_details["remote_check"] = reach_details
        val_status = "PASSED" if reach_status == "PASSED" else "WARNING"

        # 6. Query existing submissions to determine attempt number
        req_list = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="submissions",
            parameters={
                "student_id": request.student_id,
                "assignment_id": request.assignment_id,
                "course_id": assignment.course_id,
            },
            client_role=ConnectorRole.STUDENT,
        )
        res_list = self._connector.dispatch(req_list)
        existing = res_list.data or []

        # Previous attempts become non-latest
        attempt_number = len(existing) + 1

        # 7. Create new submission record
        submission_id = f"sub-{uuid.uuid4().hex[:10]}"
        trace_id = f"trace-sub-{uuid.uuid4().hex[:8]}"

        record = SubmissionRecord(
            id=submission_id,
            assignment_id=request.assignment_id,
            student_id=request.student_id,
            course_id=assignment.course_id,
            repository_url=request.repository_url,
            normalized_url=validation_res.normalized_url,
            repo_owner=validation_res.owner,
            repo_name=validation_res.repo,
            submission_timestamp=now_iso,
            attempt_number=attempt_number,
            status=status,
            validation_status=val_status,
            validation_details=validation_details,
            is_latest=True,
            review_status="PENDING",
            review_feedback=None,
            review_score=None,
            notes=request.notes,
            audit_trace_id=trace_id,
        )

        # 8. Persist through governed connector
        write_req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.WRITE,
            resource_path="submissions",
            parameters=record.model_dump(),
            client_role=ConnectorRole.STUDENT,
        )
        write_res = self._connector.dispatch(write_req)
        if not write_res.success:
            raise RuntimeError(f"Database commit failed: {write_res.error}")

        # Persistent audit logging (Bug 7)
        try:
            audit_service.log_event(
                event_type="SUBMISSION_CREATED",
                actor=request.student_id,
                actor_role=actor_role,
                resource=f"assignment:{request.assignment_id}",
                action="SUBMIT_ASSIGNMENT",
                outcome=status,
                details={
                    "submission_id": submission_id,
                    "attempt_number": attempt_number,
                    "repository_url": request.repository_url,
                    "validation_status": val_status,
                },
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.warning("Audit logging failed for submission: %s", exc)

        logger.info(
            "Recorded submission '%s' for student '%s' on assignment '%s' (Attempt %d, Status: %s)",
            submission_id, request.student_id, request.assignment_id, attempt_number, status
        )
        return record

    def get_student_submissions(
        self,
        student_id: str,
        assignment_id: Optional[str] = None,
        course_id: str = "26ECAC401",
    ) -> list[SubmissionRecord]:
        """Retrieve submission history for a student."""
        params: dict[str, Any] = {"student_id": student_id, "course_id": course_id}
        if assignment_id:
            params["assignment_id"] = assignment_id

        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="submissions",
            parameters=params,
            client_role=ConnectorRole.STUDENT,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return []

        records = []
        for r in res.data:
            rec = SubmissionRecord.model_validate(r)
            records.append(self._student_visible_record(rec))
        return records

    @staticmethod
    def _student_visible_record(record: SubmissionRecord) -> SubmissionRecord:
        """Only published results, including feedback and rubric details, are student-visible."""
        if record.review_status != "PUBLISHED" or not record.published_at:
            record.review_score = None
            record.review_feedback = None
            record.rubric_scores = None
            record.reviewed_by = None
            record.reviewed_at = None
            record.approved_by = None
            record.approved_at = None
            record.published_by = None
            record.published_at = None
        return record

    def get_submission_detail(
        self,
        submission_id: str,
        course_id: str = "26ECAC401",
        student_id: Optional[str] = None,
    ) -> Optional[SubmissionRecord]:
        """Retrieve a specific submission by ID."""
        parameters: dict[str, Any] = {"id": submission_id, "course_id": course_id}
        if student_id:
            parameters["student_id"] = student_id
        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.READ,
            resource_path="submissions",
            parameters=parameters,
            client_role=ConnectorRole.STUDENT if student_id else ConnectorRole.FACULTY,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return None
        return SubmissionRecord.model_validate(res.data)

    def get_student_submission_detail(
        self,
        submission_id: str,
        student_id: str,
        course_id: str = "26ECAC401",
    ) -> Optional[SubmissionRecord]:
        """Retrieve one submission while applying the student publication visibility rules."""
        record = self.get_submission_detail(submission_id, course_id=course_id, student_id=student_id)
        if record is None:
            return None
        return self._student_visible_record(record)

    def get_submission_audit_events(
        self,
        submission_id: str,
        course_id: str = "26ECAC401",
    ) -> list[dict[str, Any]]:
        request = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="submission_audit_events",
            parameters={"submission_id": submission_id, "course_id": course_id},
            client_role=ConnectorRole.FACULTY,
        )
        response = self._connector.dispatch(request)
        if not response.success:
            raise RuntimeError(f"Submission audit lookup failed: {response.error}")
        return response.data or []

    def list_faculty_submissions(
        self,
        course_id: str = "26ECAC401",
        assignment_id: Optional[str] = None,
        status: Optional[str] = None,
        only_latest: bool = True,
    ) -> list[SubmissionRecord]:
        """Retrieve submissions across students for faculty evaluation."""
        params: dict[str, Any] = {"course_id": course_id}
        if assignment_id:
            params["assignment_id"] = assignment_id
        if status and status.upper() != "ALL":
            params["status"] = status.upper()
        if only_latest:
            params["is_latest"] = True

        req = ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.LIST,
            resource_path="submissions",
            parameters=params,
            client_role=ConnectorRole.FACULTY,
        )
        res = self._connector.dispatch(req)
        if not res.success or not res.data:
            return []

        return [SubmissionRecord.model_validate(r) for r in res.data]

    def review_submission(
        self,
        submission_id: str,
        review_request: SubmissionReviewRequest,
        reviewer_id: str,
        reviewer_role: str,
    ) -> SubmissionRecord:
        """Save a faculty review draft and append its audit event in one transaction."""
        self._require_faculty_reviewer(reviewer_role)
        requested_status = review_request.review_status
        new_status = {
            "REVIEWED": "DRAFT_GRADED",
            "RESUBMISSION_REQUESTED": "RETURNED_FOR_REVISION",
        }.get(requested_status, requested_status)
        reviewer_id = reviewer_id.strip()
        if not reviewer_id:
            raise ValueError("Reviewer identity cannot be empty.")
        now_iso = datetime.now(timezone.utc).isoformat()
        trace_id = f"trace-review-{submission_id}-{uuid.uuid4().hex[:8]}"
        with get_db_connection(immediate=True) as conn:
            row = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            if row is None:
                raise ValueError(f"Submission with ID '{submission_id}' not found.")
            record = SubmissionRecord.model_validate(dict(row))
            current_status = LEGACY_REVIEW_STATUS_MAP.get(record.review_status, record.review_status)
            if current_status not in (
                "PENDING",
                "UNDER_REVIEW",
                "DRAFT_GRADED",
                "RETURNED_FOR_REVISION",
            ):
                raise SubmissionTransitionError(
                    f"Cannot save a review for submission in '{record.review_status}' state."
                )

            if new_status == "UNDER_REVIEW" and current_status not in ("PENDING", "UNDER_REVIEW"):
                raise SubmissionTransitionError("Only a new or active review can move to UNDER_REVIEW.")

            score = record.review_score
            feedback = record.review_feedback
            rubric_scores = record.rubric_scores
            if "review_score" in review_request.model_fields_set:
                score = review_request.review_score
            if "review_feedback" in review_request.model_fields_set:
                feedback = review_request.review_feedback
            if "rubric_scores" in review_request.model_fields_set:
                rubric_scores = review_request.rubric_scores

            conn.execute(
                """
                UPDATE submissions
                SET status = ?, review_status = ?, review_score = ?, review_feedback = ?,
                    rubric_scores = ?, reviewed_by = ?, reviewed_at = ?, audit_trace_id = ?
                WHERE id = ?
                """,
                (
                    new_status,
                    new_status,
                    score,
                    feedback,
                    json.dumps(rubric_scores) if rubric_scores is not None else None,
                    reviewer_id,
                    now_iso,
                    trace_id,
                    submission_id,
                ),
            )
            self._record_review_transition(
                conn=conn,
                record=record,
                action="REVIEW_SAVED",
                to_status=new_status,
                actor=reviewer_id,
                actor_role=reviewer_role,
                occurred_at=now_iso,
                trace_id=trace_id,
                score=score,
                feedback=feedback,
            )
            updated = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return SubmissionRecord.model_validate(dict(updated))

    @staticmethod
    def _record_review_transition(
        conn,
        record: SubmissionRecord,
        action: str,
        to_status: str,
        actor: str,
        actor_role: str,
        occurred_at: str,
        trace_id: str,
        score: Optional[float],
        feedback: Optional[str],
    ) -> None:
        """Write both lifecycle and system audit entries within the transition transaction."""
        conn.execute(
            """
            INSERT INTO submission_audit_events(
                submission_id, action, actor_id, from_status, to_status,
                review_score, review_feedback, occurred_at, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                action,
                actor,
                record.status if record.review_status == "PENDING" else record.review_status,
                to_status,
                score,
                feedback,
                occurred_at,
                trace_id,
            ),
        )
        audit_service.log_event(
            event_type=f"SUBMISSION_{action}",
            actor=actor,
            actor_role=actor_role,
            resource=f"submission:{record.id}",
            action=action,
            outcome=to_status,
            details={
                "assignment_id": record.assignment_id,
                "student_id": record.student_id,
                "review_score": score,
                "review_feedback": feedback,
            },
            trace_id=trace_id,
            connection=conn,
        )

    @staticmethod
    def _require_faculty_reviewer(reviewer_role: str) -> None:
        if reviewer_role != "FACULTY":
            raise PermissionError("Only authorized faculty may review, approve, or publish grades.")

    def approve_grade(
        self,
        submission_id: str,
        reviewer_id: str,
        reviewer_role: str,
    ) -> SubmissionRecord:
        """Approve a complete saved draft without publishing it to the student."""
        self._require_faculty_reviewer(reviewer_role)
        reviewer_id = reviewer_id.strip()
        if not reviewer_id:
            raise ValueError("Reviewer identity cannot be empty.")
        now_iso = datetime.now(timezone.utc).isoformat()
        trace_id = f"trace-approve-{submission_id}-{uuid.uuid4().hex[:8]}"

        with get_db_connection(immediate=True) as conn:
            row = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            if row is None:
                raise ValueError(f"Submission '{submission_id}' not found.")
            record = SubmissionRecord.model_validate(dict(row))
            current_status = LEGACY_REVIEW_STATUS_MAP.get(record.review_status, record.review_status)
            if current_status not in ("DRAFT_GRADED",):
                raise SubmissionTransitionError(
                    f"Only a saved grade draft can be approved; current state is '{record.review_status}'."
                )
            if record.review_score is None or not record.review_feedback or not record.review_feedback.strip():
                raise SubmissionTransitionError("A grade requires both a score and feedback before approval.")

            conn.execute(
                """
                UPDATE submissions
                SET status = 'APPROVED', review_status = 'APPROVED',
                    approved_by = ?, approved_at = ?, published_at = NULL,
                    published_by = NULL, audit_trace_id = ?
                WHERE id = ?
                """,
                (reviewer_id, now_iso, trace_id, submission_id),
            )
            self._record_review_transition(
                conn, record, "GRADE_APPROVED", "APPROVED", reviewer_id, reviewer_role, now_iso,
                trace_id, record.review_score, record.review_feedback,
            )
            updated = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return SubmissionRecord.model_validate(dict(updated))

    def publish_grade(
        self,
        submission_id: str,
        reviewer_id: str,
        reviewer_role: str,
    ) -> SubmissionRecord:
        """Publish an approved grade exactly once and audit the state transition atomically."""
        self._require_faculty_reviewer(reviewer_role)
        reviewer_id = reviewer_id.strip()
        if not reviewer_id:
            raise ValueError("Reviewer identity cannot be empty.")
        now_iso = datetime.now(timezone.utc).isoformat()
        trace_id = f"trace-publish-{submission_id}-{uuid.uuid4().hex[:8]}"
        with get_db_connection(immediate=True) as conn:
            row = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            if row is None:
                raise ValueError(f"Submission '{submission_id}' not found.")
            record = SubmissionRecord.model_validate(dict(row))
            if record.review_status != "APPROVED":
                raise SubmissionTransitionError(
                    f"Only an approved grade can be published; current state is '{record.review_status}'."
                )

            conn.execute(
                """
                UPDATE submissions
                SET status = 'PUBLISHED', review_status = 'PUBLISHED',
                    published_at = ?, published_by = ?, audit_trace_id = ?
                WHERE id = ?
                """,
                (now_iso, reviewer_id, trace_id, submission_id),
            )
            self._record_review_transition(
                conn, record, "GRADE_PUBLISHED", "PUBLISHED", reviewer_id, reviewer_role, now_iso,
                trace_id, record.review_score, record.review_feedback,
            )
            insert_notification(
                conn,
                user_id=record.student_id,
                user_role="STUDENT",
                title="Grade published",
                message=f"Your grade and feedback for {record.assignment_id} are now available.",
                category="GRADE",
                link="/#submissions",
            )
            updated = conn.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return SubmissionRecord.model_validate(dict(updated))


submission_service = SubmissionService()
