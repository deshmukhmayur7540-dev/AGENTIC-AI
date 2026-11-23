"""FastAPI routes for Lab 1: Clarify -> Plan -> Revise."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import AuthenticatedUser, require_course_access, require_roles
from app.core.coordinator import coordinator
from app.data.repository import course_repo
from app.models.common import APIEnvelope
from app.models.lab1_models import (
    FacultyCourseRequest,
    ClarificationSubmission,
    RevisionRequest,
)
import app.labs.lab1  # Register Lab 1 agent

router = APIRouter(prefix="/api/lab1", tags=["Lab 1: Clarify -> Plan -> Revise"])


@router.post("/clarify", response_model=APIEnvelope)
async def clarify_vague_request(
    request: FacultyCourseRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
) -> APIEnvelope:
    """Analyze faculty request for missing information and return at least 2 clarification questions."""
    return await coordinator.dispatch(
        lab_id="lab1",
        action="clarify",
        payload=request.model_dump(),
    )


@router.post("/generate", response_model=APIEnvelope)
async def generate_course_plan(
    submission: ClarificationSubmission,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
) -> APIEnvelope:
    """Synthesize clarified answers into CourseWorkspacePlan v1.0."""
    if not submission.course_code_hint and user.role == "FACULTY":
        if len(user.course_scopes) != 1:
            raise HTTPException(
                status_code=400,
                detail="A course code is required when the faculty account has multiple course scopes.",
            )
        submission.course_code_hint = user.course_scopes[0]
    if submission.course_code_hint:
        require_course_access(user, submission.course_code_hint)
    return await coordinator.dispatch(
        lab_id="lab1",
        action="generate",
        payload=submission.model_dump(),
    )


@router.post("/revise", response_model=APIEnvelope)
async def revise_course_plan(
    revision: RevisionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
) -> APIEnvelope:
    """Apply faculty revision requests, bump plan version, and compute exact structured diffs."""
    plan = course_repo.get_latest_plan(revision.plan_id)
    if plan:
        require_course_access(user, plan.course_code)
    return await coordinator.dispatch(
        lab_id="lab1",
        action="revise",
        payload=revision.model_dump(),
    )


@router.get("/history/{plan_id}", response_model=APIEnvelope)
async def get_plan_history(
    plan_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
) -> APIEnvelope:
    """Retrieve full version history, revision changelog, and structured diffs for a plan."""
    history = course_repo.get_plan_history(plan_id)
    if history and history.versions:
        require_course_access(user, history.versions[-1].course_code)
    return await coordinator.dispatch(
        lab_id="lab1",
        action="get_history",
        payload={"plan_id": plan_id},
    )


@router.get("/plan/{plan_id}", response_model=APIEnvelope)
async def get_plan(
    plan_id: str,
    version: Optional[str] = Query(default=None),
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
) -> APIEnvelope:
    """Retrieve a specific or latest version of a course workspace plan."""
    plan = (
        course_repo.get_plan_version(plan_id, version)
        if version
        else course_repo.get_latest_plan(plan_id)
    )
    if plan:
        require_course_access(user, plan.course_code)
    return await coordinator.dispatch(
        lab_id="lab1",
        action="get_plan",
        payload={"plan_id": plan_id, "version": version},
    )
