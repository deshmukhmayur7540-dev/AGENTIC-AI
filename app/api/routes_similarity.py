"""FastAPI routes for Similarity Checking and Rubric Grading Assistance (Part 6)."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, require_course_access, require_roles
from app.data.db import get_db_connection
from app.models.common import APIEnvelope
from app.services.similarity_service import similarity_service

router = APIRouter(prefix="/api/similarity", tags=["Similarity & Grading Assistance"])


class RunSimilarityRequest(BaseModel):
    assignment_id: str = Field(description="Assignment identifier to evaluate across all submissions")


@router.post("/run", response_model=APIEnvelope[dict[str, Any]])
async def run_similarity_check(
    request: RunSimilarityRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Faculty gate: Run pairwise similarity check across all submissions for an assignment."""
    _authorize_assignment(user, request.assignment_id)
    report = similarity_service.run_similarity_check(
        assignment_id=request.assignment_id,
        actor=user.user_id,
        actor_role=user.role,
    )
    return APIEnvelope(success=True, data=report, trace_id=f"sim-{request.assignment_id}")


@router.get("/report/{assignment_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_similarity_report(
    assignment_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Retrieve the latest similarity report for an assignment."""
    _authorize_assignment(user, assignment_id)
    report = similarity_service.get_latest_report(assignment_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No similarity report found for assignment '{assignment_id}'.",
        )
    return APIEnvelope(success=True, data=report, trace_id=f"sim-get-{assignment_id}")


@router.get("/assist-grade/{submission_id}", response_model=APIEnvelope[dict[str, Any]])
async def generate_draft_grading(
    submission_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Grading Assistance Agent: Prepare rubric-based draft scores and feedback. Requires faculty approval to publish."""
    with get_db_connection() as conn:
        submission = conn.execute(
            "SELECT course_id FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission was not found.")
    require_course_access(user, submission["course_id"])
    try:
        draft = similarity_service.generate_draft_grade(submission_id=submission_id)
        return APIEnvelope(success=True, data=draft, trace_id=f"draft-grade-{submission_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


def _authorize_assignment(user: AuthenticatedUser, assignment_id: str) -> None:
    with get_db_connection() as conn:
        assignment = conn.execute(
            "SELECT course_id FROM assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment was not found.")
    require_course_access(user, assignment["course_id"])
