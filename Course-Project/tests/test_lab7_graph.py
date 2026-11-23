"""Unit and integration tests for Lab 7: Agentic Node Graph."""

import pytest
from concurrent.futures import ThreadPoolExecutor
from app.labs.lab7.graph import agentic_graph, AgenticNodeGraph
from app.labs.lab7.agent import NodeGraphAgent
from app.models.lab7_models import NodeExecutionStatus


def test_graph_topology_integrity():
    """Verify that all 10 specialist nodes and directed/conditional edges are declared."""
    engine = AgenticNodeGraph()
    topo = engine.get_topology()
    node_ids = [n.id for n in topo.nodes]
    assert len(node_ids) == 10
    assert "coordinator" in node_ids
    assert "planning" in node_ids
    assert "notes_repo" in node_ids
    assert "assignment_dist" in node_ids
    assert "submission_col" in node_ids
    assert "grading_org" in node_ids
    assert "milestones" in node_ids
    assert "validation" in node_ids
    assert "faculty_approval" in node_ids
    assert "publish" in node_ids

    # Verify retry and conditional edges exist
    edge_types = {e.edge_type for e in topo.edges}
    assert "directed" in edge_types
    assert "conditional" in edge_types
    assert "retry" in edge_types


def test_standard_graph_execution_flow():
    """Verify standard execution passes through nodes and pauses at faculty approval gate."""
    engine = AgenticNodeGraph()
    state = engine.initialize_graph(
        user_request="Organize 26ECAC401 course workspace",
        course_id="26ECAC401",
        target_weeks=12,
    )
    final_state = engine.run_until_paused_or_complete(state.run_id)

    # Must be paused at approval gate
    assert final_state.status == "WAITING_APPROVAL"
    assert final_state.current_node == "faculty_approval"
    assert final_state.validation_passed is True
    assert len(final_state.planning_schedule) == 12
    assert len(final_state.assignments_distribution) >= 4
    assert len(final_state.execution_history) >= 8

    # Verify state passed between specialist nodes
    assert final_state.course_id == "26ECAC401"
    assert final_state.course_name == "Agentic AI"


def test_graph_step_returns_isolated_snapshot_and_advances_once():
    engine = AgenticNodeGraph()
    initial = engine.initialize_graph(
        user_request="Step through the graph",
        owner_user_id="faculty-1",
    )

    snapshot = engine.get_state(initial.run_id)
    snapshot.user_request = "mutated external copy"
    assert engine.get_state(initial.run_id).user_request == "Step through the graph"

    stepped = engine.step_node(initial.run_id)
    assert stepped.current_node == "planning"
    assert stepped.node_states["coordinator"] == "COMPLETED"
    assert len(stepped.execution_history) == 1
    assert stepped.owner_user_id == "faculty-1"


def test_concurrent_graph_steps_are_serialized():
    engine = AgenticNodeGraph()
    state = engine.initialize_graph(user_request="Concurrent step test")

    with ThreadPoolExecutor(max_workers=5) as executor:
        list(executor.map(lambda _: engine.step_node(state.run_id), range(5)))

    final_state = engine.get_state(state.run_id)
    assert final_state.current_node == "grading_org"
    assert len(final_state.execution_history) == 5
    assert [trace.node_id for trace in final_state.execution_history] == [
        "coordinator",
        "planning",
        "notes_repo",
        "assignment_dist",
        "submission_col",
    ]


def test_bounded_retry_and_self_healing():
    """Verify that a validation failure triggers a bounded retry edge back to grading_org and heals."""
    engine = AgenticNodeGraph()
    # Initialize with simulate_validation_failure=True
    state = engine.initialize_graph(
        user_request="Test self-healing retry edge",
        course_id="26ECAC401",
        simulate_validation_failure=True,
    )
    final_state = engine.run_until_paused_or_complete(state.run_id)

    # Should have retried and healed to 100% on attempt 2
    assert final_state.retry_counts.get("grading_org", 0) == 2
    assert final_state.validation_passed is True
    assert final_state.status == "WAITING_APPROVAL"

    # Check history contains a RETRYING trace record
    statuses = [t.status for t in final_state.execution_history]
    assert NodeExecutionStatus.RETRYING in statuses


def test_bounded_retry_halts_at_max_attempts():
    """Verify graph halts safely with RETRY_EXHAUSTED when defects cannot be resolved."""
    engine = AgenticNodeGraph()
    state = engine.initialize_graph(user_request="Unhealable defect test", course_id="26ECAC401")

    # Manually configure state to simulate exhausted retries
    state.current_node = "validation"
    state.retry_counts["grading_org"] = 3
    state.max_retries = 3
    state.grading_breakdown = [{"category": "Invalid", "weight": 150.0}]  # Broken weight

    final_state = engine.run_until_paused_or_complete(state.run_id)
    assert final_state.status == "RETRY_EXHAUSTED"
    assert final_state.validation_passed is False


def test_faculty_approval_gate_and_publication():
    """Verify that approval gate sign-off transitions graph to COMPLETED and publishes workspace."""
    engine = AgenticNodeGraph()
    state = engine.initialize_graph(user_request="Faculty approval demonstration", course_id="26ECAC401")
    engine.run_until_paused_or_complete(state.run_id)

    # Submit approval
    post_approval = engine.submit_approval(
        run_id=state.run_id,
        approved=True,
        comments="Syllabus and assessment distributions verified by course faculty.",
        decision_by="prof_faculty_evaluator",
    )
    assert post_approval.status == "COMPLETED"
    assert post_approval.published_workspace is not None
    assert post_approval.published_workspace["faculty_approved"] is True
    assert post_approval.published_workspace["total_grade_weight"] == 100.0


def test_run_until_does_not_resume_rejected_or_completed_runs():
    """Re-entering the runner must preserve both rejected and completed terminal states."""
    engine = AgenticNodeGraph()

    rejected = engine.initialize_graph(user_request="Rejected graph run")
    engine.run_until_paused_or_complete(rejected.run_id)
    waiting_history_size = len(rejected.execution_history)
    engine.run_until_paused_or_complete(rejected.run_id)
    assert rejected.status == "WAITING_APPROVAL"
    assert len(rejected.execution_history) == waiting_history_size

    engine.submit_approval(
        run_id=rejected.run_id,
        approved=False,
        comments="Changes are required.",
    )
    rejected_history_size = len(rejected.execution_history)
    rejected_state = engine.run_until_paused_or_complete(rejected.run_id)

    assert rejected_state.status == "REJECTED"
    assert rejected_state.node_states["faculty_approval"] == "REJECTED"
    assert len(rejected_state.execution_history) == rejected_history_size
    with pytest.raises(ValueError, match="not awaiting faculty approval"):
        engine.submit_approval(rejected.run_id, approved=True)

    completed = engine.initialize_graph(user_request="Approved graph run")
    engine.run_until_paused_or_complete(completed.run_id)
    engine.submit_approval(
        run_id=completed.run_id,
        approved=True,
        comments="Approved.",
    )
    completed_history_size = len(completed.execution_history)
    published_workspace = completed.published_workspace.copy()
    completed_state = engine.run_until_paused_or_complete(completed.run_id)

    assert completed_state.status == "COMPLETED"
    assert completed_state.published_workspace == published_workspace
    assert len(completed_state.execution_history) == completed_history_size


@pytest.mark.asyncio
async def test_node_graph_agent_full_lifecycle():
    """Verify NodeGraphAgent dispatches graph run and processes approval."""
    agent = NodeGraphAgent()

    # 1. Run graph
    res = await agent.execute("run_graph", {
        "user_request": "Organize 26ECAC401 curriculum",
        "course_id": "26ECAC401",
        "target_weeks": 12,
    })
    assert res["status"] == "WAITING_APPROVAL"
    run_id = res["run_id"]

    # 2. Submit approval
    app_res = await agent.execute("approve", {
        "run_id": run_id,
        "approved": True,
        "comments": "Approved for faculty presentation",
    })
    assert app_res["status"] == "COMPLETED"
    assert app_res["state"]["published_workspace"]["faculty_approved"] is True
