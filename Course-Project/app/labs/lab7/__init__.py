"""Lab 7: Agentic Node Graph package."""

from app.labs.lab7.agent import lab7_agent, NodeGraphAgent
from app.labs.lab7.graph import agentic_graph, AgenticNodeGraph
from app.core.registry import lab_registry

lab_registry.register_agent("lab7", lab7_agent)

__all__ = [
    "lab7_agent",
    "NodeGraphAgent",
    "agentic_graph",
    "AgenticNodeGraph",
]
