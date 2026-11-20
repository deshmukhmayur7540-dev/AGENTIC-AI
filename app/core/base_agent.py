"""Base Agent abstract class and lifecycle hooks."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from app.core.state import AgentState, WorkflowStatus


class BaseAgent(ABC):
    """Abstract base class for all CourseAgentAI lab agents."""

    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.state = AgentState(agent_id=agent_id, current_status=WorkflowStatus.IDLE)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent resources, knowledge bases, or models."""
        pass

    @abstractmethod
    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute a specific action with payload and return structured results."""
        pass

    def get_state(self) -> AgentState:
        """Retrieve current agent state for monitoring and UI updates."""
        return self.state

    def reset_state(self) -> None:
        """Reset agent state to IDLE."""
        self.state = AgentState(agent_id=self.agent_id, current_status=WorkflowStatus.IDLE)

    def update_status(self, status: WorkflowStatus, step_name: Optional[str] = None) -> None:
        """Helper to update current workflow status and step."""
        self.state.current_status = status
        self.state.current_step = step_name
