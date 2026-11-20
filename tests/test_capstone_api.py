"""Disposable-database integration coverage for the persistent Lab 14 workflow."""

import uuid
from datetime import datetime, timezone

import pytest

from app.data.db import get_db_connection
from app.knowledge.service import knowledge_service
from app.main import app
from app.services.course_materials import create_materials, delete_material
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def _insert_assignment(assignment_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            """
            INSERT INTO assignments(
                id, course_id, title, max_points, weight_percentage, due_week,
                description, due_date, submission_rules, late_policy, status,
                created_at, updated_at
            ) VALUES (?, '26ECAC401', 'Capstone integration test', 100, 10, 1,
                      'Disposable test assignment', '2099-12-31T23:59:59+00:00',
                      'Test repository', 'Test late policy', 'OPEN', ?, ?)
            """,
            (assignment_id, now, now),
        )
        conn.execute(
            """
            INSERT INTO rubrics(id, assignment_id, criterion, max_points, description, weight_percentage)
            VALUES (?, ?, 'Evidence and implementation', 100, 'Disposable test rubric', 100)
            """,
            (f"rub-{assignment_id}", assignment_id),
        )


def _cleanup_assignment(assignment_id: str) -> None:
    with get_db_connection(immediate=True) as conn:
        run_ids = [
            row["run_id"]
            for row in conn.execute(
                "SELECT run_id FROM course_workspace_runs WHERE assignment_id = ?",
                (assignment_id,),
            ).fetchall()
        ]
        if run_ids:
            placeholders = ",".join("?" for _ in run_ids)
            conn.execute(
                f"DELETE FROM course_workspace_audit_events WHERE run_id IN ({placeholders})",
                run_ids,
            )
            conn.execute(
                f"DELETE FROM course_workspace_releases WHERE run_id IN ({placeholders})",
                run_ids,
            )
            conn.execute(
                f"DELETE FROM course_workspace_runs WHERE run_id IN ({placeholders})",
                run_ids,
            )
        submission_ids = [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM submissions WHERE assignment_id = ?",
                (assignment_id,),
            ).fetchall()
        ]
        if submission_ids:
            placeholders = ",".join("?" for _ in submission_ids)
            conn.execute(
                f"DELETE FROM submission_audit_events WHERE submission_id IN ({placeholders})",
                submission_ids,
            )
        conn.execute("DELETE FROM similarity_reports WHERE assignment_id = ?", (assignment_id,))
        conn.execute("DELETE FROM submissions WHERE assignment_id = ?", (assignment_id,))
        conn.execute("DELETE FROM rubrics WHERE assignment_id = ?", (assignment_id,))
        conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))


def test_capstone_validates_gates_before_approval_then_versions_and_rolls_back(client):
    assignment_id = f"capstone-test-{uuid.uuid4().hex[:10]}"
    marker = f"coursecapstoneevidence{uuid.uuid4().hex[:12]}"
    _insert_assignment(assignment_id)
    material = create_materials(
        course_id="26ECAC401",
        category_id="notes",
        folder_id=None,
        title="Disposable capstone source",
        description="Temporary integration-test source.",
        chapter=1,
        lab=None,
        uploads=[("source.txt", f"{marker} Plan Act Observe Revise course workspace.".encode("utf-8"))],
        actor_id="test-faculty",
        actor_role="FACULTY",
    )[0]
    knowledge_service.initialize(force_reload=True)
    payload = {
        "course_id": "26ECAC401",
        "assignment_id": assignment_id,
        "request": marker,
    }

    try:
        failed = client.post(
            "/api/capstone/runs",
            json=payload,
            headers={"X-User-Role": "FACULTY"},
        )
        assert failed.status_code == 200
        failed_data = failed.json()["data"]
        assert failed_data["status"] == "VALIDATION_FAILED"
        checks = {item["check_id"]: item for item in failed_data["validation"]["checks"]}
        assert checks["submission_cycle_and_similarity"]["passed"] is False
        assert client.post(
            f"/api/capstone/runs/{failed_data['run_id']}/decision",
            json={"approved": True},
            headers={"X-User-Role": "FACULTY"},
        ).status_code == 409

        for student_id, repo in (
            ("std-001", "capstone-student-one"),
            ("std-002", "capstone-student-two"),
        ):
            submitted = client.post(
                "/api/submissions",
                json={
                    "assignment_id": assignment_id,
                    "student_id": student_id,
                    "repository_url": f"https://github.com/{repo}/course-project",
                },
                headers={"X-User-Role": "STUDENT", "X-Student-Id": student_id},
            )
            assert submitted.status_code == 200, submitted.text

        ready = client.post(
            "/api/capstone/runs",
            json=payload,
            headers={"X-User-Role": "FACULTY"},
        )
        assert ready.status_code == 200
        run = ready.json()["data"]
        assert run["status"] == "READY_FOR_FACULTY_APPROVAL"
        assert run["validation"]["passed"] is True
        assert run["package"]["materials"][0]["material_id"] == material["material_id"]
        assert run["package"]["evidence"]
        assert run["package"]["similarity"]["report_id"]
        assert run["package"]["disclosure"]["repository_source_code_was_fetched"] is False
        assert run["package"]["governance"]["evaluation_metrics"]["checks_failed"] == 0
        assert run["package"]["governance"]["risk_register"]

        assert client.get(
            f"/api/capstone/runs/{run['run_id']}",
            headers={"X-User-Role": "STUDENT"},
        ).status_code == 403
        assert client.post(
            f"/api/capstone/runs/{run['run_id']}/decision",
            json={"approved": True},
            headers={"X-User-Role": "ADMIN"},
        ).status_code == 403

        first_release = client.post(
            f"/api/capstone/runs/{run['run_id']}/decision",
            json={"approved": True, "comment": "Disposable test approval"},
            headers={"X-User-Role": "FACULTY"},
        )
        assert first_release.status_code == 200
        release_one = first_release.json()["data"]
        assert release_one["version"] == 1
        assert release_one["is_active"] == 1

        second_run = client.post(
            "/api/capstone/runs",
            json=payload,
            headers={"X-User-Role": "FACULTY"},
        ).json()["data"]
        second_release_response = client.post(
            f"/api/capstone/runs/{second_run['run_id']}/decision",
            json={"approved": True},
            headers={"X-User-Role": "FACULTY"},
        )
        assert second_release_response.status_code == 200
        release_two = second_release_response.json()["data"]
        assert release_two["version"] == 2
        student_release = client.get(
            "/api/capstone/releases/current",
            headers={"X-User-Role": "STUDENT"},
        ).json()["data"]
        assert student_release["release_id"] == release_two["release_id"]
        assert "submissions" not in student_release["package"]
        assert "pairs" not in student_release["package"]["similarity"]
        faculty_release = client.get(
            "/api/capstone/releases/current",
            headers={"X-User-Role": "FACULTY"},
        ).json()["data"]
        assert len(faculty_release["package"]["submissions"]) == 2

        rollback = client.post(
            f"/api/capstone/releases/{release_two['release_id']}/rollback",
            headers={"X-User-Role": "FACULTY"},
        )
        assert rollback.status_code == 200
        assert rollback.json()["data"]["release_id"] == release_one["release_id"]
        audit = client.get(
            f"/api/capstone/runs/{run['run_id']}/audit",
            headers={"X-User-Role": "FACULTY"},
        )
        assert [event["action"] for event in audit.json()["data"]] == [
            "RUN_CREATED",
            "RELEASE_PUBLISHED",
        ]
    finally:
        delete_material(
            material_id=material["material_id"],
            course_id="26ECAC401",
            actor_id="test-faculty",
            actor_role="FACULTY",
        )
        knowledge_service.initialize(force_reload=True)
        _cleanup_assignment(assignment_id)
