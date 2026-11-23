"""Authorization and audit-attribution tests for similarity operations."""

import pytest
from fastapi.testclient import TestClient

from app.data.db import get_db_connection
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_similarity_run_audit_uses_authenticated_actor_role(client):
    with get_db_connection() as conn:
        assignment = conn.execute(
            "SELECT id FROM assignments WHERE course_id = ? ORDER BY id LIMIT 1",
            ("26ECAC401",),
        ).fetchone()
    assert assignment is not None
    assignment_id = assignment["id"]

    assert client.post(
        "/api/similarity/run",
        json={"assignment_id": assignment_id},
        headers={"X-User-Role": "STUDENT"},
    ).status_code == 403

    for role, expected_actor, expected_role in (
        ("FACULTY", "test-faculty", "FACULTY"),
        ("ADMIN", "test-admin", "ADMIN"),
    ):
        response = client.post(
            "/api/similarity/run",
            json={"assignment_id": assignment_id},
            headers={"X-User-Role": role},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "INSUFFICIENT_SUBMISSIONS"
        with get_db_connection() as conn:
            event = conn.execute(
                """
                SELECT actor, actor_role, resource, action
                FROM audit_events
                WHERE event_type = 'SIMILARITY_CHECK_COMPLETED'
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        assert event is not None
        assert event["resource"] == f"assignment:{assignment_id}"
        assert event["action"] == "RUN_SIMILARITY_CHECK"
        assert event["actor"] == expected_actor
        assert event["actor_role"] == expected_role
