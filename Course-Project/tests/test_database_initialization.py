"""Regression tests for explicit and import-safe database initialization."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.data.db import init_database
from app.main import app
from config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORT_PROBE = "import app.data.db; import app.main"


def _import_environment(database_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_PATH"] = str(database_path)
    return env


def _run_import_probe(database_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", IMPORT_PROBE],
        cwd=PROJECT_ROOT,
        env=_import_environment(database_path),
        capture_output=True,
        text=True,
        check=False,
    )


def test_importing_database_and_application_does_not_create_database(tmp_path):
    database_path = tmp_path / "not-created.sqlite3"

    result = _run_import_probe(database_path)

    assert result.returncode == 0, result.stderr
    assert not database_path.exists()


def test_importing_database_and_application_does_not_modify_existing_database(tmp_path):
    database_path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE import_probe (value TEXT NOT NULL)")
        connection.execute("INSERT INTO import_probe (value) VALUES ('preserve me')")
    original_bytes = database_path.read_bytes()

    result = _run_import_probe(database_path)

    assert result.returncode == 0, result.stderr
    assert database_path.read_bytes() == original_bytes


def test_explicit_initialization_creates_schema_in_disposable_database(monkeypatch, tmp_path):
    database_path = tmp_path / "explicit-init.sqlite3"
    monkeypatch.setattr(settings, "database_path", str(database_path))

    init_database()

    assert database_path.exists()
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        category_count = connection.execute(
            "SELECT COUNT(*) FROM material_categories"
        ).fetchone()[0]
    assert {"assignments", "students", "material_categories", "course_materials"} <= tables
    assert category_count == 8


def test_application_startup_initializes_the_configured_database(monkeypatch, tmp_path):
    database_path = tmp_path / "startup-init.sqlite3"
    monkeypatch.setattr(settings, "database_path", str(database_path))

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert database_path.exists()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM material_categories"
        ).fetchone()[0] == 8
