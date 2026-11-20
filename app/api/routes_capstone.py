"""Course-scoped Lab 14 coordinator and governed workspace release API."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.models.common import APIEnvelope
from app.labs.lab14.capstone import capstone_service

router = APIRouter(prefix="/api/capstone", tags=["Lab 14 Capstone"])


class CreateCapstoneRunRequest(BaseModel):
    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    assignment_id: str = Field(min_length=1, max_length=80)
    request: str = Field(min_length=8, max_length=1000)


class FacultyDecisionRequest(BaseModel):
    approved: bool
    comment: str = Field(default="", max_length=1000)


def _authorized_run(run_id: str, user: AuthenticatedUser) -> dict[str, Any]:
    run = capstone_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Capstone run was not found.")
    require_course_access(user, run["course_id"])
    return run


@router.post("/runs", response_model=APIEnvelope[dict[str, Any]])
async def create_capstone_run(
    request: CreateCapstoneRunRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    require_course_access(user, request.course_id)
    try:
        result = capstone_service.create_run(
            course_id=request.course_id,
            assignment_id=request.assignment_id,
            request_text=request.request,
            actor_user_id=user.user_id,
            actor_role=user.role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(success=True, data=result, trace_id=f"capstone-{result['run_id']}")


@router.get("/runs/{run_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_capstone_run(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    run = _authorized_run(run_id, user)
    return APIEnvelope(success=True, data=run, trace_id=f"capstone-{run_id}")


@router.get("/runs/{run_id}/audit", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_capstone_audit(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    _authorized_run(run_id, user)
    return APIEnvelope(
        success=True,
        data=capstone_service.list_audit(run_id),
        trace_id=f"capstone-{run_id}-audit",
    )


@router.post("/runs/{run_id}/decision", response_model=APIEnvelope[dict[str, Any]])
async def decide_capstone_run(
    run_id: str,
    request: FacultyDecisionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    run = _authorized_run(run_id, user)
    try:
        if request.approved:
            result = capstone_service.approve(run_id, user.user_id, request.comment)
        else:
            result = capstone_service.reject(run_id, user.user_id, request.comment)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return APIEnvelope(
        success=True,
        data=result,
        trace_id=f"capstone-{run['course_id']}-decision",
    )


@router.get("/releases/current", response_model=APIEnvelope[dict[str, Any]])
async def get_current_capstone_release(
    course_id: str = "26ECAC401",
    user: AuthenticatedUser = Depends(get_current_user),
):
    require_course_access(user, course_id)
    release = capstone_service.current_release(
        course_id,
        public_view=user.role == "STUDENT",
    )
    if release is None:
        raise HTTPException(status_code=404, detail="No published course workspace release is available.")
    return APIEnvelope(success=True, data=release, trace_id=f"capstone-release-{release['version']}")


@router.post("/releases/{release_id}/rollback", response_model=APIEnvelope[dict[str, Any] | None])
async def rollback_capstone_release(
    release_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY")),
):
    release = capstone_service.get_release(release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Course workspace release was not found.")
    require_course_access(user, release["course_id"])
    try:
        restored = capstone_service.rollback(release_id, user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return APIEnvelope(success=True, data=restored, trace_id=f"capstone-rollback-{release_id}")
