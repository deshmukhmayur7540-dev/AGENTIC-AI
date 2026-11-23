"""ControlledRuntimeEngine: Manages budgets, approval gates, checkpoints, crash recovery, and audit logs."""

import logging
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from app.data.db import get_db_connection
from app.models.lab6_models import (
    ApprovalGate,
    ExecutionState,
    RunRecord,
    RuntimeAuditEntry,
    RuntimeBudget,
    RuntimeCheckpoint,
)

logger = logging.getLogger(__name__)


class ControlledRuntimeEngine:
    """Core runtime engine controlling agent execution with strict governance.
    
    Combines:
    - Budget limits (steps, tool calls, time)
    - Approval gates for consequential operations
    - Checkpoint serialization after each step
    - Crash simulation and stateful recovery
    - Observable audit logs
    """

    def __init__(self, *, persist: bool = False) -> None:
        self._lock = threading.RLock()
        self._persist = persist
        self._runs: dict[str, RunRecord] = {}

    def create_run(
        self,
        task_description: str,
        course_id: str = "26ECAC401",
        budget: Optional[RuntimeBudget] = None,
        initial_variables: Optional[dict[str, Any]] = None,
        owner_user_id: Optional[str] = None,
        owner_role: Optional[str] = None,
    ) -> RunRecord:
        """Initialize a new governed execution run."""
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        bg = budget or RuntimeBudget()
        run = RunRecord(
            run_id=run_id,
            course_id=course_id,
            owner_user_id=owner_user_id,
            owner_role=owner_role,
            state=ExecutionState.INITIALIZED,
            budget=bg,
            variables=initial_variables or {"course_id": course_id, "task": task_description},
        )
        with self._lock:
            self._runs[run_id] = run
            self._persist_run(run)
            logger.info("Initialized runtime run '%s' with budget: max_steps=%d", run_id, bg.max_steps)
        return run

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Retrieve run state by run_id."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None or not self._persist:
                return run
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT state_json FROM lab6_runtime_runs WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
            if row is None:
                return None
            run = RunRecord.model_validate_json(row["state_json"])
            self._runs[run_id] = run
            return run

    def execute_step(
        self,
        run_id: str,
        step_name: str,
        actor: str,
        action_fn: Callable[[dict[str, Any]], tuple[dict[str, Any], Optional[str]]],
        is_consequential: bool = False,
        consequential_reason: str = "Consequential change to academic workspace",
        actor_user_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        expected_tool_call: bool = False,
    ) -> dict[str, Any]:
        """Execute a discrete controlled step with budget checks, checkpointing, and approval gating."""
        step_id = f"step-{uuid.uuid4().hex[:6]}"
        start_time = time.perf_counter()

        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run '{run_id}' not found.")

            # 1. Budget constraint checks
            elapsed_run_seconds = max(
                0.0,
                (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(run.started_at)
                ).total_seconds(),
            )
            budget_error = None
            if run.steps_executed >= run.budget.max_steps:
                budget_error = f"Step limit reached ({run.steps_executed}/{run.budget.max_steps})."
            elif expected_tool_call and run.tool_calls_executed >= run.budget.max_tool_calls:
                budget_error = f"Tool-call limit reached ({run.tool_calls_executed}/{run.budget.max_tool_calls})."
            elif elapsed_run_seconds >= run.budget.max_duration_seconds:
                budget_error = (
                    f"Run duration limit reached ({elapsed_run_seconds:.3f}/"
                    f"{run.budget.max_duration_seconds:.3f} seconds)."
                )
            elif (
                is_consequential
                and run.consequential_actions_executed >= run.budget.max_consequential_actions
            ):
                budget_error = (
                    "Consequential-action limit reached "
                    f"({run.consequential_actions_executed}/{run.budget.max_consequential_actions})."
                )
            if budget_error:
                run.state = ExecutionState.BUDGET_EXCEEDED
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                err_msg = f"Budget exceeded: {budget_error}"
                self._record_audit(
                    run, step_id, actor, step_name, None, "Execute step", "Halted",
                    "BUDGET_EXCEEDED", elapsed_ms, err_msg, actor_user_id, actor_role,
                )
                self._persist_run(run)
                return {"status": "BUDGET_EXCEEDED", "error": err_msg}

            # 2. Consequential action approval gate
            if is_consequential:
                approved_for_step = run.variables.get("_last_approved_action") == step_name
                if approved_for_step:
                    run.variables.pop("_last_approved_action", None)
                    run.variables.pop("_last_approved_gate_id", None)

                if run.pending_approval and run.pending_approval.status == "REJECTED" and run.pending_approval.action_name == step_name:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    err_msg = f"Execution halted: Action '{step_name}' was REJECTED by faculty reviewer. A rejected approval gate cannot be bypassed by requesting the step again."
                    self._record_audit(
                        run, step_id, actor, step_name, None, "Execute step", "Halted",
                        "REJECTED", elapsed_ms, err_msg, actor_user_id, actor_role,
                    )
                    self._persist_run(run)
                    return {"status": "REJECTED", "error": err_msg}

                # Approval authorizes the next execution of this action exactly once.
                if not approved_for_step and not (run.pending_approval and run.pending_approval.status == "APPROVED" and run.pending_approval.action_name == step_name):
                    gate_id = f"gate-{uuid.uuid4().hex[:6]}"
                    gate = ApprovalGate(
                        gate_id=gate_id,
                        run_id=run_id,
                        step_id=step_id,
                        action_name=step_name,
                        action_payload={"variables": dict(run.variables)},
                        consequential_reason=consequential_reason,
                        status="PENDING",
                    )
                    run.pending_approval = gate
                    run.state = ExecutionState.WAITING_APPROVAL
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    self._record_audit(
                        run, step_id, actor, step_name, None,
                        f"Requires faculty gate: {consequential_reason}",
                        "Suspended awaiting human review",
                        "WAITING_APPROVAL", elapsed_ms, None, actor_user_id, actor_role,
                    )
                    # Checkpoint before pausing
                    self._save_checkpoint(run, step_id, step_name)
                    self._persist_run(run)
                    return {
                        "status": "WAITING_APPROVAL",
                        "gate_id": gate_id,
                        "action": step_name,
                        "reason": consequential_reason,
                        "message": "Execution suspended at approval gate. Faculty sign-off required.",
                    }

            # 3. Mark state as running
            run.state = ExecutionState.RUNNING
            run.current_step_id = step_id
            self._persist_run(run)

        # 4. Execute action function outside the critical lock
        try:
            output_dict, tool_or_skill = action_fn(run.variables)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            with self._lock:
                run.steps_executed += 1
                if tool_or_skill:
                    run.tool_calls_executed += 1
                if is_consequential:
                    run.consequential_actions_executed += 1
                # Update variables
                run.variables.update(output_dict)
                # Clear pending approval if this step consumed it
                if run.pending_approval and run.pending_approval.action_name == step_name:
                    run.pending_approval = None

                # Record audit
                self._record_audit(
                    run, step_id, actor, step_name, tool_or_skill,
                    f"Input vars: {list(run.variables.keys())}",
                    f"Output keys: {list(output_dict.keys())}",
                    "SUCCESS", elapsed_ms, None, actor_user_id, actor_role,
                )
                # Save checkpoint
                self._save_checkpoint(run, step_id, step_name)
                self._persist_run(run)

            return {
                "status": "SUCCESS",
                "step_id": step_id,
                "output": output_dict,
                "duration_ms": elapsed_ms,
            }

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            with self._lock:
                run.state = ExecutionState.FAILED
                run.error = str(exc)
                self._record_audit(
                    run, step_id, actor, step_name, None,
                    "Step execution failed", "Exception trapped", "ERROR", elapsed_ms,
                    str(exc), actor_user_id, actor_role,
                )
                self._persist_run(run)
            return {"status": "ERROR", "step_id": step_id, "error": str(exc)}

    def submit_approval(
        self,
        run_id: str,
        gate_id: str,
        approved: bool,
        decision_by: str = "course_faculty",
        decision_role: Optional[str] = None,
    ) -> RunRecord:
        """Submit faculty evaluation decision for a pending approval gate."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run '{run_id}' not found.")

            if not run.pending_approval:
                raise ValueError(f"No pending approval gate for run '{run_id}'.")

            if gate_id and run.pending_approval.gate_id != gate_id:
                raise ValueError(f"Approval gate ID mismatch: expected '{run.pending_approval.gate_id}', got '{gate_id}'.")

            gate = run.pending_approval
            gate.decision_by = decision_by
            gate.decision_timestamp = datetime.now(timezone.utc).isoformat()
            run.audit_entries.append(
                RuntimeAuditEntry(
                    run_id=run_id,
                    step_id=f"decision-{uuid.uuid4().hex[:8]}",
                    actor="FacultyApprovalGate",
                    actor_user_id=decision_by,
                    actor_role=decision_role,
                    action="APPROVAL_DECISION",
                    input_summary=f"gate_id={gate_id}",
                    output_summary="APPROVED" if approved else "REJECTED",
                    status="APPROVED" if approved else "REJECTED",
                )
            )

            if approved:
                gate.status = "APPROVED"
                run.pending_approval = None
                run.variables["_last_approved_gate_id"] = gate.gate_id
                run.variables["_last_approved_action"] = gate.action_name
                run.state = ExecutionState.RUNNING
                logger.info("Approval gate '%s' APPROVED by '%s' for run '%s'", gate.gate_id, decision_by, run_id)
            else:
                gate.status = "REJECTED"
                run.state = ExecutionState.REJECTED
                logger.warning("Approval gate '%s' REJECTED by '%s' for run '%s'", gate.gate_id, decision_by, run_id)

            self._persist_run(run)
            return run

    def simulate_crash(
        self,
        run_id: str,
        actor_user_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> RunRecord:
        """Simulate an abrupt execution failure / process crash.
        
        The run state becomes PAUSED/FAILED, but persisted checkpoints remain intact.
        """
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run '{run_id}' not found.")
            run.state = ExecutionState.PAUSED
            run.error = "SIMULATED_PROCESS_CRASH: Sudden execution termination"
            run.audit_entries.append(
                RuntimeAuditEntry(
                    run_id=run_id,
                    step_id=f"crash-{uuid.uuid4().hex[:8]}",
                    actor="RuntimeRecoveryEngine",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    action="SIMULATE_CRASH",
                    input_summary="Operator requested a local crash-recovery exercise",
                    output_summary="Run paused; prior checkpoints retained",
                    status="PAUSED",
                )
            )
            self._persist_run(run)
            logger.warning("Simulated process crash triggered on run '%s'", run_id)
            return run

    def resume_run(
        self,
        run_id: str,
        actor_user_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> RunRecord:
        """Resume a crashed or paused run from its latest persisted checkpoint."""
        with self._lock:
            run = self.get_run(run_id)

            if not run:
                raise ValueError(f"Run '{run_id}' not found.")

            if not run.checkpoints:
                raise ValueError(f"Run '{run_id}' has no saved checkpoints to resume from.")
            if run.state not in {ExecutionState.PAUSED, ExecutionState.FAILED}:
                raise ValueError(f"Run '{run_id}' is not paused or failed and cannot be resumed.")

            latest_checkpoint = run.checkpoints[-1]
            # Restore state and variables from snapshot
            run.variables = dict(latest_checkpoint.variables)
            run.state = ExecutionState.RUNNING
            run.error = None

            # Add resume audit record
            entry = RuntimeAuditEntry(
                run_id=run_id,
                step_id=f"resume-{uuid.uuid4().hex[:6]}",
                actor="RuntimeRecoveryEngine",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                action="RESUME_FROM_CHECKPOINT",
                input_summary=f"Restored from checkpoint {latest_checkpoint.checkpoint_id} (step {latest_checkpoint.step_index})",
                output_summary=f"Variables restored: {list(run.variables.keys())}",
                status="SUCCESS",
                duration_ms=0.0,
            )
            run.audit_entries.append(entry)
            self._persist_run(run)
            logger.info("Resumed run '%s' from checkpoint '%s'", run_id, latest_checkpoint.checkpoint_id)
            return run

    def complete_run(self, run_id: str, result_data: dict[str, Any]) -> RunRecord:
        """Mark a run as successfully completed."""
        with self._lock:
            run = self.get_run(run_id)
            if not run:
                raise ValueError(f"Run '{run_id}' not found.")
            if run.pending_approval is not None or run.state != ExecutionState.RUNNING:
                raise ValueError("A run must be active and have no pending approval before completion.")
            run.state = ExecutionState.COMPLETED
            run.result = result_data
            run.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_run(run)
            return run

    def _save_checkpoint(self, run: RunRecord, step_id: str, step_name: str) -> None:
        """Serialize and record a state checkpoint."""
        cp_id = f"chk-{uuid.uuid4().hex[:12]}"
        cp = RuntimeCheckpoint(
            checkpoint_id=cp_id,
            run_id=run.run_id,
            step_index=run.steps_executed,
            step_name=step_name,
            state_snapshot={"state": run.state.value, "steps": run.steps_executed},
            variables=dict(run.variables),
        )
        run.checkpoints.append(cp)

    def _persist_run(self, run: RunRecord) -> None:
        """Persist a run snapshot and append-only checkpoint/audit rows when enabled."""
        if not self._persist:
            return
        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO lab6_runtime_runs (
                    run_id, course_id, owner_user_id, owner_role, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    course_id = excluded.course_id,
                    owner_user_id = excluded.owner_user_id,
                    owner_role = excluded.owner_role,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    run.run_id,
                    run.course_id,
                    run.owner_user_id or "",
                    run.owner_role or "",
                    json.dumps(run.model_dump(mode="json"), ensure_ascii=False),
                    run.started_at,
                    now,
                ),
            )
            conn.executemany(
                """
                INSERT OR IGNORE INTO lab6_runtime_checkpoints (
                    checkpoint_id, run_id, step_index, step_name, checkpoint_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        checkpoint.checkpoint_id,
                        run.run_id,
                        checkpoint.step_index,
                        checkpoint.step_name,
                        json.dumps(checkpoint.model_dump(mode="json"), ensure_ascii=False),
                        checkpoint.timestamp,
                    )
                    for checkpoint in run.checkpoints
                ],
            )
            conn.executemany(
                """
                INSERT OR IGNORE INTO lab6_runtime_audit_events (
                    run_id, step_id, actor_user_id, actor_role, actor_agent, action,
                    input_summary, output_summary, status, duration_ms, error, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run.run_id,
                        entry.step_id,
                        entry.actor_user_id,
                        entry.actor_role,
                        entry.actor,
                        entry.action,
                        entry.input_summary,
                        entry.output_summary,
                        entry.status,
                        entry.duration_ms,
                        entry.error,
                        entry.timestamp,
                    )
                    for entry in run.audit_entries
                ],
            )

    def _record_audit(
        self,
        run: RunRecord,
        step_id: str,
        actor: str,
        action: str,
        tool_or_skill: Optional[str],
        in_summary: str,
        out_summary: str,
        status: str,
        duration_ms: float,
        error: Optional[str],
        actor_user_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> None:
        """Append an observable audit entry without private CoT."""
        entry = RuntimeAuditEntry(
            run_id=run.run_id,
            step_id=step_id,
            actor=actor,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            tool_or_skill=tool_or_skill,
            input_summary=in_summary[:200],
            output_summary=out_summary[:200],
            status=status,
            duration_ms=round(duration_ms, 2),
            error=error,
        )
        run.audit_entries.append(entry)


# Global singleton instance
runtime_engine = ControlledRuntimeEngine(persist=True)
