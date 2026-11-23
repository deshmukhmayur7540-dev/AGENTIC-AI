"""Agent execution states, workflow tracking, and session contexts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Lifecycle statuses for agent workflows."""
    IDLE = "IDLE"
    ANALYZING_GAPS = "ANALYZING_GAPS"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    GENERATING_PLAN = "GENERATING_PLAN"
    PLAN_READY = "PLAN_READY"
    REVISING_PLAN = "REVISING_PLAN"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class ExecutionStep(BaseModel):
    """A record of an execution step in the agent pipeline for observability."""
    step_id: str
    step_name: str
    status: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None


class AgentState(BaseModel):
    """State of an agent during execution."""
    agent_id: str
    current_status: WorkflowStatus = WorkflowStatus.IDLE
    current_step: Optional[str] = None
    execution_history: list[ExecutionStep] = Field(default_factory=list)
    memory_context: dict[str, Any] = Field(default_factory=dict)
    last_error: Optional[str] = None


class SessionContext(BaseModel):
    """Runtime context for an active session."""
    session_id: str
    active_lab: str = "lab1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
