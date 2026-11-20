"""Course repository storing workspace plans, version histories, and demo scenarios."""

from typing import Optional, Any
from app.models.lab1_models import CourseWorkspacePlan, PlanRevisionResponse, PlanHistoryRecord
from app.models.common import ScenarioDefinition


class CourseRepository:
    """Repository storing in-memory and persistent workspace plans and version histories."""

    def __init__(self):
        # Maps plan_id -> list of CourseWorkspacePlan versions (e.g. [v1.0, v1.1, v1.2])
        self._plans: dict[str, list[CourseWorkspacePlan]] = {}
        # Maps plan_id -> list of PlanRevisionResponse records
        self._revisions: dict[str, list[PlanRevisionResponse]] = {}
        # Pre-loaded evaluator scenarios
        self._scenarios: dict[str, ScenarioDefinition] = {}
        self._load_default_scenarios()

    def save_initial_plan(self, plan: CourseWorkspacePlan) -> CourseWorkspacePlan:
        """Store the initial v1.0 version of a course workspace plan."""
        if plan.plan_id not in self._plans:
            self._plans[plan.plan_id] = []
            self._revisions[plan.plan_id] = []
        
        # Verify no version collision
        existing_versions = [p.version for p in self._plans[plan.plan_id]]
        if plan.version in existing_versions:
            raise ValueError(f"Plan version '{plan.version}' already exists for plan_id '{plan.plan_id}'.")
            
        self._plans[plan.plan_id].append(plan)
        return plan

    def save_revised_plan(
        self,
        revised_plan: CourseWorkspacePlan,
        revision_response: PlanRevisionResponse,
    ) -> PlanRevisionResponse:
        """Save a new revised plan version while strictly preserving all prior versions."""
        plan_id = revised_plan.plan_id
        if plan_id not in self._plans:
            self._plans[plan_id] = []
            self._revisions[plan_id] = []

        existing_versions = [p.version for p in self._plans[plan_id]]
        if revised_plan.version in existing_versions:
            raise ValueError(
                f"Version collision: Version '{revised_plan.version}' already exists for plan '{plan_id}'. "
                f"Revisions must create an incremented version."
            )

        self._plans[plan_id].append(revised_plan)
        self._revisions[plan_id].append(revision_response)
        return revision_response

    def get_latest_plan(self, plan_id: str) -> Optional[CourseWorkspacePlan]:
        """Retrieve the latest version of a course plan."""
        versions = self._plans.get(plan_id, [])
        return versions[-1] if versions else None

    def get_plan_version(self, plan_id: str, version: str) -> Optional[CourseWorkspacePlan]:
        """Retrieve a specific version of a course plan."""
        versions = self._plans.get(plan_id, [])
        for p in versions:
            if p.version == version:
                return p
        return None

    def get_plan_history(self, plan_id: str) -> Optional[PlanHistoryRecord]:
        """Retrieve complete version history, revisions, and diffs for a plan."""
        versions = self._plans.get(plan_id)
        if not versions:
            return None
        
        return PlanHistoryRecord(
            plan_id=plan_id,
            current_version=versions[-1].version,
            versions=versions,
            revisions=self._revisions.get(plan_id, []),
        )

    def get_all_scenarios(self) -> list[ScenarioDefinition]:
        """Retrieve all demo scenarios for faculty evaluation."""
        return list(self._scenarios.values())

    def get_scenario(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Get a single scenario by ID."""
        return self._scenarios.get(scenario_id)

    def get_canonical_syllabus(self, course_id: str) -> Optional[dict[str, Any]]:
        """Retrieve canonical syllabus fixture data by course ID."""
        from app.data.course_fixtures import get_canonical_syllabus_data
        return get_canonical_syllabus_data(course_id)

    def search_canonical_notes(self, course_id: str, query: str) -> Optional[dict[str, Any]]:
        """Search course notes and lecture materials by query keyword."""
        from app.data.course_fixtures import search_canonical_notes_data
        return search_canonical_notes_data(course_id, query)

    def get_canonical_assignment(self, course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
        """Retrieve fixture data, then the persisted assignment catalog record."""
        from app.data.course_fixtures import get_canonical_assignment_data
        fixture = get_canonical_assignment_data(course_id, assignment_id)
        if fixture is not None:
            return fixture
        return self._get_persisted_assignment(course_id, assignment_id)

    def get_canonical_rubric(self, course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
        """Retrieve fixture data, then persisted criteria for the requested course assignment."""
        from app.data.course_fixtures import get_canonical_rubric_data
        fixture = get_canonical_rubric_data(course_id, assignment_id)
        if fixture is not None:
            return fixture
        return self._get_persisted_rubric(course_id, assignment_id)

    @staticmethod
    def _get_persisted_assignment(course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
        from app.data.db import get_db_connection

        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT id, course_id, title, due_week, max_points, description,
                       submission_rules
                FROM assignments
                WHERE id = ? AND course_id = ?
                """,
                (assignment_id, course_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "course_id": row["course_id"],
            "assignment_id": row["id"],
            "title": row["title"],
            "due_week": row["due_week"],
            "deliverables": [],
            "max_points": row["max_points"],
            "submission_requirements": row["submission_rules"] or "No submission requirements are recorded.",
            "description": row["description"],
            "source": "Persisted course assignment catalog",
        }

    @staticmethod
    def _get_persisted_rubric(course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
        from app.data.db import get_db_connection

        with get_db_connection() as conn:
            assignment = conn.execute(
                "SELECT id FROM assignments WHERE id = ? AND course_id = ?",
                (assignment_id, course_id),
            ).fetchone()
            if assignment is None:
                return None
            rows = conn.execute(
                """
                SELECT r.criterion, r.max_points, r.description
                FROM rubrics r
                JOIN assignments a ON a.id = r.assignment_id
                WHERE a.id = ? AND a.course_id = ?
                ORDER BY r.rowid
                """,
                (assignment_id, course_id),
            ).fetchall()
        if not rows:
            return None
        criteria = [
            {
                "criterion_name": row["criterion"],
                "points": row["max_points"],
                "description": row["description"] or "",
            }
            for row in rows
        ]
        return {
            "course_id": course_id,
            "assignment_id": assignment_id,
            "rubric_criteria": criteria,
            "total_points": sum(item["points"] for item in criteria),
            "evidence": "Persisted course rubric catalog",
        }

    def get_canonical_config(self, course_id: str) -> Optional[dict[str, Any]]:
        """Retrieve canonical course configuration and parameters."""
        from app.data.course_fixtures import get_canonical_config_data
        return get_canonical_config_data(course_id)

    def get_canonical_ta_policy(self, course_id: str, enrollment: int) -> Optional[dict[str, Any]]:
        """Calculate canonical TA policy and required staffing."""
        from app.data.course_fixtures import get_canonical_ta_policy_data
        return get_canonical_ta_policy_data(course_id, enrollment)

    def _load_default_scenarios(self) -> None:
        """Initialize realistic course scenarios for evaluator demos."""
        scenarios = [
            ScenarioDefinition(
                scenario_id="scenario-agentic-foundations",
                title="Agentic AI Course Curriculum: Foundations & Reasoning",
                course_name="26ECAC401: Agentic AI",
                category="Agentic AI",
                difficulty="Advanced Undergraduate / Graduate",
                raw_prompt="I need to structure a comprehensive course workspace for 26ECAC401 (Agentic AI) covering Chapter 1 foundations, autonomous loops (Plan-Act-Observe-Revise), and reasoning strategies (CoT, ReAct, Tree of Thoughts) for 80 graduate students.",
                description="Faculty course workspace request requiring clarification on prerequisite depth, practical tool sandboxing, and assessment breakdown.",
                expected_gaps=[
                    "Schedule pacing and duration in weeks",
                    "Prerequisite depth in generative AI and Python",
                    "Grading breakdown between hands-on agent labs and capstone",
                ],
                suggested_revision="Add a hands-on ReAct and Tree of Thoughts benchmarking lab in Week 4, and allocate 35% grade weight to the autonomous agent capstone.",
            ),
            ScenarioDefinition(
                scenario_id="scenario-agent-frameworks-tools",
                title="Agent Frameworks, Typed Tools & Memory",
                course_name="26ECAC401: Agentic AI",
                category="Agent Engineering",
                difficulty="Advanced",
                raw_prompt="Design a course workspace for 26ECAC401 focusing on Chapter 2: LangChain, LangGraph stateful graphs, typed tool calling schemas, and memory separation (short-term session vs long-term RAG).",
                description="Covers agent runtime patterns, MCP integration, and tool sandbox security.",
                expected_gaps=[
                    "Assessment weighting for stateful graph implementation",
                    "Code execution sandbox infrastructure",
                    "TA support allocation",
                ],
                suggested_revision="Include a Model Context Protocol (MCP) server integration lab in Week 6 and allocate 15 hours of TA support.",
            ),
            ScenarioDefinition(
                scenario_id="scenario-agentic-capstone",
                title="Autonomous Multi-Agent System Capstone",
                course_name="26ECAC401: Agentic AI",
                category="Autonomous Systems",
                difficulty="Capstone",
                raw_prompt="We want an end-to-end multi-week capstone project for 26ECAC401 where students build a reliable autonomous agent with perception, reasoning, typed tools, and long-term memory retrieval.",
                description="Capstone project design focusing on architectural reliability, defensive guardrails, and audit traces.",
                expected_gaps=[
                    "Evaluation benchmarks and grading rubric for autonomous agent reliability",
                    "Target environment and external API quota allocation",
                    "Prerequisite background in asynchronous programming",
                ],
                suggested_revision="Add an automated evaluation harness in Week 8 and increase the capstone project weight to 40%.",
            ),
        ]
        for s in scenarios:
            self._scenarios[s.scenario_id] = s


# Global singleton
course_repo = CourseRepository()
