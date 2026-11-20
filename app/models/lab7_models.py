"""Pydantic schemas and models for Lab 7: Agentic Node Graph."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class NodeExecutionStatus(str, Enum):
    """Execution status of an individual graph node."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    RETRYING = "RETRYING"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class NodeTraceRecord(BaseModel):
    """Audit record capturing an individual node execution trace in the graph."""
    node_id: str
    node_role: str
    status: NodeExecutionStatus
    input_summary: str
    output_summary: str
    duration_ms: float = 0.0
    transition_to: Optional[str] = None
    attempt_number: int = 1
    error: Optional[str] = None


class WorkspaceGraphState(BaseModel):
    """Stateful schema passed along directed and conditional edges of the node graph."""
    run_id: str
    owner_user_id: Optional[str] = None
    course_id: str = "26ECAC401"
    course_name: str = "Agentic AI"
    user_request: str
    target_weeks: int = 12

    # Specialist Agent State Data
    ingestion_data: dict[str, Any] = Field(default_factory=dict)
    planning_schedule: list[dict[str, Any]] = Field(default_factory=list)
    notes_repository: list[dict[str, Any]] = Field(default_factory=list)
    assignments_distribution: list[dict[str, Any]] = Field(default_factory=list)
    submission_policies: dict[str, Any] = Field(default_factory=dict)
    grading_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    project_milestones: list[str] = Field(default_factory=list)

    # Validation & Bounded Retry
    validation_passed: bool = False
    validation_issues: list[str] = Field(default_factory=list)
    retry_counts: dict[str, int] = Field(default_factory=dict)
    max_retries: int = 3

    # Human Faculty Approval Gate
    faculty_approved: bool = False
    faculty_comments: Optional[str] = None
    approval_actor_user_id: Optional[str] = None
    requires_approval: bool = True

    # Final Output
    published_workspace: Optional[dict[str, Any]] = None
    current_node: str = "coordinator"
    completed_nodes: list[str] = Field(default_factory=list)
    node_states: dict[str, str] = Field(default_factory=dict)
    retry_count: int = 0
    status: str = "INITIALIZED"  # INITIALIZED, RUNNING, WAITING_APPROVAL, COMPLETED, FAILED, RETRY_EXHAUSTED
    execution_history: list[NodeTraceRecord] = Field(default_factory=list)


class GraphTopologyNode(BaseModel):
    """Node description for visual graph rendering."""
    id: str
    label: str
    role: str
    description: str


class GraphTopologyEdge(BaseModel):
    """Edge connection for visual graph rendering."""
    source: str
    target: str
    condition: Optional[str] = None
    edge_type: str = "directed"  # directed, conditional, retry


class GraphTopologyInfo(BaseModel):
    """Visual topology describing graph nodes and edges."""
    nodes: list[GraphTopologyNode]
    edges: list[GraphTopologyEdge]


class StartGraphRunRequest(BaseModel):
    """Request payload to initiate execution of the Agentic Node Graph."""
    user_request: str = Field(description="Faculty request for course workspace organization")
    course_id: str = Field(default="26ECAC401")
    target_weeks: int = Field(default=12, ge=4, le=24)
    simulate_validation_failure: bool = Field(default=False, description="Test bounded retry path")


class GraphApprovalRequest(BaseModel):
    """Request payload to approve or reject graph publication."""
    approved: bool
    comments: Optional[str] = None
