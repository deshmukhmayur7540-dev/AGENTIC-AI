"""Automated test suite for Student GitHub Assignment Submission & Review Feature.

Covers:
1. GitHub URL Validation & SSRF Guardrails.
2. Assignment Listing & Detail Retrieval.
3. Student Listing.
4. Student GitHub Assignment Submission & Versioning (Attempts, is_latest).
5. Deadline & Late Policy Enforcement.
6. Role-Based Access Control (Student Isolation & Faculty Review Access).
7. Faculty Grading, Review Persistence, and Status Transitions.
8. Database Persistence & Restart Simulation.
"""

import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from config import settings
from app.services.github_validator import validate_github_url, check_remote_repository_access
from app.services.submission_service import submission_service
from app.labs.lab5.sources.sqlite_source import SqliteDataSource
from app.models.lab5_models import ConnectorOperation, ConnectorRole
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def create_submission(client, assignment_id="lab4", student_id="std-001"):
    response = client.post(
        "/api/submissions",
        json={
            "assignment_id": assignment_id,
            "student_id": student_id,
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers={"X-User-Role": "STUDENT", "X-Student-Id": student_id},
    )
    assert response.status_code == 200
    return response.json()["data"]


# =============================================================================
# 1. GitHub URL Validation & Security Guardrails
# =============================================================================

def test_valid_github_repository_urls():
    """Verify standard valid GitHub repo URLs are normalized and accepted."""
    valid_cases = [
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
        ("https://github.com/torvalds/linux.git", "torvalds", "linux"),
        ("https://github.com/google/gemini-cookbook/", "google", "gemini-cookbook"),
        ("https://www.github.com/username/project_123", "username", "project_123"),
    ]
    for url, expected_owner, expected_repo in valid_cases:
        res = validate_github_url(url)
        assert res.is_valid is True, f"Failed for {url}: {res.error_message}"
        assert res.owner.lower() == expected_owner.lower()
        assert res.repo.lower() == expected_repo.lower()
        assert res.normalized_url.startswith("https://github.com/")


def test_reject_invalid_schemes():
    """Verify non-HTTPS schemes are rejected."""
    invalid_schemes = [
        "http://github.com/octocat/Hello-World",
        "ftp://github.com/octocat/Hello-World",
        "git://github.com/octocat/Hello-World",
        "ssh://git@github.com:octocat/Hello-World",
    ]
    for url in invalid_schemes:
        res = validate_github_url(url)
        assert res.is_valid is False
        assert "HTTPS" in (res.error_message or "") or "scheme" in (res.error_message or "").lower()


def test_reject_lookalike_and_unauthorized_hosts():
    """Verify lookalike domains and arbitrary hostnames are rejected."""
    bad_hosts = [
        "https://g1thub.com/octocat/Hello-World",
        "https://github.com.attacker.com/octocat/Hello-World",
        "https://gitlab.com/octocat/Hello-World",
        "https://bitbucket.org/octocat/Hello-World",
        "https://fake-github.org/octocat/Hello-World",
    ]
    for url in bad_hosts:
        res = validate_github_url(url)
        assert res.is_valid is False
        assert "github.com" in (res.error_message or "").lower()


def test_reject_ssrf_and_localhost_targets():
    """Verify localhost, private IPs, and cloud metadata targets are rejected."""
    ssrf_targets = [
        "https://localhost/octocat/Hello-World",
        "https://127.0.0.1/octocat/Hello-World",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/octocat/Hello-World",
    ]
    for url in ssrf_targets:
        res = validate_github_url(url)
        assert res.is_valid is False
        assert res.error_message is not None
        assert len(res.error_message) > 0


def test_reject_embedded_credentials():
    """Verify URLs with embedded username/password are strictly rejected."""
    bad_urls = [
        "https://user:password@github.com/octocat/Hello-World",
        "https://token@github.com/octocat/Hello-World",
    ]
    for url in bad_urls:
        res = validate_github_url(url)
        assert res.is_valid is False
        assert "embedded credentials" in (res.error_message or "").lower()


def test_reject_subpaths_and_tree_branches():
    """Verify subpaths, file references, and tree branches are rejected."""
    subpaths = [
        "https://github.com/octocat/Hello-World/tree/main",
        "https://github.com/octocat/Hello-World/blob/main/README.md",
        "https://github.com/octocat/Hello-World/issues/1",
        "https://github.com/octocat/Hello-World/actions",
    ]
    for url in subpaths:
        res = validate_github_url(url)
        assert res.is_valid is False
        assert "root repository" in (res.error_message or "").lower()


def test_reject_malformed_and_injection_characters():
    """Verify malformed URLs and command injection characters are rejected."""
    malformed = [
        "not-a-url",
        "https://github.com/octocat",
        "https://github.com/octocat/repo;rm -rf /",
        "https://github.com/../evil/repo",
    ]
    for url in malformed:
        res = validate_github_url(url)
        assert res.is_valid is False


@pytest.mark.asyncio
async def test_remote_reachability_check_handling():
    """Verify remote reachability check safely handles responses and network errors."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"private": False, "default_branch": "main"}
        mock_get.return_value = mock_resp
        status_val, details = await check_remote_repository_access("octocat", "Hello-World")
        assert status_val == "PASSED"
        assert details["reachable"] is True

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        status_val, details = await check_remote_repository_access("nonexistent", "secret-repo")
        assert status_val == "WARNING"
        assert details["reachable"] is False


# =============================================================================
# 2. Assignment & Student Endpoints
# =============================================================================

def test_list_assignments(client):
    """GET /api/assignments lists assignments with due date, description, and status."""
    resp = client.get("/api/assignments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assignments = data["data"]
    assert len(assignments) >= 5
    ids = [a["id"] for a in assignments]
    assert "lab1" in ids
    assert "lab2" in ids
    assert "final_capstone" in ids

    lab1 = next(a for a in assignments if a["id"] == "lab1")
    assert "title" in lab1
    assert "due_date" in lab1
    assert "submission_rules" in lab1
    assert "late_policy" in lab1


def test_get_assignment_detail_success_and_not_found(client):
    """GET /api/assignments/{id} returns single assignment or 404."""
    resp = client.get("/api/assignments/lab1")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == "lab1"

    resp_404 = client.get("/api/assignments/non_existent_lab_999")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.json()["detail"].lower()


def test_list_students(client):
    """GET /api/students returns registered students."""
    resp = client.get("/api/students")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    students = data["data"]
    assert len(students) == 1
    ids = [s["id"] for s in students]
    assert "std-001" in ids
    assert ids == ["std-001"]


# =============================================================================
# 3. Student GitHub Assignment Submission & Versioning (Attempts)
# =============================================================================

def test_submit_assignment_success_first_attempt(client):
    """POST /api/submissions creates attempt with truthful status and receipt."""
    payload = {
        "assignment_id": "lab1",
        "student_id": "std-001",
        "repository_url": "https://github.com/octocat/Hello-World",
        "notes": "Implemented Lab 1 coordinator planning loop.",
    }
    resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    sub = data["data"]
    assert sub["assignment_id"] == "lab1"
    assert sub["student_id"] == "std-001"
    assert sub["repo_owner"].lower() == "octocat"
    assert sub["repo_name"].lower() == "hello-world"
    assert sub["attempt_number"] >= 1
    assert sub["is_latest"] is True
    assert sub["status"] in ["SUBMITTED", "LATE"]
    assert sub["id"].startswith("sub-")


def test_resubmission_increments_attempt_and_updates_latest_pointer(client):
    """Submitting again updates previous submissions to is_latest=0 and creates next attempt."""
    payload_v1 = {
        "assignment_id": "lab2",
        "student_id": "std-001",
        "repository_url": "https://github.com/octocat/Hello-World",
        "notes": "Initial draft of Lab 2 tools",
    }
    resp1 = client.post(
        "/api/submissions",
        json=payload_v1,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert resp1.status_code == 200
    sub1 = resp1.json()["data"]
    attempt_v1 = sub1["attempt_number"]

    payload_v2 = {
        "assignment_id": "lab2",
        "student_id": "std-001",
        "repository_url": "https://github.com/octocat/Hello-World.git",
        "notes": "Revised Lab 2 with all 5 tools verified",
    }
    resp2 = client.post(
        "/api/submissions",
        json=payload_v2,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert resp2.status_code == 200
    sub2 = resp2.json()["data"]
    assert sub2["attempt_number"] == attempt_v1 + 1
    assert sub2["is_latest"] is True

    # Check student history reflects both attempts, but only the latest is is_latest=True
    resp_hist = client.get(
        "/api/submissions/student/std-001",
        headers={"X-Student-Id": "std-001", "X-User-Role": "STUDENT"}
    )
    assert resp_hist.status_code == 200
    history = resp_hist.json()["data"]
    lab2_subs = [s for s in history if s["assignment_id"] == "lab2"]
    assert len(lab2_subs) >= 2
    latest_count = sum(1 for s in lab2_subs if s["is_latest"] is True)
    assert latest_count == 1


def test_submission_rejects_invalid_url(client):
    """POST /api/submissions with bad URL returns 400 Bad Request."""
    payload = {
        "assignment_id": "lab1",
        "student_id": "std-001",
        "repository_url": "https://g1thub.com/attacker/repo",
    }
    resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert resp.status_code == 400
    assert "github.com" in resp.json()["detail"].lower()


def test_submission_rejects_missing_assignment(client):
    """POST /api/submissions with non-existent assignment returns 404."""
    payload = {
        "assignment_id": "unknown_assignment_xyz",
        "student_id": "std-001",
        "repository_url": "https://github.com/octocat/Hello-World",
    }
    resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_submission_rejects_missing_student(client):
    """POST /api/submissions with unregistered student returns 404."""
    payload = {
        "assignment_id": "lab1",
        "student_id": "fake_student_999",
        "repository_url": "https://github.com/octocat/Hello-World",
    }
    resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "fake_student_999"},
    )
    assert resp.status_code == 403
    assert "student" in resp.json()["detail"].lower()


# =============================================================================
# 4. Access Control & Student Isolation (RBAC)
# =============================================================================

def test_student_cannot_view_another_student_submissions(client):
    """Student std-002 cannot view submissions of std-001 (403 Forbidden)."""
    resp = client.get(
        "/api/submissions/student/std-001",
        headers={"X-Student-Id": "std-002", "X-User-Role": "STUDENT"}
    )
    assert resp.status_code == 403
    assert "Access Denied" in resp.json()["detail"]


def test_student_can_view_own_submissions(client):
    """Student std-001 can view their own submissions."""
    resp = client.get(
        "/api/submissions/student/std-001",
        headers={"X-Student-Id": "std-001", "X-User-Role": "STUDENT"}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_faculty_can_view_any_student_submissions(client):
    """Faculty can inspect any student's submissions."""
    resp = client.get(
        "/api/submissions/student/std-001",
        headers={"X-User-Role": "FACULTY"}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# =============================================================================
# 5. Faculty Review, Grading & Portal Access
# =============================================================================

def test_student_cannot_access_faculty_portal(client):
    """Student role cannot access GET /api/submissions/faculty (403 Forbidden)."""
    resp = client.get(
        "/api/submissions/faculty",
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"}
    )
    assert resp.status_code == 403


def test_admin_cannot_access_faculty_grading_portal(client):
    """Administrator account management does not grant Faculty grading privileges."""
    resp = client.get(
        "/api/submissions/faculty",
        headers={"X-User-Role": "ADMIN"},
    )
    assert resp.status_code == 403


def test_faculty_can_list_all_submissions(client):
    """Faculty role accesses all latest student submissions."""
    resp = client.get(
        "/api/submissions/faculty",
        headers={"X-User-Role": "FACULTY"}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


def test_student_cannot_submit_review(client):
    """Student role cannot submit a grade/review (403 Forbidden)."""
    payload = {
        "assignment_id": "lab3",
        "student_id": "std-002",
        "repository_url": "https://github.com/octocat/Hello-World",
    }
    sub_resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-002"},
    )
    sub_id = sub_resp.json()["data"]["id"]

    review_payload = {
        "review_score": 100.0,
        "review_feedback": "Self awarded grade",
        "reviewer_id": "std-002"
    }
    resp = client.post(
        f"/api/submissions/{sub_id}/review",
        json=review_payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-002"}
    )
    assert resp.status_code == 403


def test_faculty_can_review_and_grade_submission(client):
    """Faculty can review a submission, award a score, and provide feedback."""
    payload = {
        "assignment_id": "lab4",
        "student_id": "std-003",
        "repository_url": "https://github.com/octocat/Hello-World",
    }
    sub_resp = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-003"},
    )
    sub_id = sub_resp.json()["data"]["id"]

    review_payload = {
        "review_score": 92.5,
        "review_feedback": "Excellent schema design and session isolation implementation.",
        "reviewer_id": "prof-smith"
    }
    resp = client.post(
        f"/api/submissions/{sub_id}/review",
        json=review_payload,
        headers={"X-User-Role": "FACULTY"}
    )
    assert resp.status_code == 200
    reviewed_sub = resp.json()["data"]
    assert reviewed_sub["status"] == "DRAFT_GRADED"
    assert reviewed_sub["review_status"] == "DRAFT_GRADED"
    assert reviewed_sub["review_score"] == 92.5
    assert reviewed_sub["review_feedback"] == "Excellent schema design and session isolation implementation."
    assert reviewed_sub["reviewed_by"] == "test-faculty"
    assert reviewed_sub["reviewed_at"] is not None
    assert reviewed_sub["approved_at"] is None
    assert reviewed_sub["published_at"] is None


def test_completed_review_requires_score_and_feedback_and_status_is_consistent(client):
    submission = client.post(
        "/api/submissions",
        json={
            "assignment_id": "lab1",
            "student_id": "std-002",
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-002"},
    ).json()["data"]
    review_url = f"/api/submissions/{submission['id']}/review"
    headers = {"X-User-Role": "FACULTY"}

    assert client.post(review_url, json={}, headers=headers).status_code == 422
    assert client.post(
        review_url,
        json={"review_score": 90, "review_feedback": "  "},
        headers=headers,
    ).status_code == 422
    assert client.post(
        review_url,
        json={"review_score": 101, "review_feedback": "Good work"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        review_url,
        content='{"review_score":NaN,"review_feedback":"Good work"}',
        headers={**headers, "Content-Type": "application/json"},
    ).status_code == 422

    pending = client.get(
        f"/api/submissions/detail/{submission['id']}",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    assert pending["status"] in ["SUBMITTED", "LATE"]
    assert pending["review_score"] is None

    under_review = client.post(
        review_url,
        json={"review_status": "UNDER_REVIEW", "reviewer_id": "faculty-1"},
        headers=headers,
    )
    assert under_review.status_code == 200
    assert under_review.json()["data"]["status"] == "UNDER_REVIEW"

    completed = client.post(
        review_url,
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 90,
            "review_feedback": "Good work",
            "reviewer_id": "faculty-1",
        },
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "DRAFT_GRADED"


def test_submission_audit_records_persisted_submit_and_review_events(client):
    submission = client.post(
        "/api/submissions",
        json={
            "assignment_id": "lab2",
            "student_id": "std-003",
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-003"},
    ).json()["data"]
    headers = {"X-User-Role": "STUDENT", "X-Student-Id": "std-003"}

    submitted_audit = client.get(
        f"/api/submissions/{submission['id']}/audit",
        headers=headers,
    )
    assert submitted_audit.status_code == 200
    submitted_event = submitted_audit.json()["data"][0]
    assert submitted_event["action"] == "SUBMITTED"
    assert submitted_event["actor_id"] == "std-003"
    assert submitted_event["trace_id"] == submission["audit_trace_id"]
    assert submitted_event["to_status"] in ["SUBMITTED", "LATE"]

    reviewed = client.post(
        f"/api/submissions/{submission['id']}/review",
        json={
            "review_score": 88,
            "review_feedback": "Evidence and tests are complete.",
            "reviewer_id": "faculty-reviewer",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert reviewed.status_code == 200
    reviewed_data = reviewed.json()["data"]
    events = client.get(
        f"/api/submissions/{submission['id']}/audit",
        headers=headers,
    ).json()["data"]
    assert [event["action"] for event in events] == ["SUBMITTED", "REVIEW_SAVED"]
    assert events[1]["actor_id"] == "test-faculty"
    assert events[1]["from_status"] in ["SUBMITTED", "LATE"]
    assert events[1]["to_status"] == "DRAFT_GRADED"
    assert events[1]["review_score"] is None
    assert events[1]["review_feedback"] is None
    assert events[1]["trace_id"] == reviewed_data["audit_trace_id"]
    assert events[1]["occurred_at"] == reviewed_data["reviewed_at"]

    faculty_events = client.get(
        f"/api/submissions/{submission['id']}/audit",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    assert faculty_events[1]["review_score"] == 88
    assert faculty_events[1]["review_feedback"] == "Evidence and tests are complete."


def test_failed_resubmission_preserves_previous_latest_attempt(client):
    first = client.post(
        "/api/submissions",
        json={
            "assignment_id": "lab3",
            "student_id": "std-001",
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert first.status_code == 200
    first_id = first.json()["data"]["id"]

    connection = sqlite3.connect(settings.database_path)
    connection.execute(
        f"""
        CREATE TRIGGER reject_submission_audit
        BEFORE INSERT ON submission_audit_events
        WHEN NEW.submission_id != '{first_id}'
        BEGIN
            SELECT RAISE(ABORT, 'injected audit write failure');
        END
        """
    )
    connection.commit()
    connection.close()
    try:
        failed = client.post(
            "/api/submissions",
            json={
                "assignment_id": "lab3",
                "student_id": "std-001",
                "repository_url": "https://github.com/octocat/Hello-World.git",
            },
            headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
        )
        assert failed.status_code == 500

        history = client.get(
            "/api/submissions/student/std-001?assignment_id=lab3",
            headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
        ).json()["data"]
        latest = [item for item in history if item["is_latest"]]
        assert [item["id"] for item in latest] == [first_id]
    finally:
        cleanup = sqlite3.connect(settings.database_path)
        cleanup.execute("DROP TRIGGER IF EXISTS reject_submission_audit")
        cleanup.commit()
        cleanup.close()


# =============================================================================
# 6. Database Persistence Across Independent Connections
# =============================================================================

def test_database_persistence_across_independent_connection(client):
    """Verify submitted records survive and are accurately queryable via raw SQLite connection."""
    response = client.post(
        "/api/submissions",
        json={
            "assignment_id": "lab1",
            "student_id": "std-001",
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert response.status_code == 200
    expected_id = response.json()["data"]["id"]

    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, repo_owner, repo_name, status, is_latest FROM submissions WHERE id = ?",
        (expected_id,),
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    sub_id, owner, repo, status, is_latest = row
    assert sub_id == expected_id
    assert owner == "octocat"
    assert repo == "Hello-World"
    assert status in ["SUBMITTED", "LATE"]
    assert is_latest == 1


def test_review_draft_is_persisted_but_hidden_from_student(client):
    submission = create_submission(client, student_id="std-002")
    submission_id = submission["id"]
    student_headers = {"X-User-Role": "STUDENT", "X-Student-Id": "std-002"}

    initial = client.get(
        f"/api/submissions/detail/{submission_id}",
        headers=student_headers,
    ).json()["data"]
    assert initial["review_score"] is None
    assert initial["review_feedback"] is None
    assert initial["approved_at"] is None
    assert initial["published_at"] is None

    faculty_detail = client.get(
        f"/api/submissions/detail/{submission_id}",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    assert faculty_detail["review_status"] == "PENDING"
    assert faculty_detail["review_score"] is None

    draft_response = client.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 87.5,
            "review_feedback": "Draft feedback must remain private.",
            "reviewer_id": "faculty-reviewer",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]
    assert draft["status"] == draft["review_status"] == "DRAFT_GRADED"
    assert draft["review_score"] == 87.5
    assert draft["review_feedback"] == "Draft feedback must remain private."
    assert draft["reviewed_by"] == "test-faculty"
    assert draft["reviewed_at"] is not None
    assert draft["approved_at"] is None
    assert draft["published_at"] is None

    faculty_list = client.get(
        "/api/submissions/faculty?only_latest=false",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    persisted_row = next(item for item in faculty_list if item["id"] == submission_id)
    persisted_detail = client.get(
        f"/api/submissions/detail/{submission_id}",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    assert persisted_row["review_status"] == persisted_detail["review_status"] == draft["review_status"]
    assert persisted_row["review_score"] == persisted_detail["review_score"] == draft["review_score"]
    assert persisted_row["review_feedback"] == persisted_detail["review_feedback"] == draft["review_feedback"]

    for path in (
        f"/api/submissions/student/std-002?assignment_id={submission['assignment_id']}",
        f"/api/submissions/detail/{submission_id}",
    ):
        visible = (
            client.get(path, headers=student_headers).json()["data"][0]
            if "?" in path
            else client.get(path, headers=student_headers).json()["data"]
        )
        assert visible["review_status"] == "DRAFT_GRADED"
        assert visible["review_score"] is None
        assert visible["review_feedback"] is None

    student_audit = client.get(
        f"/api/submissions/{submission_id}/audit",
        headers=student_headers,
    ).json()["data"]
    assert student_audit[-1]["review_score"] is None
    assert student_audit[-1]["review_feedback"] is None


def test_approval_and_publication_are_separate_authorized_transitions(client):
    submission = create_submission(client, assignment_id="lab3", student_id="std-003")
    submission_id = submission["id"]
    faculty_headers = {"X-User-Role": "FACULTY"}
    student_headers = {"X-User-Role": "STUDENT", "X-Student-Id": "std-003"}

    unauthorized = client.post(
        f"/api/submissions/{submission_id}/approve",
        json={"reviewer_id": "student"},
        headers=student_headers,
    )
    assert unauthorized.status_code == 403
    assert client.post(
        f"/api/submissions/{submission_id}/approve",
        json={"reviewer_id": "faculty"},
        headers=faculty_headers,
    ).status_code == 409
    assert client.post(
        f"/api/submissions/{submission_id}/publish",
        json={"reviewer_id": "faculty"},
        headers=faculty_headers,
    ).status_code == 409

    saved = client.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 96,
            "review_feedback": "Final rubric draft.",
            "reviewer_id": "faculty-reviewer",
        },
        headers=faculty_headers,
    )
    assert saved.status_code == 200

    approved_response = client.post(
        f"/api/submissions/{submission_id}/approve",
        json={"reviewer_id": "approving-faculty"},
        headers=faculty_headers,
    )
    assert approved_response.status_code == 200
    approved = approved_response.json()["data"]
    assert approved["status"] == approved["review_status"] == "APPROVED"
    assert approved["approved_by"] == "test-faculty"
    assert approved["approved_at"] is not None
    assert approved["published_at"] is None

    unpublished_to_student = client.get(
        f"/api/submissions/detail/{submission_id}",
        headers=student_headers,
    ).json()["data"]
    assert unpublished_to_student["review_score"] is None
    assert unpublished_to_student["review_feedback"] is None

    republish_before_publish = client.post(
        f"/api/submissions/{submission_id}/publish",
        json={"reviewer_id": "student"},
        headers=student_headers,
    )
    assert republish_before_publish.status_code == 403

    published_response = client.post(
        f"/api/submissions/{submission_id}/publish",
        json={"reviewer_id": "publishing-faculty"},
        headers=faculty_headers,
    )
    assert published_response.status_code == 200
    published = published_response.json()["data"]
    assert published["status"] == published["review_status"] == "PUBLISHED"
    assert published["published_by"] == "test-faculty"
    assert published["published_at"] is not None

    student_result = client.get(
        f"/api/submissions/detail/{submission_id}",
        headers=student_headers,
    ).json()["data"]
    assert student_result["review_score"] == 96
    assert student_result["review_feedback"] == "Final rubric draft."
    assert student_result["published_at"] == published["published_at"]
    student_events = client.get(
        f"/api/submissions/{submission_id}/audit",
        headers=student_headers,
    ).json()["data"]
    assert all(
        event["review_score"] is None and event["review_feedback"] is None
        for event in student_events
        if event["action"] != "GRADE_PUBLISHED"
    )
    assert student_events[-1]["review_score"] == 96
    assert student_events[-1]["review_feedback"] == "Final rubric draft."

    duplicate_publish = client.post(
        f"/api/submissions/{submission_id}/publish",
        json={"reviewer_id": "publishing-faculty"},
        headers=faculty_headers,
    )
    assert duplicate_publish.status_code == 409
    cannot_edit_approved = client.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 99,
            "review_feedback": "Changed after approval.",
            "reviewer_id": "faculty-reviewer",
        },
        headers=faculty_headers,
    )
    assert cannot_edit_approved.status_code == 409

    audit_events = client.get(
        f"/api/submissions/{submission_id}/audit",
        headers=faculty_headers,
    ).json()["data"]
    assert [event["action"] for event in audit_events] == [
        "SUBMITTED",
        "REVIEW_SAVED",
        "GRADE_APPROVED",
        "GRADE_PUBLISHED",
    ]
    assert [event["to_status"] for event in audit_events[-3:]] == [
        "DRAFT_GRADED",
        "APPROVED",
        "PUBLISHED",
    ]
    assert audit_events[-2]["actor_id"] == "test-faculty"
    assert audit_events[-1]["actor_id"] == "test-faculty"

    connection = sqlite3.connect(settings.database_path)
    try:
        rows = connection.execute(
            "SELECT action, outcome, actor, actor_role, trace_id "
            "FROM audit_events WHERE resource = ? ORDER BY id",
            (f"submission:{submission_id}",),
        ).fetchall()
    finally:
        connection.close()
    assert [row[0] for row in rows] == ["REVIEW_SAVED", "GRADE_APPROVED", "GRADE_PUBLISHED"]
    assert [row[1] for row in rows] == ["DRAFT_GRADED", "APPROVED", "PUBLISHED"]
    assert [row[2] for row in rows] == ["test-faculty", "test-faculty", "test-faculty"]
    assert [row[3] for row in rows] == ["FACULTY", "FACULTY", "FACULTY"]

    restarted_source = SqliteDataSource(db_path=settings.database_path)
    try:
        persisted, _provenance = restarted_source.execute(
            ConnectorOperation.READ,
            "submissions",
            {"id": submission_id, "course_id": "26ECAC401"},
            ConnectorRole.FACULTY,
        )
    finally:
        restarted_source._conn.close()
    assert persisted["review_status"] == "PUBLISHED"
    assert persisted["review_score"] == 96
    assert persisted["review_feedback"] == "Final rubric draft."
    assert persisted["approved_by"] == "test-faculty"
    assert persisted["approved_at"] == approved["approved_at"]
    assert persisted["published_by"] == "test-faculty"
    assert persisted["published_at"] == published["published_at"]


def test_faculty_review_ui_uses_persisted_state_without_fake_score_defaults(client):
    submission = create_submission(client, assignment_id="lab2", student_id="std-001")
    saved = client.post(
        f"/api/submissions/{submission['id']}/review",
        json={
            "review_status": "UNDER_REVIEW",
            "reviewer_id": "faculty-reviewer",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert saved.status_code == 200

    faculty_row = client.get(
        "/api/submissions/faculty?only_latest=false",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    row_state = next(item for item in faculty_row if item["id"] == submission["id"])
    form_state = client.get(
        f"/api/submissions/detail/{submission['id']}",
        headers={"X-User-Role": "FACULTY"},
    ).json()["data"]
    assert row_state["status"] == form_state["status"] == "UNDER_REVIEW"
    assert row_state["review_status"] == form_state["review_status"] == "UNDER_REVIEW"
    assert row_state["review_score"] is form_state["review_score"] is None

    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="btn-approve-faculty-grade"' in html
    assert 'id="btn-publish-faculty-grade"' in html
    assert 'id="modal-review-score"' in html
    assert 'placeholder="95.0"' not in html
    assert js.count("displayReviewStatus(item)") >= 2
    assert "Save Review Draft" in html
    assert "approved" in js.lower()


def test_audit_failure_rolls_back_grade_transition(client):
    submission = create_submission(client, assignment_id="lab1", student_id="std-002")
    submission_id = submission["id"]
    saved = client.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 91,
            "review_feedback": "Draft awaiting approval.",
            "reviewer_id": "faculty-reviewer",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert saved.status_code == 200

    connection = sqlite3.connect(settings.database_path)
    try:
        connection.execute(
            """
            CREATE TRIGGER reject_grade_approval_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.action = 'GRADE_APPROVED'
            BEGIN
                SELECT RAISE(ABORT, 'injected grade approval audit failure');
            END
            """
        )
        connection.commit()
    finally:
        connection.close()

    try:
        with pytest.raises(sqlite3.IntegrityError, match="injected grade approval audit failure"):
            submission_service.approve_grade(
                submission_id,
                reviewer_id="approving-faculty",
                reviewer_role="FACULTY",
            )
        current = client.get(
            f"/api/submissions/detail/{submission_id}",
            headers={"X-User-Role": "FACULTY"},
        ).json()["data"]
        assert current["review_status"] == "DRAFT_GRADED"
        assert current["approved_at"] is None
        events = client.get(
            f"/api/submissions/{submission_id}/audit",
            headers={"X-User-Role": "FACULTY"},
        ).json()["data"]
        assert not any(event["action"] == "GRADE_APPROVED" for event in events)
    finally:
        connection = sqlite3.connect(settings.database_path)
        try:
            connection.execute("DROP TRIGGER IF EXISTS reject_grade_approval_audit")
            connection.commit()
        finally:
            connection.close()
