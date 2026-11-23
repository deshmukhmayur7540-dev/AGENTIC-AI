"""Pydantic schemas and models for Lab 8: Parallel Role-Based Swarm."""

from enum import Enum
from typing import Any, Optional, Self
from pydantic import BaseModel, Field, field_validator, model_validator


class WorkerRole(str, Enum):
    """Specialized worker role per course unit."""
    UNIT_1_FOUNDATIONS = "Unit 1: Foundations Specialist"
    UNIT_2_FRAMEWORKS = "Unit 2: Frameworks & Tools Specialist"
    UNIT_3_MULTI_AGENT = "Unit 3: Multi-Agent Specialist"
    UNIT_4_SAFETY = "Unit 4: Safety & Governance Specialist"


class WorkerStatus(str, Enum):
    """Lifecycle status of an individual parallel worker."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class UnitTaskSpec(BaseModel):
    """Specification of the unit workload assigned to an individual worker."""
    unit_id: str
    chapter: int
    title: str
    topics_to_compile: list[str]
    lab_spec: str
    locked_plan_hash: str


class WorkerExecutionRecord(BaseModel):
    """Execution record and telemetry produced by a parallel worker."""
    worker_id: str
    unit_chapter: int
    role: str
    status: WorkerStatus
    output_data: Optional[dict[str, Any]] = None
    duration_ms: float = 0.0
    concurrency_thread: str = "asyncio-coro"
    provenance_chunks: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class SwarmResult(BaseModel):
    """Consolidated outcome of the parallel fan-out and fan-in merge process."""
    swarm_run_id: str
    course_id: str = "26ECAC401"
    total_workers: int
    successful_workers: int
    failed_workers: int
    workers: list[WorkerExecutionRecord]
    parallel_duration_ms: float
    sequential_estimated_ms: float
    speedup_ratio: float
    merged_workspace: Optional[dict[str, Any]] = None
    merge_rationale: list[str] = Field(default_factory=list)
    validation_passed: bool = True
    faculty_gate_required: bool = True
    status: str = "MERGED"  # MERGED, PARTIAL_SUCCESS, or FAILED


class StartSwarmRequest(BaseModel):
    """Request payload to initiate parallel swarm execution."""
    course_id: str = Field(default="26ECAC401")
    target_chapters: list[int] = Field(default_factory=lambda: [1, 2, 3, 4], min_length=1, max_length=4)
    simulate_worker_failure: Optional[int] = Field(
        default=None,
        description="Optional chapter number (1-4) to simulate failure for resilience testing",
    )

    @field_validator("target_chapters")
    @classmethod
    def validate_target_chapters(cls, chapters: list[int]) -> list[int]:
        if len(set(chapters)) != len(chapters) or any(chapter not in {1, 2, 3, 4} for chapter in chapters):
            raise ValueError("target_chapters must contain unique chapter numbers from 1 through 4.")
        return chapters

    @model_validator(mode="after")
    def validate_simulated_failure_target(self) -> Self:
        if self.simulate_worker_failure is not None:
            if self.simulate_worker_failure not in self.target_chapters:
                raise ValueError("simulate_worker_failure must identify one of the selected target_chapters.")
        return self
