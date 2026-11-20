"""Coordinator module: orchestrates requests between API layer, agents, and data layer."""

import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Any, Optional
from app.core.registry import lab_registry
from app.core.state import ExecutionStep, WorkflowStatus
from app.models.common import APIEnvelope, ErrorDetail
from app.services.audit_service import audit_service


class Coordinator:
    """Central coordinator implementing the layered architecture."""

    def __init__(self):
        self._audit_trail: list[dict[str, Any]] = []
        self._audit_lock = threading.Lock()

    def _record_audit(
        self,
        trace_id: str,
        lab_id: str,
        action: str,
        duration_ms: float,
        status: str,
        result_status: str,
    ) -> None:
        completed_at = datetime.now(timezone.utc).isoformat()
        with self._audit_lock:
            self._audit_trail.append({
                "trace_id": trace_id,
                "lab_id": lab_id,
                "action": action,
                "duration_ms": duration_ms,
                "status": status,
                "actor": None,
                "result_status": result_status,
                "completed_at": completed_at,
            })
        try:
            audit_service.log_event(
                event_type="AGENT_EXECUTION",
                actor="coordinator",
                actor_role="SYSTEM",
                resource=f"lab:{lab_id}",
                action=action,
                outcome=status,
                details={"duration_ms": round(duration_ms, 2), "result_status": result_status},
                trace_id=trace_id,
            )
        except Exception:
            pass

    async def dispatch(
        self,
        lab_id: str,
        action: str,
        payload: dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> APIEnvelope[Any]:
        """Dispatch an action to the designated lab agent with step timing and envelope wrapping."""
        trace_id = trace_id or str(uuid.uuid4())
        start_time = time.perf_counter()

        agent = lab_registry.get_agent(lab_id)
        if not agent:
            return APIEnvelope(
                success=False,
                data=None,
                error=ErrorDetail(
                    code="AGENT_NOT_FOUND",
                    message=f"No active agent registered for lab '{lab_id}'.",
                    target="lab_id",
                ),
                trace_id=trace_id,
            )

        # Log step
        step_id = str(uuid.uuid4())
        step = ExecutionStep(
            step_id=step_id,
            step_name=f"{lab_id}:{action}",
            status="RUNNING",
            input_summary=str(payload)[:200],
        )

        try:
            agent.update_status(WorkflowStatus.GENERATING_PLAN, step_name=action)
            result = await agent.execute(action, payload)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Check if agent result itself has error status
            is_error = False
            if isinstance(result, dict):
                res_status = str(result.get("status", "")).upper()
                if res_status in ("EXECUTION_ERROR", "VALIDATION_ERROR", "ERROR", "FAILED"):
                    is_error = True

            step_status = "EXECUTION_ERROR" if is_error else "SUCCESS"
            step.status = step_status
            step.completed_at = datetime.now(timezone.utc)
            step.duration_ms = elapsed_ms
            step.output_summary = str(result)[:200]
            
            agent.state.execution_history.append(step)
            agent.update_status(WorkflowStatus.ERROR if is_error else WorkflowStatus.COMPLETED)

            self._record_audit(
                trace_id,
                lab_id,
                action,
                elapsed_ms,
                step_status,
                res_status if isinstance(result, dict) and res_status else "SUCCESS",
            )

            return APIEnvelope(
                success=True,
                data=result,
                error=None,
                trace_id=trace_id,
            )

        except ValueError as val_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            step.status = "VALIDATION_ERROR"
            step.completed_at = datetime.now(timezone.utc)
            step.duration_ms = elapsed_ms
            step.error = str(val_err)
            agent.state.execution_history.append(step)
            agent.update_status(WorkflowStatus.ERROR)
            self._record_audit(
                trace_id,
                lab_id,
                action,
                elapsed_ms,
                "VALIDATION_ERROR",
                "VALIDATION_ERROR",
            )

            return APIEnvelope(
                success=False,
                data=None,
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(val_err),
                    details={"action": action, "lab_id": lab_id},
                ),
                trace_id=trace_id,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            step.status = "EXECUTION_ERROR"
            step.completed_at = datetime.now(timezone.utc)
            step.duration_ms = elapsed_ms
            step.error = str(exc)
            agent.state.execution_history.append(step)
            agent.update_status(WorkflowStatus.ERROR)
            self._record_audit(
                trace_id,
                lab_id,
                action,
                elapsed_ms,
                "EXECUTION_ERROR",
                "EXECUTION_ERROR",
            )

            return APIEnvelope(
                success=False,
                data=None,
                error=ErrorDetail(
                    code="INTERNAL_AGENT_ERROR",
                    message=f"Error during agent execution: {str(exc)}",
                    details={"action": action, "lab_id": lab_id},
                ),
                trace_id=trace_id,
            )

    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Retrieve system audit trail records."""
        with self._audit_lock:
            return list(self._audit_trail)


coordinator = Coordinator()
