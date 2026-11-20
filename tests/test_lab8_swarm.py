"""Unit and integration tests for Lab 8: Parallel Swarm."""

import asyncio

import pytest
from app.labs.lab8 import swarm as swarm_module
from app.labs.lab8.swarm import swarm_coordinator, ParallelSwarmCoordinator, LOCKED_UNITS
from app.labs.lab8.agent import ParallelSwarmAgent
from app.models.lab8_models import WorkerExecutionRecord, WorkerStatus


@pytest.mark.asyncio
async def test_full_parallel_swarm_execution():
    """Verify 4 parallel workers execute concurrently and produce merged workspace."""
    coord = ParallelSwarmCoordinator()
    res = await coord.dispatch_swarm(course_id="26ECAC401", target_chapters=[1, 2, 3, 4])

    assert res.total_workers == 4
    assert res.successful_workers == 4
    assert res.failed_workers == 0
    assert res.status == "MERGED"
    assert res.validation_passed is True

    # Telemetry and speedup verification
    assert res.parallel_duration_ms > 0
    assert res.sequential_estimated_ms > 0
    assert len(res.workers) == 4
    for w in res.workers:
        assert w.status == WorkerStatus.SUCCESS
        assert w.output_data is not None
        assert w.output_data["unit_chapter"] in [1, 2, 3, 4]

    # Merged workspace verification
    merged = res.merged_workspace
    assert merged is not None
    assert merged["course_id"] == "26ECAC401"
    assert merged["units_compiled_count"] == 4
    assert len(merged["units"]) == 4


@pytest.mark.asyncio
async def test_partial_worker_failure_resilience():
    """Verify swarm isolates worker failure and performs resilient partial merge."""
    coord = ParallelSwarmCoordinator()
    # Simulate worker 3 failing
    res = await coord.dispatch_swarm(
        course_id="26ECAC401",
        target_chapters=[1, 2, 3, 4],
        simulate_worker_failure=3,
    )

    assert res.total_workers == 4
    assert res.successful_workers == 3
    assert res.failed_workers == 1
    assert res.status == "PARTIAL_SUCCESS"
    assert res.validation_passed is False

    # Check worker 3 failed specifically
    w3 = next(w for w in res.workers if w.unit_chapter == 3)
    assert w3.status == WorkerStatus.FAILED
    assert "SIMULATED_WORKER_FAILURE" in w3.error

    # Other workers succeeded
    for w in res.workers:
        if w.unit_chapter != 3:
            assert w.status == WorkerStatus.SUCCESS

    # Merged workspace contains the 3 successful units
    assert res.merged_workspace["units_compiled_count"] == 3
    chapters_in_merged = [u["chapter"] for u in res.merged_workspace["units"]]
    assert 3 not in chapters_in_merged
    assert 1 in chapters_in_merged
    assert 2 in chapters_in_merged
    assert 4 in chapters_in_merged

    # Merge rationale explains partial failure
    rationale_text = " ".join(res.merge_rationale)
    assert "PARTIAL FAILURE" in rationale_text
    assert "Chapter 3" in rationale_text


@pytest.mark.asyncio
async def test_targeted_two_unit_swarm():
    """Verify targeted subset dispatch (Units 1 & 2)."""
    coord = ParallelSwarmCoordinator()
    res = await coord.dispatch_swarm(course_id="26ECAC401", target_chapters=[1, 2])
    assert res.total_workers == 2
    assert res.successful_workers == 2
    assert res.merged_workspace["units_compiled_count"] == 2


def test_swarm_request_rejects_empty_duplicate_and_unknown_chapters():
    from app.models.lab8_models import StartSwarmRequest

    for chapters in ([], [1, 1], [5]):
        with pytest.raises(ValueError):
            StartSwarmRequest(target_chapters=chapters)


@pytest.mark.asyncio
async def test_worker_timeout_is_reported_and_does_not_hang(monkeypatch):
    async def slow_worker(task, simulate_failure=False):
        await asyncio.sleep(0.1)

    monkeypatch.setattr(swarm_module, "execute_unit_worker", slow_worker)
    coordinator = ParallelSwarmCoordinator(worker_timeout_seconds=0.01)
    result = await coordinator.dispatch_swarm(target_chapters=[1, 2])

    assert result.status == "FAILED"
    assert result.failed_workers == 2
    assert all(worker.status == WorkerStatus.TIMEOUT for worker in result.workers)
    assert all("execution limit" in worker.error for worker in result.workers)


@pytest.mark.asyncio
async def test_fan_in_rejects_worker_output_not_matching_locked_plan(monkeypatch):
    task = LOCKED_UNITS[0]

    async def wrong_plan_worker(task, simulate_failure=False):
        return WorkerExecutionRecord(
            worker_id="worker-ch1",
            unit_chapter=task.chapter,
            role="Unit 1 Specialist",
            status=WorkerStatus.SUCCESS,
            output_data={
                "unit_chapter": task.chapter,
                "unit_title": task.title,
                "compiled_topics": task.topics_to_compile,
                "practical_deliverable": task.lab_spec,
                "locked_plan_hash": "wrong-hash",
            },
            provenance_chunks=[{"source_document": "chapter-1.txt", "excerpt": "fixture"}],
        )

    monkeypatch.setattr(swarm_module, "execute_unit_worker", wrong_plan_worker)
    result = await ParallelSwarmCoordinator().dispatch_swarm(target_chapters=[1])

    assert result.status == "FAILED"
    assert result.validation_passed is False
    assert result.failed_workers == 1
    assert result.merged_workspace["units_compiled_count"] == 0
    assert result.workers[0].error == "Worker output failed locked-plan, coverage, or provenance validation."


@pytest.mark.asyncio
async def test_swarm_result_reads_and_returns_are_isolated():
    coordinator = ParallelSwarmCoordinator()
    result = await coordinator.dispatch_swarm(target_chapters=[1])
    result.workers[0].status = WorkerStatus.FAILED
    result.workers[0].provenance_chunks.clear()

    stored = coordinator.get_result(result.swarm_run_id)
    assert stored.workers[0].status == WorkerStatus.SUCCESS
    assert stored.workers[0].provenance_chunks
    stored.workers[0].status = WorkerStatus.FAILED
    assert coordinator.get_result(result.swarm_run_id).workers[0].status == WorkerStatus.SUCCESS


@pytest.mark.asyncio
async def test_parallel_swarm_agent_dispatch():
    """Verify ParallelSwarmAgent executes action dispatch_swarm."""
    agent = ParallelSwarmAgent()
    res = await agent.execute("dispatch_swarm", {
        "course_id": "26ECAC401",
        "target_chapters": [1, 2, 3, 4],
    })
    assert res["status"] == "MERGED"
    assert res["total_workers"] == 4
    assert res["successful_workers"] == 4
