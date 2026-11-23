"""Lab and Agent registry supporting the full 14-lab curriculum roadmap."""

from typing import Any, Optional
from pydantic import BaseModel
from app.core.base_agent import BaseAgent


class LabMetadata(BaseModel):
    """Metadata describing each lab in the 14-lab progression."""
    lab_id: str
    number: int
    title: str
    focus: str
    is_active: bool = False
    description: str


class LabRegistry:
    """Registry maintaining active agents and metadata across all course labs."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._lab_catalog: dict[str, LabMetadata] = {
            "lab1": LabMetadata(
                lab_id="lab1",
                number=1,
                title="Agent vs Chatbot: Clarify → Plan → Revise",
                focus="Gap detection, multi-question clarification, course workspace plan generation, revisions, and exact diffs",
                is_active=True,
                description="Transforms vague faculty requests into structured, editable course workspace plans centered on materials, assignments, and grades with version history.",
            ),
            "lab2": LabMetadata(
                lab_id="lab2",
                number=2,
                title="Tool-Using Agent: Typed Tools for Data Access & Computation",
                focus="Typed tools, schema validation, domain math calculators, auditable execution traces",
                is_active=False,
                description="Executes strictly typed tools for course materials, rubrics, configurations, and mathematical calculations with full observability.",
            ),
            "lab3": LabMetadata(
                lab_id="lab3",
                number=3,
                title="Skill Creation",
                focus="Reusable plan and formatting skills",
                is_active=False,
                description="Modular system skills and formatting templates dynamically loaded by agents.",
            ),
            "lab4": LabMetadata(
                lab_id="lab4",
                number=4,
                title="Memory & Retrieval",
                focus="Separation of short-term run state from stored knowledge",
                is_active=False,
                description="Session memory buffers decoupled from long-term vector/semantic knowledge bases.",
            ),
            "lab5": LabMetadata(
                lab_id="lab5",
                number=5,
                title="MCP-Style Connector",
                focus="Governed typed connector for data sources",
                is_active=False,
                description="Unified protocol for connecting external course databases and LMS providers.",
            ),
            "lab6": LabMetadata(
                lab_id="lab6",
                number=6,
                title="Runtime Engine",
                focus="Skills + tools + memory + audit + checkpoints + approval gates",
                is_active=False,
                description="Comprehensive agent execution runtime with human-in-the-loop gates.",
            ),
            "lab7": LabMetadata(
                lab_id="lab7",
                number=7,
                title="Agentic Node Graph",
                focus="Stateful graph nodes and edge routers",
                is_active=False,
                description="Orchestrates complex DAGs and cyclic evaluation graphs.",
            ),
            "lab8": LabMetadata(
                lab_id="lab8",
                number=8,
                title="Parallel Agent Swarm",
                focus="Concurrent specialist dispatch & scatter-gather",
                is_active=False,
                description="Executes concurrent agent teams with map-reduce synthesis.",
            ),
            "lab9": LabMetadata(
                lab_id="lab9",
                number=9,
                title="Deep Research Agent",
                focus="Evidence candidate retrieval for AI topic research",
                is_active=False,
                description="The API retrieves lexical candidate passages with citations; the available implementation does not orchestrate research or synthesize a briefing. Detailed lab manual/specification was not supplied.",
            ),
            "lab10": LabMetadata(
                lab_id="lab10",
                number=10,
                title="Cloud Operations Agent",
                focus="Failed deployment diagnosis and repair",
                is_active=False,
                description="The course overview names failed-deployment diagnosis and repair. This project provides a grade-weight validation utility and has no safe deployment fixture or deployment-diagnosis workflow; detailed lab manual/specification was not supplied.",
            ),
            "lab11": LabMetadata(
                lab_id="lab11",
                number=11,
                title="Agentic SDLC Factory",
                focus="Requirement to tested implementation",
                is_active=False,
                description="The course overview names a requirement-to-tested-implementation workflow. The current endpoint runs fixed application smoke checks and does not generate code from a requirement; detailed lab manual/specification was not supplied.",
            ),
            "lab12": LabMetadata(
                lab_id="lab12",
                number=12,
                title="Safety & Governance",
                focus="Risk, approval, evaluation, and rollback planning",
                is_active=False,
                description="The SQLite-backed demo supports proposal approval/rejection, rollback, and audit events. Risk assessment and evaluation planning are not included; demo role headers are not authentication, and detailed lab manual/specification was not supplied.",
            ),
            "lab13": LabMetadata(
                lab_id="lab13",
                number=13,
                title="Domain-Specific Specialist Agents",
                focus="Curriculum, Rubric, and Staffing Specialist Agents",
                is_active=False,
                description="Deeply customized sub-agents for specialized academic roles.",
            ),
            "lab14": LabMetadata(
                lab_id="lab14",
                number=14,
                title="Complete Capstone",
                focus="Unified Autonomous Course Operations Suite",
                is_active=False,
                description="End-to-end multi-agent academic platform.",
            ),
        }

    def register_agent(self, lab_id: str, agent: BaseAgent) -> None:
        """Register an active agent implementation for a specific lab."""
        self._agents[lab_id] = agent
        if lab_id in self._lab_catalog:
            self._lab_catalog[lab_id].is_active = True

    def get_agent(self, lab_id: str) -> Optional[BaseAgent]:
        """Retrieve the registered agent for a specific lab."""
        return self._agents.get(lab_id)

    def get_catalog(self) -> list[LabMetadata]:
        """Return the complete 14-lab catalog."""
        return list(self._lab_catalog.values())

    def get_lab_metadata(self, lab_id: str) -> Optional[LabMetadata]:
        """Get metadata for a single lab."""
        return self._lab_catalog.get(lab_id)


# Global singleton instance
lab_registry = LabRegistry()
