"""FastAPI routes for Student GitHub Assignment Submissions and Faculty Review."""

import uuid
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.models.common import APIEnvelope, ErrorDetail
from app.models.submission_models import (
    AssignmentOut,
    GitHubSubmissionRequest,
    SubmissionApprovalRequest,
    SubmissionPublicationRequest,
    StudentOut,
    SubmissionRecord,
    SubmissionReviewRequest,
)
from app.services.submission_service import SubmissionTransitionError, submission_service

router = APIRouter(prefix="/api", tags=["Assignments & Submissions"])


@router.get("/assignments", response_model=APIEnvelope[list[AssignmentOut]])
async def list_assignments(
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List all available course assignments with configured deadlines, rules, and policies."""
    require_course_access(user, course_id)
    assignments = submission_service.list_assignments(course_id=course_id)
    return APIEnvelope(
        success=True,
        data=assignments,
        trace_id=f"trace-asgns-{uuid.uuid4().hex[:6]}",
    )


@router.get("/assignments/{assignment_id}", response_model=APIEnvelope[AssignmentOut])
async def get_assignment(assignment_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve detailed specification, rubric, and rules for a specific assignment."""
    assignment = submission_service.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID '{assignment_id}' was not found.",
        )
    require_course_access(user, assignment.course_id)
    return APIEnvelope(
        success=True,
        data=assignment,
        trace_id=f"trace-asgn-{assignment_id}",
    )


@router.get("/students", response_model=APIEnvelope[list[StudentOut]])
async def list_students(
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Return the authenticated student's profile or an authorized course roster."""
    require_course_access(user, course_id)
    if user.role == "STUDENT":
        students = [
            student
            for student in submission_service.list_students(course_id=course_id)
            if student.id == user.student_id
        ]
    else:
        students = submission_service.list_students(course_id=course_id)
    return APIEnvelope(
        success=True,
        data=students,
        trace_id=f"trace-students-{uuid.uuid4().hex[:6]}",
    )


@router.post("/submissions", response_model=APIEnvelope[SubmissionRecord])
async def submit_assignment(
    request: GitHubSubmissionRequest,
    user: AuthenticatedUser = Depends(require_roles("STUDENT")),
):
    """Submit a GitHub repository solution for an assignment.
    
    Validates URL syntax, host, parameters, and assignment eligibility.
    Enforces authorization: students can only submit for their own student identity.
    """
    if request.student_id != user.student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A student can submit only under their authenticated account.",
        )
    assignment = submission_service.get_assignment(request.assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment was not found.")
    require_course_access(user, assignment.course_id)

    try:
        record = await submission_service.submit_assignment(request, actor_role=user.role)
        return APIEnvelope(
            success=True,
            data=record,
            trace_id=record.audit_trace_id or f"trace-sub-{uuid.uuid4().hex[:6]}",
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower() or "not enrolled" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission processing error: {exc}",
        )


@router.get("/submissions/student/{student_id}", response_model=APIEnvelope[list[SubmissionRecord]])
async def get_student_submissions(
    student_id: str,
    assignment_id: Optional[str] = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve full submission history and attempts for a specific student.
    
    Enforces student isolation: students can only inspect their own submissions.
    """
    if user.role == "STUDENT" and student_id != user.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied: students may view only their own submissions.")
    from app.data.db import get_db_connection
    with get_db_connection() as conn:
        student = conn.execute(
            "SELECT course_id FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student was not found.")
    require_course_access(user, student["course_id"])

    records = submission_service.get_student_submissions(
        student_id,
        assignment_id=assignment_id,
        course_id=student["course_id"],
    )
    return APIEnvelope(
        success=True,
        data=records,
        trace_id=f"trace-history-{student_id}",
    )


@router.get("/submissions/detail/{submission_id}", response_model=APIEnvelope[SubmissionRecord])
async def get_submission_detail(
    submission_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve a single submission record by its unique submission ID."""
    record = submission_service.get_submission_detail(submission_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' was not found.",
        )

    if user.role == "STUDENT":
        if record.student_id != user.student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied: students may view only their own submissions.")
        record = submission_service.get_student_submission_detail(
            submission_id,
            student_id=user.student_id,
            course_id=record.course_id,
        )
    else:
        require_course_access(user, record.course_id)

    return APIEnvelope(
        success=True,
        data=record,
        trace_id=f"trace-sub-{submission_id}",
    )


@router.get("/submissions/{submission_id}/audit", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_submission_audit(
    submission_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Return persisted submission lifecycle events to its student or faculty."""
    record = submission_service.get_submission_detail(submission_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{submission_id}' was not found.",
        )
    if user.role == "STUDENT":
        if record.student_id != user.student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied: students may view only their own submission audit.")
    else:
        require_course_access(user, record.course_id)
    events = submission_service.get_submission_audit_events(submission_id, course_id=record.course_id)
    if user.role == "STUDENT":
        events = [
            {**event, "review_score": None, "review_feedback": None}
            if event.get("action") != "GRADE_PUBLISHED"
            else event
            for event in events
        ]
    return APIEnvelope(
        success=True,
        data=events,
        trace_id=f"trace-audit-{submission_id}",
    )


@router.get("/submissions/faculty", response_model=APIEnvelope[list[SubmissionRecord]])
async def list_faculty_submissions(
    assignment_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    only_latest: bool = Query(default=True),
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    """List submissions for faculty evaluation. Requires FACULTY authorization."""
    require_course_access(user, course_id)

    records = submission_service.list_faculty_submissions(
        course_id=course_id,
        assignment_id=assignment_id,
        status=status_filter,
        only_latest=only_latest,
    )
    return APIEnvelope(
        success=True,
        data=records,
        trace_id=f"trace-faculty-subs-{uuid.uuid4().hex[:6]}",
    )


@router.post("/submissions/{submission_id}/review", response_model=APIEnvelope[SubmissionRecord])
async def review_submission(
    submission_id: str,
    review_request: SubmissionReviewRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    """Submit faculty evaluation score, qualitative feedback, and review status."""
    record = submission_service.get_submission_detail(submission_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission was not found.")
    require_course_access(user, record.course_id)

    try:
        updated = submission_service.review_submission(
            submission_id,
            review_request,
            reviewer_id=user.user_id,
            reviewer_role=user.role,
        )
        return APIEnvelope(
            success=True,
            data=updated,
            trace_id=updated.audit_trace_id or f"trace-review-{submission_id}",
        )
    except SubmissionTransitionError as transition_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(transition_err))
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review execution failure: {exc}",
        )


@router.post("/submissions/{submission_id}/approve", response_model=APIEnvelope[SubmissionRecord])
async def approve_submission_grade(
    submission_id: str,
    request: SubmissionApprovalRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    """Approve a saved grade draft before it can be published to the student."""
    record = submission_service.get_submission_detail(submission_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission was not found.")
    require_course_access(user, record.course_id)
    try:
        updated = submission_service.approve_grade(
            submission_id,
            reviewer_id=user.user_id,
            reviewer_role=user.role,
        )
        return APIEnvelope(
            success=True,
            data=updated,
            trace_id=updated.audit_trace_id or f"trace-approve-{submission_id}",
        )
    except SubmissionTransitionError as transition_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(transition_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post("/submissions/{submission_id}/publish", response_model=APIEnvelope[SubmissionRecord])
async def publish_submission_grade(
    submission_id: str,
    request: SubmissionPublicationRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    """Faculty gate: Explicitly publish a reviewed grade and feedback so students can view it."""
    record = submission_service.get_submission_detail(submission_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission was not found.")
    require_course_access(user, record.course_id)
    try:
        updated = submission_service.publish_grade(
            submission_id,
            reviewer_id=user.user_id,
            reviewer_role=user.role,
        )
        return APIEnvelope(
            success=True,
            data=updated,
            trace_id=f"trace-publish-{submission_id}",
        )
    except SubmissionTransitionError as transition_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(transition_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/assignments", response_model=APIEnvelope[AssignmentOut])
async def create_assignment(
    assignment: AssignmentOut,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty create/publish an assignment."""
    require_course_access(user, assignment.course_id)
    from app.data.db import get_db_connection
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection(immediate=True) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO assignments (id, course_id, title, max_points, weight_percentage, due_week, description, due_date, submission_rules, late_policy, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                max_points = excluded.max_points,
                weight_percentage = excluded.weight_percentage,
                due_week = excluded.due_week,
                description = excluded.description,
                due_date = excluded.due_date,
                submission_rules = excluded.submission_rules,
                late_policy = excluded.late_policy,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                assignment.id,
                assignment.course_id,
                assignment.title,
                assignment.max_points,
                assignment.weight_percentage,
                assignment.due_week,
                assignment.description,
                assignment.due_date,
                assignment.submission_rules,
                assignment.late_policy,
                assignment.status,
                assignment.created_at or now_iso,
                now_iso,
            ),
        )
    from app.services.audit_service import audit_service
    audit_service.log_event(
        event_type="ASSIGNMENT_CONFIGURED",
        actor=user.user_id,
        actor_role=user.role,
        resource=f"assignment:{assignment.id}",
        action="CREATE_OR_UPDATE_ASSIGNMENT",
        outcome="SUCCESS",
        details={"title": assignment.title, "status": assignment.status},
    )
    return APIEnvelope(success=True, data=assignment, trace_id=f"trace-asgn-create-{assignment.id}")


@router.get("/assignments/{assignment_id}/rubrics", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_assignment_rubrics(
    assignment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve all evaluation rubric criteria for an assignment."""
    from app.data.db import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        assignment = cursor.execute("SELECT course_id FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment was not found.")
        course_id = assignment["course_id"]
        rows = cursor.execute("SELECT * FROM rubrics WHERE assignment_id = ?", (assignment_id,)).fetchall()
        rows = [dict(r) for r in rows]
    require_course_access(user, course_id)
    return APIEnvelope(success=True, data=rows, trace_id=f"trace-rubrics-{assignment_id}")


@router.post("/assignments/{assignment_id}/rubrics", response_model=APIEnvelope[list[dict[str, Any]]])
async def save_assignment_rubrics(
    assignment_id: str,
    rubric_list: list[dict[str, Any]],
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty configure evaluation rubrics for an assignment."""
    from app.data.db import get_db_connection
    with get_db_connection(immediate=True) as conn:
        cursor = conn.cursor()
        assignment = cursor.execute("SELECT course_id FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment was not found.")
        require_course_access(user, assignment["course_id"])
        cursor.execute("DELETE FROM rubrics WHERE assignment_id = ?", (assignment_id,))
        for idx, item in enumerate(rubric_list):
            rid = item.get("id") or f"rub-{assignment_id}-{idx+1}"
            cursor.execute(
                """
                INSERT INTO rubrics (id, assignment_id, criterion, max_points, description, weight_percentage)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    assignment_id,
                    item.get("criterion", f"Criterion {idx+1}"),
                    float(item.get("max_points", 25.0)),
                    item.get("description", ""),
                    float(item.get("weight_percentage", 25.0)),
                ),
            )
        cursor.execute("SELECT * FROM rubrics WHERE assignment_id = ?", (assignment_id,))
        saved = [dict(r) for r in cursor.fetchall()]
    return APIEnvelope(success=True, data=saved, trace_id=f"trace-rubrics-save-{assignment_id}")
