"""Verify recursive note discovery and original-byte downloads."""

import hashlib
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.knowledge.catalog import KnowledgeFileCatalog
from app.api import routes_knowledge
from app.services.auth_service import create_user
from tests.conftest import AuthTestClient


def test_nested_original_note_download_and_path_rejection():
    client = AuthTestClient(app)
    files = client.get("/api/knowledge/files").json()["data"]["files"]
    record = next(item for item in files if item["filename"] == "sample note with spaces.txt")
    source = Path("knowledge") / Path(record["relative_path"])
    response = client.get(f"/api/knowledge/files/{record['file_id']}/download")
    assert response.status_code == 200
    assert response.content == source.read_bytes()
    assert hashlib.sha256(response.content).digest() == hashlib.sha256(source.read_bytes()).digest()
    assert "filename*=UTF-8''sample%20note%20with%20spaces.txt" in response.headers["content-disposition"]
    assert client.get("/api/knowledge/files/..%2Fapp%2Fmain.py/download").status_code == 404
    assert client.get("/api/knowledge/files/not-a-server-issued-id/download").status_code == 404


def test_every_listed_note_download_matches_original_bytes():
    client = AuthTestClient(app)
    response = client.get("/api/knowledge/files")
    assert response.status_code == 200
    records = response.json()["data"]["files"]
    assert records

    root = Path("knowledge").resolve()
    for record in records:
        source = (root / record["relative_path"]).resolve()
        assert source.is_relative_to(root)
        original = source.read_bytes()
        download = client.get(f"/api/knowledge/files/{record['file_id']}/download")
        assert download.status_code == 200, record["relative_path"]
        assert download.content == original, record["relative_path"]
        assert hashlib.sha256(download.content).digest() == hashlib.sha256(original).digest()
        assert download.headers["content-type"].startswith(record["content_type"])
        assert record["filename"] in download.headers["content-disposition"]


def test_download_returns_not_found_if_catalogued_source_disappears(tmp_path, monkeypatch):
    note = tmp_path / "chapter_1" / "note with spaces.txt"
    note.parent.mkdir(parents=True)
    note.write_bytes(b"disposable note bytes")
    catalog = KnowledgeFileCatalog(tmp_path)
    record = catalog.list_files()[0]
    monkeypatch.setattr(routes_knowledge, "_catalog", catalog)
    note.unlink()

    response = AuthTestClient(app).get(f"/api/knowledge/files/{record.file_id}/download")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def _protected_knowledge_get_paths(file_id):
    return [
        "/api/knowledge/tree",
        "/api/knowledge/files",
        f"/api/knowledge/files/{file_id}",
        f"/api/knowledge/files/{file_id}/preview",
        f"/api/knowledge/files/{file_id}/download",
        "/api/knowledge/stats",
        "/api/knowledge/health-detail",
    ]


def test_knowledge_catalog_gets_require_verified_authentication_and_course_scope():
    record = routes_knowledge._catalog.list_files()[0]
    paths = _protected_knowledge_get_paths(record.file_id)

    anonymous = TestClient(app)
    for path in paths:
        response = anonymous.get(
            path,
            headers={"X-User-Role": "ADMIN", "X-Student-ID": "std-001"},
        )
        assert response.status_code == 401, path

    authorized = AuthTestClient(app)
    for path in paths:
        response = authorized.get(path)
        assert response.status_code == 200, path

    user_id = "test-knowledge-other-course"
    email = f"{user_id}@test.invalid"
    password = "knowledge-scope-test-password"
    try:
        create_user(
            user_id=user_id,
            email=email,
            display_name="Other Course Faculty",
            password=password,
            role="FACULTY",
            course_scopes=["OTHER-COURSE"],
        )
    except sqlite3.IntegrityError:
        pass

    other_course = TestClient(app)
    login = other_course.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    for path in paths:
        response = other_course.get(path)
        assert response.status_code == 403, path
        assert record.filename not in response.text, path
        assert response.content != (
            Path("knowledge") / record.relative_path
        ).read_bytes(), path


def test_unhandled_exception_is_logged_and_response_is_sanitized(monkeypatch, caplog):
    secret = "private-exception-detail-C:\\server\\private\\file.py"

    def fail_catalog_read():
        raise RuntimeError(secret)

    monkeypatch.setattr(routes_knowledge._catalog, "get_folder_tree", fail_catalog_read)
    with caplog.at_level("ERROR", logger="app.main"):
        client = AuthTestClient(app, raise_server_exceptions=False)
        response = client.get("/api/knowledge/tree")

    assert response.status_code == 500
    body = response.text
    assert secret not in body
    assert "private-exception-detail" not in body
    assert "C:\\server\\private\\file.py" not in body
    assert "target" not in response.json()["error"]
    assert "details" not in response.json()["error"]
    assert response.json()["error"]["message"] == (
        "An unexpected error occurred. Please try again later."
    )
    assert secret in caplog.text
    assert "Traceback" in caplog.text
