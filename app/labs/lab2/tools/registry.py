"""ToolRegistry managing tool registration, discovery, and execution dispatch."""

import uuid
from typing import Any, Optional

from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import ToolDefinition
from app.models.lab2_models import ToolCallRecord, ToolExecutionStatus


class ToolRegistry:
    """Central registry holding available typed tools for CourseAgentAI."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool. Rejects duplicate tool names or invalid types."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Expected BaseTool instance, got {type(tool).__name__}")
        if not tool.name or not tool.name.strip():
            raise ValueError("Tool name must be a non-empty string.")
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool instance by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """Return the catalog of declarative metadata for all registered tools."""
        return [tool.get_definition() for tool in self._tools.values()]

    def execute_tool(self, name: str, raw_params: dict[str, Any]) -> ToolCallRecord:
        """Execute a tool by name passing raw parameters through its typed validation pipeline.

        Returns a structured ToolCallRecord if the tool is not found.
        """
        tool = self.get_tool(name)
        if tool is None:
            available = list(self._tools.keys())
            return ToolCallRecord(
                call_id=f"call_{uuid.uuid4().hex[:12]}",
                tool_name=name,
                validated_input=raw_params if isinstance(raw_params, dict) else {},
                output_data=None,
                status=ToolExecutionStatus.EXECUTION_ERROR,
                execution_duration_ms=0.0,
                error=f"Tool '{name}' not found in registry. Available tools: {available}",
            )
        return tool.execute(raw_params)


# Global default registry instance
tool_registry = ToolRegistry()
