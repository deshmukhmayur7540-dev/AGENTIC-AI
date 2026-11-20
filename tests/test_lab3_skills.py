"""Unit and integration tests for Lab 3: Reusable Skills."""

import pytest
from app.labs.lab3.registry import skill_registry, SkillRegistry
from app.labs.lab3.skills.planning_skill import CoursePlanningSkill
from app.labs.lab3.skills.research_skill import ResearchSummarySkill
from app.labs.lab3.skills.formatting_skill import CourseContentFormattingSkill
from app.labs.lab3.agent import SkillUsingAgent


def test_default_skills_registered():
    """Verify that all default academic skills are registered in the SkillRegistry."""
    skills = skill_registry.list_skills()
    names = [s.name for s in skills]
    assert "course_planning_skill" in names
    assert "research_summary_skill" in names
    assert "course_content_formatting_skill" in names


def test_skill_schema_inspection():
    """Verify that skill schemas contain valid input/output JSON schemas."""
    meta = skill_registry.inspect_schema("course_planning_skill")
    assert meta is not None
    assert meta.name == "course_planning_skill"
    assert "properties" in meta.input_schema
    assert "target_weeks" in meta.input_schema["properties"]
    assert "properties" in meta.output_schema
    assert "schedule" in meta.output_schema["properties"]


def test_planning_skill_case_1_semester():
    """Case 1: Standard 12-week course plan across all 4 chapters."""
    params = {
        "course_code": "26ECAC401",
        "course_name": "Agentic AI",
        "target_weeks": 12,
        "focus_chapters": [1, 2, 3, 4],
    }
    record = skill_registry.execute_skill("course_planning_skill", params)
    assert record.status == "SUCCESS"
    assert record.error is None
    data = record.output_data
    assert data["total_weeks"] == 12
    assert len(data["schedule"]) == 12
    assert len(data["milestones"]) >= 3
    # Check that chapters 1 through 4 are represented in the schedule
    chapters_mapped = {item["chapter_mapped"] for item in data["schedule"]}
    assert {1, 2, 3, 4}.issubset(chapters_mapped)


def test_planning_skill_case_2_intensive():
    """Case 2: 8-week accelerated intensive focusing on Chapters 1 and 2."""
    params = {
        "course_code": "26ECAC401",
        "course_name": "Agentic AI Accelerated",
        "target_weeks": 8,
        "focus_chapters": [1, 2],
    }
    record = skill_registry.execute_skill("course_planning_skill", params)
    assert record.status == "SUCCESS"
    data = record.output_data
    assert data["total_weeks"] == 8
    assert len(data["schedule"]) == 8
    chapters_mapped = {item["chapter_mapped"] for item in data["schedule"]}
    assert chapters_mapped == {1, 2}


def test_planning_skill_validation_error_on_invalid_weeks():
    """Verify input validation rejects invalid week counts (<4 or >24)."""
    params = {
        "course_code": "26ECAC401",
        "target_weeks": 2,  # Invalid: below ge=4 constraint
    }
    record = skill_registry.execute_skill("course_planning_skill", params)
    assert record.status == "VALIDATION_ERROR"
    assert "target_weeks" in record.error
    assert record.output_data is None


def test_research_skill_case_1_react_loop():
    """Case 1: Research summary on Plan-Act-Observe-Revise and ReAct."""
    params = {
        "topic": "Plan-Act-Observe-Revise and ReAct loop",
        "course_code": "26ECAC401",
        "target_chapter": 1,
        "depth": "deep_dive",
    }
    record = skill_registry.execute_skill("research_summary_skill", params)
    assert record.status == "SUCCESS"
    data = record.output_data
    assert data["topic"] == params["topic"]
    assert len(data["cited_evidence"]) >= 1
    assert any("Plan" in e["excerpt"] or "Agent" in e["excerpt"] or "ReAct" in e["excerpt"] for e in data["cited_evidence"])


def test_research_skill_case_2_langgraph_mcp():
    """Case 2: Research summary on LangGraph and MCP."""
    params = {
        "topic": "LangGraph and Model Context Protocol",
        "course_code": "26ECAC401",
        "target_chapter": 2,
        "depth": "standard",
    }
    record = skill_registry.execute_skill("research_summary_skill", params)
    assert record.status == "SUCCESS"
    data = record.output_data
    assert len(data["cited_evidence"]) >= 1
    assert data["chapter_referenced"] == 2


def test_formatting_skill_case_1_handout():
    """Case 1: Format raw notes into a Markdown handout."""
    params = {
        "title": "Agentic AI Core Pillars",
        "course_code": "26ECAC401",
        "target_format": "markdown_handout",
        "raw_content": (
            "1. Perception: Sensing environment state\n"
            "2. Reasoning: Decomposing objectives\n"
            "3. Action: Executing typed tools\n"
            "4. Learning: Updating memory from observation feedback"
        ),
    }
    record = skill_registry.execute_skill("course_content_formatting_skill", params)
    assert record.status == "SUCCESS"
    data = record.output_data
    assert data["format_type"] == "markdown_handout"
    assert "# Agentic AI Core Pillars" in data["formatted_content"]
    assert len(data["table_of_contents"]) >= 1


def test_formatting_skill_case_2_assignment_brief():
    """Case 2: Format assignment spec with deliverables."""
    params = {
        "title": "Lab 2: Typed Tool Execution Harness",
        "course_code": "26ECAC401",
        "target_format": "assignment_brief",
        "raw_content": (
            "Build a sandboxed tool executor for university course queries.\n"
            "Deliverables:\n"
            "Python implementation of BaseTool\n"
            "Comprehensive test suite with pytest\n"
            "Trace visualizer output"
        ),
    }
    record = skill_registry.execute_skill("course_content_formatting_skill", params)
    assert record.status == "SUCCESS"
    data = record.output_data
    assert data["format_type"] == "assignment_brief"
    assert "Required Deliverables" in data["formatted_content"]


def test_unknown_skill_returns_structured_error():
    """Executing a non-existent skill returns structured EXECUTION_ERROR."""
    record = skill_registry.execute_skill("non_existent_skill_xyz", {"foo": "bar"})
    assert record.status == "EXECUTION_ERROR"
    assert "not registered" in record.error


def test_skill_execution_history_recorded():
    """Verify execution history accumulates records."""
    initial_count = len(skill_registry.get_history())
    skill_registry.execute_skill("course_planning_skill", {"course_code": "26ECAC401", "target_weeks": 10})
    updated_history = skill_registry.get_history()
    assert len(updated_history) == initial_count + 1


@pytest.mark.asyncio
async def test_skill_using_agent_natural_language_routing():
    """Verify SkillUsingAgent infers appropriate skill from natural language prompts."""
    agent = SkillUsingAgent()

    # Route 1: Planning prompt
    res_plan = await agent.execute("run_query", {"query": "Plan a 14-week course schedule for 26ECAC401"})
    assert res_plan["routing"] == "course_planning_skill"
    assert res_plan["execution"]["status"] == "SUCCESS"
    assert res_plan["execution"]["output_data"]["total_weeks"] == 14

    # Route 2: Research prompt
    res_res = await agent.execute("run_query", {"query": "Research Chapter 1 autonomous agent loops"})
    assert res_res["routing"] == "research_summary_skill"
    assert res_res["execution"]["status"] == "SUCCESS"

    # Route 3: Formatting prompt
    res_fmt = await agent.execute("run_query", {"query": "Format this into a markdown handout: Unit 1 summary"})
    assert res_fmt["routing"] == "course_content_formatting_skill"
    assert res_fmt["execution"]["status"] == "SUCCESS"
