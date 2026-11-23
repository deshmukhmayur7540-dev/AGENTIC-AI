"""SkillUsingAgent for Lab 3: Reusable schema-typed skill discovery and execution."""

import re
from typing import Any
from app.core.base_agent import BaseAgent
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID
from app.core.registry import lab_registry
from app.labs.lab3.registry import skill_registry


class SkillUsingAgent(BaseAgent):
    """Autonomous agent that dynamically discovers, selects, and executes reusable skills."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab3_skill_agent",
            name="Skill-Using Agent",
            description="Dynamically discovers and executes registered academic skills for planning, research, and formatting.",
        )

    async def initialize(self) -> None:
        """Ensure skill registry is ready."""
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch action to appropriate skill or catalog inspector."""
        if action == "list_skills":
            skills = skill_registry.list_skills()
            return {
                "status": "SUCCESS",
                "skills_count": len(skills),
                "skills": [s.model_dump() for s in skills],
            }

        elif action == "inspect_skill":
            skill_name = payload.get("skill_name", "")
            meta = skill_registry.inspect_schema(skill_name)
            if not meta:
                return {
                    "status": "ERROR",
                    "error": f"Skill '{skill_name}' not found in registry.",
                }
            return {
                "status": "SUCCESS",
                "metadata": meta.model_dump(),
            }

        elif action == "execute_skill":
            skill_name = payload.get("skill_name", "")
            params = payload.get("parameters", {})
            record = skill_registry.execute_skill(skill_name, params)
            return record.model_dump()

        elif action == "run_query":
            # Natural language skill routing
            query = payload.get("query", "")
            return self._route_and_execute(query, payload)

        return {
            "status": "ERROR",
            "error": f"Unsupported action '{action}' for SkillUsingAgent.",
        }

    def _route_and_execute(self, query: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Infer best matching skill from natural language query and dispatch."""
        q_lower = query.lower()
        course_id = normalize_course_id(payload.get("course_id") or query) or CANONICAL_COURSE_ID

        # Routing heuristic
        if any(k in q_lower for k in ["format", "handout", "markdown", "export", "brief"]):
            params = {
                "title": payload.get("title", "Agentic AI Lecture Brief"),
                "course_code": course_id,
                "raw_content": query,
                "target_format": payload.get("target_format", "markdown_handout"),
            }
            record = skill_registry.execute_skill("course_content_formatting_skill", params)
            return {
                "routing": "course_content_formatting_skill",
                "query": query,
                "execution": record.model_dump(),
            }

        elif any(k in q_lower for k in ["plan", "schedule", "weeks", "week", "pacing", "curriculum", "syllabus"]):
            # Extract target weeks if specified (e.g. 14-week, 14 weeks)
            w_match = re.search(r"(\d+)[\s\-]*weeks?", q_lower)
            weeks = int(w_match.group(1)) if w_match else 12
            params = {
                "course_code": course_id,
                "course_name": "Agentic AI",
                "target_weeks": weeks,
                "focus_chapters": [1, 2, 3, 4],
            }
            record = skill_registry.execute_skill("course_planning_skill", params)
            return {
                "routing": "course_planning_skill",
                "query": query,
                "execution": record.model_dump(),
            }

        else:
            # Default to Research Summary Skill
            # Extract topic cleanly
            topic = query
            for prefix in ["research", "summarize", "find", "search", "explain", "about"]:
                if topic.lower().startswith(prefix):
                    topic = topic[len(prefix):].strip()
            params = {
                "topic": topic or "Autonomous Agent Architectures",
                "course_code": course_id,
                "depth": payload.get("depth", "standard"),
            }
            record = skill_registry.execute_skill("research_summary_skill", params)
            return {
                "routing": "research_summary_skill",
                "query": query,
                "execution": record.model_dump(),
            }


lab3_agent = SkillUsingAgent()
lab_registry.register_agent("lab3", lab3_agent)
