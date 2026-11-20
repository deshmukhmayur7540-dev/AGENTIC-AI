"""Lab 3: Reusable Skills package."""

from app.labs.lab3.agent import lab3_agent, SkillUsingAgent
from app.labs.lab3.base import BaseSkill
from app.labs.lab3.registry import skill_registry, SkillRegistry
from app.core.registry import lab_registry

# Ensure lab3 is registered with lab_registry
lab_registry.register_agent("lab3", lab3_agent)

__all__ = ["lab3_agent", "SkillUsingAgent", "BaseSkill", "skill_registry", "SkillRegistry"]
