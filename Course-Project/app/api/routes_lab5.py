"""FastAPI routes for Lab 5: MCP-Style Governed Connector."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.core.coordinator import coordinator
from app.labs.lab5.governed_connector import governed_connector
from app.models.common import APIEnvelope
from app.models.lab5_models import (
    ConnectorOperation,
    ConnectorRequest,
    ConnectorRole,
)

router = APIRouter(prefix="/api/lab5", tags=["Lab 5: Governed Connector"])

LAB5_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab5-read-notes",
        "title": "Scenario 1: Governed Notes Read (NotesDataSource)",
        "category": "Notes Source Access",
        "source_id": "notes_source",
        "operation": "SEARCH",
        "parameters": {"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401"},
        "role": "FACULTY",
        "description": "Reads Chapter 1 lecture notes via governed connector with complete document provenance.",
    },
    {
        "scenario_id": "lab5-query-sqlite",
        "title": "Scenario 2: Governed Relational Query (SqliteDataSource)",
        "category": "Database Source Access",
        "source_id": "sqlite_source",
        "operation": "LIST",
        "parameters": {"table": "assignments"},
        "role": "FACULTY",
        "description": "Executes governed SELECT query across assignments table without raw SQL exposure.",
    },
    {
        "scenario_id": "lab5-faculty-write",
        "title": "Scenario 3: Authorized Faculty Modification (SqliteDataSource)",
        "category": "Role-Based Access Control",
        "source_id": "sqlite_source",
        "operation": "WRITE",
        "parameters": {
            "table": "assignments",
            "id": "lab5_asgn",
            "title": "Lab 5: Governed MCP Connector",
            "max_points": 100,
            "weight_percentage": 15.0,
            "due_week": 10,
        },
        "role": "FACULTY",
        "description": "Verifies that authorized FACULTY role can create and update database records via connector.",
    },
    {
        "scenario_id": "lab5-student-write-blocked",
        "title": "Scenario 4: Unauthorized Student Modification Blocked",
        "category": "Role-Based Security & Governance",
        "source_id": "sqlite_source",
        "operation": "WRITE",
        "parameters": {
            "table": "rubrics",
            "id": "hacked_rubric",
            "criterion": "Fake Credit",
            "max_points": 100,
        },
        "role": "STUDENT",
        "description": "Verifies that STUDENT role is strictly blocked (ACCESS_DENIED) from mutating grade rubrics.",
    },
    {
        "scenario_id": "lab5-registrar-api",
        "title": "Scenario 5: University Registrar API Integration",
        "category": "Academic API Source Access",
        "source_id": "academic_api_source",
        "operation": "READ",
        "parameters": {"course_code": "26ECAC401"},
        "role": "FACULTY",
        "description": "Retrieves official university catalog prerequisites and credit hours via mock API connector.",
    },
]


@router.get("/sources", response_model=APIEnvelope[dict[str, Any]])
async def list_sources():
    """List all registered data sources and their access capabilities."""
    envelope = await coordinator.dispatch(
        lab_id="lab5",
        action="list_sources",
        payload={},
    )
    return envelope


@router.post("/execute", response_model=APIEnvelope[dict[str, Any]])
async def execute_operation(
    request: ConnectorRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Execute a typed operation through the Governed Connector."""
    require_course_access(user, "26ECAC401")
    target_table = request.resource_path or request.parameters.get("table", "assignments")
    if target_table == "submissions" and request.operation in {ConnectorOperation.WRITE, ConnectorOperation.DELETE}:
        raise HTTPException(
            status_code=403,
            detail="Submission lifecycle changes must use the authorized review and grading APIs.",
        )
    if user.role == "STUDENT" and target_table in {
        "students",
        "submissions",
        "submission_audit_events",
    }:
        raise HTTPException(status_code=403, detail="Student access to identity and submission tables uses dedicated scoped APIs.")
    scoped_parameters = dict(request.parameters)
    if target_table in {"submissions", "submission_audit_events"}:
        scoped_parameters["authorized_course_ids"] = ["26ECAC401"]
    authorized_request = request.model_copy(
        update={
            "client_agent": "lab5_authenticated_api",
            "actor_user_id": user.user_id,
            "client_role": ConnectorRole.FACULTY if user.role in {"FACULTY", "ADMIN"} else ConnectorRole.STUDENT,
            "parameters": scoped_parameters,
        }
    )
    envelope = await coordinator.dispatch(
        lab_id="lab5",
        action="execute_operation",
        payload=authorized_request.model_dump(),
    )
    return envelope


@router.post("/query", response_model=APIEnvelope[dict[str, Any]])
async def query_agent(
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Natural language agent request routed through the Governed Connector."""
    require_course_access(user, "26ECAC401")
    authorized_payload = {**payload, "role": "FACULTY" if user.role in {"FACULTY", "ADMIN"} else "STUDENT"}
    envelope = await coordinator.dispatch(
        lab_id="lab5",
        action="query",
        payload=authorized_payload,
    )
    return envelope


@router.get("/audit", response_model=APIEnvelope[dict[str, Any]])
async def get_audit(
    limit: int = 50,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Retrieve immutable audit trail of all governed connector transactions."""
    envelope = await coordinator.dispatch(
        lab_id="lab5",
        action="get_audit",
        payload={"limit": limit},
    )
    return envelope


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_scenarios():
    """Retrieve preset evaluator scenarios for Lab 5."""
    return APIEnvelope(
        success=True,
        data=LAB5_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab5-scenarios",
    )
