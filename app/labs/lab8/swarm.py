"""ParallelSwarmCoordinator: Fan-out concurrent dispatch and evidence-based fan-in merge."""

import asyncio
import hashlib
import logging
import threading
import time
import uuid
from typing import Optional
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID, CANONICAL_COURSE_NAME
from app.labs.lab8.workers import execute_unit_worker
from app.models.lab8_models import (
    SwarmResult,
    UnitTaskSpec,
    WorkerExecutionRecord,
    WorkerStatus,
)

logger = logging.getLogger(__name__)

# Authoritative course unit specs aligned with locked curriculum
LOCKED_UNITS = [
    UnitTaskSpec(
        unit_id="unit-1",
        chapter=1,
        title="Foundations of Agentic AI & Autonomous Loops",
        topics_to_compile=[
            "Evolution from Generative AI to Agentic AI",
            "Autonomous Agent Characteristics",
            "Plan-Act-Observe-Revise Cycle",
            "Goal Decomposition & Reasoning Paradigms",
        ],
        lab_spec="Lab 1: Clarify -> Plan -> Revise Agent Workspace Planner",
        locked_plan_hash="ch1-plan-hash-9182",
    ),
    UnitTaskSpec(
        unit_id="unit-2",
        chapter=2,
        title="Agent Frameworks, Tools, Skills & Memory",
        topics_to_compile=[
            "Tool Calling & Pydantic Schema Validation",
            "Reusable Skills Discovery",
            "Memory Architectures: Short-Term vs Long-Term",
            "Model Context Protocol (MCP) Runtime",
        ],
        lab_spec="Lab 2: Tool-Using Agent with Auditable Trace",
        locked_plan_hash="ch2-plan-hash-8273",
    ),
    UnitTaskSpec(
        unit_id="unit-3",
        chapter=3,
        title="Multi-Agent Orchestration & Stateful Graphs",
        topics_to_compile=[
            "Multi-Agent Architectures & Collaboration Topologies",
            "Communication Protocols & Shared Memory Channels",
            "LangGraph Stateful Cyclic Execution",
            "Consensus Mechanisms & Negotiation",
        ],
        lab_spec="Lab 7: Multi-Agent Stateful Node Graph Orchestration",
        locked_plan_hash="ch3-plan-hash-7364",
    ),
    UnitTaskSpec(
        unit_id="unit-4",
        chapter=4,
        title="Learning, Deployment, Safety & Governance",
        topics_to_compile=[
            "Agentic Learning Paradigms & Feedback",
            "Safety Guardrails, Quotas & Resource Budgets",
            "Human Approval Gates & Audit Trails",
            "Production Safety Case Studies",
        ],
        lab_spec="Lab 6: Controlled Agent Runtime with Approval Gates",
        locked_plan_hash="ch4-plan-hash-6455",
    ),
]


class ParallelSwarmCoordinator:
    """Orchestrates true asynchronous parallel fan-out and rigorous fan-in merge."""

    def __init__(self, worker_timeout_seconds: float = 5.0) -> None:
        if worker_timeout_seconds <= 0:
            raise ValueError("worker_timeout_seconds must be greater than zero.")
        self._lock = threading.Lock()
        self._results: dict[str, SwarmResult] = {}
        self.worker_timeout_seconds = worker_timeout_seconds

    def get_result(self, swarm_run_id: str) -> Optional[SwarmResult]:
        """Return an isolated snapshot of a completed swarm result."""
        with self._lock:
            result = self._results.get(swarm_run_id)
            return result.model_copy(deep=True) if result else None

    async def dispatch_swarm(
        self,
        course_id: str = "26ECAC401",
        target_chapters: Optional[list[int]] = None,
        simulate_worker_failure: Optional[int] = None,
    ) -> SwarmResult:
        norm = normalize_course_id(course_id)
        if course_id and norm != CANONICAL_COURSE_ID:
            res = SwarmResult(
                swarm_run_id=f"swarm-{uuid.uuid4().hex[:8]}",
                course_id=course_id,
                total_workers=0,
                successful_workers=0,
                failed_workers=0,
                workers=[],
                parallel_duration_ms=0.0,
                sequential_estimated_ms=0.0,
                speedup_ratio=1.0,
                merged_workspace=None,
                merge_rationale=[f"Execution rejected: Course '{course_id}' is not established in course knowledge base. Only canonical course 26ECAC401 is supported."],
                validation_passed=False,
                faculty_gate_required=False,
                status="FAILED",
            )
            with self._lock:
                self._results[res.swarm_run_id] = res
            return res.model_copy(deep=True)

        cid = norm or CANONICAL_COURSE_ID
        swarm_run_id = f"swarm-{uuid.uuid4().hex[:8]}"
        ch_filter = target_chapters if target_chapters is not None else [1, 2, 3, 4]
        if (
            not ch_filter
            or len(set(ch_filter)) != len(ch_filter)
            or any(chapter not in {1, 2, 3, 4} for chapter in ch_filter)
        ):
            raise ValueError("target_chapters must contain unique chapter numbers from 1 through 4.")
        if simulate_worker_failure is not None:
            if simulate_worker_failure not in ch_filter:
                raise ValueError("simulate_worker_failure must identify one of the selected target_chapters.")

        active_tasks = [u for u in LOCKED_UNITS if u.chapter in ch_filter]

        # ---------------------------------------------------------------------
        # 1. FAN-OUT: Concurrent Parallel Worker Dispatch
        # ---------------------------------------------------------------------
        parallel_start = time.perf_counter()

        async def run_worker(task: UnitTaskSpec) -> WorkerExecutionRecord:
            start_time = time.perf_counter()
            try:
                return await asyncio.wait_for(
                    execute_unit_worker(
                        task,
                        simulate_failure=(simulate_worker_failure == task.chapter),
                    ),
                    timeout=self.worker_timeout_seconds,
                )
            except asyncio.TimeoutError:
                elapsed = (time.perf_counter() - start_time) * 1000
                return WorkerExecutionRecord(
                    worker_id=f"worker-ch{task.chapter}",
                    unit_chapter=task.chapter,
                    role=f"Unit {task.chapter} Specialist",
                    status=WorkerStatus.TIMEOUT,
                    output_data=None,
                    duration_ms=round(elapsed, 2),
                    concurrency_thread=f"asyncio-task-{task.chapter}",
                    provenance_chunks=[],
                    error=f"Worker exceeded the {self.worker_timeout_seconds:.2f}s execution limit.",
                )

        worker_coros = [run_worker(task) for task in active_tasks]

        # True concurrent execution via asyncio.gather
        worker_records: list[WorkerExecutionRecord] = await asyncio.gather(*worker_coros)

        parallel_duration_ms = (time.perf_counter() - parallel_start) * 1000
        sequential_estimated_ms = sum(w.duration_ms for w in worker_records)
        speedup = (
            round(sequential_estimated_ms / parallel_duration_ms, 2)
            if parallel_duration_ms > 0
            else 1.0
        )

        # ---------------------------------------------------------------------
        # 2. FAN-IN: Merge & Selector Engine
        # ---------------------------------------------------------------------
        merge_rationale: list[str] = []
        expected_by_chapter = {task.chapter: task for task in active_tasks}
        successful_workers: list[WorkerExecutionRecord] = []
        failed_workers: list[WorkerExecutionRecord] = []
        for worker in worker_records:
            if worker.status == WorkerStatus.SUCCESS:
                expected_task = expected_by_chapter.get(worker.unit_chapter)
                output = worker.output_data or {}
                if expected_task is None or (
                    output.get("unit_chapter") != expected_task.chapter
                    or output.get("unit_title") != expected_task.title
                    or output.get("compiled_topics") != expected_task.topics_to_compile
                    or output.get("practical_deliverable") != expected_task.lab_spec
                    or output.get("locked_plan_hash") != expected_task.locked_plan_hash
                    or not worker.provenance_chunks
                ):
                    worker.status = WorkerStatus.FAILED
                    worker.error = "Worker output failed locked-plan, coverage, or provenance validation."
                    worker.output_data = None
                    worker.provenance_chunks = []
                    failed_workers.append(worker)
                else:
                    successful_workers.append(worker)
            else:
                failed_workers.append(worker)

        validation_passed = not failed_workers and len(successful_workers) == len(active_tasks)

        merge_rationale.append(f"Fan-out dispatched {len(worker_records)} concurrent specialist workers.")
        merge_rationale.append(
            f"Execution telemetry: parallel={parallel_duration_ms:.1f}ms, "
            f"sequential_sum={sequential_estimated_ms:.1f}ms, speedup={speedup:.2f}x."
        )

        # Merge strategy: select according to locked plan conformity
        merged_modules: list[dict] = []
        for w in successful_workers:
            out = w.output_data
            if out:
                merged_modules.append({
                    "chapter": out["unit_chapter"],
                    "title": out["unit_title"],
                    "topics": out["compiled_topics"],
                    "deliverable": out["practical_deliverable"],
                    "grounding_count": out["grounding_count"],
                    "provenance": w.provenance_chunks,
                })
                merge_rationale.append(
                    f"Selected Unit {w.unit_chapter} from {w.worker_id}: Schema valid, locked plan hash verified."
                )

        merged_modules.sort(key=lambda m: m["chapter"])

        # Partial failure handling
        if failed_workers:
            validation_passed = False
            for fw in failed_workers:
                merge_rationale.append(
                    f"PARTIAL FAILURE: Worker for Chapter {fw.unit_chapter} failed ({fw.error}). "
                    f"Fault isolated without aborting remaining {len(successful_workers)} units."
                )
            status = "PARTIAL_SUCCESS"
        else:
            merge_rationale.append(
                f"All {len(active_tasks)} selected chapters passed locked-plan, coverage, and provenance validation."
            )
            status = "MERGED"

        if not successful_workers:
            status = "FAILED"

        merged_workspace = {
            "course_id": cid,
            "course_name": CANONICAL_COURSE_NAME,
            "units_compiled_count": len(merged_modules),
            "units": merged_modules,
            "validation_passed": validation_passed,
            "compiled_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }

        result = SwarmResult(
            swarm_run_id=swarm_run_id,
            course_id=cid,
            total_workers=len(worker_records),
            successful_workers=len(successful_workers),
            failed_workers=len(failed_workers),
            workers=worker_records,
            parallel_duration_ms=round(parallel_duration_ms, 2),
            sequential_estimated_ms=round(sequential_estimated_ms, 2),
            speedup_ratio=speedup,
            merged_workspace=merged_workspace,
            merge_rationale=merge_rationale,
            validation_passed=validation_passed,
            faculty_gate_required=True,
            status=status,
        )

        with self._lock:
            self._results[swarm_run_id] = result

        return result.model_copy(deep=True)


# Global singleton instance
swarm_coordinator = ParallelSwarmCoordinator()
