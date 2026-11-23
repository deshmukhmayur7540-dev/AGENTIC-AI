"""API endpoint tests for Lab 5: MCP-Style Governed Connector."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.db import get_db_connection
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_api_lab5_list_sources(client):
    """GET /api/lab5/sources lists registered data sources."""
    resp = client.get("/api/lab5/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    sources = body["data"]["sources"]
    assert len(sources) >= 4
    source_ids = [s["source_id"] for s in sources]
    assert "notes_source" in source_ids
    assert "sqlite_source" in source_ids


def test_api_lab5_execute_operation(client):
    """POST /api/lab5/execute runs a typed operation through the connector."""
    payload = {
        "source_id": "sqlite_source",
        "operation": "LIST",
        "resource_path": "assignments",
        "client_role": "FACULTY",
    }
    resp = client.post("/api/lab5/execute", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["success"] is True
    assert len(data["data"]) >= 4


def test_api_lab5_student_write_denied(client):
    """POST /api/lab5/execute with STUDENT role rejects write with ACCESS_DENIED."""
    payload = {
        "source_id": "sqlite_source",
        "operation": "WRITE",
        "resource_path": "rubrics",
        "parameters": {"id": "tamper_rubric", "criterion": "Illegal Change"},
        "client_role": "STUDENT",
    }
    resp = client.post("/api/lab5/execute", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["success"] is False
    assert "Access Denied" in data["error"]
    logs = client.get("/api/lab5/audit", headers={"X-User-Role": "FACULTY"}).json()["data"]["logs"]
    assert any(log["status"] == "ACCESS_DENIED" and log["source_id"] == "sqlite_source" for log in logs)


def test_api_lab5_agent_query(client):
    """POST /api/lab5/query routes natural language queries through governed connector."""
    payload = {
        "query": "What are the prerequisites in the official catalog?",
        "role": "FACULTY",
    }
    resp = client.post("/api/lab5/query", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["intent"] == "REGISTRAR_API_QUERY"


def test_api_lab5_audit(client):
    """GET /api/lab5/audit returns immutable connector audit entries."""
    resp = client.get("/api/lab5/audit", headers={"X-User-Role": "FACULTY"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "logs" in body["data"]
    assert len(body["data"]["logs"]) >= 1


def test_api_lab5_audit_tracks_latest_dispatch(client):
    """Audit attribution must use server-authenticated identity, not caller fields."""
    faculty_headers = {"X-User-Role": "FACULTY"}
    before = client.get("/api/lab5/audit", headers=faculty_headers)
    ids_before = {log["audit_id"] for log in before.json()["data"]["logs"]}

    client.post(
        "/api/lab5/execute",
        json={
            "source_id": "notes_source",
            "operation": "SEARCH",
            "parameters": {"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401"},
            "client_agent": "forged_admin_agent",
            "actor_user_id": "forged-admin",
            "client_role": "FACULTY",
        },
        headers=faculty_headers,
    )

    after = client.get("/api/lab5/audit", headers=faculty_headers)
    logs = after.json()["data"]["logs"]
    assert logs[0]["audit_id"] not in ids_before
    latest = logs[0]
    assert latest["client_agent"] == "lab5_authenticated_api"
    assert latest["actor_user_id"] == "test-faculty"
    assert latest["client_role"] == "FACULTY"


def test_lab5_submission_reads_are_limited_to_authenticated_course_scope(client):
    """LIST, READ, SEARCH and audit reads cannot expose another course's submissions."""
    other_course = "99OTHER999"
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            """
            INSERT INTO assignments (id, course_id, title, max_points, weight_percentage, due_week)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("lab5-other-course", other_course, "Private course assignment", 100, 10.0, 1),
        )
        conn.execute(
            "INSERT INTO students (id, name, email, course_id, created_at) VALUES (?, ?, ?, ?, ?)",
            ("lab5-other-student", "Private Student", "private-99@test.invalid", other_course, "2026-11-17T00:00:00Z"),
        )
        conn.execute(
            """
            INSERT INTO submissions (
                id, assignment_id, student_id, course_id, repository_url, normalized_url,
                repo_owner, repo_name, submission_timestamp, attempt_number, status, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lab5-other-submission",
                "lab5-other-course",
                "lab5-other-student",
                other_course,
                "https://github.com/private/student-repository",
                "https://github.com/private/student-repository",
                "private",
                "student-repository",
                "2026-11-17T00:00:00Z",
                1,
                "SUBMITTED",
                "PASSED",
            ),
        )
        conn.execute(
            """
            INSERT INTO submission_audit_events (
                submission_id, action, actor_id, to_status, occurred_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("lab5-other-submission", "PRIVATE_EVENT", "private-faculty", "SUBMITTED", "2026-11-17T00:00:00Z"),
        )

    headers = {"X-User-Role": "FACULTY"}
    list_result = client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "LIST",
            "resource_path": "submissions",
            "parameters": {
                "course_id": other_course,
                "authorized_course_ids": [other_course],
            },
        },
        headers=headers,
    )
    assert list_result.status_code == 200
    records = list_result.json()["data"]["data"]
    assert all(record["course_id"] == "26ECAC401" for record in records)
    assert "lab5-other-submission" not in {record["id"] for record in records}

    read_result = client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "READ",
            "resource_path": "submissions",
            "parameters": {"id": "lab5-other-submission"},
        },
        headers=headers,
    )
    assert read_result.status_code == 200
    assert read_result.json()["data"]["data"] is None

    search_result = client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "SEARCH",
            "resource_path": "submissions",
            "parameters": {"query": "student-repository"},
        },
        headers=headers,
    )
    assert search_result.status_code == 200
    assert search_result.json()["data"]["data"] == []

    audit_result = client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "LIST",
            "resource_path": "submission_audit_events",
            "parameters": {"submission_id": "lab5-other-submission"},
        },
        headers=headers,
    )
    assert audit_result.status_code == 200
    assert audit_result.json()["data"]["data"] == []


def test_api_lab5_scenarios(client):
    """GET /api/lab5/scenarios returns predefined evaluator scenarios."""
    resp = client.get("/api/lab5/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 4
