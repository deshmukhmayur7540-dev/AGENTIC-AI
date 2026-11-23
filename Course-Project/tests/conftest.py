"""Shared test isolation and external-service safeguards."""

import os
import shutil
import sys
import tempfile
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="courseagentai-tests-"))
os.environ["DATABASE_PATH"] = str(_TEST_DATA_DIR / "governed_academic_test.db")
os.environ["COURSEAGENTAI_CORS_ORIGINS"] = (
    "http://testserver,http://127.0.0.1:8000,http://localhost:8000"
)

from app.data.db import init_database

init_database()

from app.labs.lab5.governed_connector import governed_connector
from app.labs.lab12.governance import governed_change_store

governed_connector.initialize()
governed_change_store.initialize()

_TEST_PASSWORD = "courseagent-test-password"
_TEST_TOKENS = {}
_TEST_CSRF_TOKEN = "test-only-csrf-token"


def _test_session(role, student_id=None):
    from app.services.auth_service import authenticate, create_user

    normalized_role = role.upper()
    if normalized_role == "STUDENT":
        student_id = student_id if student_id in {"std-001", "std-002", "std-003", "std-004"} else "std-001"
        user_id = f"test-{student_id}"
        email = f"{user_id}@test.invalid"
        display_name = f"Test {student_id}"
        scopes = []
    elif normalized_role == "FACULTY":
        user_id = "test-faculty"
        email = "test-faculty@test.invalid"
        display_name = "Test Faculty"
        student_id = None
        scopes = ["26ECAC401"]
    elif normalized_role == "ADMIN":
        user_id = "test-admin"
        email = "test-admin@test.invalid"
        display_name = "Test Admin"
        student_id = None
        scopes = []
    else:
        raise ValueError(f"Unsupported test role: {role}")

    if user_id not in _TEST_TOKENS:
        try:
            create_user(
                user_id=user_id,
                email=email,
                display_name=display_name,
                password=_TEST_PASSWORD,
                role=normalized_role,
                student_id=student_id,
                course_scopes=scopes,
            )
        except sqlite3.IntegrityError:
            pass
        authenticated = authenticate(email, _TEST_PASSWORD, f"test-client-{user_id}")
        if not authenticated:
            raise RuntimeError(f"Could not create the test {normalized_role} session.")
        _TEST_TOKENS[user_id] = authenticated[1]
    return _TEST_TOKENS[user_id]


class AuthTestClient(TestClient):
    """Translate legacy test-only role selectors into real server-issued sessions."""

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self._use_session("STUDENT", "std-001")

    def _use_session(self, role, student_id=None):
        self.cookies.set("courseagent_session", _test_session(role, student_id), path="/")
        self.cookies.set("courseagent_csrf", _TEST_CSRF_TOKEN, path="/")

    def request(self, method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        role = next((value for key, value in headers.items() if key.lower() == "x-user-role"), None)
        student_id = next((value for key, value in headers.items() if key.lower() == "x-student-id"), None)
        if role:
            self._use_session(role, student_id)
        kwargs["headers"] = {
            key: value for key, value in headers.items()
            if key.lower() not in {"x-user-role", "x-student-id"}
        }
        return super().request(method, url, **kwargs)


@pytest.fixture(autouse=True)
def add_test_browser_security_headers(monkeypatch):
    """Model same-origin browser requests while allowing explicit CSRF-negative cases."""
    original_request = TestClient.request
    missing = object()

    def request_with_security_headers(client, method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        origin_key = next((key for key in headers if key.lower() == "origin"), None)
        origin = headers.pop(origin_key) if origin_key is not None else missing
        if origin is missing:
            headers["Origin"] = "http://testserver"
        elif origin is not None:
            headers["Origin"] = origin

        csrf_key = next((key for key in headers if key.lower() == "x-csrf-token"), None)
        csrf_header = headers.pop(csrf_key) if csrf_key is not None else missing
        if csrf_header is missing:
            csrf_cookie = client.cookies.get("courseagent_csrf")
            if csrf_cookie:
                headers["X-CSRF-Token"] = csrf_cookie
        elif csrf_header is not None:
            headers["X-CSRF-Token"] = csrf_header

        kwargs["headers"] = headers
        return original_request(client, method, url, **kwargs)

    monkeypatch.setattr(TestClient, "request", request_with_security_headers)


@pytest.fixture(autouse=True)
def disable_external_github_access(monkeypatch):
    """Keep submission workflows deterministic and offline in automated tests."""
    from app.services import submission_service

    async def unverified_repository(*args, **kwargs):
        return "WARNING", {
            "reachable": "UNVERIFIED",
            "note": "Remote repository checks are disabled in automated tests.",
        }

    monkeypatch.setattr(
        submission_service,
        "check_remote_repository_access",
        unverified_repository,
    )


@pytest.fixture(autouse=True)
def isolate_login_throttle_state():
    """Keep rate-limit behavior local to each test while preserving in-test assertions."""
    yield
    from app.data.db import get_db_connection

    with get_db_connection(immediate=True) as conn:
        conn.execute("DELETE FROM auth_login_limits")


def pytest_unconfigure(config):
    """Close the test database before removing this run's private temp directory."""
    connector_module = sys.modules.get("app.labs.lab5.governed_connector")
    if connector_module is not None:
        connector_module.governed_connector.close()
    shutil.rmtree(_TEST_DATA_DIR)
