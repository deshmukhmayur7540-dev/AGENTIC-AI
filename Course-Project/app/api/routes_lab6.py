"""FastAPI routes for Lab 6: Controlled Agent Runtime.

Provides both RESTful resource endpoints (/run/{id}/...) and frontend-convenience
endpoints (/start, /step, /crash, /resume, /decision) for complete interoperability.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.core.coordinator import coordinator
from app.labs.lab6.engine import runtime_engine
from app.models.common import APIEnvelope
from app.models.lab6_models import (
    ApprovalDecisionRequest,
    StartRunRequest,
)

router = APIRouter(prefix="/api/lab6", tags=["Lab 6: Controlled Runtime"])


class Lab6ActionRequest(BaseModel):
    """Payload for step, crash, and resume actions."""
    run_id: str


class Lab6DecisionRequest(BaseModel):
    """Frontend-compatible approval decision payload."""
    run_id: str
    approved: bool
    comment: Optional[str] = None
    gate_id: Optional[str] = None


def _enrich_run_data(envelope_data: Any, run_id: Optional[str] = None) -> Any:
    """Enrich envelope data so that both nested {'run': {...}} and top-level fields match expectations."""
    if not isinstance(envelope_data, dict):
        return envelope_data

    run_obj = envelope_data.get("run")
    if not run_obj and run_id:
        r = runtime_engine.get_run(run_id)
        if r:
            run_obj = r.model_dump()
            envelope_data["run"] = run_obj

    if isinstance(run_obj, dict):
        # Merge run fields to top level without overwriting existing explicit action response keys
        for k, v in run_obj.items():
            if k not in envelope_data:
                envelope_data[k] = v

    return envelope_data


def _authorize_run(run_id: str, user: AuthenticatedUser) -> None:
    run = runtime_engine.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runtime run was not found.")
    require_course_access(user, run.course_id)


LAB6_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab6-full-lifecycle",
        "title": "Scenario 1: Complete Governed Lifecycle with Approval Gate",
        "category": "Controlled Execution",
        "task": "Compile, ground, structure, and publish 26ECAC401 course workspace",
        "description": "Advances through prerequisite check, notes grounding, weekly schedule synthesis, and pauses at faculty approval gate before final publishing.",
    },
    {
        "scenario_id": "lab6-budget-overrun",
        "title": "Scenario 2: Strict Budget Constraint Enforcement",
        "category": "Budget & Resource Guardrails",
        "task": "Attempt infinite execution loop on course compilation",
        "budget": {"max_steps": 2, "max_tool_calls": 2},
        "description": "Enforces max step budget guardrail (2 steps) and halts execution with BUDGET_EXCEEDED state.",
    },
    {
        "scenario_id": "lab6-crash-recovery",
        "title": "Scenario 3: Checkpointing & Crash Recovery Simulation",
        "category": "Fault Tolerance & Checkpointing",
        "task": "Simulate process failure during compilation, verify checkpoints, and resume seamlessly",
        "description": "Executes 2 steps, simulates a sudden server failure, restores state from checkpoint, and continues without data loss.",
    },
    {
        "scenario_id": "lab6-audit-observability",
        "title": "Scenario 4: Full Audit Trail & Observability",
        "category": "Audit & Observability",
        "task": "Inspect auditable execution history with zero private CoT tokens",
        "description": "Audits step IDs, durations, actor roles, and execution statuses for accreditation review.",
    },
]


@router.post("/run", response_model=APIEnvelope[dict[str, Any]])
async def start_run(
    request: StartRunRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Start a new governed execution run with budget parameters."""
    require_course_access(user, request.course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="start_run",
        payload={
            **request.model_dump(),
            "owner_user_id": user.user_id,
            "owner_role": user.role,
            "actor_user_id": user.user_id,
            "actor_role": user.role,
        },
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data)
    return envelope


@router.post("/start", response_model=APIEnvelope[dict[str, Any]])
async def start_run_frontend_alias(
    request: StartRunRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Frontend-compatible alias: starts a new controlled runtime run."""
    return await start_run(request, user)


@router.get("/run/{run_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_run_status(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Retrieve current state, budget progress, checkpoints, and pending gates."""
    _authorize_run(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="get_run",
        payload={"run_id": run_id},
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=run_id)
    return envelope


@router.post("/run/{run_id}/step", response_model=APIEnvelope[dict[str, Any]])
async def advance_step(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Advance the run by executing the next controlled step."""
    _authorize_run(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="step",
        payload={"run_id": run_id, "actor_user_id": user.user_id, "actor_role": user.role},
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=run_id)
    return envelope


@router.post("/step", response_model=APIEnvelope[dict[str, Any]])
async def advance_step_frontend_alias(
    request: Lab6ActionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Frontend-compatible alias: executes next controlled step with run_id in request body."""
    return await advance_step(request.run_id, user)


@router.post("/run/{run_id}/approve", response_model=APIEnvelope[dict[str, Any]])
async def submit_approval(
    run_id: str,
    request: ApprovalDecisionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Submit faculty approval or rejection for a pending consequential action gate."""
    _authorize_run(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="approve",
        payload={
            "run_id": run_id,
            "gate_id": request.gate_id,
            "approved": request.approved,
            "decision_by": user.user_id,
            "actor_user_id": user.user_id,
            "actor_role": user.role,
        },
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=run_id)
    return envelope


@router.post("/decision", response_model=APIEnvelope[dict[str, Any]])
async def submit_decision_frontend_alias(
    request: Lab6DecisionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Frontend-compatible alias: submits approval decision with run_id in body."""
    _authorize_run(request.run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="approve",
        payload={
            "run_id": request.run_id,
            "gate_id": request.gate_id,
            "approved": request.approved,
            "decision_by": user.user_id,
            "actor_user_id": user.user_id,
            "actor_role": user.role,
        },
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=request.run_id)
    return envelope


@router.post("/run/{run_id}/crash", response_model=APIEnvelope[dict[str, Any]])
async def simulate_crash(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Simulate an abrupt failure / process termination."""
    _authorize_run(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="crash",
        payload={"run_id": run_id, "actor_user_id": user.user_id, "actor_role": user.role},
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=run_id)
    return envelope


@router.post("/crash", response_model=APIEnvelope[dict[str, Any]])
async def simulate_crash_frontend_alias(
    request: Lab6ActionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Frontend-compatible alias: injects simulated crash with run_id in body."""
    return await simulate_crash(request.run_id, user)


@router.post("/run/{run_id}/resume", response_model=APIEnvelope[dict[str, Any]])
async def resume_run(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Resume execution from the latest persisted checkpoint."""
    _authorize_run(run_id, user)
    envelope = await coordinator.dispatch(
        lab_id="lab6",
        action="resume",
        payload={"run_id": run_id, "actor_user_id": user.user_id, "actor_role": user.role},
    )
    if envelope.data:
        envelope.data = _enrich_run_data(envelope.data, run_id=run_id)
    return envelope


@router.post("/resume", response_model=APIEnvelope[dict[str, Any]])
async def resume_run_frontend_alias(
    request: Lab6ActionRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Frontend-compatible alias: resumes run from checkpoint with run_id in body."""
    return await resume_run(request.run_id, user)


@router.get("/run/{run_id}/audit", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_run_audit(
    run_id: str,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Retrieve full audit trail of actions executed within this run."""
    _authorize_run(run_id, user)
    run = runtime_engine.get_run(run_id)
    if not run:
        return APIEnvelope(
            success=False,
            data=None,
            error=None,
            trace_id=f"audit-{run_id}",
        )
    return APIEnvelope(
        success=True,
        data=[a.model_dump() for a in run.audit_entries],
        error=None,
        trace_id=f"audit-{run_id}",
    )


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_scenarios():
    """Retrieve preset evaluator scenarios for Lab 6."""
    return APIEnvelope(
        success=True,
        data=LAB6_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab6-scenarios",
    )
