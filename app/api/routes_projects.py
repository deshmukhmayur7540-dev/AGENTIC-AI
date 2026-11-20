"""FastAPI routes for Course Project Management and Milestone Tracking (Part 7)."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.data.db import get_db_connection
from app.models.common import APIEnvelope
from app.services.project_service import project_service

router = APIRouter(prefix="/api/projects", tags=["Course Projects & Milestones"])


def _authorized_project(project_id: str, user: AuthenticatedUser) -> dict[str, Any]:
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' was not found.")
    require_course_access(user, project["course_id"])
    if user.role == "STUDENT" and not any(member["student_id"] == user.student_id for member in project["members"]):
        raise HTTPException(status_code=403, detail="Students may access only projects they belong to.")
    return project


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5, max_length=2000)
    course_id: str = Field(default="26ECAC401")
    project_type: str = Field(default="GROUP")  # INDIVIDUAL or GROUP
    repository_url: Optional[str] = None
    members: Optional[list[dict[str, Any]]] = None
    milestones: Optional[list[dict[str, Any]]] = None


class UpdateMilestoneRequest(BaseModel):
    status: Optional[str] = None  # NOT_STARTED, IN_PROGRESS, COMPLETED, OVERDUE, BLOCKED
    deliverable_name: Optional[str] = None
    deliverable_url: Optional[str] = None
    comments: Optional[str] = None


class MilestoneCommentRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=1000)


@router.get("", response_model=APIEnvelope[list[dict[str, Any]]])
async def list_course_projects(
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List authorized course projects; students see projects they belong to."""
    require_course_access(user, course_id)
    projects = project_service.list_projects(course_id=course_id)
    if user.role == "STUDENT":
        visible_projects = []
        for item in projects:
            project = project_service.get_project(item["id"])
            if project and any(member["student_id"] == user.student_id for member in project["members"]):
                visible_projects.append(item)
        projects = visible_projects
    return APIEnvelope(success=True, data=projects, trace_id="projects-list")


@router.post("", response_model=APIEnvelope[dict[str, Any]])
async def create_course_project(
    request: CreateProjectRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Create a new course project with assigned members and deliverables."""
    require_course_access(user, request.course_id)
    for member in request.members or []:
        with get_db_connection() as conn:
            enrolled = conn.execute(
                "SELECT 1 FROM students WHERE id = ? AND course_id = ?",
                (member.get("student_id"), request.course_id),
            ).fetchone()
        if not enrolled:
            raise HTTPException(status_code=400, detail="Every project member must be enrolled in the project course.")
    proj = project_service.create_project(
        title=request.title,
        description=request.description,
        course_id=request.course_id,
        project_type=request.project_type,
        repository_url=request.repository_url,
        members=request.members,
        milestones=request.milestones,
        actor=user.user_id,
        actor_role=user.role,
    )
    return APIEnvelope(success=True, data=proj, trace_id=f"proj-create-{proj.get('id')}")


@router.get("/dashboard", response_model=APIEnvelope[dict[str, Any]])
async def get_project_dashboard(
    course_id: str = Query(default="26ECAC401"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve an authorized course or student-scoped project overview."""
    require_course_access(user, course_id)
    if user.role == "STUDENT":
        projects = [
            project_service.get_project(item["id"])
            for item in project_service.list_projects(course_id)
        ]
        projects = [
            project for project in projects if project
            and any(member["student_id"] == user.student_id for member in project["members"])
        ]
        milestones = [
            {
                "title": milestone["title"],
                "due_date": milestone["due_date"],
                "status": milestone["status"],
                "project_title": project["title"],
                "project_id": project["id"],
            }
            for project in projects
            for milestone in project["milestones"]
            if milestone["status"] != "COMPLETED"
        ]
        summary = {
            "course_id": course_id,
            "total_projects": len(projects),
            "average_progress": round(
                sum(project["progress_percentage"] for project in projects) / len(projects), 1
            ) if projects else 0.0,
            "overdue_milestones_count": 0,
            "upcoming_milestones": sorted(milestones, key=lambda item: item["due_date"])[:5],
        }
        return APIEnvelope(success=True, data=summary, trace_id="projects-dashboard")
    summary = project_service.get_dashboard_summary(course_id=course_id)
    return APIEnvelope(success=True, data=summary, trace_id="projects-dashboard")


@router.get("/{project_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_project_details(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve complete project details including member roster, milestone progression, and activity."""
    proj = _authorized_project(project_id, user)
    return APIEnvelope(success=True, data=proj, trace_id=f"proj-{project_id}")


@router.put("/{project_id}/milestones/{milestone_id}", response_model=APIEnvelope[dict[str, Any]])
async def update_project_milestone(
    project_id: str,
    milestone_id: str,
    request: UpdateMilestoneRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Update milestone status, record deliverable evidence, and recalculate project completion."""
    _authorized_project(project_id, user)
    try:
        updated = project_service.update_milestone(
            project_id=project_id,
            milestone_id=milestone_id,
            status=request.status,
            deliverable_name=request.deliverable_name,
            deliverable_url=request.deliverable_url,
            comments=request.comments,
            actor=user.user_id,
            actor_role=user.role,
            actor_student_id=user.student_id,
        )
        return APIEnvelope(success=True, data=updated, trace_id=f"ms-update-{milestone_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))


@router.post("/{project_id}/milestones/{milestone_id}/comments", response_model=APIEnvelope[dict[str, Any]])
async def add_milestone_comment(
    project_id: str,
    milestone_id: str,
    request: MilestoneCommentRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Post feedback or notes to a milestone."""
    _authorized_project(project_id, user)
    try:
        res = project_service.add_milestone_comment(
            project_id=project_id,
            milestone_id=milestone_id,
            comment=request.comment,
            actor=user.user_id,
            actor_student_id=user.student_id,
        )
        return APIEnvelope(success=True, data=res, trace_id=f"ms-comment-{milestone_id}")
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(val_err))
