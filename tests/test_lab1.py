"""Comprehensive unit and integration tests for Lab 1 (Clarify -> Plan -> Revise)."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from tests.conftest import _test_session
from app.labs.lab1.gap_analyzer import gap_analyzer
from app.labs.lab1.plan_generator import plan_generator
from app.labs.lab1.revision_engine import revision_engine
from app.labs.lab1.validator import plan_validator
from app.data.repository import course_repo
from app.models.lab1_models import (
    FacultyCourseRequest,
    ClarificationSubmission,
    RevisionRequest,
    CourseWorkspacePlan,
    MissingInfoCategory,
)


@pytest.mark.asyncio
async def test_gap_analysis_detects_missing_info_and_min_two_questions():
    """Verify that gap analysis inspects vague prompts and generates >= 2 clarification questions."""
    vague_request = FacultyCourseRequest(
        raw_prompt="I want to create an Agentic AI course covering Chapter 1 foundations and Chapter 2 tools for 80 students with labs.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(vague_request)
    
    assert len(questions) >= 2, f"Expected at least 2 questions, got {len(questions)}"
    for q in questions:
        assert q.question_id.startswith("q-")
        assert len(q.question_text) > 10
        assert len(q.suggested_options) >= 2
        assert len(q.rationale) > 5


@pytest.mark.asyncio
async def test_plan_generator_produces_three_core_pillars():
    """Verify that PlanGenerator produces a CourseWorkspacePlan strictly centered on materials, assignments, and grades."""
    vague_request = FacultyCourseRequest(
        raw_prompt="Foundations of Agentic AI and Tool Integration for 80 students with weekly labs.",
        course_title_hint="26ECAC401",
    )
    questions = gap_analyzer.analyze(vague_request)
    
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="test-req-1",
        original_prompt=vague_request.raw_prompt,
        course_code_hint="26ECAC401",
        answers=questions,
    )

    plan = plan_generator.generate(submission)

    # Core Plan assertions
    assert isinstance(plan, CourseWorkspacePlan)
    assert plan.version == "1.0"
    assert plan.course_code == "26ECAC401"
    assert plan.duration_weeks in [10, 12, 15]

    # Pillar 1: Notes & Materials
    assert len(plan.materials_and_notes) == plan.duration_weeks
    for mat in plan.materials_and_notes:
        assert mat.week >= 1
        assert len(mat.topics) >= 1
        assert len(mat.reading_materials) >= 1
        assert len(mat.lecture_notes_summary) >= 10

    # Pillar 2: Assignments & Labs
    assert len(plan.assignments) >= 3
    for asgn in plan.assignments:
        assert asgn.assignment_id
        assert asgn.title
        assert asgn.due_week <= plan.duration_weeks
        assert len(asgn.deliverables) >= 1
        assert asgn.max_points > 0

    # Pillar 3: Grades Breakdown
    assert len(plan.grade_breakdown) >= 3
    total_weight = sum(item.weight_percentage for item in plan.grade_breakdown)
    assert abs(total_weight - 100.0) < 0.01, f"Grade breakdown must sum to 100%, got {total_weight}%"


@pytest.mark.asyncio
async def test_revision_engine_increments_version_and_computes_exact_diffs():
    """Verify that revision creates version 1.1, computes exact structured diffs, and preserves previous versions."""
    vague_request = FacultyCourseRequest(
        raw_prompt="Design a 10-week Python programming course for 100 undergrads.",
    )
    questions = gap_analyzer.analyze(vague_request)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="test-req-2",
        original_prompt=vague_request.raw_prompt,
        answers=questions,
    )
    plan_v1 = plan_generator.generate(submission)
    course_repo.save_initial_plan(plan_v1)

    rev_req = RevisionRequest(
        plan_id=plan_v1.plan_id,
        revision_prompt="Add an AI ethics and algorithmic bias module to Week 5, add peer code review to assignments, and adjust capstone project weight to 35%.",
    )

    revision_response = revision_engine.revise(plan_v1, rev_req)
    course_repo.save_revised_plan(revision_response.revised_plan, revision_response)

    assert revision_response.previous_version == "1.0"
    assert revision_response.current_version == "1.1"
    assert revision_response.revised_plan.version == "1.1"

    assert len(revision_response.structured_diffs) >= 2
    sections_modified = {d.section for d in revision_response.structured_diffs}
    assert "materials_and_notes" in sections_modified or "grade_breakdown" in sections_modified or "assignments" in sections_modified

    retrieved_v1 = course_repo.get_plan_version(plan_v1.plan_id, "1.0")
    retrieved_v1_1 = course_repo.get_plan_version(plan_v1.plan_id, "1.1")
    latest_plan = course_repo.get_latest_plan(plan_v1.plan_id)

    assert retrieved_v1 is not None
    assert retrieved_v1.version == "1.0"
    assert retrieved_v1_1 is not None
    assert retrieved_v1_1.version == "1.1"
    assert latest_plan.version == "1.1"

    history = course_repo.get_plan_history(plan_v1.plan_id)
    assert len(history.versions) == 2
    assert len(history.revisions) == 1


@pytest.mark.asyncio
async def test_fastapi_lab1_full_api_workflow():
    """Integration test verifying end-to-end HTTP API contracts for Lab 1."""
    transport = ASGITransport(app=app)
    csrf_token = "test-only-csrf-token"
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Origin": "http://testserver", "X-CSRF-Token": csrf_token},
        cookies={
            "courseagent_session": _test_session("FACULTY"),
            "courseagent_csrf": csrf_token,
        },
    ) as client:
        # 1. POST /api/lab1/clarify
        clarify_res = await client.post(
            "/api/lab1/clarify",
            json={"raw_prompt": "I need a Distributed Systems syllabus covering Raft consensus in Go for 60 students."},
        )
        assert clarify_res.status_code == 200
        c_body = clarify_res.json()
        assert c_body["success"] is True
        assert "questions" in c_body["data"]
        questions = c_body["data"]["questions"]
        assert len(questions) >= 2

        # 2. POST /api/lab1/generate
        for q in questions:
            q["selected_option"] = q["suggested_options"][0]

        generate_res = await client.post(
            "/api/lab1/generate",
            json={
                "request_id": "api-test-req",
                "original_prompt": "I need an Agentic AI course covering Chapter 1 foundations and Chapter 2 tools for 60 students.",
                "course_code_hint": "26ECAC401",
                "answers": questions,
            },
        )
        assert generate_res.status_code == 200
        g_body = generate_res.json()
        assert g_body["success"] is True
        plan = g_body["data"]
        plan_id = plan["plan_id"]
        assert plan["version"] == "1.0"
        assert len(plan["materials_and_notes"]) >= 10
        assert len(plan["assignments"]) >= 3
        assert len(plan["grade_breakdown"]) >= 3

        # 3. POST /api/lab1/revise
        revise_res = await client.post(
            "/api/lab1/revise",
            json={
                "plan_id": plan_id,
                "revision_prompt": "Make final project weight 35% and add a fault injection lab in Week 8.",
            },
        )
        assert revise_res.status_code == 200
        r_body = revise_res.json()
        assert r_body["success"] is True
        rev_data = r_body["data"]
        assert rev_data["previous_version"] == "1.0"
        assert rev_data["current_version"] == "1.1"
        assert len(rev_data["structured_diffs"]) >= 1

        # 4. GET /api/lab1/history/{plan_id}
        history_res = await client.get(f"/api/lab1/history/{plan_id}")
        assert history_res.status_code == 200
        h_body = history_res.json()
        assert h_body["success"] is True
        assert len(h_body["data"]["versions"]) == 2
        assert len(h_body["data"]["revisions"]) == 1

        # 5. GET /api/lab1/plan/{plan_id}?version=1.0 and version=1.1
        p1_res = await client.get(f"/api/lab1/plan/{plan_id}?version=1.0")
        assert p1_res.status_code == 200
        assert p1_res.json()["data"]["version"] == "1.0"

        p2_res = await client.get(f"/api/lab1/plan/{plan_id}?version=1.1")
        assert p2_res.status_code == 200
        assert p2_res.json()["data"]["version"] == "1.1"


@pytest.mark.asyncio
async def test_system_status_and_scenarios_endpoints():
    """Verify system diagnostics and pre-loaded evaluator scenarios."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        status_res = await client.get("/api/system/status")
        assert status_res.status_code == 200
        s_data = status_res.json()["data"]
        assert s_data["total_labs_count"] == 14
        assert s_data["active_labs_count"] >= 1

        scenarios_res = await client.get("/api/system/scenarios")
        assert scenarios_res.status_code == 200
        scenarios = scenarios_res.json()["data"]
        assert len(scenarios) >= 3


# =========================================================================
# RIGOROUS REAL BEHAVIOR TESTS FOR LAB 1 REVISION PIPELINE
# =========================================================================

@pytest.mark.asyncio
async def test_unseen_compound_revision_modifies_structure_and_no_fallback():
    """TEST 1: Unseen compound revision must alter duration, assignments, grade weights, and NOT use description fallback."""
    # 1. Generate standard 10-week plan v1.0
    req = FacultyCourseRequest(
        raw_prompt="I want to organize a course for undergraduate students covering Python, machine learning, and practical projects.",
    )
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    submission = ClarificationSubmission(
        request_id="test-compound-1",
        original_prompt=req.raw_prompt,
        answers=questions,
    )
    plan_v1 = plan_generator.generate(submission)
    plan_v1.duration_weeks = 10  # Ensure starting from 10 weeks
    plan_v1.materials_and_notes = plan_v1.materials_and_notes[:10]
    initial_desc = plan_v1.description
    initial_asgn_count = len(plan_v1.assignments)
    
    # Locate project weight in v1.0
    initial_proj_weight = next(g.weight_percentage for g in plan_v1.grade_breakdown if "project" in g.category.lower() or "capstone" in g.category.lower())

    course_repo.save_initial_plan(plan_v1)

    # 2. Execute unseen compound revision
    unseen_prompt = "Change the course to 12 weeks, add one additional programming lab, and increase the final project weight by 5 percentage points."
    rev_req = RevisionRequest(plan_id=plan_v1.plan_id, revision_prompt=unseen_prompt)
    rev_res = revision_engine.revise(plan_v1, rev_req)
    revised_plan = rev_res.revised_plan
    course_repo.save_revised_plan(revised_plan, rev_res)

    # Assertions:
    # 1. Duration changed to 12 weeks
    assert revised_plan.duration_weeks == 12
    assert len(revised_plan.materials_and_notes) == 12

    # 2. Assignment structure changed (added 1 programming lab)
    assert len(revised_plan.assignments) == initial_asgn_count + 1
    added_lab = next((a for a in revised_plan.assignments if "LAB_PRACTICAL" in a.assignment_id), None)
    assert added_lab is not None

    # 3. Final project weight increased by 5 percentage points
    revised_proj_weight = next(g.weight_percentage for g in revised_plan.grade_breakdown if "project" in g.category.lower() or "capstone" in g.category.lower())
    assert revised_proj_weight == initial_proj_weight + 5.0

    # 4. Grade total is strictly 100.0%
    total_grade = sum(g.weight_percentage for g in revised_plan.grade_breakdown)
    assert abs(total_grade - 100.0) < 0.01

    # 5. Version changed from 1.0 to 1.1
    assert rev_res.previous_version == "1.0"
    assert rev_res.current_version == "1.1"
    assert revised_plan.version == "1.1"

    # 6. Description was NOT used as a fallback
    assert revised_plan.description == initial_desc
    assert "[Revised:" not in revised_plan.description

    # 7. Diff contains actual field paths
    diff_paths = [d.path for d in rev_res.structured_diffs]
    assert "duration_weeks" in diff_paths
    assert any("assignments" in p for p in diff_paths)
    assert any("grade_breakdown" in p for p in diff_paths)


@pytest.mark.asyncio
async def test_relative_duration_extension():
    """TEST 2: 'Please extend the course by two weeks' must dynamically expand duration and weekly materials."""
    req = FacultyCourseRequest(raw_prompt="Design a 10-week Python and algorithms course.")
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    plan_v1 = plan_generator.generate(ClarificationSubmission(
        request_id="test-ext-1",
        original_prompt=req.raw_prompt,
        answers=questions,
    ))
    plan_v1.duration_weeks = 10
    plan_v1.materials_and_notes = plan_v1.materials_and_notes[:10]

    rev_res = revision_engine.revise(plan_v1, RevisionRequest(
        plan_id=plan_v1.plan_id,
        revision_prompt="Please extend the course by two weeks.",
    ))

    assert rev_res.revised_plan.duration_weeks == 12
    assert len(rev_res.revised_plan.materials_and_notes) == 12
    assert rev_res.revised_plan.materials_and_notes[-1].week == 12
    assert any(d.path == "duration_weeks" and d.new_value == 12 for d in rev_res.structured_diffs)


@pytest.mark.asyncio
async def test_relative_grade_weight_raise():
    """TEST 3: 'Raise the capstone weighting by 5 percentage points' must update weight and rebalance other categories."""
    req = FacultyCourseRequest(raw_prompt="Design an advanced systems engineering curriculum.")
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    plan_v1 = plan_generator.generate(ClarificationSubmission(
        request_id="test-weight-1",
        original_prompt=req.raw_prompt,
        answers=questions,
    ))

    initial_capstone_wt = next(g.weight_percentage for g in plan_v1.grade_breakdown if "project" in g.category.lower() or "capstone" in g.category.lower())

    rev_res = revision_engine.revise(plan_v1, RevisionRequest(
        plan_id=plan_v1.plan_id,
        revision_prompt="Raise the capstone weighting by 5 percentage points.",
    ))

    revised_capstone_wt = next(g.weight_percentage for g in rev_res.revised_plan.grade_breakdown if "project" in g.category.lower() or "capstone" in g.category.lower())
    assert revised_capstone_wt == initial_capstone_wt + 5.0

    total_weight = sum(g.weight_percentage for g in rev_res.revised_plan.grade_breakdown)
    assert abs(total_weight - 100.0) < 0.01


@pytest.mark.asyncio
async def test_ambiguous_revision_rejected_no_fallback():
    """TEST 4: 'Make the course more exciting' must be rejected with ValueError and NOT create a fake revision or mutate description."""
    req = FacultyCourseRequest(raw_prompt="Introductory Python programming.")
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    plan_v1 = plan_generator.generate(ClarificationSubmission(
        request_id="test-ambig-1",
        original_prompt=req.raw_prompt,
        answers=questions,
    ))
    initial_desc = plan_v1.description

    # Assert that ambiguous request raises ValueError
    with pytest.raises(ValueError) as exc_info:
        revision_engine.revise(plan_v1, RevisionRequest(
            plan_id=plan_v1.plan_id,
            revision_prompt="Make the course more exciting.",
        ))

    err_msg = str(exc_info.value)
    assert "Unsupported or ambiguous revision request" in err_msg
    assert "No actionable course modifications could be detected" in err_msg

    # Verify v1 description is intact and untouched
    assert plan_v1.description == initial_desc


@pytest.mark.asyncio
async def test_invalid_grade_distribution_rejected():
    """TEST 5: Grade distributions that do not sum to 100% must be rejected by validator."""
    req = FacultyCourseRequest(raw_prompt="Introductory Python programming.")
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    plan_v1 = plan_generator.generate(ClarificationSubmission(
        request_id="test-invalid-grade",
        original_prompt=req.raw_prompt,
        answers=questions,
    ))

    # Artificially alter grade weights to sum to 105%
    plan_v1.grade_breakdown[0].weight_percentage += 5.0
    with pytest.raises(ValueError) as exc_info:
        plan_validator.validate(plan_v1)

    assert "Invalid grade distribution" in str(exc_info.value)
    assert "Discrepancy: +5.0 percentage points" in str(exc_info.value)


@pytest.mark.asyncio
async def test_immutability_preservation_after_revision():
    """TEST 6: Verify that v1.0 stored in repository is completely unchanged after v1.1 is generated."""
    req = FacultyCourseRequest(raw_prompt="Design a 10-week Python and data science course.")
    questions = gap_analyzer.analyze(req)
    for q in questions:
        q.selected_option = q.suggested_options[0]

    plan_v1 = plan_generator.generate(ClarificationSubmission(
        request_id="test-immutability",
        original_prompt=req.raw_prompt,
        answers=questions,
    ))
    plan_v1.duration_weeks = 10
    plan_v1.materials_and_notes = plan_v1.materials_and_notes[:10]
    course_repo.save_initial_plan(plan_v1)

    # Make revision to 12 weeks
    rev_res = revision_engine.revise(plan_v1, RevisionRequest(
        plan_id=plan_v1.plan_id,
        revision_prompt="Change the course to 12 weeks and add one additional programming lab.",
    ))
    course_repo.save_revised_plan(rev_res.revised_plan, rev_res)

    # Retrieve v1.0 and v1.1 from repo
    v1_stored = course_repo.get_plan_version(plan_v1.plan_id, "1.0")
    v1_1_stored = course_repo.get_plan_version(plan_v1.plan_id, "1.1")

    # Assert v1.0 is unchanged
    assert v1_stored.version == "1.0"
    assert v1_stored.duration_weeks == 10
    assert len(v1_stored.materials_and_notes) == 10
    assert len(v1_stored.assignments) == len(plan_v1.assignments)

    # Assert v1.1 contains the modifications
    assert v1_1_stored.version == "1.1"
    assert v1_1_stored.duration_weeks == 12
    assert len(v1_1_stored.materials_and_notes) == 12
    assert len(v1_1_stored.assignments) == len(plan_v1.assignments) + 1
