"""SkillRegistry for registering, discovering, inspecting, and executing typed skills."""

import logging
from typing import Any, Optional
from app.labs.lab3.base import BaseSkill
from app.labs.lab3.skills.planning_skill import CoursePlanningSkill
from app.labs.lab3.skills.research_skill import ResearchSummarySkill
from app.labs.lab3.skills.formatting_skill import CourseContentFormattingSkill
from app.models.lab3_models import SkillExecutionRecord, SkillMetadata

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Central registry maintaining schema-typed, case-agnostic reusable skills."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._execution_history: list[SkillExecutionRecord] = []
        self._register_default_skills()

    def _register_default_skills(self) -> None:
        """Register default academic skills for Lab 3."""
        self.register(CoursePlanningSkill())
        self.register(ResearchSummarySkill())
        self.register(CourseContentFormattingSkill())

    def register(self, skill: BaseSkill) -> None:
        """Register a new skill instance in the registry."""
        if skill.name in self._skills:
            logger.warning("Overwriting previously registered skill '%s'", skill.name)
        self._skills[skill.name] = skill
        logger.info("Registered skill '%s' (v%s)", skill.name, skill.version)

    SKILL_ALIASES = {
        "planning_skill": "course_planning_skill",
        "research_skill": "research_summary_skill",
        "formatting_skill": "course_content_formatting_skill",
    }

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Look up skill instance by unique name or alias."""
        resolved_name = self.SKILL_ALIASES.get(name, name)
        return self._skills.get(resolved_name) or self._skills.get(name)

    def list_skills(self) -> list[SkillMetadata]:
        """Return metadata and schemas for all registered skills."""
        return [skill.get_metadata() for skill in self._skills.values()]

    def inspect_schema(self, name: str) -> Optional[SkillMetadata]:
        """Inspect input and output schemas for a specific skill."""
        skill = self.get_skill(name)
        return skill.get_metadata() if skill else None

    def execute_skill(self, name: str, parameters: dict[str, Any]) -> SkillExecutionRecord:
        """Execute a registered skill with strict validation and record auditable history."""
        skill = self.get_skill(name)
        if not skill:
            record = SkillExecutionRecord(
                execution_id=f"skexec-err",
                skill_name=name,
                status="EXECUTION_ERROR",
                input_parameters=parameters,
                output_data=None,
                duration_ms=0.0,
                error=f"Skill '{name}' is not registered in the Skill Registry.",
            )
            self._execution_history.append(record)
            return record

        record = skill.execute(parameters)
        self._execution_history.append(record)
        return record

    def get_history(self, limit: int = 50) -> list[SkillExecutionRecord]:
        """Retrieve recent skill execution records."""
        return list(reversed(self._execution_history[-limit:]))


# Global singleton instance
skill_registry = SkillRegistry()
