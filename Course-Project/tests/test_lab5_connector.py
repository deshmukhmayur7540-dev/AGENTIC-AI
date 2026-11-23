"""Unit and integration tests for Lab 5: MCP-Style Governed Connector."""

import pytest
from app.labs.lab5.governed_connector import governed_connector, GovernedConnector
from app.labs.lab5.agent import ConnectorAgent
from app.models.lab5_models import (
    ConnectorOperation,
    ConnectorRequest,
    ConnectorRole,
)


def test_registered_sources():
    """Verify all 4 academic sources are registered behind the governed connector."""
    sources = governed_connector.list_sources()
    source_ids = [s.source_id for s in sources]
    assert "notes_source" in source_ids
    assert "sqlite_source" in source_ids
    assert "file_source" in source_ids
    assert "academic_api_source" in source_ids


def test_notes_source_governed_search():
    """Verify governed search on NotesDataSource returns grounded chunks and provenance."""
    req = ConnectorRequest(
        source_id="notes_source",
        operation=ConnectorOperation.SEARCH,
        parameters={"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401"},
        client_agent="test_agent",
        client_role=ConnectorRole.FACULTY,
    )
    res = governed_connector.dispatch(req)
    assert res.success is True
    assert res.data["count"] >= 1
    assert "chapter" in res.provenance.lower()
    assert res.duration_ms > 0


def test_sqlite_source_governed_query():
    """Verify governed SELECT query on SqliteDataSource."""
    req = ConnectorRequest(
        source_id="sqlite_source",
        operation=ConnectorOperation.LIST,
        resource_path="assignments",
        client_agent="test_agent",
        client_role=ConnectorRole.STUDENT,
    )
    res = governed_connector.dispatch(req)
    assert res.success is True
    assert len(res.data) >= 4  # Default seeded lab1-lab4
    assert res.data[0]["id"] == "lab1"
    assert "assignments" in res.provenance


def test_sqlite_faculty_write_authorized():
    """Verify FACULTY role is authorized to insert or update course assignments."""
    req = ConnectorRequest(
        source_id="sqlite_source",
        operation=ConnectorOperation.WRITE,
        resource_path="assignments",
        parameters={
            "id": "lab5_test_unit",
            "course_id": "26ECAC401",
            "title": "Lab 5: Governed MCP Connector Exercise",
            "max_points": 100,
            "weight_percentage": 10.0,
            "due_week": 8,
        },
        client_agent="test_agent",
        client_role=ConnectorRole.FACULTY,
    )
    res = governed_connector.dispatch(req)
    assert res.success is True
    assert res.data["status"] == "RECORD_WRITTEN"

    # Verify record was written by reading back
    read_req = ConnectorRequest(
        source_id="sqlite_source",
        operation=ConnectorOperation.READ,
        resource_path="assignments",
        parameters={"id": "lab5_test_unit"},
        client_agent="test_agent",
        client_role=ConnectorRole.FACULTY,
    )
    read_res = governed_connector.dispatch(read_req)
    assert read_res.success is True
    assert read_res.data["title"] == "Lab 5: Governed MCP Connector Exercise"


def test_sqlite_student_write_access_denied():
    """Verify STUDENT role is strictly blocked from modifying grade rubrics or assignments."""
    req = ConnectorRequest(
        source_id="sqlite_source",
        operation=ConnectorOperation.WRITE,
        resource_path="rubrics",
        parameters={"id": "hacked_rubric", "criterion": "Free Points", "max_points": 100},
        client_agent="malicious_or_mistaken_agent",
        client_role=ConnectorRole.STUDENT,
    )
    res = governed_connector.dispatch(req)
    assert res.success is False
    assert "Access Denied" in res.error
    assert "unauthorized" in res.error


def test_file_store_governed_read():
    """Verify reading course documents through FileStoreDataSource."""
    req = ConnectorRequest(
        source_id="file_source",
        operation=ConnectorOperation.READ,
        resource_path="26ECAC401_Syllabus.md",
        client_agent="test_agent",
        client_role=ConnectorRole.STUDENT,
    )
    res = governed_connector.dispatch(req)
    assert res.success is True
    assert "26ECAC401" in res.data["content"]
    assert "course_files" in res.provenance


def test_academic_api_governed_catalog_read():
    """Verify retrieving course information via AcademicApiDataSource."""
    req = ConnectorRequest(
        source_id="academic_api_source",
        operation=ConnectorOperation.READ,
        resource_path="26ECAC401",
        client_agent="test_agent",
        client_role=ConnectorRole.FACULTY,
    )
    res = governed_connector.dispatch(req)
    assert res.success is True
    assert res.data["course_title"] == "Agentic AI"
    assert res.data["credits"] == 4.0
    assert "Registrar API" in res.provenance


def test_connector_audit_logging():
    """Verify every operation through the connector produces an auditable entry."""
    initial_ids = {entry.audit_id for entry in governed_connector.get_audit_log()}
    req = ConnectorRequest(
        source_id="notes_source",
        operation=ConnectorOperation.LIST,
        client_agent="auditor_agent",
        client_role=ConnectorRole.FACULTY,
    )
    governed_connector.dispatch(req)
    logs = governed_connector.get_audit_log()
    assert logs[0].audit_id not in initial_ids
    assert logs[0].client_agent == "auditor_agent"
    assert logs[0].status == "SUCCESS"


def test_connector_audit_records_denied_and_unsupported_operations():
    """Denied and unsupported requests must be auditable just like successful operations."""
    connector = GovernedConnector()
    connector.initialize()
    requests = [
        ConnectorRequest(
            source_id="sqlite_source",
            operation=ConnectorOperation.WRITE,
            resource_path="rubrics",
            parameters={"id": "blocked_rubric", "criterion": "Blocked"},
            client_agent="audit_denied_agent",
            client_role=ConnectorRole.STUDENT,
        ),
        ConnectorRequest(
            source_id="notes_source",
            operation=ConnectorOperation.WRITE,
            resource_path="syllabus.md",
            client_agent="audit_unsupported_agent",
            client_role=ConnectorRole.FACULTY,
        ),
    ]

    try:
        results = [connector.dispatch(request) for request in requests]
        logs = connector.get_audit_log()

        assert all(not result.success for result in results)
        assert [entry.status for entry in logs] == ["EXECUTION_ERROR", "ACCESS_DENIED"]
    finally:
        connector.close()


def test_connector_unknown_source_error():
    """Verify querying an unregistered source returns structured error."""
    req = ConnectorRequest(
        source_id="non_existent_source_999",
        operation=ConnectorOperation.READ,
        client_agent="test_agent",
        client_role=ConnectorRole.FACULTY,
    )
    res = governed_connector.dispatch(req)
    assert res.success is False
    assert "not registered" in res.error


@pytest.mark.asyncio
async def test_connector_agent_query():
    """Verify ConnectorAgent queries external data mediated exclusively by GovernedConnector."""
    agent = ConnectorAgent()

    # Query 1: Database query
    res_db = await agent.execute("query", {"query": "List all course assignments and rubrics", "role": "FACULTY"})
    assert res_db["intent"] == "DATABASE_QUERY"
    assert res_db["connector_response"]["success"] is True

    # Query 2: Catalog API query
    res_api = await agent.execute("query", {"query": "Check prerequisites and credits with registrar catalog", "role": "FACULTY"})
    assert res_api["intent"] == "REGISTRAR_API_QUERY"
    assert res_api["connector_response"]["success"] is True
    assert res_api["connector_response"]["data"]["credits"] == 4.0
