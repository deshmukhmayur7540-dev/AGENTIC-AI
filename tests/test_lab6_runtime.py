"""Unit and integration tests for Lab 6: Controlled Agent Runtime."""

import json
import os
import subprocess
import sys
import time

import pytest
from app.labs.lab6.engine import ControlledRuntimeEngine, runtime_engine
from app.labs.lab6.agent import ControlledRuntimeAgent
from app.models.lab6_models import ExecutionState, RuntimeBudget
from config import settings


def test_budget_step_limit_enforced():
    """Verify runtime halts and transitions to BUDGET_EXCEEDED when max steps is reached."""
    engine = ControlledRuntimeEngine()
    budget = RuntimeBudget(max_steps=2)
    run = engine.create_run("Task with tight budget", budget=budget)

    # Step 1: within budget
    res1 = engine.execute_step(
        run.run_id, "Step 1", "Worker1", lambda v: ({"v1": 1}, None)
    )
    assert res1["status"] == "SUCCESS"
    assert engine.get_run(run.run_id).state == ExecutionState.RUNNING

    # Step 2: within budget
    res2 = engine.execute_step(
        run.run_id, "Step 2", "Worker2", lambda v: ({"v2": 2}, None)
    )
    assert res2["status"] == "SUCCESS"

    # Step 3: exceeds budget of 2
    res3 = engine.execute_step(
        run.run_id, "Step 3", "Worker3", lambda v: ({"v3": 3}, None)
    )
    assert res3["status"] == "BUDGET_EXCEEDED"
    updated_run = engine.get_run(run.run_id)
    assert updated_run.state == ExecutionState.BUDGET_EXCEEDED
    assert updated_run.steps_executed == 2


def test_tool_and_elapsed_time_budgets_are_enforced_before_action():
    """Tool-call and wall-clock budgets block work before an over-budget action runs."""
    engine = ControlledRuntimeEngine()
    tool_run = engine.create_run("Tool budget", budget=RuntimeBudget(max_tool_calls=1))
    first = engine.execute_step(
        tool_run.run_id,
        "Tool step one",
        "Worker",
        lambda variables: ({"completed": 1}, "tool"),
        expected_tool_call=True,
    )
    assert first["status"] == "SUCCESS"
    second = engine.execute_step(
        tool_run.run_id,
        "Tool step two",
        "Worker",
        lambda variables: pytest.fail("over-budget tool action must not run"),
        expected_tool_call=True,
    )
    assert second["status"] == "BUDGET_EXCEEDED"
    assert engine.get_run(tool_run.run_id).tool_calls_executed == 1

    time_run = engine.create_run(
        "Elapsed-time budget",
        budget=RuntimeBudget(max_duration_seconds=0.01),
    )
    time.sleep(0.02)
    elapsed = engine.execute_step(
        time_run.run_id,
        "Expired step",
        "Worker",
        lambda variables: pytest.fail("expired action must not run"),
    )
    assert elapsed["status"] == "BUDGET_EXCEEDED"


def test_approval_gate_suspension_and_decision():
    """Verify consequential actions trigger an approval gate and require faculty sign-off."""
    engine = ControlledRuntimeEngine()
    run = engine.create_run("Workspace with grade publishing")

    # Step 1: non-consequential
    res1 = engine.execute_step(
        run.run_id, "Step 1: Ingestion", "Worker", lambda v: ({"step": 1}, None)
    )
    assert res1["status"] == "SUCCESS"

    # Step 2: Consequential action
    res2 = engine.execute_step(
        run.run_id,
        "Step 2: Publish Official Grades",
        "PublishWorker",
        lambda v: ({"grades_published": True}, None),
        is_consequential=True,
        consequential_reason="Modifying published grading weights requires faculty approval.",
    )
    assert res2["status"] == "WAITING_APPROVAL"
    gate_id = res2["gate_id"]

    updated_run = engine.get_run(run.run_id)
    assert updated_run.state == ExecutionState.WAITING_APPROVAL
    assert updated_run.pending_approval is not None
    assert updated_run.pending_approval.status == "PENDING"

    # Faculty approves
    engine.submit_approval(run.run_id, gate_id, approved=True, decision_by="prof_smith")
    assert engine.get_run(run.run_id).state == ExecutionState.RUNNING

    # Now step can execute successfully
    res3 = engine.execute_step(
        run.run_id,
        "Step 2: Publish Official Grades",
        "PublishWorker",
        lambda v: ({"grades_published": True}, None),
        is_consequential=True,
    )
    assert res3["status"] == "SUCCESS"
    assert engine.get_run(run.run_id).variables.get("grades_published") is True


def test_checkpointing_crash_simulation_and_resume():
    """Verify crash simulation preserves checkpoints and resume restores state without loss."""
    engine = ControlledRuntimeEngine()
    run = engine.create_run("Mission critical course compile")

    # Execute step 1 and step 2
    engine.execute_step(run.run_id, "Step 1", "Worker", lambda v: ({"data1": "A"}, None))
    engine.execute_step(run.run_id, "Step 2", "Worker", lambda v: ({"data2": "B"}, None))

    assert len(engine.get_run(run.run_id).checkpoints) == 2
    assert engine.get_run(run.run_id).variables["data1"] == "A"
    assert engine.get_run(run.run_id).variables["data2"] == "B"

    # Simulate abrupt crash
    engine.simulate_crash(run.run_id)
    crashed_run = engine.get_run(run.run_id)
    assert crashed_run.state == ExecutionState.PAUSED
    assert "SIMULATED_PROCESS_CRASH" in crashed_run.error
    assert len(crashed_run.checkpoints) == 2  # Checkpoints preserved!

    # Resume from checkpoint
    resumed_run = engine.resume_run(run.run_id)
    assert resumed_run.state == ExecutionState.RUNNING
    assert resumed_run.error is None
    assert resumed_run.variables["data1"] == "A"
    assert resumed_run.variables["data2"] == "B"

    # Continue with step 3
    res_final = engine.execute_step(run.run_id, "Step 3", "Worker", lambda v: ({"data3": "C"}, None))
    assert res_final["status"] == "SUCCESS"
    assert engine.get_run(run.run_id).variables["data3"] == "C"


def test_runtime_audit_trail_completeness():
    """Verify runtime audit trail records step IDs, timing, and actor details."""
    engine = ControlledRuntimeEngine()
    run = engine.create_run("Auditable course compile")
    engine.execute_step(run.run_id, "AuditStep", "AuditActor", lambda v: ({"ok": True}, "test_tool"))

    run_record = engine.get_run(run.run_id)
    assert len(run_record.audit_entries) >= 1
    entry = run_record.audit_entries[0]
    assert entry.run_id == run.run_id
    assert entry.actor == "AuditActor"
    assert entry.action == "AuditStep"
    assert entry.tool_or_skill == "test_tool"
    assert entry.status == "SUCCESS"
    assert entry.duration_ms >= 0


def test_approval_clears_gate_and_allows_run_to_continue():
    """Approval should clear the active gate so the same run can proceed immediately afterward."""
    engine = ControlledRuntimeEngine()
    run = engine.create_run("Continue after approval")

    engine.execute_step(
        run.run_id,
        "Step 1: Consequential approval gate",
        "PublishWorker",
        lambda v: ({"published": True}, None),
        is_consequential=True,
        consequential_reason="Faculty review required",
    )

    gate = engine.get_run(run.run_id).pending_approval
    assert gate is not None

    engine.submit_approval(run.run_id, gate.gate_id, approved=True, decision_by="prof_smith")
    assert engine.get_run(run.run_id).pending_approval is None

    res = engine.execute_step(
        run.run_id,
        "Step 1: Consequential approval gate",
        "PublishWorker",
        lambda v: ({"published": True}, None),
        is_consequential=True,
        consequential_reason="Faculty review required",
    )

    assert res["status"] == "SUCCESS"


def test_rejected_approval_remains_terminal():
    """A rejected action cannot create a fresh approval gate when retried."""
    engine = ControlledRuntimeEngine()
    run = engine.create_run("Reject consequential action")
    gate_result = engine.execute_step(
        run.run_id,
        "Publish course",
        "PublishWorker",
        lambda v: ({"published": True}, None),
        is_consequential=True,
    )

    engine.submit_approval(run.run_id, gate_result["gate_id"], approved=False)
    retry = engine.execute_step(
        run.run_id,
        "Publish course",
        "PublishWorker",
        lambda v: ({"published": True}, None),
        is_consequential=True,
    )

    assert retry["status"] == "REJECTED"
    assert engine.get_run(run.run_id).state == ExecutionState.REJECTED


def test_persistent_run_checkpoint_and_audit_survive_process_restart():
    """A fresh Python process can reload a paused run, its checkpoint, and audit history."""
    engine = ControlledRuntimeEngine(persist=True)
    run = engine.create_run(
        "Persisted restart recovery",
        owner_user_id="test-faculty",
        owner_role="FACULTY",
    )
    result = engine.execute_step(
        run.run_id,
        "Persisted step",
        "RestartWorker",
        lambda variables: ({"durable_value": "checkpointed"}, "test_tool"),
        actor_user_id="test-faculty",
        actor_role="FACULTY",
    )
    assert result["status"] == "SUCCESS"
    engine.simulate_crash(run.run_id, actor_user_id="test-faculty", actor_role="FACULTY")

    script = (
        "import json; "
        "from app.labs.lab6.engine import ControlledRuntimeEngine; "
        f"run = ControlledRuntimeEngine(persist=True).get_run({run.run_id!r}); "
        "print(json.dumps(run.model_dump(mode='json')))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(settings.project_root),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    restored = json.loads(completed.stdout)
    assert restored["run_id"] == run.run_id
    assert restored["state"] == "PAUSED"
    assert restored["owner_user_id"] == "test-faculty"
    assert restored["checkpoints"][-1]["variables"]["durable_value"] == "checkpointed"
    assert restored["audit_entries"][-1]["action"] == "SIMULATE_CRASH"

    resumed = ControlledRuntimeEngine(persist=True).resume_run(
        run.run_id,
        actor_user_id="test-faculty",
        actor_role="FACULTY",
    )
    assert resumed.state == ExecutionState.RUNNING
    assert resumed.variables["durable_value"] == "checkpointed"


@pytest.mark.asyncio
async def test_controlled_runtime_agent_end_to_end():
    """Verify ControlledRuntimeAgent runs multi-step flow and pauses at approval gate."""
    agent = ControlledRuntimeAgent()

    # 1. Start run
    start_res = await agent.execute("start_run", {"task_description": "Build 26ECAC401 course", "course_id": "26ECAC401"})
    assert start_res["status"] == "INITIALIZED"
    run_id = start_res["run"]["run_id"]

    # 2. Advance Step 1 (Registrar Verification via Connector)
    step1 = await agent.execute("step", {"run_id": run_id})
    assert step1["status"] == "SUCCESS"

    # 3. Advance Step 2 (Lecture Notes Grounding via Connector)
    step2 = await agent.execute("step", {"run_id": run_id})
    assert step2["status"] == "SUCCESS"

    # 4. Advance Step 3 (Curriculum Synthesis via Skills)
    step3 = await agent.execute("step", {"run_id": run_id})
    assert step3["status"] == "SUCCESS"

    # 5. Advance Step 4 (Consequential Publish -> Pauses at Approval Gate)
    step4 = await agent.execute("step", {"run_id": run_id})
    assert step4["status"] == "WAITING_APPROVAL"
    gate_id = step4["gate_id"]

    # 6. Faculty approves
    approve_res = await agent.execute("approve", {"run_id": run_id, "gate_id": gate_id, "approved": True})
    assert approve_res["status"] == "SUCCESS"

    # 7. Final step executes and marks complete
    step4_post = await agent.execute("step", {"run_id": run_id})
    assert step4_post["status"] == "SUCCESS"
