"""FastAPI routes for Lab 3: Reusable Schema-Typed Skills."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.auth import AuthenticatedUser, get_current_user, require_course_access
from app.core.coordinator import coordinator
from app.labs.lab3.registry import skill_registry
from app.models.common import APIEnvelope
from app.models.lab3_models import SkillExecutionRequest

router = APIRouter(prefix="/api/lab3", tags=["Lab 3: Reusable Skills"])

LAB3_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab3-planning-case-1",
        "title": "Scenario 1: 12-Week Agentic AI Course Plan",
        "category": "Course Planning Skill",
        "skill_name": "course_planning_skill",
        "parameters": {
            "course_code": "26ECAC401",
            "course_name": "Agentic AI",
            "target_weeks": 12,
            "focus_chapters": [1, 2, 3, 4],
        },
        "description": "Generates a complete 12-week schedule with milestones across all four Agentic AI chapters.",
    },
    {
        "scenario_id": "lab3-planning-case-2",
        "title": "Scenario 2: 8-Week Accelerated Lab Intensive",
        "category": "Course Planning Skill (Distinct Case)",
        "skill_name": "course_planning_skill",
        "parameters": {
            "course_code": "26ECAC401",
            "course_name": "Agentic AI Accelerated Bootcamp",
            "target_weeks": 8,
            "focus_chapters": [1, 2, 3],
        },
        "description": "Tests skill reusability on a distinct shortened 8-week intensive format without code modification.",
    },
    {
        "scenario_id": "lab3-research-react",
        "title": "Scenario 3: Research Summary on ReAct & Loops",
        "category": "Research Summary Skill",
        "skill_name": "research_summary_skill",
        "parameters": {
            "topic": "Plan-Act-Observe-Revise and ReAct reasoning",
            "course_code": "26ECAC401",
            "target_chapter": 1,
            "depth": "deep_dive",
        },
        "description": "Retrieves Chapter 1 lecture notes and synthesizes a structured academic brief with citations.",
    },
    {
        "scenario_id": "lab3-research-mcp",
        "title": "Scenario 4: Research Summary on MCP & Tool Calling",
        "category": "Research Summary Skill (Distinct Case)",
        "skill_name": "research_summary_skill",
        "parameters": {
            "topic": "Model Context Protocol and Typed Tool Calling",
            "course_code": "26ECAC401",
            "target_chapter": 2,
            "depth": "standard",
        },
        "description": "Retrieves Chapter 2 notes on MCP, function calling, and sandboxed runtimes.",
    },
    {
        "scenario_id": "lab3-format-handout",
        "title": "Scenario 5: Format Academic Handout",
        "category": "Course Content Formatting Skill",
        "skill_name": "course_content_formatting_skill",
        "parameters": {
            "title": "Autonomous Agent Core Architectures Handout",
            "course_code": "26ECAC401",
            "target_format": "markdown_handout",
            "raw_content": (
                "Perception: Ingests user input, API events, and environment states.\n"
                "Reasoning: Formulates plans, decomposes goals, and decides next actions.\n"
                "Action: Dispatches strictly typed tools to perform operations.\n"
                "Learning: Updates scratchpad and revises trajectory from observation feedback."
            ),
        },
        "description": "Converts raw lecture points into a standardized Markdown study guide with auto-generated TOC.",
    },
    {
        "scenario_id": "lab3-format-assignment",
        "title": "Scenario 6: Format Assignment Brief",
        "category": "Course Content Formatting Skill (Distinct Case)",
        "skill_name": "course_content_formatting_skill",
        "parameters": {
            "title": "Programming Lab 2: Tool-Using Agent with Auditable Trace",
            "course_code": "26ECAC401",
            "target_format": "assignment_brief",
            "raw_content": (
                "Implement a tool-using agent with strictly typed Pydantic input/output schemas.\n"
                "Deliverables: Python module with ToolRegistry, automated unit tests, and JSON execution trace.\n"
                "Grading Criteria: 50% Schema validation, 30% Deterministic calculator math, 20% Auditable trace."
            ),
        },
        "description": "Generates a structured assignment specification with problem statement and rubric section.",
    },
]


@router.get("/skills", response_model=APIEnvelope[dict[str, Any]])
async def list_skills():
    """List all registered skills with schema metadata."""
    envelope = await coordinator.dispatch(
        lab_id="lab3",
        action="list_skills",
        payload={},
    )
    return envelope


@router.get("/skills/{skill_name}", response_model=APIEnvelope[dict[str, Any]])
async def inspect_skill(skill_name: str):
    """Inspect input and output schemas for a specific skill."""
    envelope = await coordinator.dispatch(
        lab_id="lab3",
        action="inspect_skill",
        payload={"skill_name": skill_name},
    )
    return envelope


@router.post("/execute", response_model=APIEnvelope[dict[str, Any]])
@router.post("/skills/execute", response_model=APIEnvelope[dict[str, Any]])
async def execute_skill(
    request: SkillExecutionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Directly execute a registered skill with parameters."""
    course_id = request.parameters.get("course_code") or request.parameters.get("course_id") or "26ECAC401"
    if not isinstance(course_id, str):
        raise HTTPException(status_code=422, detail="Skill course code must be a string.")
    require_course_access(user, course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab3",
        action="execute_skill",
        payload={"skill_name": request.skill_name, "parameters": request.parameters},
    )
    return envelope


@router.post("/query", response_model=APIEnvelope[dict[str, Any]])
async def run_skill_agent_query(
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Natural language agent prompt routed to appropriate skill."""
    course_id = payload.get("course_code") or payload.get("course_id") or "26ECAC401"
    if not isinstance(course_id, str):
        raise HTTPException(status_code=422, detail="Skill course code must be a string.")
    require_course_access(user, course_id)
    # Accept both 'request' (frontend field name) and 'query' (internal field)
    if "request" in payload and "query" not in payload:
        payload = {**payload, "query": payload["request"]}

    envelope = await coordinator.dispatch(
        lab_id="lab3",
        action="run_query",
        payload=payload,
    )

    # Normalise backend response into the shape the frontend renders
    if envelope.success and isinstance(envelope.data, dict):
        raw = envelope.data
        execution = raw.get("execution", {})
        skill_name = raw.get("routing", "unknown_skill")
        status = execution.get("status", "SUCCESS")
        duration_ms = execution.get("duration_ms", 0) or 0
        output_data = execution.get("output_data", {})

        # Build a skills_executed list compatible with the frontend renderer
        skills_executed = [{
            "skill_name": skill_name,
            "status": status,
            "rationale": f"Routed by query: {raw.get('query', '')}",
            "output_data": output_data,
            "duration_ms": duration_ms,
        }]

        # Derive formatted_output from the execution output
        formatted_output = (
            output_data.get("formatted_content")
            or output_data.get("schedule_table")
            or output_data.get("summary")
            or output_data.get("content")
            or output_data.get("output")
            or ""
        )
        if not formatted_output and output_data:
            import json as _json
            formatted_output = _json.dumps(output_data, indent=2)

        envelope.data = {
            "status": status,
            "skills_executed": skills_executed,
            "duration_ms": duration_ms,
            "formatted_output": formatted_output,
            "routing": skill_name,
            "raw": raw,
        }

    return envelope



@router.get("/history", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_skill_history():
    """Retrieve recent skill execution records."""
    history = [r.model_dump() for r in skill_registry.get_history()]
    return APIEnvelope(
        success=True,
        data=history,
        error=None,
        trace_id="lab3-history",
    )


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_lab3_scenarios():
    """Retrieve preset evaluator scenarios for Lab 3."""
    return APIEnvelope(
        success=True,
        data=LAB3_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab3-scenarios",
    )
