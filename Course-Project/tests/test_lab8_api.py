"""API endpoint tests for Lab 8: Parallel Swarm."""

import pytest
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_api_lab8_dispatch_full(client):
    """POST /api/lab8/dispatch runs 4-unit parallel swarm."""
    payload = {
        "course_id": "26ECAC401",
        "target_chapters": [1, 2, 3, 4],
    }
    resp = client.post("/api/lab8/dispatch", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "MERGED"
    assert data["total_workers"] == 4
    assert data["successful_workers"] == 4
    assert data["speedup_ratio"] > 0
    run_id = data["swarm_run_id"]

    # Check status endpoint
    st_resp = client.get(f"/api/lab8/status/{run_id}")
    assert st_resp.status_code == 200
    assert st_resp.json()["data"]["result"]["total_workers"] == 4


def test_api_lab8_dispatch_simulated_failure(client):
    """POST /api/lab8/dispatch with simulated failure returns PARTIAL_SUCCESS."""
    payload = {
        "course_id": "26ECAC401",
        "target_chapters": [1, 2, 3, 4],
        "simulate_worker_failure": 2,
    }
    resp = client.post("/api/lab8/dispatch", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "PARTIAL_SUCCESS"
    assert data["failed_workers"] == 1
    assert data["successful_workers"] == 3


def test_api_lab8_rejects_invalid_worker_selection(client):
    for chapters in ([], [1, 1], [5]):
        response = client.post(
            "/api/lab8/dispatch",
            json={"course_id": "26ECAC401", "target_chapters": chapters},
        )
        assert response.status_code == 422

    response = client.post(
        "/api/lab8/dispatch",
        json={
            "course_id": "26ECAC401",
            "target_chapters": [1],
            "simulate_worker_failure": 2,
        },
    )
    assert response.status_code == 422


def test_api_lab8_scenarios(client):
    """GET /api/lab8/scenarios returns predefined evaluator scenarios."""
    resp = client.get("/api/lab8/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 3
