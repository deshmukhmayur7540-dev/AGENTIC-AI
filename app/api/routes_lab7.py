"""FastAPI routes for Lab 7: Agentic Node Graph."""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import AuthenticatedUser, require_course_access, require_roles
from app.core.coordinator import coordinator
from app.labs.lab7.graph import agentic_graph
from app.models.common import APIEnvelope
from app.models.lab7_models import (
    GraphApprovalRequest,
    StartGraphRunRequest,
    WorkspaceGraphState,
)


class StepGraphRequest(BaseModel):
    """Request to step the graph one node at a time by run_id."""
    run_id: Optional[str] = Field(default=None, description="Existing run_id to continue")
    user_request: Optional[str] = Field(default=None, description="New run request (if run_id not set)")
    course_id: str = Field(default="26ECAC401")
    target_weeks: int = Field(default=12)
    simulate_validation_failure: bool = Field(default=False)


class BodyApprovalRequest(BaseModel):
    """Body-based approval request (run_id in body for frontend compatibility)."""
    run_id: str
    approved: bool
    comments: Optional[str] = None

router = APIRouter(prefix="/api/lab7", tags=["Lab 7: Agentic Node Graph"])


def _require_run_access(run_id: str, user: AuthenticatedUser) -> WorkspaceGraphState:
    state = agentic_graph.get_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Graph run was not found.")
    require_course_access(user, state.course_id)
    return state


LAB7_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab7-standard-pipeline",
        "title": "Scenario 1: End-to-End Specialist Multi-Agent Pipeline",
        "category": "Graph Orchestration",
        "user_request": "Coordinate all specialist nodes to assemble the complete 26ECAC401 course workspace.",
        "target_weeks": 12,
        "simulate_validation_failure": False,
        "description": "Executes Coordinator -> Planning -> Notes Repo -> Assignment Dist -> Submission Col -> Grading Org -> Milestones -> Validation -> Faculty Approval Gate.",
    },
    {
        "scenario_id": "lab7-bounded-retry-healing",
        "title": "Scenario 2: Validation Failure & Bounded Self-Healing Retry",
        "category": "Integrity Gates & Bounded Loops",
        "user_request": "Simulate grading weight sum defect (110%), trigger validation failure edge, retry back to grading_org, and self-heal.",
        "target_weeks": 12,
        "simulate_validation_failure": True,
        "description": "Demonstrates cyclic conditional transition: Validation catches defect, safely routes back to GradingOrgNode (attempt 2), self-heals to 100%, and passes.",
    },
    {
        "scenario_id": "lab7-approval-gate-publish",
        "title": "Scenario 3: Consequential Faculty Sign-off & Publication",
        "category": "Faculty Oversight",
        "user_request": "Demonstrate that the finalized course workspace remains unreleased until explicit faculty approval.",
        "target_weeks": 14,
        "simulate_validation_failure": False,
        "description": "Verifies that status pauses in WAITING_APPROVAL and transitions to COMPLETED / PUBLISHED only upon evaluator sign-off.",
    },
]


@router.post("/run", response_model=APIEnvelope[dict[str, Any]])
async def run_graph(
    request: StartGraphRunRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Execute the multi-agent node graph."""
    require_course_access(user, request.course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab7",
        action="run_graph",
        payload={
            **request.model_dump(),
            "authenticated_user_id": user.user_id,
        },
    )
    return envelope


@router.get("/state/{run_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_graph_state(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Retrieve full execution state, node traces, and workspace assembly for a run."""
    _require_run_access(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab7",
        action="get_state",
        payload={"run_id": run_id},
    )
    return envelope


@router.post("/approve/{run_id}", response_model=APIEnvelope[dict[str, Any]])
async def approve_graph_run(
    run_id: str,
    request: GraphApprovalRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Submit human faculty approval or rejection for publishing the course workspace."""
    state = _require_run_access(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab7",
        action="approve",
        payload={
            "run_id": run_id,
            "approved": request.approved,
            "comments": request.comments,
            "decision_by": user.user_id,
            "course_id": state.course_id,
        },
    )
    return envelope


@router.post("/step", response_model=APIEnvelope[dict[str, Any]])
async def step_graph(
    request: StepGraphRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Execute a single node step in the graph (for UI step-through mode).
    
    If run_id is provided, continues that run one step.
    If no run_id, initializes a new run and executes the first node.
    """
    if request.run_id:
        _require_run_access(request.run_id, user)
    else:
        require_course_access(user, request.course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab7",
        action="step_graph",
        payload={
            "run_id": request.run_id,
            "user_request": request.user_request or "Synthesize 26ECAC401 workspace",
            "course_id": request.course_id,
            "target_weeks": request.target_weeks,
            "simulate_validation_failure": request.simulate_validation_failure,
            "authenticated_user_id": user.user_id,
        },
    )
    return envelope


@router.post("/approve", response_model=APIEnvelope[dict[str, Any]])
async def approve_graph_body(
    request: BodyApprovalRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Submit faculty approval or rejection using run_id in request body (frontend-friendly)."""
    state = _require_run_access(request.run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab7",
        action="approve",
        payload={
            "run_id": request.run_id,
            "approved": request.approved,
            "comments": request.comments,
            "decision_by": user.user_id,
            "course_id": state.course_id,
        },
    )
    return envelope


@router.get("/topology", response_model=APIEnvelope[dict[str, Any]])
async def get_graph_topology():
    """Retrieve visual topology of nodes and directed/conditional edges."""
    topology = agentic_graph.get_topology()
    return APIEnvelope(
        success=True,
        data=topology.model_dump(),
        error=None,
        trace_id="lab7-topology",
    )


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_scenarios():
    """Retrieve preset evaluator scenarios for Lab 7."""
    return APIEnvelope(
        success=True,
        data=LAB7_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab7-scenarios",
    )
