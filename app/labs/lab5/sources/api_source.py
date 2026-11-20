"""AcademicApiDataSource: Governed mock API for university catalog and course enrollment policies."""

from typing import Any
from app.labs.lab5.sources.base_source import BaseDataSource
from app.models.lab5_models import ConnectorOperation, ConnectorRole


class AcademicApiDataSource(BaseDataSource):
    """Governed API connector communicating with university academic registrar services."""

    source_id = "academic_api_source"
    name = "University Registrar Catalog API"
    source_type = "ACADEMIC_API"
    description = "Governed access to official university course catalog, department codes, and credits."
    supported_operations = [
        ConnectorOperation.READ,
        ConnectorOperation.SEARCH,
        ConnectorOperation.LIST,
    ]
    is_read_only = True
    requires_auth = False

    def __init__(self) -> None:
        self._catalog: dict[str, dict[str, Any]] = {
            "26ECAC401": {
                "course_code": "26ECAC401",
                "course_title": "Agentic AI",
                "department": "Electronics & Computer Communication",
                "academic_level": "Undergraduate / Postgraduate Advanced Elective",
                "credits": 4.0,
                "status": "ACTIVE_ACADEMIC_OFFERING",
                "prerequisites": ["Data Structures", "Generative AI Foundations"],
                "lab_requirement": "Mandatory Hands-on Laboratory",
            }
        }

    def execute(
        self,
        operation: ConnectorOperation,
        resource_path: str,
        parameters: dict[str, Any],
        role: ConnectorRole,
    ) -> tuple[Any, str]:
        code = (resource_path or parameters.get("course_code") or "26ECAC401").upper()

        if operation == ConnectorOperation.READ:
            info = self._catalog.get(code)
            if not info:
                return None, f"University Catalog API: Course '{code}' (Not Found)"
            return info, f"University Registrar API Endpoint: /catalog/courses/{code}"

        elif operation == ConnectorOperation.LIST:
            return list(self._catalog.values()), "University Registrar API Endpoint: /catalog/courses"

        elif operation == ConnectorOperation.SEARCH:
            kw = parameters.get("query", "").lower()
            results = [
                c for c in self._catalog.values()
                if kw in c["course_code"].lower() or kw in c["course_title"].lower()
            ]
            return results, f"University Registrar API Endpoint: /catalog/search?q={kw}"

        raise ValueError(f"Operation '{operation}' not supported by AcademicApiDataSource.")
