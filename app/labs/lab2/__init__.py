"""Lab 2: Tool-Using Agent with Typed Tools and Auditable Execution Traces."""

from app.core.registry import lab_registry
from app.labs.lab2.agent import ToolUsingAgent, lab2_agent
from app.labs.lab2.planner import ActionPlanner, ToolAction

# Register Lab 2 agent in the curriculum catalog
lab_registry.register_agent("lab2", lab2_agent)

__all__ = [
    "ToolUsingAgent",
    "lab2_agent",
    "ActionPlanner",
    "ToolAction",
]
