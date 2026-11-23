"""Unit and integration tests for Lab 2 Tool Foundation and Typed Tools."""

import math
import pytest
from pydantic import BaseModel, Field

from app.data.repository import CourseRepository
from app.labs.lab2.tools.assignments import GetAssignmentSpecTool, GetRubricBreakdownTool
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.calculators import (
    CalculateGradeBreakdownTotalTool,
    ComputeWorkloadHoursTool,
    ValidateRubricSumTool,
)
from app.labs.lab2.tools.notes import SearchCourseNotesTool
from app.labs.lab2.tools.policy import GetCourseConfigTool, GetTAPolicyTool
from app.labs.lab2.tools.registry import ToolRegistry, tool_registry
from app.labs.lab2.tools.schemas import (
    AssignmentQueryInput,
    AssignmentSpecOutput,
    CourseConfigOutput,
    CourseNotesOutput,
    CourseNotesQueryInput,
    CourseQueryInput,
    GradeWeightsInput,
    GradeWeightsTotalOutput,
    RubricBreakdownOutput,
    RubricSumInput,
    RubricSumOutput,
    SyllabusOutput,
    TAPolicyOutput,
    TAPolicyQueryInput,
    ToolCategory,
    ToolDefinition,
    WorkloadInput,
    WorkloadOutput,
)
from app.labs.lab2.tools.syllabus import ReadCourseSyllabusTool
from app.models.lab2_models import ToolCallRecord, ToolExecutionStatus


class DummyInput(BaseModel):
    query: str = Field(min_length=2)


class DummyOutput(BaseModel):
    result: str
    count: int


class DummyValidTool(BaseTool):
    name = "dummy_tool"
    description = "A valid dummy tool for registry tests."
    category = ToolCategory.READER.value
    input_model = DummyInput
    output_model = DummyOutput

    def _run(self, typed_input: DummyInput) -> DummyOutput:
        return DummyOutput(result=f"processed_{typed_input.query}", count=len(typed_input.query))


class DummyBrokenOutputTool(BaseTool):
    name = "broken_output_tool"
    description = "A tool that returns data violating output schema."
    category = ToolCategory.CALCULATOR.value
    input_model = DummyInput
    output_model = DummyOutput

    def _run(self, typed_input: DummyInput) -> dict:
        return {"result": 12345}


# =========================================================================
# SECTION 1: Foundation Tests (A - L)
# =========================================================================
def test_tool_registration_success():
    registry = ToolRegistry()
    tool = ReadCourseSyllabusTool()
    registry.register(tool)
    assert registry.get_tool("read_course_syllabus") is tool


def test_duplicate_tool_registration_rejected():
    registry = ToolRegistry()
    tool1 = ReadCourseSyllabusTool()
    tool2 = ReadCourseSyllabusTool()
    registry.register(tool1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


def test_tool_lookup():
    registry = ToolRegistry()
    tool = ReadCourseSyllabusTool()
    registry.register(tool)
    found = registry.get_tool("read_course_syllabus")
    assert found is not None
    assert found.name == "read_course_syllabus"
    assert registry.get_tool("non_existent_tool") is None


def test_tool_catalog():
    registry = ToolRegistry()
    registry.register(ReadCourseSyllabusTool())
    catalog = registry.list_tools()
    assert len(catalog) == 1
    definition = catalog[0]
    assert isinstance(definition, ToolDefinition)
    assert definition.name == "read_course_syllabus"
    assert definition.category == "reader"


def test_valid_typed_input():
    tool = ReadCourseSyllabusTool()
    record = tool.execute({"course_id": "26ECAC401"})
    assert record.status == ToolExecutionStatus.SUCCESS
    assert record.validated_input == {"course_id": "26ECAC401"}
    assert record.output_data is not None
    assert record.output_data["course_id"] == "26ECAC401"
    assert record.error is None


def test_invalid_input_rejected_empty_string():
    tool = ReadCourseSyllabusTool()
    record = tool.execute({"course_id": ""})
    assert record.status == ToolExecutionStatus.VALIDATION_ERROR
    assert record.output_data is None
    assert "Input validation error" in record.error


def test_invalid_input_rejected_missing_field():
    tool = ReadCourseSyllabusTool()
    record = tool.execute({})
    assert record.status == ToolExecutionStatus.VALIDATION_ERROR
    assert record.output_data is None
    assert "Input validation error" in record.error


def test_invalid_input_rejected_non_dict():
    tool = ReadCourseSyllabusTool()
    record = tool.execute("not a dict")  # type: ignore
    assert record.status == ToolExecutionStatus.VALIDATION_ERROR
    assert record.output_data is None
    assert "Invalid parameter format" in record.error


def test_real_26ecac401_lookup_from_repository():
    repo = CourseRepository()
    tool = ReadCourseSyllabusTool(repository=repo)
    record = tool.execute({"course_id": "26ECAC401"})
    assert record.status == ToolExecutionStatus.SUCCESS
    out = record.output_data
    assert out["course_id"] == "26ECAC401"
    assert "Agentic AI" in out["course_name"]
    assert len(out["modules"]) >= 2

    # Obsolete CS101 lookup must fail
    old_record = tool.execute({"course_id": "CS101"})
    assert old_record.status == ToolExecutionStatus.EXECUTION_ERROR


def test_unknown_course_returns_structured_error():
    tool = ReadCourseSyllabusTool()
    record = tool.execute({"course_id": "UNKNOWN999"})
    assert record.status == ToolExecutionStatus.EXECUTION_ERROR
    assert record.output_data is None
    assert "UNKNOWN999" in record.error

    # Obsolete CS101 must also return execution error
    cs101_record = tool.execute({"course_id": "CS101"})
    assert cs101_record.status == ToolExecutionStatus.EXECUTION_ERROR


def test_execution_timing_exists():
    tool = ReadCourseSyllabusTool()
    record = tool.execute({"course_id": "26ECAC401"})
    assert isinstance(record.execution_duration_ms, float)
    assert record.execution_duration_ms >= 0.0


def test_tool_call_record_contract():
    registry = ToolRegistry()
    registry.register(ReadCourseSyllabusTool())
    record = registry.execute_tool("read_course_syllabus", {"course_id": "26ECAC401"})
    assert isinstance(record, ToolCallRecord)
    assert record.call_id.startswith("call_")
    assert record.tool_name == "read_course_syllabus"
    assert record.validated_input == {"course_id": "26ECAC401"}
    assert record.output_data is not None
    assert record.status == ToolExecutionStatus.SUCCESS


def test_invalid_tool_name_returns_structured_error():
    registry = ToolRegistry()
    record = registry.execute_tool("non_existent_tool", {"course_id": "26ECAC401"})
    assert isinstance(record, ToolCallRecord)
    assert record.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "not found in registry" in record.error


def test_output_schema_validation_rejects_corrupted_output():
    tool = DummyBrokenOutputTool()
    record = tool.execute({"query": "testing"})
    assert record.status == ToolExecutionStatus.EXECUTION_ERROR
    assert record.output_data is None
    assert "Output validation error" in record.error


# =========================================================================
# SECTION 2: Tool 1 - search_course_notes
# =========================================================================
def test_search_course_notes_success_different_queries():
    tool = SearchCourseNotesTool()

    # Query 1: react (from Chapter 1)
    res_react = tool.execute({"course_id": "26ECAC401", "query": "react"})
    assert res_react.status == ToolExecutionStatus.SUCCESS
    assert res_react.output_data["match_count"] >= 1
    assert any("ReAct" in m["topic"] for m in res_react.output_data["matches"])
    assert any(m["chapter"] == 1 for m in res_react.output_data["matches"])

    # Query 2: memory (from Chapter 2)
    res_mem = tool.execute({"course_id": "26ECAC401", "query": "memory"})
    assert res_mem.status == ToolExecutionStatus.SUCCESS
    assert res_mem.output_data["match_count"] >= 1
    assert any("Memory" in m["topic"] for m in res_mem.output_data["matches"])
    assert any(m["chapter"] == 2 for m in res_mem.output_data["matches"])

    # Verify query results are distinct
    assert res_react.output_data["matches"] != res_mem.output_data["matches"]


def test_search_course_notes_no_match():
    tool = SearchCourseNotesTool()
    res = tool.execute({"course_id": "26ECAC401", "query": "quantum gravity non-existent"})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["match_count"] == 0
    assert res.output_data["matches"] == []


def test_search_course_notes_unknown_course():
    tool = SearchCourseNotesTool()
    res = tool.execute({"course_id": "NONEXISTENT", "query": "react"})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "NONEXISTENT" in res.error


def test_search_course_notes_validation_error():
    tool = SearchCourseNotesTool()
    res = tool.execute({"course_id": "26ECAC401", "query": ""})
    assert res.status == ToolExecutionStatus.VALIDATION_ERROR


# =========================================================================
# SECTION 3: Tool 2 - get_assignment_spec
# =========================================================================
def test_get_assignment_spec_unestablished_for_26ecac401():
    """Assignments are not established in supplied Agentic AI notes; tool must return structured error."""
    tool = GetAssignmentSpecTool()
    res = tool.execute({"course_id": "26ECAC401", "assignment_id": "hw1"})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "26ECAC401" in res.error


def test_get_assignment_spec_with_dynamic_repository():
    """When assignment spec is provided in repository, tool executes and validates output schema."""
    custom_repo = CourseRepository()
    custom_assignment = {
        "course_id": "26ECAC401",
        "assignment_id": "lab1_react",
        "title": "ReAct Autonomous Agent Implementation",
        "due_week": 4,
        "deliverables": ["react_agent.py", "evaluator.py"],
        "max_points": 100.0,
        "submission_requirements": "GitHub repository link with passing test suite",
        "description": "Implement ReAct autonomous loop with tool calling",
        "source": "Dynamic Course Repository",
    }
    custom_repo.get_canonical_assignment = lambda course_id, assignment_id: (
        custom_assignment if (course_id == "26ECAC401" and assignment_id == "lab1_react") else None
    )
    tool = GetAssignmentSpecTool(repository=custom_repo)
    res = tool.execute({"course_id": "26ECAC401", "assignment_id": "lab1_react"})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["title"] == "ReAct Autonomous Agent Implementation"
    assert res.output_data["max_points"] == 100.0


def test_get_assignment_spec_unknown_course():
    tool = GetAssignmentSpecTool()
    res = tool.execute({"course_id": "BADCOURSE", "assignment_id": "hw1"})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "BADCOURSE" in res.error


# =========================================================================
# SECTION 4: Tool 3 - get_rubric_breakdown
# =========================================================================
def test_get_rubric_breakdown_unestablished_for_26ecac401():
    """Rubrics are not established in supplied Agentic AI notes; tool must return structured error."""
    tool = GetRubricBreakdownTool()
    res = tool.execute({"course_id": "26ECAC401", "assignment_id": "unknown_rubric"})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "unknown_rubric" in res.error


def test_get_rubric_breakdown_with_dynamic_repository():
    """When rubric is provided in repository, tool validates criteria structure and total points."""
    custom_repo = CourseRepository()
    custom_rubric = {
        "course_id": "26ECAC401",
        "assignment_id": "lab1_react",
        "rubric_criteria": [
            {"criterion_name": "ReAct Loop Correctness", "points": 40.0, "description": "Accurate thought-action-observation cycles"},
            {"criterion_name": "Tool Schema Validation", "points": 30.0, "description": "Pydantic typed validation"},
            {"criterion_name": "Audit Logging", "points": 30.0, "description": "Complete execution trace logging"},
        ],
        "total_points": 100.0,
        "evidence": "Course Syllabus Lab 1 Specification",
    }
    custom_repo.get_canonical_rubric = lambda course_id, assignment_id: (
        custom_rubric if (course_id == "26ECAC401" and assignment_id == "lab1_react") else None
    )
    tool = GetRubricBreakdownTool(repository=custom_repo)
    res = tool.execute({"course_id": "26ECAC401", "assignment_id": "lab1_react"})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert len(res.output_data["rubric_criteria"]) == 3
    assert res.output_data["total_points"] == 100.0


# =========================================================================
# SECTION 5: Tool 4 - get_course_config
# =========================================================================
def test_get_course_config_success():
    tool = GetCourseConfigTool()
    res = tool.execute({"course_id": "26ECAC401"})
    assert res.status == ToolExecutionStatus.SUCCESS
    data = res.output_data
    assert data["course_id"] == "26ECAC401"
    assert "Agentic AI" in data["course_name"]
    assert "Python 3.10+" in data["lab_environment"]
    assert "LangGraph" in data["lab_environment"]
    assert data["duration_weeks"] is None
    assert data["students_per_ta"] is None


def test_get_course_config_unknown():
    tool = GetCourseConfigTool()
    res = tool.execute({"course_id": "INVALID_COURSE"})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "INVALID_COURSE" in res.error

    # Old CS101 must also fail
    res_cs101 = tool.execute({"course_id": "CS101"})
    assert res_cs101.status == ToolExecutionStatus.EXECUTION_ERROR


# =========================================================================
# SECTION 6: Tool 5 - get_ta_policy
# =========================================================================
def test_get_ta_policy_unestablished_for_26ecac401():
    """TA staffing ratio is unestablished in Agentic AI notes; returns structured error."""
    tool = GetTAPolicyTool()
    res = tool.execute({"course_id": "26ECAC401", "enrollment_count": 80})
    assert res.status == ToolExecutionStatus.EXECUTION_ERROR
    assert "26ECAC401" in res.error


def test_get_ta_policy_deterministic_math_with_configured_repo():
    """When policy configuration is provided, verifies deterministic math: ceil(enrollment / ratio) * hours."""
    custom_repo = CourseRepository()
    custom_repo.get_canonical_ta_policy = lambda course_id, enrollment: {
        "course_id": course_id,
        "enrollment": enrollment,
        "required_ta_count": math.ceil(enrollment / 25),
        "required_hours_per_week": float(math.ceil(enrollment / 25) * 20),
        "policy_ratio": "1 TA per 25 students (1:25)",
        "formula_applied": f"max(1, ceil({enrollment} / 25)) = {math.ceil(enrollment / 25)} TAs @ 20 hrs/wk",
        "source": "Custom TA Policy",
    } if course_id == "26ECAC401" else None

    tool = GetTAPolicyTool(repository=custom_repo)

    # 75 students (25 per TA) -> 3 TAs, 60 hrs/wk
    res_75 = tool.execute({"course_id": "26ECAC401", "enrollment_count": 75})
    assert res_75.status == ToolExecutionStatus.SUCCESS
    assert res_75.output_data["required_ta_count"] == 3
    assert res_75.output_data["required_hours_per_week"] == 60.0

    # 30 students -> ceil(30/25) = 2 TAs, 40 hrs/wk
    res_30 = tool.execute({"course_id": "26ECAC401", "enrollment_count": 30})
    assert res_30.status == ToolExecutionStatus.SUCCESS
    assert res_30.output_data["required_ta_count"] == 2
    assert res_30.output_data["required_hours_per_week"] == 40.0


def test_get_ta_policy_invalid_enrollment():
    tool = GetTAPolicyTool()
    res = tool.execute({"course_id": "26ECAC401", "enrollment_count": 0})
    assert res.status == ToolExecutionStatus.VALIDATION_ERROR


# =========================================================================
# SECTION 7: Tool 6 - calculate_grade_breakdown_total
# =========================================================================
def test_calculate_grade_breakdown_total_valid():
    tool = CalculateGradeBreakdownTotalTool()
    res = tool.execute({"weights": [30, 20, 20, 30]})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["total_percentage"] == 100.0
    assert res.output_data["is_valid"] is True
    assert res.output_data["delta_from_hundred"] == 0.0


def test_calculate_grade_breakdown_total_invalid_over():
    tool = CalculateGradeBreakdownTotalTool()
    res = tool.execute({"weights": [40, 25, 30, 10]})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["total_percentage"] == 105.0
    assert res.output_data["is_valid"] is False
    assert res.output_data["delta_from_hundred"] == 5.0


def test_calculate_grade_breakdown_total_invalid_under():
    tool = CalculateGradeBreakdownTotalTool()
    res = tool.execute({"weights": [25, 25, 25]})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["total_percentage"] == 75.0
    assert res.output_data["is_valid"] is False
    assert res.output_data["delta_from_hundred"] == 25.0


def test_calculate_grade_breakdown_empty_weights():
    tool = CalculateGradeBreakdownTotalTool()
    res = tool.execute({"weights": []})
    assert res.status == ToolExecutionStatus.VALIDATION_ERROR


# =========================================================================
# SECTION 8: Tool 7 - validate_rubric_sum
# =========================================================================
def test_validate_rubric_sum_matching():
    tool = ValidateRubricSumTool()
    res = tool.execute({"criteria_points": [40, 25, 20, 15], "expected_max_points": 100.0})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["sum_points"] == 100.0
    assert res.output_data["expected_points"] == 100.0
    assert res.output_data["is_matching"] is True
    assert res.output_data["difference"] == 0.0


def test_validate_rubric_sum_mismatch():
    tool = ValidateRubricSumTool()
    res = tool.execute({"criteria_points": [40, 25, 20], "expected_max_points": 100.0})
    assert res.status == ToolExecutionStatus.SUCCESS
    assert res.output_data["sum_points"] == 85.0
    assert res.output_data["is_matching"] is False
    assert res.output_data["difference"] == 15.0


# =========================================================================
# SECTION 9: Tool 8 - compute_workload_hours
# =========================================================================
def test_compute_workload_hours_valid():
    tool = ComputeWorkloadHoursTool()
    res = tool.execute({
        "enrollment": 120,
        "assignments_count": 4,
        "grading_minutes_per_submission": 15,
    })
    assert res.status == ToolExecutionStatus.SUCCESS
    # 120 students * 4 assignments * 15 mins = 7200 mins = 120.0 hours
    assert res.output_data["total_grading_hours"] == 120.0
    # Per batch: 120 * 15 / 60 = 30.0 hours
    assert res.output_data["hours_per_assignment"] == 30.0


def test_compute_workload_hours_invalid():
    tool = ComputeWorkloadHoursTool()
    # Negative enrollment
    res = tool.execute({
        "enrollment": -10,
        "assignments_count": 4,
        "grading_minutes_per_submission": 15,
    })
    assert res.status == ToolExecutionStatus.VALIDATION_ERROR


# =========================================================================
# SECTION 10: Anti-Hardcoding Repository Dynamic Dependency Proof
# =========================================================================
def test_anti_hardcoding_assignment_spec_reflects_repository():
    """Prove that GetAssignmentSpecTool dynamically reads from repository, not a hardcoded dict."""
    custom_repo = CourseRepository()
    # Inject a distinct customized course assignment into the repository
    custom_assignment = {
        "course_id": "TEST_CS999",
        "assignment_id": "custom_hw",
        "title": "Dynamic Anti-Hardcode Assignment",
        "due_week": 8,
        "deliverables": ["custom_artifact.py"],
        "max_points": 250.0,
        "submission_requirements": "Custom submission pipeline via secure token",
        "description": "Custom non-hardcoded test assignment",
        "source": "Dynamic Unit Test Repository",
    }
    custom_repo.get_canonical_assignment = lambda course_id, assignment_id: (
        custom_assignment if (course_id == "TEST_CS999" and assignment_id == "custom_hw") else None
    )

    tool = GetAssignmentSpecTool(repository=custom_repo)
    record = tool.execute({"course_id": "TEST_CS999", "assignment_id": "custom_hw"})

    assert record.status == ToolExecutionStatus.SUCCESS
    assert record.output_data["title"] == "Dynamic Anti-Hardcode Assignment"
    assert record.output_data["max_points"] == 250.0
    assert record.output_data["deliverables"] == ["custom_artifact.py"]


def test_anti_hardcoding_rubric_reflects_repository():
    """Prove that GetRubricBreakdownTool dynamically reads rubric criteria from repository."""
    custom_repo = CourseRepository()
    custom_rubric = {
        "course_id": "TEST_CS999",
        "assignment_id": "custom_hw",
        "rubric_criteria": [
            {
                "criterion_name": "Dynamic Rubric Item 1",
                "points": 77.0,
                "description": "Dynamic criterion test",
            },
            {
                "criterion_name": "Dynamic Rubric Item 2",
                "points": 23.0,
                "description": "Second criterion",
            },
        ],
        "total_points": 100.0,
        "evidence": "Custom Test Evidence",
    }
    custom_repo.get_canonical_rubric = lambda course_id, assignment_id: (
        custom_rubric if (course_id == "TEST_CS999" and assignment_id == "custom_hw") else None
    )

    tool = GetRubricBreakdownTool(repository=custom_repo)
    record = tool.execute({"course_id": "TEST_CS999", "assignment_id": "custom_hw"})

    assert record.status == ToolExecutionStatus.SUCCESS
    assert record.output_data["rubric_criteria"][0]["criterion_name"] == "Dynamic Rubric Item 1"
    assert record.output_data["rubric_criteria"][0]["points"] == 77.0


# =========================================================================
# SECTION 11: Global Registry Catalog Completeness
# =========================================================================
def test_global_registry_contains_all_tools():
    catalog = tool_registry.list_tools()
    tool_names = {t.name for t in catalog}
    expected_tools = {
        "read_course_syllabus",
        "search_course_notes",
        "get_assignment_spec",
        "get_rubric_breakdown",
        "get_course_config",
        "get_ta_policy",
        "calculate_grade_breakdown_total",
        "validate_rubric_sum",
        "compute_workload_hours",
    }
    assert expected_tools.issubset(tool_names)
