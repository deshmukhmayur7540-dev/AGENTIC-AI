"""Regression tests for End-to-End Audit & Fix of Lab 1 and Lab 2.

Covers:
1. Lab 2 API and Agent request defaults to canonical 26ECAC401.
2. Natural language 'AI' queries never execute with 'AI' as course_id.
3. Agentic AI Chapter 1 retrieval succeeds ('What is Plan-Act-Observe-Revise?').
4. Agentic AI Chapter 2 retrieval succeeds ('What is function calling?').
5. Agentic AI Chapter 3 & 4 retrieval succeeds ('What is multi-agent orchestration?', 'What are the safety and governance concepts?').
6. Unsupported information is not fabricated ('Explain quantum gravity.').
7. Lab 1 end-to-end clarification flow produces >= 2 questions.
8. Lab 1 end-to-end plan generation and revision immutability with structured diffs.
"""

import pytest

from app.main import app
from tests.conftest import AuthTestClient
from app.core.constants import CANONICAL_COURSE_CODE, CANONICAL_COURSE_NAME
from app.labs.lab2.agent import ToolUsingAgent
from app.labs.lab2.planner import ActionPlanner
from app.models.lab2_models import ToolExecutionStatus


@pytest.fixture
def client():
    return AuthTestClient(app)


# =============================================================================
# 1. Lab 2 UI / API Defaults to 26ECAC401
# =============================================================================
def test_lab2_request_defaults_to_26ecac401(client):
    """Verify that omitting course_id defaults to 26ECAC401 without error."""
    resp = client.post("/api/lab2/query", json={"request": "Audit course syllabus and modules"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    trace = data["data"]
    assert trace["status"] == "SUCCESS"
    assert trace["verified_facts"]["course_id"] == CANONICAL_COURSE_CODE


# =============================================================================
# 2. No "AI" Course ID Execution Error
# =============================================================================
def test_lab2_ai_in_prompt_never_passes_ai_as_course_id(client):
    """Verify queries containing natural language 'AI' do not raise 'Course AI was not found'."""
    queries = [
        "Search AI notes for ReAct",
        "Audit AI grading breakdown",
        "Check Agentic AI course syllabus",
        "What does AI cover about tools and memory?",
    ]
    agent = ToolUsingAgent()
    for q in queries:
        trace = agent.run(q)
        assert trace.status != ToolExecutionStatus.EXECUTION_ERROR
        for step in trace.steps:
            if step.tool_call and "course_id" in step.tool_call.validated_input:
                assert step.tool_call.validated_input["course_id"] != "AI"
                assert step.tool_call.validated_input["course_id"] == CANONICAL_COURSE_CODE

        # Also test through API client
        resp = client.post("/api/lab2/query", json={"request": q})
        assert resp.status_code == 200
        api_data = resp.json()
        assert api_data["success"] is True
        assert "Course 'AI' was not found" not in str(api_data)


def test_planner_extract_entities_ignores_standalone_ai():
    """ActionPlanner must never extract standalone 'AI' as a course ID."""
    planner = ActionPlanner()
    entities = planner.extract_entities("Search AI notes for ReAct")
    assert entities.get("course_id") != "AI"

    entities_cat = planner.extract_entities("Check CS101 syllabus")
    assert entities_cat.get("course_id") == "CS101"

    entities_canonical = planner.extract_entities("Inspect 26ECAC401 materials")
    assert entities_canonical.get("course_id") == "26ECAC401"


# =============================================================================
# 3. Agentic AI Chapter 1 Retrieval Succeeds
# =============================================================================
def test_chapter_1_retrieval_plan_act_observe_revise():
    """Verify 'What is Plan-Act-Observe-Revise?' retrieves Chapter 1 evidence."""
    agent = ToolUsingAgent()
    trace = agent.run("What is Plan-Act-Observe-Revise?")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.tool_name == "search_course_notes"
    assert trace.verified_facts["notes_match_count"] >= 1
    matches = trace.verified_facts["notes_matches"]
    assert any(m["chapter"] == 1 for m in matches)
    assert "Plan-Act-Observe-Revise" in trace.final_conclusion or "Chapter 1" in trace.final_conclusion


# =============================================================================
# 4. Agentic AI Chapter 2 Retrieval Succeeds
# =============================================================================
def test_chapter_2_retrieval_function_calling():
    """Verify 'What is function calling?' retrieves Chapter 2 evidence."""
    agent = ToolUsingAgent()
    trace = agent.run("What is function calling?")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.tool_name == "search_course_notes"
    assert trace.verified_facts["notes_match_count"] >= 1
    matches = trace.verified_facts["notes_matches"]
    assert any(m["chapter"] == 2 for m in matches)
    assert "Chapter 2" in trace.final_conclusion


# =============================================================================
# 5. Agentic AI Chapter 3 & 4 Retrieval Succeeds
# =============================================================================
def test_chapter_3_retrieval_multi_agent_orchestration():
    """Verify 'What is multi-agent orchestration?' retrieves Chapter 3 evidence."""
    agent = ToolUsingAgent()
    trace = agent.run("What is multi-agent orchestration?")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.tool_name == "search_course_notes"
    assert trace.verified_facts["notes_match_count"] >= 1
    matches = trace.verified_facts["notes_matches"]
    assert any(m["chapter"] == 3 for m in matches)


def test_chapter_4_retrieval_safety_governance():
    """Verify 'What are the safety and governance concepts?' retrieves Chapter 4 evidence."""
    agent = ToolUsingAgent()
    trace = agent.run("What are the safety and governance concepts?")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert len(trace.steps) == 1
    assert trace.steps[0].tool_call.tool_name == "search_course_notes"
    assert trace.verified_facts["notes_match_count"] >= 1
    matches = trace.verified_facts["notes_matches"]
    assert any(m["chapter"] == 4 for m in matches)


# =============================================================================
# 6. Unsupported Information Is Not Fabricated
# =============================================================================
def test_unsupported_query_quantum_gravity_no_hallucination():
    """Verify 'Explain quantum gravity.' produces 0 matches and explicit unsupported conclusion."""
    agent = ToolUsingAgent()
    trace = agent.run("Explain quantum gravity.")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert len(trace.steps) == 1
    assert trace.verified_facts["notes_match_count"] == 0
    assert "unsupported" in trace.final_conclusion.lower() or "no lecture notes" in trace.final_conclusion.lower()


# =============================================================================
# 7. Lab 1 End-to-End Clarification Flow
# =============================================================================
def test_lab1_clarification_end_to_end(client):
    """Verify 'Organize my Agentic AI Chapter 1 learning material.' asks at least 2 questions."""
    client._use_session("FACULTY")
    resp = client.post(
        "/api/lab1/clarify",
        json={"raw_prompt": "Organize my Agentic AI Chapter 1 learning material."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    payload = data["data"]
    assert payload["questions_count"] >= 2
    assert len(payload["questions"]) >= 2
    for q in payload["questions"]:
        assert len(q["suggested_options"]) >= 2
        assert q["question_text"]


# =============================================================================
# 8. Lab 1 End-to-End Plan Generation & Revision
# =============================================================================
def test_lab1_plan_generation_and_revision_end_to_end(client):
    """Verify plan synthesis for 26ECAC401 and subsequent immutable revision with structured diffs."""
    client._use_session("FACULTY")
    # Step 1: Clarify
    raw_prompt = "Organize my Agentic AI Chapter 1 learning material."
    clarify_resp = client.post("/api/lab1/clarify", json={"raw_prompt": raw_prompt})
    questions = clarify_resp.json()["data"]["questions"]

    # Step 2: Answer
    answered = []
    for q in questions:
        q["selected_option"] = q["suggested_options"][0]
        answered.append(q)

    # Step 3: Generate
    gen_resp = client.post(
        "/api/lab1/generate",
        json={
            "request_id": "req-regression-test",
            "original_prompt": raw_prompt,
            "course_code_hint": CANONICAL_COURSE_CODE,
            "answers": answered,
        },
    )
    assert gen_resp.status_code == 200
    plan_v1 = gen_resp.json()["data"]
    assert plan_v1["version"] == "1.0"
    assert plan_v1["course_code"] == CANONICAL_COURSE_CODE
    assert len(plan_v1["materials_and_notes"]) >= 1
    assert len(plan_v1["assignments"]) == 0
    assert len(plan_v1["grade_breakdown"]) == 0
    assert "assignments" in plan_v1["unestablished_fields"]
    assert "grade_breakdown" in plan_v1["unestablished_fields"]

    # Step 4: Revise
    rev_resp = client.post(
        "/api/lab1/revise",
        json={
            "plan_id": plan_v1["plan_id"],
            "revision_prompt": "Add one more section covering ReAct and keep the existing material.",
        },
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()["data"]
    assert rev_data["previous_version"] == "1.0"
    assert rev_data["current_version"] == "1.1"
    assert len(rev_data["structured_diffs"]) >= 1

    # Step 5: Verify immutability of v1.0 in history
    hist_resp = client.get(f"/api/lab1/history/{plan_v1['plan_id']}")
    assert hist_resp.status_code == 200
    history = hist_resp.json()["data"]
    versions = [p["version"] for p in history["versions"]]
    assert "1.0" in versions
    assert "1.1" in versions


# =============================================================================
# 9. Lab 2 Anti-Hallucination & Error Isolation Regressions
# =============================================================================
def test_lab2_unknown_course_cs101_returns_execution_error_and_zero_verified_facts():
    """Verify that unknown course queries (CS101) return EXECUTION_ERROR and zero verified facts."""
    agent = ToolUsingAgent()
    trace = agent.run("Check CS101 syllabus", course_id="CS101")
    assert trace.status == ToolExecutionStatus.EXECUTION_ERROR
    assert len(trace.verified_facts) == 0
    assert "CS101" in trace.final_conclusion
    assert "was not found" in trace.final_conclusion or "Unable to complete audit" in trace.final_conclusion


def test_lab2_unestablished_ta_policy_returns_execution_error_and_zero_verified_facts():
    """Verify that unestablished TA policy query returns EXECUTION_ERROR and zero verified facts."""
    agent = ToolUsingAgent()
    trace = agent.run("What is the official TA staffing ratio for 26ECAC401?")
    assert trace.status == ToolExecutionStatus.EXECUTION_ERROR
    assert len(trace.verified_facts) == 0
    assert "not established" in trace.final_conclusion.lower() or "unable to complete audit" in trace.final_conclusion.lower()


def test_lab2_canonical_syllabus_contains_all_four_chapters():
    """Verify canonical syllabus returns all 4 chapters (Chapters 1 to 4)."""
    agent = ToolUsingAgent()
    trace = agent.run("Retrieve 26ECAC401 syllabus and verify established course chapters and topics.")
    assert trace.status == ToolExecutionStatus.SUCCESS
    assert "modules" in trace.verified_facts
    modules = trace.verified_facts["modules"]
    assert len(modules) == 4
    chapters = {m["chapter"] for m in modules}
    assert chapters == {1, 2, 3, 4}
    assert any("Foundations" in m["title"] for m in modules)
    assert any("Frameworks" in m["title"] for m in modules)
    assert any("Multi-Agent" in m["title"] for m in modules)
    assert any("Safety" in m["title"] for m in modules)


# =============================================================================
# 10. Lab 1 Revision Quality & Grounding Regressions
# =============================================================================
def test_lab1_invalid_revision_prompt_rejected_safely(client):
    """Verify non-actionable or ambiguous revision prompt is rejected safely without traceback."""
    client._use_session("FACULTY")
    # Create plan
    resp = client.post("/api/lab1/clarify", json={"raw_prompt": "Organize my Agentic AI Chapter 1 learning material."})
    questions = resp.json()["data"]["questions"]
    for q in questions:
        q["selected_option"] = q["suggested_options"][0]

    gen_resp = client.post(
        "/api/lab1/generate",
        json={
            "request_id": "req-invalid-rev-test",
            "original_prompt": "Organize my Agentic AI Chapter 1 learning material.",
            "answers": questions,
        },
    )
    plan = gen_resp.json()["data"]

    # Submit non-actionable revision
    rev_resp = client.post(
        "/api/lab1/revise",
        json={
            "plan_id": plan["plan_id"],
            "revision_prompt": "Make this course cooler and more exciting.",
        },
    )
    assert rev_resp.status_code == 200
    res_data = rev_resp.json()
    assert res_data["success"] is False
    assert res_data["error"] is not None
    assert res_data["error"]["code"] == "VALIDATION_ERROR"
    assert "Unsupported or ambiguous" in res_data["error"]["message"]


def test_lab1_diff_descriptions_do_not_contain_week_none(client):
    """Verify section-based plan revision produces clean diff descriptions without 'Week None'."""
    client._use_session("FACULTY")
    resp = client.post("/api/lab1/clarify", json={"raw_prompt": "Organize my Agentic AI Chapter 1 learning material."})
    questions = resp.json()["data"]["questions"]
    for q in questions:
        q["selected_option"] = q["suggested_options"][0]

    gen_resp = client.post(
        "/api/lab1/generate",
        json={
            "request_id": "req-no-week-none-test",
            "original_prompt": "Organize my Agentic AI Chapter 1 learning material.",
            "answers": questions,
        },
    )
    plan = gen_resp.json()["data"]
    assert plan["duration_weeks"] is None

    rev_resp = client.post(
        "/api/lab1/revise",
        json={
            "plan_id": plan["plan_id"],
            "revision_prompt": "Add one more section covering ReAct and keep the existing material.",
        },
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()["data"]
    diffs = rev_data["structured_diffs"]
    assert len(diffs) >= 1
    for d in diffs:
        assert "Week None" not in d["change_description"]
        assert "None" not in d["change_description"]


def test_lab1_user_provided_duration_plan_provenance(client):
    """Verify user-provided duration (6 weeks) is distinguished from official course duration."""
    client._use_session("FACULTY")
    resp = client.post("/api/lab1/clarify", json={"raw_prompt": "Create a 6-week study plan for Agentic AI."})
    questions = resp.json()["data"]["questions"]
    for q in questions:
        q["selected_option"] = q["suggested_options"][0]

    gen_resp = client.post(
        "/api/lab1/generate",
        json={
            "request_id": "req-6week-test",
            "original_prompt": "Create a 6-week study plan for Agentic AI.",
            "answers": questions,
        },
    )
    plan = gen_resp.json()["data"]
    assert plan["duration_weeks"] == 6
    assert plan["provenance_summary"]["duration_weeks"] == "USER_PROVIDED"
    assert "official course duration" not in plan["description"].lower()
    assert len(plan["materials_and_notes"]) == 6
