"""API endpoint tests for Lab 4: Memory & Retrieval."""

import hashlib
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.data.db import get_db_connection
from app.services.auth_service import create_user
from tests.conftest import AuthTestClient


_PASSWORD = "courseagent-test-password"


def _ensure_test_user(user_id, course_scopes=None):
    try:
        create_user(
            user_id=user_id,
            email=f"{user_id}@test.invalid",
            display_name=user_id,
            password=_PASSWORD,
            role="FACULTY",
            course_scopes=course_scopes or ["26ECAC401"],
        )
    except sqlite3.IntegrityError:
        pass


@pytest.fixture
def client():
    test_client = TestClient(app)
    _ensure_test_user("lab4-test-owner")
    assert test_client.post(
        "/api/auth/login",
        json={"email": "lab4-test-owner@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    return test_client


def test_api_lab4_session_lifecycle(client):
    """POST /api/lab4/session/create creates session and GET /session/{id} returns state."""
    resp = client.post("/api/lab4/session/create", json={"course_id": "26ECAC401"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    sid = data["data"]["session_id"]

    # Retrieve session
    get_resp = client.get(f"/api/lab4/session/{sid}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["success"] is True
    assert get_data["data"]["session"]["session_id"] == sid

    # Clear session
    clear_resp = client.post(f"/api/lab4/session/{sid}/clear")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["data"]["cleared"] is True


def test_api_lab4_retrieval_search(client):
    """POST /api/lab4/retrieval/search returns grounded course notes."""
    payload = {
        "query": "What is Plan-Act-Observe-Revise?",
        "course_id": "26ECAC401",
        "top_k": 3,
    }
    resp = client.post("/api/lab4/retrieval/search", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    search_data = body["data"]
    assert search_data["match_count"] >= 1
    assert any(m["chapter"] == 1 for m in search_data["matches"])
    assert all(m["source_document"] and m["source"] for m in search_data["matches"])

    tagged = client.post(
        "/api/lab4/retrieval/search",
        json={
            "query": "Plan Act Observe Revise",
            "course_id": "26ECAC401",
            "tags": ["chapter-1"],
            "top_k": 5,
        },
    )
    assert tagged.status_code == 200
    assert tagged.json()["data"]["match_count"] > 0
    assert all("chapter-1" in match["tags"] for match in tagged.json()["data"]["matches"])


def test_api_lab4_chapters_and_tags(client):
    """GET /api/lab4/retrieval/chapters and /tags return indexed metadata."""
    ch_resp = client.get("/api/lab4/retrieval/chapters")
    assert ch_resp.status_code == 200
    assert len(ch_resp.json()["data"]) >= 2

    tags_resp = client.get("/api/lab4/retrieval/tags")
    assert tags_resp.status_code == 200
    assert len(tags_resp.json()["data"]) >= 5


def test_api_lab4_agent_query(client):
    """POST /api/lab4/query maintains session turns while grounding in notes."""
    payload = {
        "query": "What does Chapter 2 cover regarding tools and memory?",
        "course_id": "26ECAC401",
    }
    resp = client.post("/api/lab4/query", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["long_term_matches_found"] >= 1
    assert body["data"]["short_term_turn_count"] >= 2


def test_lab4_session_access_is_bound_to_authenticated_owner(client):
    created = client.post(
        "/api/lab4/session/create",
        json={"course_id": "26ECAC401", "user_id": "forged-owner"},
    )
    assert created.status_code == 200
    session = created.json()["data"]
    session_id = session["session_id"]
    assert session["user_id"] == "lab4-test-owner"

    other_user = TestClient(app)
    _ensure_test_user("lab4-test-other")
    assert other_user.post(
        "/api/auth/login",
        json={"email": "lab4-test-other@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    assert other_user.get(f"/api/lab4/session/{session_id}").status_code == 404
    assert other_user.post(
        f"/api/lab4/session/{session_id}/turn",
        json={"role": "user", "content": "unauthorized"},
    ).status_code == 404
    assert other_user.post(
        f"/api/lab4/session/{session_id}/scratchpad",
        json={"key": "private", "value": "unauthorized"},
    ).status_code == 404
    assert other_user.post(f"/api/lab4/session/{session_id}/clear").status_code == 404
    assert other_user.delete(f"/api/lab4/session/{session_id}").status_code == 404
    assert other_user.post(
        "/api/lab4/session/create",
        json={"session_id": session_id, "course_id": "26ECAC401"},
    ).status_code == 404
    listed = other_user.get("/api/lab4/sessions").json()["data"]
    assert all(item["session_id"] != session_id for item in listed)


def test_lab4_session_same_owner_can_manage_session(client):
    created = client.post("/api/lab4/session/create", json={"course_id": "26ECAC401"})
    assert created.status_code == 200
    session_id = created.json()["data"]["session_id"]

    appended = client.post(
        f"/api/lab4/session/{session_id}/turn",
        json={"role": "user", "content": "owner turn"},
    )
    assert appended.status_code == 200
    updated = client.post(
        f"/api/lab4/session/{session_id}/scratchpad",
        json={"key": "pacing", "value": "12 weeks"},
    )
    assert updated.status_code == 200

    fetched = client.get(f"/api/lab4/session/{session_id}")
    assert fetched.status_code == 200
    assert len(fetched.json()["data"]["session"]["dialogue_turns"]) == 1
    assert fetched.json()["data"]["session"]["scratchpad"]["pacing"] == "12 weeks"
    listed = client.get("/api/lab4/sessions").json()["data"]
    assert any(item["session_id"] == session_id for item in listed)
    assert client.post(f"/api/lab4/session/{session_id}/clear").json()["data"]["cleared"] is True
    assert client.delete(f"/api/lab4/session/{session_id}").json()["data"]["deleted"] is True
    assert client.get(f"/api/lab4/session/{session_id}").status_code == 404


def test_lab4_session_routes_require_authentication_and_course_access():
    anonymous = TestClient(app)
    assert anonymous.post("/api/lab4/session/create", json={}).status_code == 401
    assert anonymous.get("/api/lab4/sessions").status_code == 401

    _ensure_test_user("lab4-test-unscoped", ["OTHER-COURSE"])
    unscoped = TestClient(app)
    assert unscoped.post(
        "/api/auth/login",
        json={"email": "lab4-test-unscoped@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    assert unscoped.post(
        "/api/lab4/session/create",
        json={"course_id": "26ECAC401"},
    ).status_code == 403


def test_lab4_retrieval_routes_require_authentication_and_course_access():
    anonymous = TestClient(app)
    assert anonymous.post(
        "/api/lab4/retrieval/search",
        json={"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401"},
    ).status_code == 401
    for path in ("/api/lab4/retrieval/chapters", "/api/lab4/retrieval/tags", "/api/lab4/scenarios"):
        assert anonymous.get(path).status_code == 401

    _ensure_test_user("lab4-retrieval-unscoped", ["OTHER-COURSE"])
    unscoped = TestClient(app)
    assert unscoped.post(
        "/api/auth/login",
        json={"email": "lab4-retrieval-unscoped@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    assert unscoped.post(
        "/api/lab4/retrieval/search",
        json={"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401"},
    ).status_code == 403
    for path in ("/api/lab4/retrieval/chapters", "/api/lab4/retrieval/tags", "/api/lab4/scenarios"):
        assert unscoped.get(path).status_code == 403
    other_course = unscoped.post(
        "/api/lab4/retrieval/search",
        json={"query": "Plan-Act-Observe-Revise", "course_id": "OTHER-COURSE"},
    )
    assert other_course.status_code == 200
    assert other_course.json()["data"]["match_count"] == 0
    assert unscoped.post(
        "/api/lab4/retrieval/memories",
        json={
            "course_id": "26ECAC401",
            "title": "Private memory",
            "content": "This memory is outside the requester's course scope.",
        },
    ).status_code == 403


def test_long_term_memories_are_explicit_persistent_tagged_and_owner_scoped(client):
    saved = client.post(
        "/api/lab4/retrieval/memories",
        json={
            "course_id": "26ECAC401",
            "title": "Lab 4 rubric evidence",
            "content": "Rubric scores need feedback linked to assignment evidence and criteria.",
            "tags": ["rubric", "grading"],
        },
    )
    assert saved.status_code == 200, saved.text
    memory = saved.json()["data"]

    query = {
        "course_id": "26ECAC401",
        "query": "rubric scores feedback criteria",
        "tags": ["grading"],
        "top_k": 5,
    }
    matches = client.post("/api/lab4/retrieval/memories/similar", json=query)
    assert matches.status_code == 200
    result = matches.json()["data"]
    assert result["match_count"] == 1
    assert result["matches"][0]["memory_id"] == memory["memory_id"]
    assert result["matches"][0]["similarity_score"] > 0
    assert result["embedding_similarity"] is False

    other_user = TestClient(app)
    _ensure_test_user("lab4-memory-other")
    assert other_user.post(
        "/api/auth/login",
        json={"email": "lab4-memory-other@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    hidden = other_user.post("/api/lab4/retrieval/memories/similar", json=query)
    assert hidden.status_code == 200
    assert hidden.json()["data"]["match_count"] == 0
    assert other_user.delete(
        f"/api/lab4/retrieval/memories/{memory['memory_id']}?course_id=26ECAC401"
    ).status_code == 404

    # Dialogue is short-term state and must not be copied into the long-term memory table.
    session = client.post("/api/lab4/session/create", json={"course_id": "26ECAC401"}).json()["data"]
    private_turn = f"session-only-{memory['memory_id']}-never-promote"
    assert client.post(
        f"/api/lab4/session/{session['session_id']}/turn",
        json={"role": "user", "content": private_turn},
    ).status_code == 200
    no_promotion = client.post(
        "/api/lab4/retrieval/memories/similar",
        json={"course_id": "26ECAC401", "query": private_turn},
    )
    assert no_promotion.status_code == 200
    assert no_promotion.json()["data"]["match_count"] == 0

    # A new store instance reads the same durable long-term row.
    from app.labs.lab4.knowledge_store import LongTermKnowledgeStore

    restarted = LongTermKnowledgeStore().search_similar_memories(
        user_id="lab4-test-owner",
        course_id="26ECAC401",
        query="rubric feedback",
        tags=["rubric"],
    )
    assert restarted["match_count"] == 1
    assert restarted["matches"][0]["memory_id"] == memory["memory_id"]

    assert client.delete(
        f"/api/lab4/retrieval/memories/{memory['memory_id']}?course_id=26ECAC401"
    ).status_code == 200


def test_student_memories_are_not_retrievable_by_another_student():
    student_a = AuthTestClient(app)
    student_b = AuthTestClient(app)
    a_headers = {"X-User-Role": "STUDENT", "X-Student-Id": "std-001"}
    b_headers = {"X-User-Role": "STUDENT", "X-Student-Id": "std-002"}
    saved = student_a.post(
        "/api/lab4/retrieval/memories",
        json={
            "course_id": "26ECAC401",
            "title": "Student A private notes",
            "content": "Private retrieval experiment about vector index isolation.",
            "tags": ["private"],
        },
        headers=a_headers,
    )
    assert saved.status_code == 200, saved.text
    query = {
        "course_id": "26ECAC401",
        "query": "private retrieval experiment vector index isolation",
        "tags": ["private"],
    }
    assert student_a.post(
        "/api/lab4/retrieval/memories/similar",
        json=query,
        headers=a_headers,
    ).json()["data"]["match_count"] == 1
    hidden = student_b.post(
        "/api/lab4/retrieval/memories/similar",
        json=query,
        headers=b_headers,
    )
    assert hidden.status_code == 200
    assert hidden.json()["data"]["match_count"] == 0
    assert student_b.delete(
        f"/api/lab4/retrieval/memories/{saved.json()['data']['memory_id']}?course_id=26ECAC401",
        headers=b_headers,
    ).status_code == 404


def test_prior_submission_retrieval_respects_student_and_faculty_course_scope(client, monkeypatch):
    student_client = AuthTestClient(app)
    submissions = [
        (
            "std-001",
            "https://github.com/alice/lab4-memory-a",
            "distinctive vector retrieval session checkpoint evidence",
        ),
        (
            "std-002",
            "https://github.com/bob/lab4-memory-b",
            "unrelated greenhouse robotics sensor calibration",
        ),
    ]
    for student_id, repository_url, notes in submissions:
        response = student_client.post(
            "/api/submissions",
            json={
                "assignment_id": "lab4",
                "student_id": student_id,
                "repository_url": repository_url,
                "notes": notes,
            },
            headers={"X-User-Role": "STUDENT", "X-Student-Id": student_id},
        )
        assert response.status_code == 200, response.text

    query = {
        "course_id": "26ECAC401",
        "query": "vector retrieval session checkpoint evidence",
        "top_k": 10,
    }
    student_a = student_client.post(
        "/api/lab4/retrieval/submissions/similar",
        json=query,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert student_a.status_code == 200
    own_matches = student_a.json()["data"]["matches"]
    assert own_matches
    assert {item["student_id"] for item in own_matches} == {"std-001"}
    assert all(item["citation"]["source_location"].startswith("/api/submissions/detail/") for item in own_matches)
    assert student_a.json()["data"]["source_code_analyzed"] is False

    student_b = student_client.post(
        "/api/lab4/retrieval/submissions/similar",
        json=query,
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-002"},
    )
    assert student_b.status_code == 200
    assert all(item["student_id"] == "std-002" for item in student_b.json()["data"]["matches"])

    faculty_matches = client.post(
        "/api/lab4/retrieval/submissions/similar",
        json=query,
    )
    assert faculty_matches.status_code == 200
    assert {"std-001", "std-002"}.issubset(
        {item["student_id"] for item in faculty_matches.json()["data"]["matches"]}
    )

    import numpy as np
    from app.api.routes_lab4 import long_term_store

    class ScopedTestEncoder:
        model_id = "test/scoped-submission-model"
        model_revision = "test-revision-1"
        dimension = 3

        def __init__(self):
            self.encoded_texts = []

        def encode(self, texts):
            self.encoded_texts.extend(texts)
            return np.asarray(
                [
                    [0.0, 1.0, 0.0] if "greenhouse" in text.casefold() else [1.0, 0.0, 0.0]
                    for text in texts
                ],
                dtype=np.float32,
            )

    monkeypatch.setattr(long_term_store, "_embedding_service", ScopedTestEncoder())
    semantic_student = student_client.post(
        "/api/lab4/retrieval/submissions/similar",
        json={**query, "retrieval_mode": "semantic"},
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert semantic_student.status_code == 200
    semantic_result = semantic_student.json()["data"]
    assert semantic_result["retrieval_method"] == "local_sentence_transformer_cosine"
    assert semantic_result["source_code_analyzed"] is False
    assert semantic_result["matches"]
    assert {item["student_id"] for item in semantic_result["matches"]} == {"std-001"}
    assert all("greenhouse" not in text.casefold() for text in long_term_store._embedding_service.encoded_texts)
    assert all(
        item["citation"]["source_location"].startswith("/api/submissions/detail/")
        for item in semantic_result["matches"]
    )

    with get_db_connection() as conn:
        submission = conn.execute(
            """
            SELECT s.id, s.assignment_id, a.title AS assignment_title, s.repo_name, s.notes
            FROM submissions s JOIN assignments a ON a.id = s.assignment_id
            WHERE s.student_id = ? AND s.course_id = ? AND s.repository_url = ?
            """,
            ("std-001", "26ECAC401", "https://github.com/alice/lab4-memory-a"),
        ).fetchone()
    assert submission is not None
    replacement_note = "source text replacement invalidates its cached vector"
    with get_db_connection(immediate=True) as conn:
        conn.execute(
            "UPDATE submissions SET notes = ? WHERE id = ?",
            (replacement_note, submission["id"]),
        )
    refreshed = student_client.post(
        "/api/lab4/retrieval/submissions/similar",
        json={**query, "retrieval_mode": "semantic"},
        headers={"X-User-Role": "STUDENT", "X-Student-Id": "std-001"},
    )
    assert refreshed.status_code == 200
    assert any(replacement_note in text for text in long_term_store._embedding_service.encoded_texts)
    with get_db_connection(immediate=True) as conn:
        updated_source = conn.execute(
            """
            SELECT s.assignment_id, a.title AS assignment_title, s.repo_name, s.notes
            FROM submissions s JOIN assignments a ON a.id = s.assignment_id
            WHERE s.id = ?
            """,
            (submission["id"],),
        ).fetchone()
        from app.labs.lab4.knowledge_store import LongTermKnowledgeStore

        updated_text = LongTermKnowledgeStore._submission_embedding_text(dict(updated_source))
        embedding = conn.execute(
            "SELECT text_hash FROM lab4_submission_embeddings WHERE submission_id = ?",
            (submission["id"],),
        ).fetchone()
        assert embedding["text_hash"] == hashlib.sha256(updated_text.encode("utf-8")).hexdigest()
        conn.execute("DELETE FROM submissions WHERE id = ?", (submission["id"],))
        assert conn.execute(
            "SELECT 1 FROM lab4_submission_embeddings WHERE submission_id = ?",
            (submission["id"],),
        ).fetchone() is None

    unscoped_user = TestClient(app)
    _ensure_test_user("lab4-submission-unscoped", ["OTHER-COURSE"])
    assert unscoped_user.post(
        "/api/auth/login",
        json={"email": "lab4-submission-unscoped@test.invalid", "password": _PASSWORD},
    ).status_code == 200
    assert unscoped_user.post(
        "/api/lab4/retrieval/submissions/similar",
        json=query,
    ).status_code == 403
