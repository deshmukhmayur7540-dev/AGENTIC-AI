"""Authentication, session, and role-scope regression tests."""

import hashlib
import sqlite3
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.data.db import get_db_connection
from app.main import app
from app.services.auth_service import create_user
from config import settings

PASSWORD = "courseagent-test-password"


@pytest.fixture(scope="module", autouse=True)
def auth_test_accounts():
    accounts = [
        ("test-std-001", "test-std-001@test.invalid", "STUDENT", "std-001", []),
        ("test-std-002", "test-std-002@test.invalid", "STUDENT", "std-002", []),
        ("auth-faculty", "auth-faculty@test.invalid", "FACULTY", None, ["26ECAC401"]),
        ("auth-faculty-other", "auth-faculty-other@test.invalid", "FACULTY", None, ["OTHER-COURSE"]),
        ("auth-admin", "auth-admin@test.invalid", "ADMIN", None, []),
    ]
    for user_id, email, role, student_id, scopes in accounts:
        try:
            create_user(
                user_id=user_id,
                email=email,
                display_name=user_id,
                password=PASSWORD,
                role=role,
                student_id=student_id,
                course_scopes=scopes,
            )
        except sqlite3.IntegrityError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


def sign_in(client, email="test-std-001@test.invalid", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def create_student_submission(client):
    response = client.post(
        "/api/submissions",
        json={
            "assignment_id": "lab1",
            "student_id": "std-001",
            "repository_url": "https://github.com/octocat/CourseAgentAuthTest",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_login_valid_password_hash_and_cookie(client):
    response = sign_in(client)
    assert response.status_code == 200
    assert response.json()["role"] == "STUDENT"
    assert response.json()["student_id"] == "std-001"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert client.get("/api/auth/me").json()["user_id"] == "test-std-001"
    with get_db_connection() as conn:
        account = conn.execute(
            "SELECT password_hash FROM auth_users WHERE user_id = 'test-std-001'"
        ).fetchone()
    assert account["password_hash"].startswith("$argon2id$")
    assert account["password_hash"] != PASSWORD


def test_secure_cookie_flag_follows_deployment_setting(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", True)
    response = sign_in(client)
    assert response.status_code == 200
    cookies = [value.lower() for value in response.headers.get_list("set-cookie")]
    assert any(value.startswith("courseagent_session=") and "secure" in value for value in cookies)
    assert any(value.startswith("courseagent_csrf=") and "secure" in value for value in cookies)


@pytest.mark.parametrize(
    "email,password",
    [
        ("test-std-001@test.invalid", "incorrect-password"),
        ("unknown-account@test.invalid", PASSWORD),
    ],
)
def test_login_rejects_wrong_password_and_unknown_user(client, email, password):
    response = sign_in(client, email, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_logout_revokes_server_side_session(client):
    assert sign_in(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_concurrent_sessions_are_independent_and_logout_is_per_session():
    first_client = TestClient(app)
    second_client = TestClient(app)
    assert sign_in(first_client).status_code == 200
    first_token = first_client.cookies.get("courseagent_session")
    assert sign_in(second_client).status_code == 200
    second_token = second_client.cookies.get("courseagent_session")

    assert first_token != second_token
    assert first_client.get("/api/auth/me").status_code == 200
    assert second_client.get("/api/auth/me").status_code == 200

    assert first_client.post("/api/auth/logout").status_code == 204
    assert first_client.get("/api/auth/me").status_code == 401
    assert second_client.get("/api/auth/me").status_code == 200


def test_expired_session_is_rejected(client):
    assert sign_in(client).status_code == 200
    token = client.cookies.get("courseagent_session")
    token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            "UPDATE auth_sessions SET expires_at = ? WHERE token_hash = ?",
            (expired, token_hash),
        )
    assert client.get("/api/auth/me").status_code == 401


def test_login_requires_a_trusted_origin(client):
    payload = {"email": "test-std-001@test.invalid", "password": PASSWORD}
    missing_origin = client.post("/api/auth/login", json=payload, headers={"Origin": None})
    untrusted_origin = client.post(
        "/api/auth/login",
        json=payload,
        headers={"Origin": "https://attacker.invalid"},
    )
    assert missing_origin.status_code == 403
    assert untrusted_origin.status_code == 403
    assert client.post("/api/auth/login", json=payload).status_code == 200


def test_csrf_protects_logout_and_cookie_authenticated_mutations(client):
    login_response = sign_in(client)
    assert login_response.status_code == 200
    csrf_cookie = client.cookies.get("courseagent_csrf")
    assert csrf_cookie
    csrf_cookie_header = next(
        header.lower()
        for header in login_response.headers.get_list("set-cookie")
        if header.lower().startswith("courseagent_csrf=")
    )
    assert "httponly" not in csrf_cookie_header
    assert "samesite=strict" in csrf_cookie_header

    missing_origin_logout = client.post(
        "/api/auth/logout",
        headers={"Origin": None},
    )
    untrusted_origin_logout = client.post(
        "/api/auth/logout",
        headers={"Origin": "https://attacker.invalid"},
    )
    missing_token_logout = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": None},
    )
    assert missing_origin_logout.status_code == 403
    assert untrusted_origin_logout.status_code == 403
    assert missing_token_logout.status_code == 403
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/auth/me", headers={"Origin": None}).status_code == 200
    assert client.post("/api/auth/logout").status_code == 204


def test_csrf_protects_authenticated_submission_mutations(client):
    assert sign_in(client).status_code == 200
    payload = {
        "assignment_id": "lab1",
        "student_id": "std-001",
        "repository_url": "https://github.com/octocat/CourseAgentCsrfTest",
    }

    missing_origin = client.post(
        "/api/submissions",
        json=payload,
        headers={"Origin": None},
    )
    untrusted_origin = client.post(
        "/api/submissions",
        json=payload,
        headers={"Origin": "https://attacker.invalid"},
    )
    missing_token = client.post(
        "/api/submissions",
        json=payload,
        headers={"X-CSRF-Token": None},
    )
    assert missing_origin.status_code == 403
    assert untrusted_origin.status_code == 403
    assert missing_token.status_code == 403

    trusted_browser_request = client.post("/api/submissions", json=payload)
    assert trusted_browser_request.status_code == 200


def test_session_remains_valid_for_another_client_after_process_style_restart(client):
    assert sign_in(client).status_code == 200
    token = client.cookies.get("courseagent_session")
    restarted_client = TestClient(app)
    restarted_client.cookies.set("courseagent_session", token, path="/")
    response = restarted_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user_id"] == "test-std-001"
    env = os.environ.copy()
    env["COURSEAGENTAI_SESSION_PROBE_TOKEN"] = token
    process_probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; from app.services.auth_service import get_session_user; "
            "user = get_session_user(os.environ['COURSEAGENTAI_SESSION_PROBE_TOKEN']); "
            "print(user['user_id'] if user else 'missing')",
        ],
        cwd=settings.project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process_probe.returncode == 0, process_probe.stderr
    assert process_probe.stdout.strip() == "test-std-001"


def test_student_can_access_own_submission_only_and_headers_do_not_change_identity(client):
    assert sign_in(client).status_code == 200
    submission_id = create_student_submission(client)
    own = client.get("/api/submissions/student/std-001")
    assert own.status_code == 200
    own_detail = client.get(f"/api/submissions/detail/{submission_id}")
    assert own_detail.status_code == 200
    other_history = client.get(
        "/api/submissions/student/std-002",
        headers={"X-Student-Id": "std-002", "X-User-Role": "ADMIN"},
    )
    assert other_history.status_code == 403


def test_forged_role_header_without_session_is_not_authentication(client):
    response = client.get(
        "/api/submissions/faculty",
        headers={"X-User-Role": "ADMIN", "X-Student-Id": "std-001"},
    )
    assert response.status_code == 401
    assert client.get("/api/assignments", headers={"X-User-Role": "ADMIN"}).status_code == 401


def test_student_cannot_review_approve_or_publish_even_with_forged_headers(client):
    assert sign_in(client).status_code == 200
    submission_id = create_student_submission(client)
    headers = {"X-User-Role": "FACULTY"}
    review = client.post(
        f"/api/submissions/{submission_id}/review",
        headers=headers,
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 90,
            "review_feedback": "Test feedback",
            "reviewer_id": "forged-faculty",
        },
    )
    approval = client.post(
        f"/api/submissions/{submission_id}/approve",
        headers=headers,
        json={"reviewer_id": "forged-faculty"},
    )
    publication = client.post(
        f"/api/submissions/{submission_id}/publish",
        headers=headers,
        json={"reviewer_id": "forged-faculty"},
    )
    assert (review.status_code, approval.status_code, publication.status_code) == (403, 403, 403)
    lab6_approval = client.post(
        "/api/lab6/run/not-a-real-run/approve",
        headers=headers,
        json={"approved": True},
    )
    lab7_approval = client.post(
        "/api/lab7/approve/not-a-real-run",
        headers=headers,
        json={"approved": True},
    )
    assert lab6_approval.status_code == 403
    assert lab7_approval.status_code == 403
    forged_submission = client.post(
        "/api/submissions",
        headers={"X-Student-Id": "std-002", "X-User-Role": "FACULTY"},
        json={
            "assignment_id": "lab1",
            "student_id": "std-002",
            "repository_url": "https://github.com/octocat/ImpersonatedSubmission",
        },
    )
    assert forged_submission.status_code == 403


def test_only_scoped_faculty_can_grade_and_admin_student_or_anonymous_users_are_denied(client):
    student_client = TestClient(app)
    assert sign_in(student_client).status_code == 200
    submission_id = create_student_submission(student_client)
    review_path = f"/api/submissions/{submission_id}/review"
    approve_path = f"/api/submissions/{submission_id}/approve"
    publish_path = f"/api/submissions/{submission_id}/publish"
    review_payload = {
        "review_status": "DRAFT_GRADED",
        "review_score": 90,
        "review_feedback": "Course-scoped faculty review.",
    }
    operations = [
        (review_path, review_payload),
        (approve_path, {}),
        (publish_path, {}),
    ]

    for role, email in (
        ("STUDENT", "test-std-001@test.invalid"),
        ("ADMIN", "auth-admin@test.invalid"),
    ):
        denied_client = TestClient(app)
        assert sign_in(denied_client, email).status_code == 200
        assert [denied_client.post(path, json=body).status_code for path, body in operations] == [
            403,
            403,
            403,
        ], role

    unauthenticated = TestClient(app)
    assert [unauthenticated.post(path, json=body).status_code for path, body in operations] == [
        401,
        401,
        401,
    ]

    out_of_scope_faculty = TestClient(app)
    assert sign_in(out_of_scope_faculty, "auth-faculty-other@test.invalid").status_code == 200
    assert [out_of_scope_faculty.post(path, json=body).status_code for path, body in operations] == [
        403,
        403,
        403,
    ]


def test_faculty_scope_authorizes_review_and_blocks_other_courses(client):
    student_client = TestClient(app)
    assert sign_in(student_client).status_code == 200
    submission_id = create_student_submission(student_client)

    faculty_client = TestClient(app)
    assert sign_in(faculty_client, "auth-faculty@test.invalid").status_code == 200
    listed = faculty_client.get("/api/submissions/faculty?course_id=26ECAC401")
    assert listed.status_code == 200
    reviewed = faculty_client.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 91,
            "review_feedback": "Scoped reviewer feedback",
            "reviewer_id": "spoofed-reviewer",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["reviewed_by"] == "auth-faculty"
    assert faculty_client.get("/api/submissions/faculty?course_id=OTHER-COURSE").status_code == 403


def test_admin_only_governance_and_admin_account_access(client):
    assert sign_in(client, "auth-faculty@test.invalid").status_code == 200
    assert client.get("/api/lab12/proposals").status_code == 403
    admin_client = TestClient(app)
    assert sign_in(admin_client, "auth-admin@test.invalid").status_code == 200
    assert admin_client.get("/api/lab12/proposals").status_code == 200
    proposal = admin_client.post(
        "/api/lab12/proposals",
        json={
            "resource_id": "auth-audit-resource",
            "current_value": {"mode": "draft"},
            "proposed_value": {"mode": "approved"},
            "summary": "Check authenticated audit actor",
        },
    )
    assert proposal.status_code == 200
    proposal_id = proposal.json()["data"]["proposal_id"]
    events = admin_client.get(f"/api/lab12/proposals/{proposal_id}/audit").json()["data"]
    assert events[0]["actor"] == "auth-admin"


def test_lab5_uses_authenticated_role_and_cannot_bypass_submission_lifecycle(client):
    assert sign_in(client).status_code == 200
    forged_faculty_write = client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "WRITE",
            "resource_path": "assignments",
            "parameters": {
                "id": "auth-forgery-must-not-write",
                "title": "Must remain unauthorized",
            },
            "client_role": "FACULTY",
        },
    )
    assert forged_faculty_write.status_code == 200
    assert forged_faculty_write.json()["data"]["authorized_role"] == "STUDENT"
    assert forged_faculty_write.json()["data"]["success"] is False
    assert client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "LIST",
            "resource_path": "students",
            "client_role": "FACULTY",
        },
    ).status_code == 403

    faculty_client = TestClient(app)
    assert sign_in(faculty_client, "auth-faculty@test.invalid").status_code == 200
    assert faculty_client.post(
        "/api/lab5/execute",
        json={
            "source_id": "sqlite_source",
            "operation": "WRITE",
            "resource_path": "submissions",
            "parameters": {"id": "bypass-lifecycle"},
        },
    ).status_code == 403


def test_student_project_data_is_member_scoped_and_faculty_course_scoped(client):
    faculty_client = TestClient(app)
    assert sign_in(faculty_client, "auth-faculty@test.invalid").status_code == 200
    created = faculty_client.post(
        "/api/projects",
        json={
            "title": "Scoped auth test project",
            "description": "Project fixture for authenticated membership checks.",
            "course_id": "26ECAC401",
            "members": [{"student_id": "std-001", "student_name": "Student One"}],
            "milestones": [],
        },
    )
    assert created.status_code == 200
    project_id = created.json()["data"]["id"]

    owner_client = TestClient(app)
    assert sign_in(owner_client, "test-std-001@test.invalid").status_code == 200
    assert owner_client.get(f"/api/projects/{project_id}").status_code == 200

    other_student = TestClient(app)
    assert sign_in(other_student, "test-std-002@test.invalid").status_code == 200
    assert other_student.get(f"/api/projects/{project_id}").status_code == 403
    assert all(
        project["id"] != project_id
        for project in other_student.get("/api/projects").json()["data"]
    )

    out_of_scope_faculty = TestClient(app)
    assert sign_in(out_of_scope_faculty, "auth-faculty-other@test.invalid").status_code == 200
    assert out_of_scope_faculty.get("/api/projects?course_id=26ECAC401").status_code == 403


def test_student_assignment_scope_and_admin_audit_authorization(client):
    assert sign_in(client).status_code == 200
    assert client.get("/api/assignments").status_code == 200
    assert client.get("/api/assignments?course_id=OTHER-COURSE").status_code == 403
    assert client.get("/api/system/audit").status_code == 403

    administrator = TestClient(app)
    assert sign_in(administrator, "auth-admin@test.invalid").status_code == 200
    assert administrator.get("/api/system/audit").status_code == 200


def test_environment_based_account_initialization_creates_only_hash(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_PATH": str(tmp_path / "auth-bootstrap.sqlite3"),
            "COURSEAGENTAI_INIT_USER_ID": "bootstrap-student",
            "COURSEAGENTAI_INIT_EMAIL": "bootstrap-student@test.invalid",
            "COURSEAGENTAI_INIT_DISPLAY_NAME": "Bootstrap Student",
            "COURSEAGENTAI_INIT_ROLE": "STUDENT",
            "COURSEAGENTAI_INIT_STUDENT_ID": "std-001",
            "COURSEAGENTAI_INIT_PASSWORD": PASSWORD,
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "scripts.initialize_auth_user"],
        cwd=settings.project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "bootstrap-student@test.invalid" in result.stdout
    conn = sqlite3.connect(env["DATABASE_PATH"])
    try:
        stored_hash = conn.execute(
            "SELECT password_hash FROM auth_users WHERE user_id = 'bootstrap-student'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert stored_hash.startswith("$argon2id$")
    assert stored_hash != PASSWORD


def test_login_throttling_after_repeated_failures(client):
    with get_db_connection(immediate=True) as conn:
        conn.execute("DELETE FROM auth_login_limits")
    for _ in range(5):
        response = sign_in(client, "test-std-002@test.invalid", "wrong-password")
        assert response.status_code == 401
    assert sign_in(client, "test-std-002@test.invalid").status_code == 429
