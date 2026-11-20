"""Lab 8: Parallel Swarm package."""

from app.labs.lab8.agent import lab8_agent, ParallelSwarmAgent
from app.labs.lab8.swarm import swarm_coordinator, ParallelSwarmCoordinator
from app.core.registry import lab_registry

lab_registry.register_agent("lab8", lab8_agent)

__all__ = [
    "lab8_agent",
    "ParallelSwarmAgent",
    "swarm_coordinator",
    "ParallelSwarmCoordinator",
]
