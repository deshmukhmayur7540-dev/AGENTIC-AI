"""End-to-End HTTP Simulation of the Frontend User Journey.

Simulates the exact sequence of asynchronous calls made by app.js:
1. Load dashboard (GET /) and static assets (app.js, styles.css).
2. Fetch course assignments (GET /api/assignments) and enrolled students (GET /api/students).
3. Student std-001 checks their submission history (GET /api/submissions/student/std-001).
4. Student submits a new GitHub repository solution (POST /api/submissions).
5. Student history refreshes and confirms the latest attempt pointer.
6. Student attempts duplicate/resubmission with a revised commit/repo, verifying attempt increment.
7. Unauthorized cross-student inspection attempt (std-002 accessing std-001) is denied (403).
8. Unauthorized student accessing faculty portal is denied (403).
9. Faculty switches to review portal, lists submissions (GET /api/submissions/faculty).
10. Faculty submits review and grade for the submission (POST /api/submissions/{id}/review).
11. Submission record reflects REVIEWED status, score, and feedback.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_complete_frontend_user_journey(client):
    # Step 1: Frontend initial load
    index_resp = client.get("/")
    assert index_resp.status_code == 200
    html_content = index_resp.text
    assert "CourseAgentAI" in html_content
    assert "nav-tab-submissions" in html_content
    assert "sub-github-url-input" in html_content
    assert "faculty-review-modal" in html_content
    assert "Seeded Demo Assignment Data — Not Faculty-Verified" in html_content

    # Verify static assets
    js_resp = client.get("/static/app.js")
    assert js_resp.status_code == 200
    assert "handleSubmitGithubAssignment" in js_resp.text
    assert "loadFacultySubmissions" in js_resp.text

    css_resp = client.get("/static/style.css")
    assert css_resp.status_code == 200

    # Step 2: Populate dropdowns on tab open
    asgns_resp = client.get("/api/assignments")
    assert asgns_resp.status_code == 200
    assignments = asgns_resp.json()["data"]
    assert len(assignments) >= 5
    assignment_id = assignments[0]["id"]

    students_resp = client.get("/api/students")
    assert students_resp.status_code == 200
    students = students_resp.json()["data"]
    assert len(students) == 1
    student_id = "std-001"

    # Step 3: Fetch student history initially
    hist_resp_1 = client.get(
        f"/api/submissions/student/{student_id}",
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert hist_resp_1.status_code == 200
    initial_subs_count = len(hist_resp_1.json()["data"])

    # Step 4: Student submits repository URL
    submit_payload = {
        "assignment_id": assignment_id,
        "student_id": student_id,
        "repository_url": "https://github.com/torvalds/linux",
        "notes": "E2E automated simulation submission",
    }
    submit_resp = client.post(
        "/api/submissions",
        json=submit_payload,
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()["data"]
    submission_id = sub_data["id"]
    assert sub_data["is_latest"] is True
    assert sub_data["repo_name"].lower() == "linux"

    # Step 5: Student history refreshes
    hist_resp_2 = client.get(
        f"/api/submissions/student/{student_id}",
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert hist_resp_2.status_code == 200
    new_subs = hist_resp_2.json()["data"]
    assert len(new_subs) == initial_subs_count + 1

    # Step 6: Resubmission increments attempt
    resubmit_payload = {
        "assignment_id": assignment_id,
        "student_id": student_id,
        "repository_url": "https://github.com/torvalds/linux.git",
        "notes": "Attempt 2 revision",
    }
    resubmit_resp = client.post(
        "/api/submissions",
        json=resubmit_payload,
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert resubmit_resp.status_code == 200
    sub_data_2 = resubmit_resp.json()["data"]
    assert sub_data_2["attempt_number"] == sub_data["attempt_number"] + 1
    assert sub_data_2["is_latest"] is True

    # Step 7: Security check - student std-002 cannot read std-001's history
    tamper_resp = client.get(
        f"/api/submissions/student/{student_id}",
        headers={"X-Student-Id": "std-002", "X-User-Role": "STUDENT"}
    )
    assert tamper_resp.status_code == 403

    # Step 8: Security check - student cannot open faculty portal
    fac_forbidden_resp = client.get(
        "/api/submissions/faculty",
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert fac_forbidden_resp.status_code == 403

    # Step 9: Faculty portal access
    fac_resp = client.get(
        "/api/submissions/faculty",
        headers={"X-User-Role": "FACULTY"}
    )
    assert fac_resp.status_code == 200
    fac_submissions = fac_resp.json()["data"]
    assert len(fac_submissions) >= 1
    target_sub = next((s for s in fac_submissions if s["id"] == sub_data_2["id"]), None)
    assert target_sub is not None

    # Step 10: Faculty evaluates and grades submission
    review_payload = {
        "review_score": 98.0,
        "review_feedback": "Exemplary solution architecture and verified provenance.",
        "reviewer_id": "prof_lead"
    }
    review_resp = client.post(
        f"/api/submissions/{sub_data_2['id']}/review",
        json=review_payload,
        headers={"X-User-Role": "FACULTY"}
    )
    assert review_resp.status_code == 200
    reviewed_data = review_resp.json()["data"]
    assert reviewed_data["status"] == "DRAFT_GRADED"
    assert reviewed_data["review_score"] == 98.0
    assert reviewed_data["reviewed_by"] == "test-faculty"

    # Draft details remain private to faculty until explicit approval and publication.
    detail_resp = client.get(
        f"/api/submissions/detail/{sub_data_2['id']}",
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"}
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()["data"]
    assert detail_data["status"] == "DRAFT_GRADED"
    assert detail_data["review_score"] is None
    assert detail_data["review_feedback"] is None

    approved = client.post(
        f"/api/submissions/{sub_data_2['id']}/approve",
        json={"reviewer_id": "prof_lead"},
        headers={"X-User-Role": "FACULTY"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "APPROVED"
    assert approved.json()["data"]["published_at"] is None

    published = client.post(
        f"/api/submissions/{sub_data_2['id']}/publish",
        json={"reviewer_id": "prof_lead"},
        headers={"X-User-Role": "FACULTY"},
    )
    assert published.status_code == 200
    assert published.json()["data"]["status"] == "PUBLISHED"

    published_detail = client.get(
        f"/api/submissions/detail/{sub_data_2['id']}",
        headers={"X-Student-Id": student_id, "X-User-Role": "STUDENT"},
    )
    assert published_detail.status_code == 200
    assert published_detail.json()["data"]["review_score"] == 98.0
    assert published_detail.json()["data"]["review_feedback"] == review_payload["review_feedback"]
