"""Lab 5: MCP-Style Governed Connector package."""

from app.labs.lab5.agent import lab5_agent, ConnectorAgent
from app.labs.lab5.governed_connector import governed_connector, GovernedConnector
from app.core.registry import lab_registry

lab_registry.register_agent("lab5", lab5_agent)

__all__ = [
    "lab5_agent",
    "ConnectorAgent",
    "governed_connector",
    "GovernedConnector",
]
