"""Pydantic schemas and contracts for Lab 6: Controlled Agent Runtime."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ExecutionState(str, Enum):
    """Lifecycle execution states of a runtime run."""
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    REJECTED = "REJECTED"


class RuntimeBudget(BaseModel):
    """Resource limits and execution constraints."""
    max_steps: int = Field(default=8, ge=1, le=50, description="Max allowed execution steps")
    max_tool_calls: int = Field(default=10, ge=1, le=50, description="Max allowed tool/skill calls")
    max_duration_seconds: float = Field(default=30.0, gt=0, le=600, description="Execution timeout limit")
    max_consequential_actions: int = Field(default=2, ge=0, le=50, description="Max allowed consequential actions")


class ApprovalGate(BaseModel):
    """Human-in-the-loop approval gate for consequential actions."""
    gate_id: str
    run_id: str
    step_id: str
    action_name: str
    action_payload: dict[str, Any]
    consequential_reason: str = Field(description="Why human faculty approval is required")
    status: str = Field(default="PENDING", description="PENDING, APPROVED, or REJECTED")
    decision_by: Optional[str] = None
    decision_timestamp: Optional[str] = None


class RuntimeCheckpoint(BaseModel):
    """Serialized snapshot of runtime state at a discrete step."""
    checkpoint_id: str
    run_id: str
    step_index: int
    step_name: str
    state_snapshot: dict[str, Any]
    variables: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuntimeAuditEntry(BaseModel):
    """Observable record of an action executed within the runtime."""
    run_id: str
    step_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    tool_or_skill: Optional[str] = None
    input_summary: str
    output_summary: str
    status: str = Field(description="SUCCESS, WAITING_APPROVAL, BUDGET_EXCEEDED, or ERROR")
    duration_ms: float = 0.0
    error: Optional[str] = None


class RunRecord(BaseModel):
    """Complete state and trajectory of an agent runtime execution."""
    run_id: str
    course_id: str = "26ECAC401"
    owner_user_id: Optional[str] = None
    owner_role: Optional[str] = None
    state: ExecutionState = ExecutionState.INITIALIZED
    budget: RuntimeBudget
    steps_executed: int = 0
    tool_calls_executed: int = 0
    consequential_actions_executed: int = 0
    current_step_id: Optional[str] = None
    pending_approval: Optional[ApprovalGate] = None
    checkpoints: list[RuntimeCheckpoint] = Field(default_factory=list)
    audit_entries: list[RuntimeAuditEntry] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None


from pydantic import BaseModel, Field, model_validator


class StartRunRequest(BaseModel):
    """Request payload to initiate a new controlled runtime run."""
    task_description: str = Field(default="Compile and verify 26ECAC401 course workspace", description="Task to execute within controlled runtime")
    task: Optional[str] = None
    course_id: str = Field(default="26ECAC401")
    budget: Optional[RuntimeBudget] = None
    require_approval_for_publish: bool = True

    @model_validator(mode="before")
    @classmethod
    def map_task_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            t = data.get("task") or data.get("task_description") or "Compile and verify 26ECAC401 course workspace"
            data["task_description"] = t
            data["task"] = t
        return data


class ApprovalDecisionRequest(BaseModel):
    """Payload to approve or reject a pending approval gate."""
    run_id: Optional[str] = None
    gate_id: Optional[str] = None
    approved: bool
    comments: Optional[str] = None
    comment: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_comment_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            c = data.get("comment") or data.get("comments")
            data["comments"] = c
            data["comment"] = c
        return data
