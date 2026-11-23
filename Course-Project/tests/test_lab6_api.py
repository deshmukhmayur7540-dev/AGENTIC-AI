"""API endpoint tests for Lab 6: Controlled Agent Runtime."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    test_client = AuthTestClient(app)
    test_client._use_session("FACULTY")
    return test_client


def test_api_lab6_start_and_status(client):
    """POST /api/lab6/run creates a run and GET /run/{id} returns state."""
    resp = client.post("/api/lab6/run", json={"task_description": "Build 26ECAC401 course", "course_id": "26ECAC401"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    run_id = body["data"]["run"]["run_id"]
    assert body["data"]["run"]["owner_user_id"] == "test-faculty"

    # Check status
    st_resp = client.get(f"/api/lab6/run/{run_id}")
    assert st_resp.status_code == 200
    assert st_resp.json()["data"]["run"]["state"] == "INITIALIZED"
    assert st_resp.json()["data"]["run"]["course_id"] == "26ECAC401"


def test_api_lab6_step_and_approval_flow(client):
    """Test step execution, approval gate suspension, and approval submission via API."""
    resp = client.post("/api/lab6/run", json={"task_description": "Compile and publish course"})
    run_id = resp.json()["data"]["run"]["run_id"]

    # Step 1
    s1 = client.post(f"/api/lab6/run/{run_id}/step")
    assert s1.status_code == 200
    assert s1.json()["data"]["status"] == "SUCCESS"
    audit = client.get(f"/api/lab6/run/{run_id}/audit").json()["data"]
    assert audit[0]["actor_user_id"] == "test-faculty"
    assert audit[0]["actor_role"] == "FACULTY"

    # Step 2
    s2 = client.post(f"/api/lab6/run/{run_id}/step")
    assert s2.json()["data"]["status"] == "SUCCESS"

    # Step 3
    s3 = client.post(f"/api/lab6/run/{run_id}/step")
    assert s3.json()["data"]["status"] == "SUCCESS"

    # Step 4 (Consequential -> Approval gate)
    s4 = client.post(f"/api/lab6/run/{run_id}/step")
    s4_data = s4.json()["data"]
    assert s4_data["status"] == "WAITING_APPROVAL"
    gate_id = s4_data["gate_id"]

    # Submit approval
    app_resp = client.post(
        f"/api/lab6/run/{run_id}/approve",
        json={"gate_id": gate_id, "approved": True, "decision_by": "prof_faculty"},
        headers={"X-User-Role": "FACULTY"},
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["data"]["run"]["state"] == "RUNNING"


def test_api_lab6_crash_and_resume(client):
    """Test crash simulation and state resumption via API."""
    resp = client.post("/api/lab6/run", json={"task_description": "Crash test run"})
    run_id = resp.json()["data"]["run"]["run_id"]

    # Execute a step
    client.post(f"/api/lab6/run/{run_id}/step")

    # Simulate crash
    crash_resp = client.post(f"/api/lab6/run/{run_id}/crash")
    assert crash_resp.status_code == 200
    assert crash_resp.json()["data"]["status"] == "PAUSED"

    # Resume run
    res_resp = client.post(f"/api/lab6/run/{run_id}/resume")
    assert res_resp.status_code == 200
    assert res_resp.json()["data"]["status"] == "RESUMED"


def test_api_lab6_scenarios(client):
    """GET /api/lab6/scenarios returns predefined evaluator scenarios."""
    resp = client.get("/api/lab6/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 3


def test_lab6_runtime_routes_require_faculty_and_course_access(client):
    """Student sessions cannot start or inspect faculty runtime runs."""
    run_response = client.post("/api/lab6/run", json={"course_id": "26ECAC401"})
    assert run_response.status_code == 200
    run_id = run_response.json()["data"]["run"]["run_id"]

    denied_status = client.get(
        f"/api/lab6/run/{run_id}",
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert denied_status.status_code == 403
    denied_action = client.post(
        f"/api/lab6/run/{run_id}/step",
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert denied_action.status_code == 403

    unauthorized_course = client.post(
        "/api/lab6/run",
        json={"course_id": "99OTHER999"},
    )
    assert unauthorized_course.status_code == 403
