"""FastAPI routes for Lab 8: Parallel Swarm."""

from typing import Any
from fastapi import APIRouter, Depends
from app.auth import AuthenticatedUser, get_current_user, require_course_access
from app.core.coordinator import coordinator
from app.labs.lab8.swarm import swarm_coordinator
from app.models.common import APIEnvelope
from app.models.lab8_models import StartSwarmRequest

router = APIRouter(prefix="/api/lab8", tags=["Lab 8: Parallel Swarm"])

LAB8_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab8-full-parallel-success",
        "title": "Scenario 1: 4-Unit Parallel Fan-Out & Merge (100% Success)",
        "category": "Parallel Processing",
        "course_id": "26ECAC401",
        "target_chapters": [1, 2, 3, 4],
        "simulate_worker_failure": None,
        "description": "Dispatches 4 concurrent specialist workers (Chapters 1-4) simultaneously, measures speedup, and performs evidence-based fan-in merge.",
    },
    {
        "scenario_id": "lab8-partial-failure-resilience",
        "title": "Scenario 2: Worker 3 Failure & Resilient Merge Strategy",
        "category": "Fault Containment & Merge Selection",
        "course_id": "26ECAC401",
        "target_chapters": [1, 2, 3, 4],
        "simulate_worker_failure": 3,
        "description": "Simulates worker 3 encountering a network partition; demonstrates fault isolation, partial success merge, and transparent logging without crashing the swarm.",
    },
    {
        "scenario_id": "lab8-two-unit-micro-swarm",
        "title": "Scenario 3: Foundations & Tools Micro-Swarm (Chapters 1 & 2)",
        "category": "Targeted Fan-Out",
        "course_id": "26ECAC401",
        "target_chapters": [1, 2],
        "simulate_worker_failure": None,
        "description": "Dispatches a focused 2-worker team on foundational agent loops and tool integration.",
    },
]


@router.post("/dispatch", response_model=APIEnvelope[dict[str, Any]])
async def dispatch_swarm(
    request: StartSwarmRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Dispatch parallel specialist workers concurrently and merge results."""
    require_course_access(user, request.course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab8",
        action="dispatch_swarm",
        payload=request.model_dump(),
    )
    return envelope


@router.get("/status/{swarm_run_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_swarm_status(
    swarm_run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve execution metrics, worker statuses, and merge details for a swarm run."""
    require_course_access(user, "26ECAC401")
    envelope = await coordinator.dispatch(
        lab_id="lab8",
        action="get_status",
        payload={"swarm_run_id": swarm_run_id},
    )
    return envelope


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_scenarios():
    """Retrieve preset evaluator scenarios for Lab 8."""
    return APIEnvelope(
        success=True,
        data=LAB8_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab8-scenarios",
    )
