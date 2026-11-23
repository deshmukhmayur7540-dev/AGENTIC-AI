"""Tests for authenticated notifications, project delivery, and course announcements."""

import uuid

from fastapi.testclient import TestClient

from app.data.db import get_db_connection
from app.main import app
from tests.conftest import AuthTestClient


def _session_headers(role: str, student_id: str | None = None) -> dict[str, str]:
    headers = {"X-User-Role": role}
    if student_id:
        headers["X-Student-Id"] = student_id
    return headers


def _insert_notification(user_id: str, user_role: str, title: str) -> str:
    notification_id = f"test-notif-{uuid.uuid4().hex}"
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO notifications
                (id, user_id, user_role, title, message, category, is_read, link, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL, datetime('now'))
            """,
            (notification_id, user_id, user_role, title, "test message", "TEST"),
        )
    return notification_id


def test_notification_list_unread_and_mark_read_are_recipient_scoped():
    student_one = AuthTestClient(app)
    student_two = AuthTestClient(app)
    own_id = _insert_notification("std-001", "STUDENT", "Own notification")
    other_user_id = _insert_notification("std-002", "STUDENT", "Other student's notification")
    other_role_id = _insert_notification("std-001", "FACULTY", "Same ID, other role")

    response = student_one.get(
        "/api/notifications?user_id=std-002&user_role=FACULTY",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert response.status_code == 200
    listed_ids = {item["id"] for item in response.json()["data"]}
    assert own_id in listed_ids
    assert other_user_id not in listed_ids
    assert other_role_id not in listed_ids

    unread_response = student_one.get(
        "/api/notifications/unread",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert unread_response.status_code == 200
    assert own_id in {item["id"] for item in unread_response.json()["data"]}

    denied = student_one.post(
        f"/api/notifications/{other_user_id}/read",
        json={"user_id": "std-002"},
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert denied.status_code == 404
    cross_role_denied = student_one.post(
        f"/api/notifications/{other_role_id}/read",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert cross_role_denied.status_code == 404
    with get_db_connection() as conn:
        cross_role_row = conn.execute(
            "SELECT is_read FROM notifications WHERE id = ?",
            (other_role_id,),
        ).fetchone()
    assert cross_role_row["is_read"] == 0

    marked = student_one.post(
        f"/api/notifications/{own_id}/read",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert marked.status_code == 200
    assert marked.json()["data"]["is_read"] == 1
    assert own_id not in {
        item["id"]
        for item in student_one.get(
            "/api/notifications/unread",
            headers=_session_headers("STUDENT", "std-001"),
        ).json()["data"]
    }

    other_unread = student_two.get(
        "/api/notifications/unread",
        headers=_session_headers("STUDENT", "std-002"),
    ).json()["data"]
    assert other_id_exists(other_unread, other_user_id)


def other_id_exists(notifications: list[dict], expected_id: str) -> bool:
    return any(item["id"] == expected_id for item in notifications)


def test_grade_notification_is_created_only_on_publication():
    student = AuthTestClient(app)
    faculty = AuthTestClient(app)
    submitted = student.post(
        "/api/submissions",
        json={
            "assignment_id": "lab3",
            "student_id": "std-003",
            "repository_url": "https://github.com/octocat/Hello-World",
        },
        headers=_session_headers("STUDENT", "std-003"),
    )
    assert submitted.status_code == 200
    submission_id = submitted.json()["data"]["id"]
    student_headers = _session_headers("STUDENT", "std-003")
    faculty_headers = _session_headers("FACULTY")

    initial = student.get("/api/notifications", headers=student_headers).json()["data"]
    initial_grade_ids = {item["id"] for item in initial if item["category"] == "GRADE"}

    draft = faculty.post(
        f"/api/submissions/{submission_id}/review",
        json={
            "review_status": "DRAFT_GRADED",
            "review_score": 87,
            "review_feedback": "Private draft feedback",
        },
        headers=faculty_headers,
    )
    assert draft.status_code == 200
    assert draft.json()["data"]["review_status"] == "DRAFT_GRADED"

    approved = faculty.post(
        f"/api/submissions/{submission_id}/approve",
        json={},
        headers=faculty_headers,
    )
    assert approved.status_code == 200
    after_approval = student.get("/api/notifications", headers=student_headers).json()["data"]
    assert {item["id"] for item in after_approval if item["category"] == "GRADE"} == initial_grade_ids

    published = faculty.post(
        f"/api/submissions/{submission_id}/publish",
        json={},
        headers=faculty_headers,
    )
    assert published.status_code == 200
    after_publication = student.get("/api/notifications", headers=student_headers).json()["data"]
    grade_notifications = [item for item in after_publication if item["category"] == "GRADE"]
    assert len(grade_notifications) == len(initial_grade_ids) + 1
    assert any(item["title"] == "Grade published" for item in grade_notifications)


def test_project_milestone_and_comment_events_notify_members_not_actor():
    client = AuthTestClient(app)
    created = client.post(
        "/api/projects",
        json={
            "title": "Notification test project",
            "description": "A project created to test member notifications.",
            "course_id": "26ECAC401",
            "members": [
                {"student_id": "std-001", "student_name": "Alice"},
                {"student_id": "std-002", "student_name": "Bob"},
            ],
            "milestones": [
                {
                    "title": "Notification milestone",
                    "description": "Track project changes.",
                    "due_date": "2027-01-01",
                }
            ],
        },
        headers=_session_headers("FACULTY"),
    )
    assert created.status_code == 200
    project = created.json()["data"]
    project_id = project["id"]
    milestone_id = project["milestones"][0]["id"]

    comment = client.post(
        f"/api/projects/{project_id}/milestones/{milestone_id}/comments",
        json={"comment": "Review notes are ready."},
        headers=_session_headers("FACULTY"),
    )
    assert comment.status_code == 200

    student_one = AuthTestClient(app)
    student_two = AuthTestClient(app)
    one_items = student_one.get("/api/notifications", headers=_session_headers("STUDENT", "std-001")).json()["data"]
    two_items = student_two.get("/api/notifications", headers=_session_headers("STUDENT", "std-002")).json()["data"]
    assert any(item["title"] == "New project milestone comment" for item in one_items)
    assert any(item["title"] == "New project milestone comment" for item in two_items)
    one_project_count = sum(item["category"] == "PROJECT" for item in one_items)

    update = student_one.put(
        f"/api/projects/{project_id}/milestones/{milestone_id}",
        json={"status": "IN_PROGRESS"},
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert update.status_code == 200

    one_after = student_one.get("/api/notifications", headers=_session_headers("STUDENT", "std-001")).json()["data"]
    two_after = student_two.get("/api/notifications", headers=_session_headers("STUDENT", "std-002")).json()["data"]
    assert sum(item["category"] == "PROJECT" for item in one_after) == one_project_count
    assert sum(item["category"] == "PROJECT" for item in two_after) == sum(
        item["category"] == "PROJECT" for item in two_items
    ) + 1
    assert any(item["title"] == "Project milestone updated" for item in two_after)


def test_announcements_are_authenticated_and_course_scoped():
    anonymous = TestClient(app)
    assert anonymous.get("/api/announcements").status_code == 401

    student = AuthTestClient(app)
    allowed = student.get(
        "/api/announcements?course_id=26ECAC401",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]
    assert all(item["course_id"] == "26ECAC401" for item in allowed.json()["data"])

    denied = student.get(
        "/api/announcements?course_id=another-course",
        headers=_session_headers("STUDENT", "std-001"),
    )
    assert denied.status_code == 403
