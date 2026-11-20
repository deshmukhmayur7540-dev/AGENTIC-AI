"""API endpoint tests for Lab 7: Agentic Node Graph."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_api_lab7_run_graph(client):
    """POST /api/lab7/run initiates graph and advances to faculty approval gate."""
    payload = {
        "user_request": "Structure 26ECAC401 course workspace",
        "course_id": "26ECAC401",
        "target_weeks": 12,
    }
    resp = client.post(
        "/api/lab7/run",
        json=payload,
        headers={"X-User-Role": "FACULTY"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "WAITING_APPROVAL"
    run_id = body["data"]["run_id"]

    # Check state endpoint
    st_resp = client.get(
        f"/api/lab7/state/{run_id}",
        headers={"X-User-Role": "FACULTY"},
    )
    assert st_resp.status_code == 200
    st_data = st_resp.json()["data"]["state"]
    assert len(st_data["execution_history"]) >= 8

    # Submit approval
    app_resp = client.post(
        f"/api/lab7/approve/{run_id}",
        json={"approved": True, "comments": "Accreditation approved", "decision_by": "prof_evaluator"},
        headers={"X-User-Role": "FACULTY"},
    )
    assert app_resp.status_code == 200
    app_data = app_resp.json()["data"]["state"]
    assert app_data["status"] == "COMPLETED"
    assert app_data["published_workspace"] is not None
    assert app_data["approval_actor_user_id"] == "test-faculty"


def test_api_lab7_requires_faculty_and_course_access(client):
    payload = {
        "user_request": "Private course workspace",
        "course_id": "26ECAC401",
        "target_weeks": 12,
    }

    assert client.post("/api/lab7/run", json=payload).status_code == 403
    assert client.post(
        "/api/lab7/run",
        json={**payload, "course_id": "OTHER-COURSE"},
        headers={"X-User-Role": "FACULTY"},
    ).status_code == 403

    response = client.post(
        "/api/lab7/run",
        json=payload,
        headers={"X-User-Role": "FACULTY"},
    )
    run_id = response.json()["data"]["run_id"]

    assert client.get(
        f"/api/lab7/state/{run_id}",
        headers={"X-User-Role": "STUDENT"},
    ).status_code == 403
    assert client.post(
        "/api/lab7/step",
        json={"run_id": run_id},
        headers={"X-User-Role": "STUDENT"},
    ).status_code == 403
    assert client.get(
        f"/api/lab7/state/{run_id}",
        headers={"X-User-Role": "FACULTY"},
    ).status_code == 200


def test_api_lab7_topology(client):
    """GET /api/lab7/topology returns node graph topology."""
    resp = client.get("/api/lab7/topology")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["nodes"]) == 10
    assert len(body["data"]["edges"]) >= 8


def test_api_lab7_scenarios(client):
    """GET /api/lab7/scenarios returns predefined evaluator scenarios."""
    resp = client.get("/api/lab7/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 3
