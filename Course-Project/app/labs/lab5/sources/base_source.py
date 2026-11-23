"""Abstract base class for all governed data sources accessible via connector."""

from abc import ABC, abstractmethod
from typing import Any
from app.models.lab5_models import (
    ConnectorOperation,
    ConnectorRole,
    SourceMetadata,
)


class BaseDataSource(ABC):
    """Abstract interface representing a governed data source behind the connector."""

    source_id: str
    name: str
    source_type: str
    description: str
    supported_operations: list[ConnectorOperation]
    is_read_only: bool = False
    requires_auth: bool = True

    def get_metadata(self) -> SourceMetadata:
        """Inspect source capabilities and access controls."""
        return SourceMetadata(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            description=self.description,
            supported_operations=self.supported_operations,
            is_read_only=self.is_read_only,
            requires_auth=self.requires_auth,
        )

    @abstractmethod
    def execute(
        self,
        operation: ConnectorOperation,
        resource_path: str,
        parameters: dict[str, Any],
        role: ConnectorRole,
    ) -> tuple[Any, str]:
        """Execute typed operation. Returns tuple of (result_data, provenance_string)."""
        raise NotImplementedError
