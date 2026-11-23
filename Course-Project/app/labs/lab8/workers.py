"""Asynchronous specialist unit workers for parallel swarm execution."""

import asyncio
import re
import time
from typing import Any
from app.knowledge.service import knowledge_service
from app.models.lab8_models import (
    UnitTaskSpec,
    WorkerExecutionRecord,
    WorkerRole,
    WorkerStatus,
)

ROLE_MAP = {
    1: WorkerRole.UNIT_1_FOUNDATIONS.value,
    2: WorkerRole.UNIT_2_FRAMEWORKS.value,
    3: WorkerRole.UNIT_3_MULTI_AGENT.value,
    4: WorkerRole.UNIT_4_SAFETY.value,
}


async def execute_unit_worker(task: UnitTaskSpec, simulate_failure: bool = False) -> WorkerExecutionRecord:
    """Asynchronously execute a unit processing task.
    
    Extracts authoritative knowledge for the assigned chapter, validates topics,
    and produces structured academic unit material concurrently.
    """
    start_time = time.perf_counter()
    worker_id = f"worker-ch{task.chapter}"
    role_name = ROLE_MAP.get(task.chapter, f"Unit {task.chapter} Specialist")

    # Simulate realistic non-trivial async work (I/O, analysis)
    await asyncio.sleep(0.05)

    if simulate_failure:
        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkerExecutionRecord(
            worker_id=worker_id,
            unit_chapter=task.chapter,
            role=role_name,
            status=WorkerStatus.FAILED,
            output_data=None,
            duration_ms=round(elapsed, 2),
            concurrency_thread=f"asyncio-task-{task.chapter}",
            provenance_chunks=[],
            error=f"SIMULATED_WORKER_FAILURE: Network partition or timeout in {worker_id}",
        )

    try:
        provenance_chunks: list[dict[str, Any]] = []
        seen_evidence: set[tuple[str, str]] = set()
        for topic_query in task.topics_to_compile:
            queries = [topic_query]
            queries.extend(
                token for token in re.findall(r"[A-Za-z][A-Za-z-]{3,}", topic_query)
                if token.casefold() != topic_query.casefold()
            )
            matches = []
            for query in queries:
                search_res = knowledge_service.search(
                    query=query,
                    course_id="26ECAC401",
                    chapter=task.chapter,
                    top_k=1,
                )
                if search_res.matches:
                    matches = search_res.matches
                    break

            for match in matches:
                evidence_key = (match.source_document, match.matched_text)
                if evidence_key in seen_evidence:
                    continue
                seen_evidence.add(evidence_key)
                provenance_chunks.append({
                    "chapter": match.chapter,
                    "topic": match.topic,
                    "source": match.source,
                    "source_document": match.source_document,
                    "excerpt": match.matched_text[:200],
                })
                break

            if len(provenance_chunks) == 3:
                break

        output = {
            "unit_chapter": task.chapter,
            "unit_title": task.title,
            "compiled_topics": task.topics_to_compile,
            "practical_deliverable": task.lab_spec,
            "grounding_count": len(provenance_chunks),
            "locked_plan_hash": task.locked_plan_hash,
        }

        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkerExecutionRecord(
            worker_id=worker_id,
            unit_chapter=task.chapter,
            role=role_name,
            status=WorkerStatus.SUCCESS,
            output_data=output,
            duration_ms=round(elapsed, 2),
            concurrency_thread=f"asyncio-task-{task.chapter}",
            provenance_chunks=provenance_chunks,
            error=None,
        )

    except Exception as exc:
        elapsed = (time.perf_counter() - start_time) * 1000
        return WorkerExecutionRecord(
            worker_id=worker_id,
            unit_chapter=task.chapter,
            role=role_name,
            status=WorkerStatus.FAILED,
            output_data=None,
            duration_ms=round(elapsed, 2),
            concurrency_thread=f"asyncio-task-{task.chapter}",
            provenance_chunks=[],
            error=str(exc),
        )
