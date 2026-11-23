"""GovernedConnector: Central governed layer mediating all agent access to external data."""

import logging
import threading
import time
import uuid
from typing import Any, Optional
from app.labs.lab5.sources.base_source import BaseDataSource
from app.labs.lab5.sources.notes_source import NotesDataSource
from app.labs.lab5.sources.sqlite_source import SqliteDataSource
from app.labs.lab5.sources.file_source import FileStoreDataSource
from app.labs.lab5.sources.api_source import AcademicApiDataSource
from app.models.lab5_models import (
    ConnectorAuditEntry,
    ConnectorOperation,
    ConnectorRequest,
    ConnectorResponse,
    ConnectorRole,
    SourceMetadata,
)

logger = logging.getLogger(__name__)


class GovernedConnector:
    """Central Governed Connector interface (MCP-Style architecture).
    
    Academic Goal: Agents do NOT directly touch SQLite, disk files, or remote APIs.
    All data read/write/search requests must pass through this governed layer,
    which enforces typed schemas, authorization roles, timing, and immutable audit logs.
    """

    def __init__(self, *, initialize: bool = False) -> None:
        self._lock = threading.RLock()
        self._sources: dict[str, BaseDataSource] = {}
        self._audit_log: list[ConnectorAuditEntry] = []
        self._initialized = False
        if initialize:
            self.initialize()

    def initialize(self) -> None:
        """Register default sources when application startup explicitly initializes services."""
        with self._lock:
            if self._initialized:
                return
            self._register_default_sources()
            self._initialized = True

    def close(self) -> None:
        """Close registered sources that own resources and allow a later reinitialization."""
        with self._lock:
            sources = list(self._sources.values())
            self._sources.clear()
            self._initialized = False
        for source in sources:
            close = getattr(source, "close", None)
            if close is not None:
                close()

    def _register_default_sources(self) -> None:
        """Register default academic data sources."""
        self.register_source(NotesDataSource())
        self.register_source(SqliteDataSource())
        self.register_source(FileStoreDataSource())
        self.register_source(AcademicApiDataSource())

    def register_source(self, source: BaseDataSource) -> None:
        """Register a new governed data source."""
        with self._lock:
            self._sources[source.source_id] = source
            logger.info("Registered governed data source '%s' (%s)", source.source_id, source.source_type)

    def get_source(self, source_id: str) -> Optional[BaseDataSource]:
        """Look up registered data source by source_id."""
        with self._lock:
            return self._sources.get(source_id)

    def list_sources(self) -> list[SourceMetadata]:
        """List metadata and access capabilities for all registered sources."""
        with self._lock:
            return [src.get_metadata() for src in self._sources.values()]

    def dispatch(self, request: ConnectorRequest) -> ConnectorResponse:
        """Dispatch a typed connector request through the governed security and audit layer."""
        req_id = f"mcp-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        source = self.get_source(request.source_id)
        if not source:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            err_msg = f"Data source '{request.source_id}' is not registered with the Governed Connector."
            self._record_audit(req_id, request, "EXECUTION_ERROR", elapsed_ms, err_msg)
            return ConnectorResponse(
                request_id=req_id,
                success=False,
                operation=request.operation,
                source_id=request.source_id,
                data=None,
                error=err_msg,
                provenance="Governed Connector (Unregistered Source)",
                duration_ms=elapsed_ms,
                authorized_role=request.client_role,
            )

        # Enforce supported operations check
        if request.operation not in source.supported_operations:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            err_msg = f"Operation '{request.operation.value}' is not supported by source '{request.source_id}'."
            self._record_audit(req_id, request, "EXECUTION_ERROR", elapsed_ms, err_msg)
            return ConnectorResponse(
                request_id=req_id,
                success=False,
                operation=request.operation,
                source_id=request.source_id,
                data=None,
                error=err_msg,
                provenance=f"Governed Connector ({request.source_id})",
                duration_ms=elapsed_ms,
                authorized_role=request.client_role,
            )

        # Execute under source boundary
        try:
            data, provenance = source.execute(
                operation=request.operation,
                resource_path=request.resource_path,
                parameters=request.parameters,
                role=request.client_role,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._record_audit(req_id, request, "SUCCESS", elapsed_ms, None)

            return ConnectorResponse(
                request_id=req_id,
                success=True,
                operation=request.operation,
                source_id=request.source_id,
                data=data,
                error=None,
                provenance=provenance,
                duration_ms=elapsed_ms,
                authorized_role=request.client_role,
            )

        except PermissionError as perm_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._record_audit(req_id, request, "ACCESS_DENIED", elapsed_ms, str(perm_err))
            return ConnectorResponse(
                request_id=req_id,
                success=False,
                operation=request.operation,
                source_id=request.source_id,
                data=None,
                error=str(perm_err),
                provenance=f"Governed Connector ({request.source_id}) [Access Denied]",
                duration_ms=elapsed_ms,
                authorized_role=request.client_role,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._record_audit(req_id, request, "EXECUTION_ERROR", elapsed_ms, str(exc))
            return ConnectorResponse(
                request_id=req_id,
                success=False,
                operation=request.operation,
                source_id=request.source_id,
                data=None,
                error=str(exc),
                provenance=f"Governed Connector ({request.source_id}) [Error]",
                duration_ms=elapsed_ms,
                authorized_role=request.client_role,
            )

    def _record_audit(
        self,
        req_id: str,
        request: ConnectorRequest,
        status: str,
        duration_ms: float,
        error: Optional[str],
    ) -> None:
        """Append an entry to the connector audit log."""
        entry = ConnectorAuditEntry(
            audit_id=req_id,
            client_agent=request.client_agent,
            client_role=request.client_role,
            actor_user_id=request.actor_user_id,
            operation=request.operation,
            source_id=request.source_id,
            resource_path=request.resource_path,
            status=status,
            duration_ms=round(duration_ms, 2),
            error=error,
        )
        with self._lock:
            self._audit_log.append(entry)

    def get_audit_log(self, limit: int = 50) -> list[ConnectorAuditEntry]:
        """Retrieve recent connector audit entries."""
        with self._lock:
            return list(reversed(self._audit_log[-limit:]))


# Global singleton; database-backed sources are registered during explicit initialization.
governed_connector = GovernedConnector()
