"""API endpoint tests for Lab 3: Reusable Skills."""

import pytest
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_api_lab3_list_skills(client):
    """GET /api/lab3/skills returns the list of registered skills with metadata."""
    resp = client.get("/api/lab3/skills")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    skills = body["data"]["skills"]
    assert len(skills) >= 3
    skill_names = [s["name"] for s in skills]
    assert "course_planning_skill" in skill_names
    assert "research_summary_skill" in skill_names
    assert "course_content_formatting_skill" in skill_names


def test_api_lab3_inspect_skill(client):
    """GET /api/lab3/skills/{name} returns input/output schemas."""
    resp = client.get("/api/lab3/skills/course_planning_skill")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    metadata = body["data"]["metadata"]
    assert metadata["name"] == "course_planning_skill"
    assert "properties" in metadata["input_schema"]


def test_api_lab3_direct_execute(client):
    """POST /api/lab3/execute runs a registered skill."""
    payload = {
        "skill_name": "course_planning_skill",
        "parameters": {
            "course_code": "26ECAC401",
            "target_weeks": 10,
        },
    }
    resp = client.post("/api/lab3/execute", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    exec_data = body["data"]
    assert exec_data["status"] == "SUCCESS"
    assert exec_data["output_data"]["total_weeks"] == 10


def test_api_lab3_agent_query(client):
    """POST /api/lab3/query routes natural language query to appropriate skill and returns normalised shape."""
    payload = {
        "query": "Research Chapter 2 LangGraph and MCP architectures",
    }
    resp = client.post("/api/lab3/query", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    # New normalised response shape (UI-compatible)
    assert "status" in data
    assert data["status"] == "SUCCESS"
    assert "skills_executed" in data
    assert len(data["skills_executed"]) >= 1
    skill = data["skills_executed"][0]
    assert skill["skill_name"] == "research_summary_skill"
    assert skill["status"] == "SUCCESS"
    # routing field still present for audit
    assert data.get("routing") == "research_summary_skill"
    # formatted_output should be non-empty
    assert data.get("formatted_output", "")  # truthy



def test_api_lab3_scenarios(client):
    """GET /api/lab3/scenarios returns predefined evaluator scenarios."""
    resp = client.get("/api/lab3/scenarios")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) >= 4
