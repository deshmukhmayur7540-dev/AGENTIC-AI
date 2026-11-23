"""Comprehensive tests verifying that Lab 1 is grounded strictly in actual Agentic AI notes.

Specifically validates:
1. Clarification loop produces >= 2 targeted questions on vague prompts.
2. Organizing Chapter 1 materials grounds strictly in Chapter 1 documents.
3. Anti-fabrication guarantees: Pure material prompts do NOT fabricate 10 weeks,
   5 deliverables, or 4 grading categories.
4. Unestablished fields are explicitly tracked in `unestablished_fields` and `provenance_summary`.
5. User-supplied parameters (e.g. 6-week duration, custom grade weights) are accepted
   with USER_PROVIDED provenance.
6. Course code strictly adheres to canonical 26ECAC401.
7. Revisions are immutable, bump version to 1.1, and produce exact structured diffs.
8. Section 1.6 Plan-Act-Observe-Revise and Section 1.8 ReAct are accurately grounded.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app
from tests.conftest import AuthTestClient
from app.core.constants import CANONICAL_COURSE_CODE, CANONICAL_COURSE_NAME
from app.labs.lab1.gap_analyzer import gap_analyzer
from app.labs.lab1.plan_generator import plan_generator
from app.labs.lab1.revision_engine import revision_engine
from app.labs.lab1.validator import plan_validator
from app.models.lab1_models import (
    FacultyCourseRequest,
    ClarificationSubmission,
    RevisionRequest,
    CourseWorkspacePlan,
    MissingInfoCategory,
)


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_clarification_loop_vague_prompt_returns_at_least_two_questions():
    """Verify that vague prompts yield >= 2 targeted clarification questions with options and rationales."""
    request = FacultyCourseRequest(
        raw_prompt="Organize my Agentic AI Chapter 1 learning material.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(request)

    assert len(questions) >= 2, f"Expected at least 2 questions, got {len(questions)}"
    for q in questions:
        assert q.question_id.startswith("q-")
        assert len(q.question_text) > 15
        assert len(q.suggested_options) >= 2
        assert len(q.rationale) > 10


def test_chapter_1_material_prompt_grounds_without_fabricating_structure():
    """Verify that 'Organize my Agentic AI Chapter 1 learning material' produces a grounded modular plan.

    Must NOT fabricate:
    - 10 weekly modules
    - 5 deliverables
    - 4 grading categories
    """
    request = FacultyCourseRequest(
        raw_prompt="Organize my Agentic AI Chapter 1 learning material.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="sub-grounding-001",
        original_prompt=request.raw_prompt,
        course_code_hint="26ECAC401",
        answers=questions[:2],
    )
    plan = plan_generator.generate(submission)

    # 1. Course Identity
    assert plan.course_code == "26ECAC401"
    assert plan.course_name == "Agentic AI"

    # 2. Duration: Not artificially set to 10 weeks
    assert plan.duration_weeks is None
    assert "duration_weeks" in plan.unestablished_fields
    assert plan.provenance_summary.get("duration_weeks") == "UNESTABLISHED"

    # 3. Grounded Materials: 8 core sections from Chapter 1 documents
    assert len(plan.materials_and_notes) == 8
    assert plan.provenance_summary.get("materials") == "COURSE_GROUNDED"

    # Check specific grounded topics from Chapter 1 notes
    all_topics = [t for m in plan.materials_and_notes for t in m.topics]
    assert any("Plan, Act, Observe, Revise" in t or "Plan–Act–Observe–Revise" in t for t in all_topics)
    assert any("Three Pillars of Agency" in t for t in all_topics)
    assert any("Evolution from Generative AI" in t for t in all_topics)
    assert any("ReAct" in t for t in all_topics)

    # 4. Anti-Fabrication: Assignments must NOT be fabricated
    assert len(plan.assignments) == 0, f"Expected 0 fabricated assignments, got {len(plan.assignments)}"
    assert "assignments" in plan.unestablished_fields
    assert plan.provenance_summary.get("assignments") == "UNESTABLISHED"

    # 5. Anti-Fabrication: Grade breakdown must NOT be fabricated
    assert len(plan.grade_breakdown) == 0, f"Expected 0 fabricated grade items, got {len(plan.grade_breakdown)}"
    assert "grade_breakdown" in plan.unestablished_fields
    assert plan.provenance_summary.get("grade_breakdown") == "UNESTABLISHED"


def test_section_1_6_plan_act_observe_revise_is_authoritative():
    """Verify Section 1.6 Plan-Act-Observe-Revise loop is explicitly represented with authoritative citation."""
    request = FacultyCourseRequest(raw_prompt="Organize my Agentic AI Chapter 1 learning material.")
    questions = gap_analyzer.analyze(request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="sub-sec-1-6",
        original_prompt=request.raw_prompt,
        answers=questions[:2],
    )
    plan = plan_generator.generate(submission)

    # Find the module covering Section 1.6
    sec_1_6_modules = [
        m for m in plan.materials_and_notes
        if "1.6" in m.source_section or "Plan" in m.title
    ]
    assert len(sec_1_6_modules) >= 1
    m16 = sec_1_6_modules[0]
    assert "Chapter1_Foundations_of_Agentic_AI.docx" in m16.source_document
    assert any("Plan, Act, Observe, Revise" in t or "Plan–Act–Observe–Revise" in t for t in m16.topics)
    assert "Stopping Conditions" in m16.topics[2] or "Stopping" in m16.topics[2]


def test_user_provided_duration_is_recorded_with_user_provided_provenance():
    """When the user explicitly requests a 6-week plan, duration is 6 and provenance is USER_PROVIDED."""
    request = FacultyCourseRequest(
        raw_prompt="Organize my Agentic AI Chapter 1 learning material into a 6-week study schedule.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="sub-6-week",
        original_prompt=request.raw_prompt,
        answers=questions[:2],
    )
    plan = plan_generator.generate(submission)

    assert plan.duration_weeks == 6
    assert plan.provenance_summary.get("duration_weeks") == "USER_PROVIDED"
    assert "duration_weeks" not in plan.unestablished_fields
    assert len(plan.materials_and_notes) == 6


def test_user_provided_grading_is_recorded_with_user_provided_provenance():
    """When the user explicitly asks for grading weights, grade breakdown is created with USER_PROVIDED provenance."""
    request = FacultyCourseRequest(
        raw_prompt="Create an Agentic AI course plan with 40% labs, 30% project, 20% midterm, 10% homework.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="sub-grading",
        original_prompt=request.raw_prompt,
        answers=questions[:2],
    )
    plan = plan_generator.generate(submission)

    assert len(plan.grade_breakdown) >= 1
    assert plan.provenance_summary.get("grade_breakdown") == "USER_PROVIDED"
    assert "grade_breakdown" not in plan.unestablished_fields
    total_weight = sum(item.weight_percentage for item in plan.grade_breakdown)
    assert abs(total_weight - 100.0) < 0.05


def test_modular_plan_revision_bumps_version_and_records_diffs():
    """Verify that revising a modular course plan increments version to 1.1 and computes diffs."""
    request = FacultyCourseRequest(raw_prompt="Organize my Agentic AI Chapter 1 learning material.")
    questions = gap_analyzer.analyze(request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="sub-rev-test",
        original_prompt=request.raw_prompt,
        answers=questions[:2],
    )
    plan_v1 = plan_generator.generate(submission)
    assert plan_v1.version == "1.0"

    rev_response = revision_engine.revise(
        plan_v1,
        RevisionRequest(
            plan_id=plan_v1.plan_id,
            revision_prompt="Add one more section covering ReAct and keep the existing material.",
        ),
    )

    assert rev_response.previous_version == "1.0"
    assert rev_response.current_version == "1.1"
    assert len(rev_response.structured_diffs) >= 1
    assert rev_response.revised_plan.version == "1.1"
    # Verify original plan_v1 object is unmodified (immutability)
    assert plan_v1.version == "1.0"


def test_api_lab1_full_grounding_workflow(client):
    """Full HTTP API integration test ensuring grounded non-fabrication over REST endpoints."""
    # 1. Clarify
    resp = client.post(
        "/api/lab1/clarify",
        json={"raw_prompt": "Organize my Agentic AI Chapter 1 learning material."},
        headers={"X-User-Role": "FACULTY"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["questions"]) >= 2

    # 2. Answer
    answered = []
    for q in data["questions"]:
        q["selected_option"] = q["suggested_options"][0]
        answered.append(q)

    # 3. Generate
    gen_resp = client.post(
        "/api/lab1/generate",
        json={
            "request_id": "api-grounding-test",
            "original_prompt": "Organize my Agentic AI Chapter 1 learning material.",
            "course_code_hint": "26ECAC401",
            "answers": answered,
        },
    )
    assert gen_resp.status_code == 200
    plan = gen_resp.json()["data"]

    assert plan["course_code"] == "26ECAC401"
    assert plan["duration_weeks"] is None
    assert len(plan["assignments"]) == 0
    assert len(plan["grade_breakdown"]) == 0
    assert "assignments" in plan["unestablished_fields"]
    assert "grade_breakdown" in plan["unestablished_fields"]
    assert len(plan["materials_and_notes"]) == 8

    # 4. Revise
    rev_resp = client.post(
        "/api/lab1/revise",
        json={
            "plan_id": plan["plan_id"],
            "revision_prompt": "Add one more section covering ReAct and keep the existing material.",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()["data"]
    assert rev_data["previous_version"] == "1.0"
    assert rev_data["current_version"] == "1.1"
    assert len(rev_data["structured_diffs"]) >= 1


def test_lab1_api_requires_faculty_and_enforces_course_scope():
    """Unauthenticated/Student users and out-of-scope course plans are denied."""
    anonymous = TestClient(app)
    assert anonymous.post(
        "/api/lab1/clarify",
        json={"raw_prompt": "Organize course materials."},
    ).status_code == 401

    student = AuthTestClient(app)
    assert student.post(
        "/api/lab1/clarify",
        json={"raw_prompt": "Organize course materials."},
    ).status_code == 403

    faculty = AuthTestClient(app)
    headers = {"X-User-Role": "FACULTY"}
    clarified = faculty.post(
        "/api/lab1/clarify",
        json={"raw_prompt": "Organize course materials."},
        headers=headers,
    )
    assert clarified.status_code == 200
    questions = clarified.json()["data"]["questions"]
    for question in questions:
        question["selected_option"] = question["suggested_options"][0]
    denied = faculty.post(
        "/api/lab1/generate",
        json={
            "request_id": "out-of-scope-lab1",
            "original_prompt": "Organize course materials.",
            "course_code_hint": "OTHER101",
            "answers": questions,
        },
    )
    assert denied.status_code == 403
