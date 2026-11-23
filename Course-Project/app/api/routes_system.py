"""System and diagnostic endpoints for CourseAgentAI."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.auth import AuthenticatedUser, require_roles
from app.data.db import get_db_connection
from config import settings
from app.core.coordinator import coordinator
from app.core.registry import lab_registry
from app.data.repository import course_repo
from app.models.common import APIEnvelope, ScenarioDefinition
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/system", tags=["System Diagnostics & Scenarios"])


class AccountStateUpdate(BaseModel):
    is_active: bool


@router.get("/admin/users", response_model=APIEnvelope)
async def list_admin_users(
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> APIEnvelope:
    """List protected application accounts for authenticated administrators."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_id, email, display_name, role, student_id, course_scopes, is_active, created_at
            FROM auth_users
            ORDER BY role, display_name
            """
        ).fetchall()
    data = [dict(row) for row in rows]
    return APIEnvelope(success=True, data=data, trace_id="admin-users")


@router.patch("/admin/users/{user_id}/active", response_model=APIEnvelope)
async def update_admin_user_active(
    user_id: str,
    request: AccountStateUpdate,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> APIEnvelope:
    """Activate or deactivate an account; administrator account removal is not performed."""
    with get_db_connection(immediate=True) as conn:
        target = conn.execute(
            "SELECT user_id, role FROM auth_users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Account was not found.")
        if target["role"] == "ADMIN" and not request.is_active:
            active_admin_count = conn.execute(
                "SELECT COUNT(*) AS count FROM auth_users WHERE role = 'ADMIN' AND is_active = 1"
            ).fetchone()["count"]
            if active_admin_count <= 1:
                raise HTTPException(status_code=400, detail="The final administrator account cannot be deactivated.")
        conn.execute(
            "UPDATE auth_users SET is_active = ? WHERE user_id = ?",
            (1 if request.is_active else 0, user_id),
        )
        if not request.is_active:
            conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
    return APIEnvelope(
        success=True,
        data={"user_id": user_id, "is_active": request.is_active},
        trace_id=f"admin-account-{user_id}",
    )


@router.get("/status", response_model=APIEnvelope)
async def get_system_status() -> APIEnvelope:
    """Return system readiness, active LLM provider mode, and 14-lab curriculum catalog."""
    catalog = lab_registry.get_catalog()
    return APIEnvelope(
        success=True,
        data={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "llm_provider": settings.llm_provider,
            "active_labs_count": len([lab for lab in catalog if lab.is_active]),
            "total_labs_count": len(catalog),
            "labs_catalog": [lab.model_dump() for lab in catalog],
        },
        trace_id="system-status",
    )


@router.get("/scenarios", response_model=APIEnvelope)
async def get_demo_scenarios() -> APIEnvelope:
    """Retrieve pre-built realistic faculty scenarios for quick evaluation."""
    scenarios = course_repo.get_all_scenarios()
    return APIEnvelope(
        success=True,
        data=[s.model_dump() for s in scenarios],
        trace_id="system-scenarios",
    )


@router.get("/audit", response_model=APIEnvelope)
async def get_audit_trail(
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> APIEnvelope:
    """Retrieve execution audit logs."""
    # First get persistent events from database
    persistent_events = audit_service.list_events(limit=100)
    if persistent_events:
        return APIEnvelope(
            success=True,
            data=persistent_events,
            trace_id="system-audit",
        )
    # Fallback to coordinator in-memory trail
    logs = coordinator.get_audit_trail()
    return APIEnvelope(
        success=True,
        data=logs,
        trace_id="system-audit",
    )


@router.get("/audit/events", response_model=APIEnvelope)
async def get_audit_events(
    event_type: Optional[str] = Query(default=None),
    actor: Optional[str] = Query(default=None),
    resource: Optional[str] = Query(default=None),
    outcome: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
) -> APIEnvelope:
    """Retrieve queryable persistent audit log records."""
    events = audit_service.list_events(
        event_type=event_type,
        actor=actor,
        resource=resource,
        outcome=outcome,
        limit=limit,
    )
    return APIEnvelope(
        success=True,
        data={
            "total_count": audit_service.get_event_count(),
            "returned_count": len(events),
            "events": events,
        },
        trace_id="system-audit-events",
    )
