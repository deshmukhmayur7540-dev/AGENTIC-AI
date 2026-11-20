"""NodeGraphAgent for Lab 7: Dispatches and manages stateful Agentic Node Graph workflows."""

from typing import Any
from app.core.base_agent import BaseAgent
from app.core.registry import lab_registry
from app.labs.lab7.graph import agentic_graph


class NodeGraphAgent(BaseAgent):
    """Orchestrates multi-agent specialist workflows using explicit stateful node graph transitions."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab7_graph_agent",
            name="Node Graph Orchestration Agent",
            description="Coordinates specialist agent nodes, validates intermediate states, bounds retries, and enforces faculty approval gates.",
        )

    async def initialize(self) -> None:
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch actions: run_graph, step_graph, get_state, approve, get_topology."""
        if action == "run_graph":
            run_id = payload.get("run_id")
            if run_id and agentic_graph.get_state(run_id):
                final_state = agentic_graph.run_until_paused_or_complete(run_id)
            else:
                req_text = payload.get("user_request", "Organize 26ECAC401 course workspace")
                cid = payload.get("course_id", "26ECAC401")
                weeks = payload.get("target_weeks", 12)
                defect = payload.get("simulate_validation_failure", False)

                state = agentic_graph.initialize_graph(
                    user_request=req_text,
                    course_id=cid,
                    target_weeks=weeks,
                    simulate_validation_failure=defect,
                    owner_user_id=payload.get("authenticated_user_id"),
                )
                final_state = agentic_graph.run_until_paused_or_complete(state.run_id)

            dump = final_state.model_dump()
            return {
                "status": final_state.status,
                "run_id": final_state.run_id,
                "state": dump,
                **dump,
            }

        elif action in ("step_graph", "step"):
            run_id = payload.get("run_id")
            if run_id and agentic_graph.get_state(run_id):
                stepped_state = agentic_graph.step_node(run_id)
            else:
                req_text = payload.get("user_request", "Organize 26ECAC401 course workspace")
                cid = payload.get("course_id", "26ECAC401")
                weeks = payload.get("target_weeks", 12)
                defect = payload.get("simulate_validation_failure", False)

                state = agentic_graph.initialize_graph(
                    user_request=req_text,
                    course_id=cid,
                    target_weeks=weeks,
                    simulate_validation_failure=defect,
                    owner_user_id=payload.get("authenticated_user_id"),
                )
                stepped_state = agentic_graph.step_node(state.run_id)

            dump = stepped_state.model_dump()
            return {
                "status": stepped_state.status,
                "run_id": stepped_state.run_id,
                "state": dump,
                **dump,
            }

        elif action == "get_state":
            run_id = payload.get("run_id", "")
            state = agentic_graph.get_state(run_id)
            if not state:
                return {"status": "ERROR", "error": f"Graph state '{run_id}' not found."}
            dump = state.model_dump()
            return {"status": state.status, "run_id": state.run_id, "state": dump, **dump}

        elif action == "approve":
            run_id = payload.get("run_id", "")
            approved = payload.get("approved", True)
            comments = payload.get("comments")
            dec_by = payload.get("decision_by", "course_faculty")
            state = agentic_graph.submit_approval(run_id, approved, comments, dec_by)
            dump = state.model_dump()
            return {"status": state.status, "run_id": state.run_id, "state": dump, **dump}

        elif action == "get_topology":
            topology = agentic_graph.get_topology()
            return {"status": "SUCCESS", "topology": topology.model_dump()}

        return {
            "status": "ERROR",
            "error": f"Unsupported action '{action}' for NodeGraphAgent.",
        }


lab7_agent = NodeGraphAgent()
lab_registry.register_agent("lab7", lab7_agent)
