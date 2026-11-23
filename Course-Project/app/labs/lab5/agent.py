"""ConnectorAgent for Lab 5: Specialist agent accessing all data exclusively through GovernedConnector."""

from typing import Any
from app.core.base_agent import BaseAgent
from app.core.registry import lab_registry
from app.labs.lab5.governed_connector import governed_connector
from app.models.lab5_models import (
    ConnectorOperation,
    ConnectorRequest,
    ConnectorRole,
)


class ConnectorAgent(BaseAgent):
    """Specialist agent accessing course data exclusively via the MCP-Style Governed Connector."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab5_connector_agent",
            name="Governed Connector Agent",
            description="Accesses notes, databases, files, and registrar APIs strictly through the Governed Connector layer.",
        )

    async def initialize(self) -> None:
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch action through the GovernedConnector interface."""
        if action == "list_sources":
            sources = governed_connector.list_sources()
            return {
                "status": "SUCCESS",
                "sources_count": len(sources),
                "sources": [s.model_dump() for s in sources],
            }

        elif action == "execute_operation":
            req = ConnectorRequest.model_validate(payload)
            res = governed_connector.dispatch(req)
            return res.model_dump()

        elif action == "query":
            # Natural language query routing through connector
            return self._handle_query(payload)

        elif action == "get_audit":
            limit = payload.get("limit", 50)
            logs = governed_connector.get_audit_log(limit=limit)
            return {
                "status": "SUCCESS",
                "logs_count": len(logs),
                "logs": [l.model_dump() for l in logs],
            }

        return {
            "status": "ERROR",
            "error": f"Unsupported action '{action}' for ConnectorAgent.",
        }

    def _handle_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Natural language request routed through governed connector operations."""
        query = payload.get("query", "").lower()
        role = ConnectorRole(payload.get("role", "FACULTY"))

        # Route query to corresponding data source via connector
        if any(k in query for k in ["assignment", "rubric", "grade", "due"]):
            # Query SQLite Database via Connector
            req = ConnectorRequest(
                source_id="sqlite_source",
                operation=ConnectorOperation.LIST,
                resource_path="assignments",
                parameters={"query": query},
                client_agent=self.agent_id,
                client_role=role,
            )
            res = governed_connector.dispatch(req)
            return {
                "intent": "DATABASE_QUERY",
                "connector_response": res.model_dump(),
                "conclusion": f"Retrieved {len(res.data) if res.data else 0} assignments from SQLite database via connector.",
            }

        elif any(k in query for k in ["catalog", "credit", "prerequisite", "department", "registrar"]):
            # Query Academic API via Connector
            req = ConnectorRequest(
                source_id="academic_api_source",
                operation=ConnectorOperation.READ,
                resource_path="26ECAC401",
                parameters={"course_code": "26ECAC401"},
                client_agent=self.agent_id,
                client_role=role,
            )
            res = governed_connector.dispatch(req)
            return {
                "intent": "REGISTRAR_API_QUERY",
                "connector_response": res.model_dump(),
                "conclusion": f"Retrieved official catalog record for 26ECAC401 via academic API connector.",
            }

        elif any(k in query for k in ["handout", "file", "download"]):
            # Query File Store via Connector
            req = ConnectorRequest(
                source_id="file_source",
                operation=ConnectorOperation.LIST,
                parameters={},
                client_agent=self.agent_id,
                client_role=role,
            )
            res = governed_connector.dispatch(req)
            return {
                "intent": "FILE_STORE_QUERY",
                "connector_response": res.model_dump(),
                "conclusion": f"Retrieved {len(res.data) if res.data else 0} course documents from file store via connector.",
            }

        else:
            # Default to Course Notes via Connector
            req = ConnectorRequest(
                source_id="notes_source",
                operation=ConnectorOperation.SEARCH,
                parameters={"query": query, "course_id": "26ECAC401"},
                client_agent=self.agent_id,
                client_role=role,
            )
            res = governed_connector.dispatch(req)
            return {
                "intent": "NOTES_SEARCH_QUERY",
                "connector_response": res.model_dump(),
                "conclusion": f"Retrieved {res.data.get('count', 0) if res.data else 0} notes matches via connector.",
            }


lab5_agent = ConnectorAgent()
lab_registry.register_agent("lab5", lab5_agent)
