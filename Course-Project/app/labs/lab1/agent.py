"""ClarifyPlanReviseAgent implementation for Lab 1."""

from typing import Any
from app.core.base_agent import BaseAgent
from app.core.state import WorkflowStatus
from app.data.repository import course_repo
from app.labs.lab1.gap_analyzer import gap_analyzer
from app.labs.lab1.plan_generator import plan_generator
from app.labs.lab1.revision_engine import revision_engine
from app.models.lab1_models import (
    FacultyCourseRequest,
    ClarificationSubmission,
    RevisionRequest,
)


class ClarifyPlanReviseAgent(BaseAgent):
    """Agent that transforms vague course requests into structured plans through interactive clarification and revisions."""

    def __init__(self):
        super().__init__(
            agent_id="lab1_clarify_plan_revise_agent",
            name="Lab 1: Clarify -> Plan -> Revise Agent",
            description="Analyzes vague course requests, asks clarification questions, generates structured course plans, and applies targeted revisions with exact diffs.",
        )

    async def initialize(self) -> None:
        """Initialize resources and state."""
        self.reset_state()

    async def execute(self, action: str, payload: dict[str, Any]) -> Any:
        """Execute Lab 1 actions: clarify, generate, revise, get_history, get_plan."""
        if action == "clarify":
            return await self._handle_clarify(payload)
        elif action == "generate":
            return await self._handle_generate(payload)
        elif action == "revise":
            return await self._handle_revise(payload)
        elif action == "get_history":
            return await self._handle_get_history(payload)
        elif action == "get_plan":
            return await self._handle_get_plan(payload)
        else:
            raise ValueError(f"Unsupported action '{action}' for ClarifyPlanReviseAgent.")

    async def _handle_clarify(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Detect missing information and return clarification questions."""
        self.update_status(WorkflowStatus.ANALYZING_GAPS, step_name="detect_gaps")
        req = FacultyCourseRequest.model_validate(payload)
        questions = gap_analyzer.analyze(req)
        
        self.update_status(WorkflowStatus.AWAITING_CLARIFICATION, step_name="await_faculty_answers")
        return {
            "prompt": req.raw_prompt,
            "questions_count": len(questions),
            "questions": [q.model_dump() for q in questions],
        }

    async def _handle_generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Synthesize original prompt and faculty answers into CourseWorkspacePlan v1.0."""
        self.update_status(WorkflowStatus.GENERATING_PLAN, step_name="synthesize_plan_v1")
        submission = ClarificationSubmission.model_validate(payload)
        plan_v1 = plan_generator.generate(submission)
        
        # Save to version store
        saved_plan = course_repo.save_initial_plan(plan_v1)
        self.update_status(WorkflowStatus.PLAN_READY, step_name="plan_v1_ready")
        return saved_plan.model_dump()

    async def _handle_revise(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Revise plan based on faculty feedback, compute structured diffs, and save new version."""
        self.update_status(WorkflowStatus.REVISING_PLAN, step_name="apply_revisions")
        rev_req = RevisionRequest.model_validate(payload)
        
        current_plan = course_repo.get_latest_plan(rev_req.plan_id)
        if not current_plan:
            raise ValueError(f"Cannot revise: Plan with ID '{rev_req.plan_id}' not found.")

        revision_response = revision_engine.revise(current_plan, rev_req)
        
        # Save revised version while preserving previous versions
        course_repo.save_revised_plan(revision_response.revised_plan, revision_response)
        self.update_status(WorkflowStatus.PLAN_READY, step_name=f"plan_v{revision_response.current_version}_ready")
        
        return revision_response.model_dump()

    async def _handle_get_history(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Retrieve complete version history and structured diffs for a plan."""
        plan_id = payload.get("plan_id")
        if not plan_id:
            raise ValueError("Missing required 'plan_id' parameter.")
        history = course_repo.get_plan_history(plan_id)
        if not history:
            raise ValueError(f"No history found for plan '{plan_id}'.")
        return history.model_dump()

    async def _handle_get_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Retrieve a specific or latest plan version."""
        plan_id = payload.get("plan_id")
        version = payload.get("version")
        if not plan_id:
            raise ValueError("Missing required 'plan_id' parameter.")
        
        if version:
            plan = course_repo.get_plan_version(plan_id, version)
        else:
            plan = course_repo.get_latest_plan(plan_id)
            
        if not plan:
            raise ValueError(f"Plan '{plan_id}' (version: {version or 'latest'}) not found.")
        return plan.model_dump()


# Register agent singleton in the LabRegistry
lab1_agent = ClarifyPlanReviseAgent()
from app.core.registry import lab_registry
lab_registry.register_agent("lab1", lab1_agent)
