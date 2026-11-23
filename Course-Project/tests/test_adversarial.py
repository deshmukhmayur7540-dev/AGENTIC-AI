"""Adversarial and boundary condition tests across all layers (Labs 1-8)."""

import pytest
from app.core.course_identity import normalize_course_id, resolve_course_identity
from app.labs.lab2.tools.calculators import CalculateGradeBreakdownTotalTool
from app.labs.lab2.tools.registry import tool_registry
from app.labs.lab3.registry import skill_registry
from app.labs.lab4.knowledge_store import long_term_store
from app.models.lab4_models import LongTermRetrievalQuery
from app.labs.lab5.governed_connector import governed_connector
from app.models.lab5_models import ConnectorOperation, ConnectorRequest, ConnectorRole
from app.labs.lab6.engine import ControlledRuntimeEngine
from app.models.lab6_models import RuntimeBudget
from app.labs.lab7.graph import AgenticNodeGraph


def test_adversarial_course_identity_standalone_ai():
    """Input 'AI' alone must never be resolved as a course ID."""
    assert normalize_course_id("AI") is None
    assert normalize_course_id("ai") is None
    assert normalize_course_id("Explain AI") is None


def test_adversarial_course_identity_gibberish():
    """Random gibberish returns None for course ID."""
    assert normalize_course_id("asdfgh12345!@#$") is None


def test_adversarial_unknown_course_cs101_rejection():
    """Foreign course 'CS101' is preserved so repository lookups reject it safely."""
    assert normalize_course_id("CS101") == "CS101"
    res = long_term_store.search(LongTermRetrievalQuery(query="syllabus", course_id="CS101"))
    assert res.match_count == 0
    assert "not indexed" in res.source


def test_adversarial_calculator_invalid_grade_weights():
    """Calculator tool strictly rejects weights that do not sum to 100%."""
    calc_tool = CalculateGradeBreakdownTotalTool()
    # Case 1: 40 + 30 + 20 + 20 = 110% (Over)
    record_over = calc_tool.execute({
        "weights": [40.0, 30.0, 20.0, 20.0]
    })
    assert record_over.status.value == "SUCCESS"
    assert record_over.output_data["is_valid"] is False
    assert record_over.output_data["total_percentage"] == 110.0

    # Case 2: 40 + 40 + 40 = 120%
    record_120 = calc_tool.execute({
        "weights": [40.0, 40.0, 40.0]
    })
    assert record_120.status.value == "SUCCESS"
    assert record_120.output_data["is_valid"] is False


def test_adversarial_knowledge_hallucination_prevention():
    """Queries for non-existent concepts (e.g. quantum gravity in medieval times) return 0 matches."""
    res = long_term_store.search(LongTermRetrievalQuery(
        query="Give me facts not in the notes about medieval quantum gravity",
        course_id="26ECAC401",
    ))
    assert res.match_count == 0


def test_adversarial_invalid_chapter_filter():
    """Querying a non-existent chapter (e.g. Chapter 99) is rejected at schema level or yields zero matches."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LongTermRetrievalQuery(
            query="Autonomous agent loops",
            course_id="26ECAC401",
            chapter=99,
        )


def test_adversarial_call_nonexistent_tool():
    """Calling an unknown tool through tool registry returns structured error."""
    res = tool_registry.execute_tool("hack_database_tool", {})
    assert res.status.value in ["EXECUTION_ERROR", "ERROR"]
    assert "not found" in res.error.lower()


def test_adversarial_call_nonexistent_skill():
    """Calling an unknown skill returns structured error."""
    record = skill_registry.execute_skill("unknown_magic_skill", {})
    assert record.status == "EXECUTION_ERROR"
    assert "not registered" in record.error


def test_adversarial_student_unauthorized_database_mutation():
    """STUDENT role attempting direct write through connector is blocked with ACCESS_DENIED."""
    req = ConnectorRequest(
        source_id="sqlite_source",
        operation=ConnectorOperation.WRITE,
        resource_path="assignments",
        parameters={"id": "student_hack", "title": "Free A Grade"},
        client_role=ConnectorRole.STUDENT,
    )
    res = governed_connector.dispatch(req)
    assert res.success is False
    assert "Access Denied" in res.error


def test_adversarial_runtime_budget_run_forever_protection():
    """Attempting unbounded execution loop is blocked by runtime budget."""
    engine = ControlledRuntimeEngine()
    budget = RuntimeBudget(max_steps=3)
    run = engine.create_run("Infinite loop attempt", budget=budget)

    for i in range(5):
        step_res = engine.execute_step(run.run_id, f"LoopStep{i}", "LoopWorker", lambda v: ({f"k{i}": i}, None))
        if i >= 3:
            assert step_res["status"] == "BUDGET_EXCEEDED"

    assert engine.get_run(run.run_id).state.value == "BUDGET_EXCEEDED"


def test_adversarial_graph_unapproved_publish_blocked():
    """Publish node in graph cannot execute without explicit faculty approval."""
    engine = AgenticNodeGraph()
    state = engine.initialize_graph(user_request="Publish without approval test", course_id="26ECAC401")
    engine.run_until_paused_or_complete(state.run_id)

    # State must be WAITING_APPROVAL, published_workspace must be None
    assert state.status == "WAITING_APPROVAL"
    assert state.published_workspace is None
