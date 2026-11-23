"""Common schemas, envelopes, and error contracts."""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload for explicit error handling."""
    code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error explanation")
    target: Optional[str] = Field(default=None, description="Field or parameter causing the error")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional context or diagnostics")


class APIEnvelope(BaseModel, Generic[T]):
    """Standard unified API response wrapper for all CourseAgentAI endpoints."""
    success: bool = Field(default=True, description="Indicates if the operation completed successfully")
    data: Optional[T] = Field(default=None, description="Payload data returned upon success")
    error: Optional[ErrorDetail] = Field(default=None, description="Error detail if operation failed")
    trace_id: str = Field(description="Unique request tracing identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of response")


class AuditRecord(BaseModel):
    """Audit record capturing agent events and actions for transparency."""
    record_id: str
    lab_id: str
    event_type: str
    actor: str
    payload_summary: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScenarioDefinition(BaseModel):
    """Preset scenario definition for evaluator demonstration."""
    scenario_id: str
    title: str
    course_name: str
    category: str
    difficulty: str
    raw_prompt: str
    description: str
    expected_gaps: list[str]
    suggested_revision: str
