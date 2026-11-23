"""Unit and integration tests for Lab 2 ToolUsingAgent, Planning, and Auditable Traces."""

import copy
import pytest
from app.data.course_fixtures import CANONICAL_CONFIGS, CANONICAL_RUBRICS, CANONICAL_SYLLABI
from app.data.repository import CourseRepository, course_repo
from app.labs.lab2.agent import ToolUsingAgent
from app.labs.lab2.planner import ActionPlanner, ToolAction
from app.labs.lab2.tools.registry import ToolRegistry, tool_registry
from app.models.lab2_models import AuditableExecutionTrace, ToolExecutionStatus


# =========================================================================
# 1. Agent Initialization
# =========================================================================
def test_agent_initialization():
    agent = ToolUsingAgent()
    assert agent.agent_id == "lab2"
    assert "Tool-Using Agent" in agent.name
    assert agent.max_tool_calls == 10
    assert agent.registry is not None
    assert agent.planner is not None


# =========================================================================
# 2. Registry Integration
# =========================================================================
def test_agent_registry_integration():
    agent = ToolUsingAgent()
    tools = agent.registry.list_tools()
    assert len(tools) >= 9
    tool_names = [t.name for t in tools]
    assert "read_course_syllabus" in tool_names
    assert "calculate_grade_breakdown_total" in tool_names
    assert "get_rubric_breakdown" in tool_names


# =========================================================================
# 3. Tool Selection / Entity Extraction
# =========================================================================
def test_tool_selection_and_entity_extraction():
    planner = ActionPlanner()
    entities = planner.extract_entities("Audit 26ECAC401 syllabus and course modules")
    assert entities.get("course_id") == "26ECAC401"

    action = planner.plan_next_action(
        "Audit 26ECAC401 syllabus",
        context={},
        verified_facts={},
        steps=[],
    )
    assert isinstance(action, ToolAction)
    assert action.tool_name == "read_course_syllabus"
    assert action.parameters == {"course_id": "26ECAC401"}


# =========================================================================
# 4. Single-Tool Query: Course Notes Search
# =========================================================================
def test_single_tool_query_notes():
    agent = ToolUsingAgent()
    trace = agent.run("Search 26ECAC401 course notes for ReAct")

    assert isinstance(trace, AuditableExecutionTrace)
    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.tool_call is not None
    assert step.tool_call.tool_name == "search_course_notes"
    assert step.tool_call.status == ToolExecutionStatus.SUCCESS
    assert "ReAct" in trace.final_conclusion
    assert trace.verified_facts["notes_match_count"] >= 1


# =========================================================================
# 5. Single-Tool Query: Syllabus Verification
# =========================================================================
def test_single_tool_query_syllabus():
    agent = ToolUsingAgent()
    trace = agent.run("Audit 26ECAC401 syllabus and course modules")

    assert isinstance(trace, AuditableExecutionTrace)
    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.tool_call.tool_name == "read_course_syllabus"
    assert step.tool_call.status == ToolExecutionStatus.SUCCESS
    assert "Agentic AI" in trace.final_conclusion
    assert "Foundations of Agentic AI" in trace.final_conclusion


# =========================================================================
# 6. Multi-Tool Query: Workload & Staffing
# =========================================================================
def test_multi_tool_query_workload(monkeypatch):
    mutated_configs = copy.deepcopy(CANONICAL_CONFIGS)
    mutated_configs["26ECAC401"]["students_per_ta"] = 30
    mutated_configs["26ECAC401"]["hours_per_ta_per_week"] = 20.0
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_CONFIGS", mutated_configs)

    agent = ToolUsingAgent()
    trace = agent.run("Check whether TA staffing is sufficient for 120 students and 4 assignments, assuming 15 minutes of grading per submission in 26ECAC401.")

    assert len(trace.steps) == 2
    step_tools = [s.tool_call.tool_name for s in trace.steps]
    assert step_tools == ["get_ta_policy", "compute_workload_hours"]
    assert trace.verified_facts["required_ta_count"] == 4
    assert trace.verified_facts["total_grading_hours"] == 120.0
    assert "sufficient" in trace.final_conclusion.lower()


# =========================================================================
# 7. Actual Data Passed Between Tools in Grading Audit
# =========================================================================
def test_actual_data_passed_between_tools_in_grading_audit(monkeypatch):
    mutated_syllabi = copy.deepcopy(CANONICAL_SYLLABI)
    mutated_syllabi["26ECAC401"]["grading_weights"] = [
        {"category": "Lab Assignments", "weight_percentage": 40.0, "description": "Hands-on labs"},
        {"category": "Midterm Exam", "weight_percentage": 25.0, "description": "Theory exam"},
        {"category": "Final Project", "weight_percentage": 35.0, "description": "Multi-agent capstone"},
    ]
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_SYLLABI", mutated_syllabi)

    agent = ToolUsingAgent()
    trace = agent.run("Audit 26ECAC401 grading breakdown: do assignments, midterm, and project sum to 100%?")

    assert len(trace.steps) == 2
    step1 = trace.steps[0]
    step2 = trace.steps[1]

    assert step1.tool_call.tool_name == "read_course_syllabus"
    assert step2.tool_call.tool_name == "calculate_grade_breakdown_total"

    # Verify that weights passed to step 2 match step 1's actual output
    step1_weights = [gw["weight_percentage"] for gw in step1.tool_call.output_data["grading_weights"]]
    step2_input_weights = step2.tool_call.validated_input["weights"]
    assert step2_input_weights == step1_weights


# =========================================================================
# 8. Grade Audit Scenario: Sum Validation
# =========================================================================
def test_grade_audit_scenario(monkeypatch):
    mutated_syllabi = copy.deepcopy(CANONICAL_SYLLABI)
    mutated_syllabi["26ECAC401"]["grading_weights"] = [
        {"category": "Lab Assignments", "weight_percentage": 40.0, "description": "Hands-on labs"},
        {"category": "Midterm Exam", "weight_percentage": 30.0, "description": "Theory exam"},
        {"category": "Capstone Project", "weight_percentage": 30.0, "description": "Multi-agent project"},
    ]
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_SYLLABI", mutated_syllabi)

    agent = ToolUsingAgent()
    trace = agent.run("Audit 26ECAC401 grading breakdown: do assignments, midterm, and project sum to 100%?")

    assert trace.status == ToolExecutionStatus.SUCCESS
    assert trace.verified_facts["calculated_total_percentage"] == 100.0
    assert trace.verified_facts["is_valid_grade_breakdown"] is True
    assert "100.0%" in trace.final_conclusion
    assert "valid" in trace.final_conclusion.lower()


# =========================================================================
# 9. Rubric Query Scenario
# =========================================================================
def test_rubric_query_scenario(monkeypatch):
    mutated_rubrics = copy.deepcopy(CANONICAL_RUBRICS)
    mutated_rubrics["26ECAC401"] = {
        "lab1": {
            "course_id": "26ECAC401",
            "assignment_id": "lab1",
            "rubric_criteria": [
                {"criterion_name": "ReAct Reasoning Loop", "points": 40.0, "description": "Proper Thought-Action-Observation cycle"},
                {"criterion_name": "Code Quality & PEP 8", "points": 25.0, "description": "Clean, typed Python code adhering to PEP 8"},
                {"criterion_name": "Tool Schemas", "points": 35.0, "description": "Pydantic typed validation"},
            ],
            "total_points": 100.0,
            "evidence": "Lab 1 Grading Specification",
        }
    }
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_RUBRICS", mutated_rubrics)

    agent = ToolUsingAgent()
    trace = agent.run("Show me what the rubric says about code quality for lab1 in 26ECAC401.")

    assert trace.verified_facts["course_id"] == "26ECAC401"
    assert trace.verified_facts["assignment_id"] == "lab1"
    assert "PEP 8" in trace.final_conclusion or "Code Quality" in trace.final_conclusion


# =========================================================================
# 10. TA Policy Query Scenario
# =========================================================================
def test_ta_policy_query_scenario(monkeypatch):
    mutated_configs = copy.deepcopy(CANONICAL_CONFIGS)
    mutated_configs["26ECAC401"]["students_per_ta"] = 30
    mutated_configs["26ECAC401"]["hours_per_ta_per_week"] = 20.0
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_CONFIGS", mutated_configs)

    agent = ToolUsingAgent()
    trace = agent.run("How many TA hours are required for 120 students in 26ECAC401?")

    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.tool_name == "get_ta_policy"
    assert trace.verified_facts["required_ta_count"] == 4
    assert trace.verified_facts["required_hours_per_week"] == 80.0
    assert "80.0 TA hours" in trace.final_conclusion


# =========================================================================
# 11. Workload Query Scenario
# =========================================================================
def test_workload_query_scenario(monkeypatch):
    mutated_configs = copy.deepcopy(CANONICAL_CONFIGS)
    mutated_configs["26ECAC401"]["students_per_ta"] = 30
    mutated_configs["26ECAC401"]["hours_per_ta_per_week"] = 20.0
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_CONFIGS", mutated_configs)

    agent = ToolUsingAgent()
    trace = agent.run("Check whether the TA staffing is sufficient for 120 students and 4 assignments, assuming 15 minutes of grading per submission in 26ECAC401.")

    assert len(trace.steps) == 2
    assert trace.verified_facts["total_grading_hours"] == 120.0
    assert trace.verified_facts["hours_per_assignment"] == 30.0
    assert "30.0 hours per batch" in trace.final_conclusion


# =========================================================================
# 12. Unknown Course Handling (Anti-Hallucination)
# =========================================================================
def test_unknown_course_handling():
    agent = ToolUsingAgent()
    trace = agent.run("Audit UNKNOWN999 grading breakdown: do the assignments and project sum to 100%?")

    # Top-level status must indicate failure/error, not SUCCESS
    assert trace.status != ToolExecutionStatus.SUCCESS
    assert trace.status == ToolExecutionStatus.EXECUTION_ERROR

    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.tool_call.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "UNKNOWN999" in step.tool_call.error
    assert trace.verified_facts == {}
    assert "not found" in trace.final_conclusion.lower() or "unable" in trace.final_conclusion.lower()
    # No fabricated course data exists
    assert "CS101" not in trace.final_conclusion


# =========================================================================
# 13. Unknown Assignment Handling (Anti-Hallucination)
# =========================================================================
def test_unknown_assignment_handling():
    agent = ToolUsingAgent()
    trace = agent.run("Show rubric for hw999 in 26ECAC401.")

    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.tool_call.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "hw999" in step.tool_call.error
    assert "Unable to complete audit" in trace.final_conclusion or "not found" in trace.final_conclusion


# =========================================================================
# 14. Tool Validation Failure Handling
# =========================================================================
def test_tool_validation_failure_handling():
    custom_registry = ToolRegistry()
    from app.labs.lab2.tools.notes import SearchCourseNotesTool
    custom_registry.register(SearchCourseNotesTool())

    agent = ToolUsingAgent(registry=custom_registry)
    tool_record = agent.registry.execute_tool("search_course_notes", {"course_id": "", "query": "testing"})
    assert tool_record.status == ToolExecutionStatus.VALIDATION_ERROR


# =========================================================================
# 15. Tool Execution Failure Handling
# =========================================================================
def test_tool_execution_failure_handling():
    agent = ToolUsingAgent()
    trace = agent.run("Retrieve configuration for BADCOURSE")

    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "not found" in trace.steps[0].tool_call.error.lower()


# =========================================================================
# 16. Verified Facts Contain ONLY Tool-Backed Facts
# =========================================================================
def test_verified_facts_contain_only_tool_backed_facts():
    agent = ToolUsingAgent()
    trace = agent.run("Audit UNKNOWN999 grading.")
    # On failure, no hallucinated facts must be stored in verified_facts
    assert trace.verified_facts == {}


# =========================================================================
# 17. Trace Contains Actual Tool Calls
# =========================================================================
def test_trace_contains_actual_tool_calls():
    agent = ToolUsingAgent()
    trace = agent.run("Search 26ECAC401 course notes for ReAct")

    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.step_number == 1
    assert step.tool_call.tool_name == "search_course_notes"
    assert step.tool_call.validated_input["course_id"] == "26ECAC401"
    assert step.tool_call.validated_input["query"].lower() == "react"
    assert step.tool_call.output_data["match_count"] >= 1


# =========================================================================
# 18. Trace Does NOT Expose Private Chain-of-Thought
# =========================================================================
def test_trace_does_not_expose_private_chain_of_thought():
    agent = ToolUsingAgent()
    trace = agent.run("Audit 26ECAC401 syllabus and course modules")

    for step in trace.steps:
        assert "chain of thought" not in step.selected_action.lower()
        assert "hidden reasoning" not in step.selected_action.lower()
        assert len(step.selected_action) < 250


# =========================================================================
# 19. Bounded Execution Prevents Infinite Loops
# =========================================================================
def test_bounded_execution(monkeypatch):
    mutated_configs = copy.deepcopy(CANONICAL_CONFIGS)
    mutated_configs["26ECAC401"]["students_per_ta"] = 30
    mutated_configs["26ECAC401"]["hours_per_ta_per_week"] = 20.0
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_CONFIGS", mutated_configs)

    agent = ToolUsingAgent(max_tool_calls=1)
    trace = agent.run("Check whether TA staffing is sufficient for 120 students and 4 assignments in 26ECAC401, assuming 15 minutes of grading per submission.")

    assert len(trace.steps) == 1
    assert "limit" in trace.final_conclusion.lower() or "1" in str(len(trace.steps))


# =========================================================================
# 20. Anti-Hardcoding Mutation Test (No Tool Bypass)
# =========================================================================
def test_anti_hardcoding_mutation_alters_agent_conclusion(monkeypatch):
    mutated_syllabi = copy.deepcopy(CANONICAL_SYLLABI)
    mutated_syllabi["26ECAC401"]["grading_weights"] = [
        {"category": "Lab Assignments", "weight_percentage": 40.0, "description": "Labs"},
        {"category": "Midterm Exam", "weight_percentage": 30.0, "description": "Midterm"},
        {"category": "Capstone Project", "weight_percentage": 35.0, "description": "Capstone"},
    ]
    monkeypatch.setattr("app.data.course_fixtures.CANONICAL_SYLLABI", mutated_syllabi)

    agent = ToolUsingAgent()
    trace = agent.run("Audit 26ECAC401 grading breakdown: do assignments, midterm, and project sum to 100%?")

    assert trace.verified_facts["calculated_total_percentage"] == 105.0
    assert trace.verified_facts["is_valid_grade_breakdown"] is False
    assert trace.verified_facts["grade_delta_from_hundred"] == 5.0
    assert "105.0%" in trace.final_conclusion
    assert "INVALID" in trace.final_conclusion


# =========================================================================
# 21. Final Conclusion Strictly Uses Tool Results
# =========================================================================
def test_final_conclusion_strictly_uses_tool_results():
    agent = ToolUsingAgent()
    trace = agent.run("Search 26ECAC401 course notes for ReAct")

    assert len(trace.steps) >= 1
    assert "ReAct" in trace.final_conclusion
    assert trace.steps[0].tool_call.tool_name == "search_course_notes"
    assert trace.verified_facts["notes_match_count"] >= 1
