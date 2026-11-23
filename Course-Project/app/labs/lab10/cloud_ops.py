"""Cloud Operations & Resilient Infrastructure Diagnostics for Lab 10 (Bug 3 repair).

Provides honest, transparent automated infrastructure health monitoring, failure diagnosis,
and consequential human-in-the-loop remediation gates.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CloudOperationsAgent:
    """Agentic Cloud Infrastructure Management with Automated Health Diagnostics and Gated Remediation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cluster_state: dict[str, Any] = {
            "cluster_id": "courseagent-local-k8s-cluster",
            "environment": "sandboxed_academic_cloud_simulation",
            "components": {
                "api-gateway": {
                    "name": "API Gateway Service",
                    "replicas": 2,
                    "status": "HEALTHY",
                    "latency_ms": 14.2,
                    "error_rate": 0.001,
                    "last_restarted": "2026-11-15T18:00:00Z",
                },
                "worker-swarm": {
                    "name": "Orchestrator Worker Swarm",
                    "replicas": 4,
                    "status": "DEGRADED",
                    "cpu_percent": 88.5,
                    "memory_mb": 1420,
                    "deadlock_queue_size": 12,
                    "failing_nodes": ["worker-unit-3"],
                    "error_log": "WorkerUnit3 thread hung waiting for unbounded upstream socket response.",
                },
                "retrieval-cache": {
                    "name": "Knowledge BM25 Cache",
                    "replicas": 1,
                    "status": "HEALTHY",
                    "hit_rate": 0.89,
                    "memory_mb": 310,
                },
                "database-primary": {
                    "name": "Governed SQLite Primary Store",
                    "replicas": 1,
                    "status": "HEALTHY",
                    "active_connections": 4,
                    "pool_capacity": 20,
                },
            },
            "remediation_history": [],
        }
        self._pending_remediations: set[str] = set()
        self._active_remediation_id: str | None = None
        self._pre_remediation_worker_state: dict[str, Any] | None = None

    def get_cluster_status(self) -> dict[str, Any]:
        """Return full cluster component status and resource metrics."""
        with self._lock:
            return {
                "cluster": copy.deepcopy(self._cluster_state),
                "disclosure": (
                    "Lab 10 Honest Architecture Disclosure: Operates within a sandboxed academic cluster simulator. "
                    "Provides simulated health monitoring, failure diagnosis, and human-in-the-loop approval gates "
                    "without contacting or mutating an external cloud provider."
                ),
            }

    def diagnose_infrastructure(self, target_component: Optional[str] = None) -> dict[str, Any]:
        """Inspect cluster components, detect degraded services, and generate failure diagnosis."""
        with self._lock:
            components = self._cluster_state["components"]
            if target_component and target_component not in components:
                raise ValueError(f"Unknown simulated component '{target_component}'.")
            targets = (
                {target_component: components[target_component]}
                if target_component
                else components
            )
            degraded = []
            for cid, comp in targets.items():
                if comp.get("status") != "HEALTHY":
                    degraded.append({
                        "component_id": cid,
                        "component_name": comp["name"],
                        "status": comp["status"],
                        "symptoms": comp.get("error_log") or f"CPU/Memory threshold exceeded ({comp.get('cpu_percent', 0)}%)",
                        "root_cause": (
                            "Worker thread deadlock occurred during asynchronous swarm fan-out; "
                            "queue backlog increased to 12 items."
                            if cid == "worker-swarm"
                            else "Transient socket timeout."
                        ),
                        "suggested_action": "Restart hung worker pod 'worker-unit-3', flush dead letter queue, and scale replicas to 5.",
                        "risk_level": "MEDIUM",
                        "requires_approval": True,
                    })

            return {
                "diagnosis_id": f"diag-{uuid.uuid4().hex[:8]}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "overall_health": "DEGRADED" if degraded else "HEALTHY",
                "issues_detected": len(degraded),
                "diagnostics": degraded,
                "next_step": "Submit proposed remediation plan for faculty/ops approval.",
            }

    def propose_remediation(
        self,
        component_id: str = "worker-swarm",
        actor: str = "faculty_ops",
    ) -> dict[str, Any]:
        """Generate a structured, reviewable remediation proposal with explicit approval gating."""
        with self._lock:
            if self._active_remediation_id:
                raise ValueError("Rollback the active simulated remediation before proposing another.")
            if component_id != "worker-swarm" or self._cluster_state["components"][component_id]["status"] == "HEALTHY":
                raise ValueError("Only a degraded worker-swarm simulation can be remediated.")
            plan_id = f"rem-{uuid.uuid4().hex[:8]}"
            self._pending_remediations.add(plan_id)
            plan = {
                "remediation_id": plan_id,
                "component_id": component_id,
                "actions": [
                    "1. Gracefully terminate hung pod 'worker-unit-3'.",
                    "2. Purge and requeue 12 deadlocked task envelopes.",
                    "3. Scale worker swarm replicas from 4 to 5 for redundancy.",
                    "4. Capture post-remediation health telemetry and verify latency.",
                ],
                "risk_level": "MEDIUM",
                "requires_human_approval": True,
                "applied_automatically": False,
                "status": "AWAITING_APPROVAL",
            }
            self._record_event(plan_id, "PROPOSE_REMEDIATION", actor, "AWAITING_APPROVAL")
            return plan

    def apply_remediation(
        self,
        remediation_id: str,
        approved: bool,
        actor: str = "faculty_ops",
    ) -> dict[str, Any]:
        """Apply the remediation plan only upon explicit human approval."""
        with self._lock:
            if self._active_remediation_id:
                raise ValueError("Rollback the active simulated remediation before applying another.")
            if remediation_id not in self._pending_remediations:
                raise ValueError("The simulated remediation proposal is unknown or already decided.")
            self._pending_remediations.remove(remediation_id)
            if not approved:
                self._record_event(remediation_id, "REJECT_REMEDIATION", actor, "REJECTED")
                return {
                    "remediation_id": remediation_id,
                    "status": "REJECTED_BY_OPERATOR",
                    "message": f"Remediation plan rejected by operator '{actor}'. No infrastructure state was changed.",
                    "applied": False,
                }

            ws = self._cluster_state["components"]["worker-swarm"]
            self._pre_remediation_worker_state = copy.deepcopy(ws)
            self._active_remediation_id = remediation_id
            ws["status"] = "HEALTHY"
            ws["replicas"] = 5
            ws["cpu_percent"] = 28.4
            ws["deadlock_queue_size"] = 0
            ws["failing_nodes"] = []
            ws["error_log"] = None
            ws["last_healed"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

            self._record_event(remediation_id, "APPLY_REMEDIATION", actor, "HEALTHY")

            return {
                "remediation_id": remediation_id,
                "status": "REMEDIATION_APPLIED_SUCCESS",
                "applied": True,
                "applied_by": actor,
                "applied_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "component_status": "HEALTHY",
                "new_replicas": 5,
                "message": "Simulated worker restart and scale operation completed; no external provider was contacted.",
            }

    def rollback_remediation(self, remediation_id: str, actor: str = "faculty_ops") -> dict[str, Any]:
        """Safely restore previous infrastructure configuration and log event."""
        with self._lock:
            if remediation_id != self._active_remediation_id or self._pre_remediation_worker_state is None:
                raise ValueError("No matching active simulated remediation is available to roll back.")
            self._cluster_state["components"]["worker-swarm"] = copy.deepcopy(self._pre_remediation_worker_state)
            self._pre_remediation_worker_state = None
            self._active_remediation_id = None
            self._record_event(remediation_id, "ROLLBACK_REMEDIATION", actor, "ROLLED_BACK")
            return {
                "remediation_id": remediation_id,
                "status": "ROLLED_BACK",
                "restored_replicas": 4,
                "message": f"Rolled back the simulated cluster configuration to its previous baseline by {actor}.",
            }

    def _record_event(self, remediation_id: str, action: str, actor: str, outcome: str) -> None:
        self._cluster_state["remediation_history"].append({
            "remediation_id": remediation_id,
            "action": action,
            "actor": actor,
            "outcome": outcome,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        })


cloud_ops_agent = CloudOperationsAgent()
