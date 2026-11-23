"""ControlledRuntimeAgent for Lab 6: End-to-end execution combining tools, skills, memory, and approval gates."""

from typing import Any
from app.core.base_agent import BaseAgent
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID
from app.core.registry import lab_registry
from app.labs.lab5.governed_connector import governed_connector
from app.labs.lab3.registry import skill_registry
from app.labs.lab6.engine import runtime_engine
from app.models.lab5_models import ConnectorOperation, ConnectorRequest, ConnectorRole
from app.models.lab6_models import RuntimeBudget


class ControlledRuntimeAgent(BaseAgent):
    """Executes multi-step course compilation under the strict governance of the ControlledRuntimeEngine."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab6_runtime_agent",
            name="Controlled Runtime Agent",
            description="Executes governed academic workflows under budget limits, checkpoints, crash recovery, and approval gates.",
        )

    async def initialize(self) -> None:
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch actions: start_run, step, approve, crash, resume, get_status."""
        if action == "start_run":
            task = payload.get("task_description", "Compile and verify 26ECAC401 course workspace")
            course_id = normalize_course_id(payload.get("course_id")) or CANONICAL_COURSE_ID
            budget_dict = payload.get("budget")
            budget = RuntimeBudget.model_validate(budget_dict) if budget_dict else RuntimeBudget()
            run = runtime_engine.create_run(
                task,
                course_id=course_id,
                budget=budget,
                owner_user_id=payload.get("owner_user_id"),
                owner_role=payload.get("owner_role"),
            )
            return {"status": "INITIALIZED", "run": run.model_dump()}

        elif action == "step":
            run_id = payload.get("run_id", "")
            return self._advance_run_step(run_id, payload)

        elif action == "approve":
            run_id = payload.get("run_id", "")
            gate_id = payload.get("gate_id", "")
            approved = payload.get("approved", True)
            decision_by = payload.get("decision_by", "course_faculty")
            run = runtime_engine.submit_approval(
                run_id,
                gate_id,
                approved,
                decision_by,
                decision_role=payload.get("actor_role"),
            )
            return {"status": "SUCCESS", "run": run.model_dump()}

        elif action == "crash":
            run_id = payload.get("run_id", "")
            run = runtime_engine.simulate_crash(
                run_id,
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
            )
            return {"status": "PAUSED", "message": "Crash simulated. Checkpoints preserved.", "run": run.model_dump()}

        elif action == "resume":
            run_id = payload.get("run_id", "")
            run = runtime_engine.resume_run(
                run_id,
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
            )
            return {"status": "RESUMED", "run": run.model_dump()}

        elif action == "get_run":
            run_id = payload.get("run_id", "")
            run = runtime_engine.get_run(run_id)
            if not run:
                return {"status": "ERROR", "error": f"Run '{run_id}' not found."}
            return {"status": "SUCCESS", "run": run.model_dump()}

        return {
            "status": "ERROR",
            "error": f"Unsupported action '{action}' for ControlledRuntimeAgent.",
        }

    def _advance_run_step(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Advance the run through the prescribed academic compilation steps."""
        run = runtime_engine.get_run(run_id)
        if not run:
            return {"status": "ERROR", "error": f"Run '{run_id}' not found."}

        step_idx = run.steps_executed

        # Step 0: Catalog prerequisite check (Governed Connector)
        if step_idx == 0:
            def action_step_0(vars_in: dict[str, Any]):
                cid = vars_in.get("course_id", "26ECAC401")
                req = ConnectorRequest(
                    source_id="academic_api_source",
                    operation=ConnectorOperation.READ,
                    resource_path=cid,
                    client_role=ConnectorRole.FACULTY,
                )
                res = governed_connector.dispatch(req)
                return {"catalog_data": res.data}, "connector:academic_api_source"

            return runtime_engine.execute_step(
                run_id=run_id,
                step_name="Step 1: Registrar Prerequisite Verification",
                actor="RegistrarVerificationNode",
                action_fn=action_step_0,
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
                expected_tool_call=True,
            )

        # Step 1: Notes grounding check (Notes connector)
        elif step_idx == 1:
            def action_step_1(vars_in: dict[str, Any]):
                cid = vars_in.get("course_id", "26ECAC401")
                req = ConnectorRequest(
                    source_id="notes_source",
                    operation=ConnectorOperation.SEARCH,
                    parameters={"query": "autonomous agents", "course_id": cid},
                    client_role=ConnectorRole.FACULTY,
                )
                res = governed_connector.dispatch(req)
                return {"grounding_evidence": res.data}, "connector:notes_source"

            return runtime_engine.execute_step(
                run_id=run_id,
                step_name="Step 2: Lecture Notes Grounding Inspection",
                actor="NotesGroundingNode",
                action_fn=action_step_1,
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
                expected_tool_call=True,
            )

        # Step 2: Course weekly plan synthesis (Skills Layer)
        elif step_idx == 2:
            def action_step_2(vars_in: dict[str, Any]):
                cid = vars_in.get("course_id", "26ECAC401")
                params = {"course_code": cid, "target_weeks": 12, "focus_chapters": [1, 2, 3, 4]}
                record = skill_registry.execute_skill("course_planning_skill", params)
                return {"curriculum_schedule": record.output_data}, "skill:course_planning_skill"

            return runtime_engine.execute_step(
                run_id=run_id,
                step_name="Step 3: Curriculum Schedule Synthesis",
                actor="PlanningSkillNode",
                action_fn=action_step_2,
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
                expected_tool_call=True,
            )

        # Step 3: Consequential Publication & Grading Policy Sign-off (APPROVAL GATE!)
        elif step_idx == 3:
            def action_step_3(vars_in: dict[str, Any]):
                # Publishes course workspace to SQLite database
                req = ConnectorRequest(
                    source_id="sqlite_source",
                    operation=ConnectorOperation.WRITE,
                    resource_path="assignments",
                    parameters={
                        "id": "final_capstone",
                        "course_id": vars_in.get("course_id", "26ECAC401"),
                        "title": "Agentic AI Final Capstone Project",
                        "max_points": 100,
                        "weight_percentage": 25.0,
                        "due_week": 12,
                    },
                    client_role=ConnectorRole.FACULTY,
                )
                res = governed_connector.dispatch(req)
                return {"published_status": "OFFICIAL_SYLLABUS_PUBLISHED", "capstone": res.data}, "connector:sqlite_source"

            step_res = runtime_engine.execute_step(
                run_id=run_id,
                step_name="Step 4: Official Course Publication & Grade Lock",
                actor="CoursePublishingNode",
                action_fn=action_step_3,
                is_consequential=True,
                consequential_reason="Publishing official course workspace and locking assessment weight distribution requires faculty sign-off.",
                actor_user_id=payload.get("actor_user_id"),
                actor_role=payload.get("actor_role"),
                expected_tool_call=True,
            )

            # If approval was just granted and executed, mark run completed
            if step_res.get("status") == "SUCCESS":
                runtime_engine.complete_run(run_id, result_data={"workspace_status": "PUBLISHED", "course_id": run.variables.get("course_id")})

            return step_res

        else:
            return {"status": "COMPLETED", "message": "All steps executed successfully."}


lab6_agent = ControlledRuntimeAgent()
lab_registry.register_agent("lab6", lab6_agent)
