"""FastAPI routes for Lab 2: Tool-Using Agent with Typed Tools and Auditable Execution Traces."""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth import AuthenticatedUser, get_current_user, require_course_access
from app.core.coordinator import coordinator
from app.labs.lab2.tools.registry import tool_registry
from app.models.common import APIEnvelope
from app.models.lab2_models import (
    AgentQueryRequest,
    DirectToolExecutionRequest,
)
import app.labs.lab2  # Ensure Lab 2 agent is registered in lab_registry

router = APIRouter(prefix="/api/lab2", tags=["Lab 2: Tool-Using Agent"])


LAB2_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab2-notes-react-reasoning",
        "title": "Scenario 1: Agent Reasoning & ReAct Notes",
        "category": "Curriculum Knowledge Retrieval",
        "prompt": "Search 26ECAC401 notes for ReAct and Plan-Act-Observe-Revise agent architecture.",
        "description": "Retrieves verified lecture notes from Chapter 1 without hallucinating missing topics.",
        "expected_tools": ["search_course_notes"],
    },
    {
        "scenario_id": "lab2-frameworks-langgraph-memory",
        "title": "Scenario 2: Frameworks, LangGraph & Memory",
        "category": "Curriculum Knowledge Retrieval",
        "prompt": "What does 26ECAC401 cover about LangGraph, tools, and short-term vs long-term memory?",
        "description": "Retrieves Chapter 2 framework, tool calling, and memory architecture sections.",
        "expected_tools": ["search_course_notes"],
    },
    {
        "scenario_id": "lab2-syllabus-inspection",
        "title": "Scenario 3: Canonical Syllabus & Chapters",
        "category": "Curriculum Verification",
        "prompt": "Retrieve 26ECAC401 syllabus and verify established course chapters and topics.",
        "description": "Inspects canonical 26ECAC401 syllabus modules grounded in Chapter 1 and Chapter 2.",
        "expected_tools": ["read_course_syllabus"],
    },
    {
        "scenario_id": "lab2-grading-audit",
        "title": "Scenario 4: Grading Policy & Syllabus Audit",
        "category": "Academic Integrity & Non-Hallucination",
        "prompt": "Audit 26ECAC401 grading breakdown: verify if published weights sum to 100%.",
        "description": "Inspects syllabus and verifies that unestablished grading policy is safely reported without hallucination.",
        "expected_tools": ["read_course_syllabus"],
    },
    {
        "scenario_id": "lab2-rubric-non-hallucination",
        "title": "Scenario 5: Catalog-Backed Lab 1 Rubric",
        "category": "Anti-Hallucination & Error Containment",
        "prompt": "Show me the persisted rubric for Lab 1 in 26ECAC401.",
        "course_id": "26ECAC401",
        "assignment_id": "lab1",
        "description": "Retrieves the actual Lab 1 rubric from the authorized course assignment catalog.",
        "expected_tools": ["get_rubric_breakdown"],
    },
    {
        "scenario_id": "lab2-unknown-course-error",
        "title": "Scenario 6: Intentional Invalid-Course Safety Check",
        "category": "Error Containment & Safety",
        "prompt": "Audit UNKNOWN999 grading.",
        "description": "Negative test only: intentionally requests a course absent from the catalog and expects an explicit error.",
        "expected_tools": ["read_course_syllabus"],
    },
]


@router.post("/query", response_model=APIEnvelope)
@router.post("/agent/query", response_model=APIEnvelope)
async def query_tool_agent(
    query_req: AgentQueryRequest,
    req: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> APIEnvelope:
    """Execute a natural language request through the ToolUsingAgent and return an AuditableExecutionTrace."""
    require_course_access(user, query_req.course_id or "26ECAC401")
    return await coordinator.dispatch(
        lab_id="lab2",
        action="query",
        payload=query_req.model_dump(),
    )


@router.get("/tools", response_model=APIEnvelope)
async def list_available_tools() -> APIEnvelope:
    """Return the catalog of registered typed tools and their JSON schemas."""
    definitions = tool_registry.list_tools()
    return APIEnvelope(
        success=True,
        data=[d.model_dump() for d in definitions],
        trace_id="lab2-tools-list",
    )


@router.post("/tools/execute", response_model=APIEnvelope)
async def execute_tool_directly(
    req: DirectToolExecutionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> APIEnvelope:
    """Execute a registered tool directly for diagnostics and verification."""
    course_id = req.parameters.get("course_id", "26ECAC401")
    if not isinstance(course_id, str):
        raise HTTPException(status_code=422, detail="Tool course_id must be a string.")
    require_course_access(user, course_id)
    record = tool_registry.execute_tool(req.tool_name, req.parameters)
    return APIEnvelope(
        success=True,
        data=record.model_dump(),
        trace_id=record.call_id,
    )


@router.get("/scenarios", response_model=APIEnvelope)
async def get_lab2_scenarios() -> APIEnvelope:
    """Retrieve pre-built faculty/auditor evaluation scenarios for Lab 2."""
    return APIEnvelope(
        success=True,
        data=LAB2_EVALUATOR_SCENARIOS,
        trace_id="lab2-scenarios",
    )
