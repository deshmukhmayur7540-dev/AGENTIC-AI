"""System and diagnostic endpoints for CourseAgentAI."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.auth import AuthenticatedUser, require_roles
from config import settings
from app.core.coordinator import coordinator
from app.core.registry import lab_registry
from app.data.repository import course_repo
from app.models.common import APIEnvelope, ScenarioDefinition
from app.services.audit_service import audit_service

router = APIRouter(prefix="/api/system", tags=["System Diagnostics & Scenarios"])


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
