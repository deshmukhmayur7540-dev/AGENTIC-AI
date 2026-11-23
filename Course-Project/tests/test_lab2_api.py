"""API integration tests for Lab 2 endpoints using FastAPI TestClient."""

import pytest
from app.main import app
from tests.conftest import AuthTestClient

client = AuthTestClient(app)


def test_api_lab2_query_syllabus_structure():
    response = client.post(
        "/api/lab2/query",
        json={"request": "Audit 26ECAC401 syllabus and course modules"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["error"] is None

    trace = data["data"]
    assert trace["status"] == "SUCCESS"
    assert trace["user_request"] != ""
    assert len(trace["steps"]) == 1
    assert trace["verified_facts"]["course_id"] == "26ECAC401"
    assert "Agentic AI" in trace["final_conclusion"]
    assert "Foundations of Agentic AI" in trace["final_conclusion"]


def test_api_lab2_query_notes_search():
    response = client.post(
        "/api/lab2/query",
        json={"request": "Search 26ECAC401 course notes for ReAct"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    trace = data["data"]
    assert len(trace["steps"]) == 1
    assert trace["verified_facts"]["notes_match_count"] >= 1
    assert "ReAct" in trace["final_conclusion"]


def test_api_lab2_query_requires_selected_assignment_for_ordinal_prompt():
    response = client.post(
        "/api/lab2/query",
        json={"request": "Show me what the rubric says about code quality for Assignment 1 in 26ECAC401."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    trace = data["data"]
    assert trace["status"] == "VALIDATION_ERROR"
    assert len(trace["steps"]) == 1
    assert trace["steps"][0]["tool_call"]["status"] == "VALIDATION_ERROR"
    assert "assignment_id" in trace["final_conclusion"].lower()
    assert "CS101" not in trace["final_conclusion"]


def test_api_lab2_query_reads_selected_assignment_rubric_from_database():
    response = client.post(
        "/api/lab2/query",
        json={
            "request": "Show the rubric for this assignment in 26ECAC401.",
            "course_id": "26ECAC401",
            "assignment_id": "lab1",
        },
    )
    assert response.status_code == 200
    trace = response.json()["data"]
    assert trace["status"] == "SUCCESS"
    assert trace["verified_facts"]["assignment_id"] == "lab1"
    assert any(
        criterion["criterion_name"] == "Structured Plan Synthesis"
        for criterion in trace["verified_facts"]["rubric_criteria"]
    )
    assert trace["steps"][0]["tool_call"]["output_data"]["evidence"] == "Persisted course rubric catalog"


def test_api_lab2_query_reads_selected_assignment_spec_from_database():
    response = client.post(
        "/api/lab2/query",
        json={
            "request": "Show the assignment specification and deliverables.",
            "course_id": "26ECAC401",
            "assignment_id": "lab1",
        },
    )
    assert response.status_code == 200
    trace = response.json()["data"]
    assert trace["status"] == "SUCCESS"
    assert trace["verified_facts"]["assignment_spec"]["assignment_id"] == "lab1"
    assert trace["verified_facts"]["assignment_spec"]["source"] == "Persisted course assignment catalog"


def test_api_lab2_query_unknown_course():
    response = client.post(
        "/api/lab2/query",
        json={"request": "Audit UNKNOWN999 syllabus and topics"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    trace = data["data"]
    assert trace["status"] == "EXECUTION_ERROR"
    assert len(trace["steps"]) == 1
    assert trace["steps"][0]["tool_call"]["status"] == "EXECUTION_ERROR"
    assert trace["verified_facts"] == {}
    assert "not found" in trace["final_conclusion"].lower() or "unable" in trace["final_conclusion"].lower()
    assert "CS101" not in trace["final_conclusion"]


def test_api_lab2_tools_list():
    response = client.get("/api/lab2/tools")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    tools = data["data"]
    assert len(tools) >= 9
    tool_names = [t["name"] for t in tools]
    assert "read_course_syllabus" in tool_names
    assert "get_ta_policy" in tool_names
    assert "compute_workload_hours" in tool_names


def test_api_lab2_tools_direct_execute():
    response = client.post(
        "/api/lab2/tools/execute",
        json={"tool_name": "calculate_grade_breakdown_total", "parameters": {"weights": [30, 20, 20, 30]}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    record = data["data"]
    assert record["status"] == "SUCCESS"
    assert record["output_data"]["total_percentage"] == 100.0
    assert record["output_data"]["is_valid"] is True


def test_api_lab2_scenarios():
    response = client.get("/api/lab2/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    scenarios = data["data"]
    assert len(scenarios) >= 6
    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert "lab2-notes-react-reasoning" in scenario_ids
    assert "lab2-rubric-non-hallucination" in scenario_ids
    assert "lab2-syllabus-inspection" in scenario_ids


def test_api_system_status_reports_lab2_active():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    catalog = data["data"]["labs_catalog"]
    lab2_meta = next((l for l in catalog if l["lab_id"] == "lab2"), None)
    assert lab2_meta is not None
    assert lab2_meta["is_active"] is True
