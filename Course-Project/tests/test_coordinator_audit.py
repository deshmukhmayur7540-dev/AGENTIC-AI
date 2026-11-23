"""Regression tests for truthful coordinator audit records."""

import pytest

from app.core.coordinator import Coordinator, lab_registry
from app.core.state import AgentState


class FailingAgent:
    def __init__(self) -> None:
        self.state = AgentState(agent_id="failing-test-agent")

    def update_status(self, status, step_name=None):
        return None

    async def execute(self, action, payload):
        raise ValueError("Invalid test action")


@pytest.mark.asyncio
async def test_coordinator_records_failed_action_with_completion_telemetry(monkeypatch):
    agent = FailingAgent()
    monkeypatch.setattr(lab_registry, "get_agent", lambda lab_id: agent)
    coordinator = Coordinator()

    response = await coordinator.dispatch(
        lab_id="test-lab",
        action="fail",
        payload={},
        trace_id="trace-validation-failure",
    )

    assert response.success is False
    assert response.error.code == "VALIDATION_ERROR"
    audit = coordinator.get_audit_trail()
    assert len(audit) == 1
    event = audit[0]
    assert event["trace_id"] == "trace-validation-failure"
    assert event["status"] == "VALIDATION_ERROR"
    assert event["result_status"] == "VALIDATION_ERROR"
    assert event["duration_ms"] >= 0
    assert event["completed_at"]
    assert event["actor"] is None

    step = agent.state.execution_history[0]
    assert step.status == "VALIDATION_ERROR"
    assert step.completed_at is not None
    assert step.duration_ms is not None


@pytest.mark.asyncio
async def test_coordinator_does_not_log_missing_agent_as_executed(monkeypatch):
    monkeypatch.setattr(lab_registry, "get_agent", lambda lab_id: None)
    coordinator = Coordinator()

    response = await coordinator.dispatch(
        lab_id="missing-lab",
        action="not-run",
        payload={},
        trace_id="trace-missing-agent",
    )

    assert response.success is False
    assert response.error.code == "AGENT_NOT_FOUND"
    assert coordinator.get_audit_trail() == []
