"""Pydantic schemas and contracts for Lab 5: MCP-Style Governed Connector."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ConnectorOperation(str, Enum):
    """Supported typed connector operations."""
    READ = "READ"
    WRITE = "WRITE"
    SEARCH = "SEARCH"
    LIST = "LIST"
    DELETE = "DELETE"


class ConnectorRole(str, Enum):
    """Security and authorization roles for connector access."""
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"
    TA = "TA"
    SYSTEM = "SYSTEM"


class SourceMetadata(BaseModel):
    """Declarative metadata for a registered data source."""
    source_id: str
    name: str
    source_type: str = Field(description="NOTES, SQLITE, FILE_STORE, or ACADEMIC_API")
    description: str
    supported_operations: list[ConnectorOperation]
    is_read_only: bool = False
    requires_auth: bool = True


class ConnectorRequest(BaseModel):
    """Typed request payload dispatched through the governed connector interface."""
    source_id: str = Field(description="Target data source identifier")
    operation: ConnectorOperation = Field(description="Typed operation to perform")
    resource_path: str = Field(default="", description="Resource path, table name, or endpoint")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Operation input parameters")
    client_agent: str = Field(default="lab5_connector_agent", description="Identifier of invoking agent")
    client_role: ConnectorRole = Field(default=ConnectorRole.FACULTY, description="Caller authorization role")
    actor_user_id: Optional[str] = Field(default=None, description="Authenticated actor assigned by the API")


class ConnectorResponse(BaseModel):
    """Typed response envelope returned by the governed connector."""
    request_id: str
    success: bool
    operation: ConnectorOperation
    source_id: str
    data: Optional[Any] = None
    error: Optional[str] = None
    provenance: str = Field(description="Verified source attribution and document path")
    duration_ms: float = 0.0
    authorized_role: ConnectorRole
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConnectorAuditEntry(BaseModel):
    """Auditable log record tracking every connector interaction for faculty review."""
    audit_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    client_agent: str
    client_role: ConnectorRole
    actor_user_id: Optional[str] = None
    operation: ConnectorOperation
    source_id: str
    resource_path: str
    status: str = Field(description="SUCCESS, ACCESS_DENIED, or EXECUTION_ERROR")
    duration_ms: float
    error: Optional[str] = None
