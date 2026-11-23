"""Contracts for Lab 2 (Tool-Using Agent) to preserve architecture compatibility."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"


class ToolCallRecord(BaseModel):
    """Observable tool invocation record with strictly validated inputs and outputs."""
    call_id: str
    tool_name: str
    validated_input: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    status: ToolExecutionStatus
    execution_duration_ms: float
    error: Optional[str] = None


class AuditableTraceStep(BaseModel):
    """Auditable execution step displayed in the UI (no private chain-of-thought tokens)."""
    step_number: int
    selected_action: str
    tool_call: Optional[ToolCallRecord] = None
    validation_result: str
    evidence_source: str
    intermediate_summary: str


class AuditableExecutionTrace(BaseModel):
    """Complete transparent execution trace for faculty/auditor evaluation."""
    user_request: str
    steps: list[AuditableTraceStep]
    verified_facts: dict[str, Any]
    final_conclusion: str
    total_duration_ms: float
    status: ToolExecutionStatus = ToolExecutionStatus.SUCCESS


from app.core.constants import CANONICAL_COURSE_CODE


class AgentQueryRequest(BaseModel):
    """Input payload for submitting a query to the Lab 2 Tool-Using Agent."""
    request: str = Field(min_length=1, description="Natural language faculty or auditor request")
    course_id: Optional[str] = Field(
        default=CANONICAL_COURSE_CODE,
        description="Target canonical course code (defaults to 26ECAC401)",
    )
    assignment_id: Optional[str] = Field(
        default=None,
        description="Assignment selected from the authorized course catalog, when relevant",
    )


class DirectToolExecutionRequest(BaseModel):
    """Input payload for executing a single tool directly for inspection."""
    tool_name: str = Field(min_length=1, description="Name of the registered tool to invoke")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Raw input parameter dictionary")
