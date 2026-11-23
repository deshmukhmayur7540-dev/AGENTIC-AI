"""Lab 6: Controlled Agent Runtime package."""

from app.labs.lab6.agent import lab6_agent, ControlledRuntimeAgent
from app.labs.lab6.engine import runtime_engine, ControlledRuntimeEngine
from app.core.registry import lab_registry

lab_registry.register_agent("lab6", lab6_agent)

__all__ = [
    "lab6_agent",
    "ControlledRuntimeAgent",
    "runtime_engine",
    "ControlledRuntimeEngine",
]
