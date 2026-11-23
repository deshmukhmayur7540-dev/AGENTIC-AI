"""ParallelSwarmAgent for Lab 8: Orchestrates parallel fan-out and evidence-based fan-in merge."""

from typing import Any
from app.core.base_agent import BaseAgent
from app.core.registry import lab_registry
from app.labs.lab8.swarm import swarm_coordinator


class ParallelSwarmAgent(BaseAgent):
    """Executes parallel role-based specialist swarms with concurrent fan-out and fan-in merge."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab8_swarm_agent",
            name="Parallel Swarm Agent",
            description="Coordinates concurrent specialist unit workers, measures speedup, and performs evidence-based fan-in merge.",
        )

    async def initialize(self) -> None:
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch actions: dispatch_swarm, get_status."""
        if action == "dispatch_swarm":
            cid = payload.get("course_id", "26ECAC401")
            target_chapters = payload.get("target_chapters", [1, 2, 3, 4])
            simulate_failure = payload.get("simulate_worker_failure")

            result = await swarm_coordinator.dispatch_swarm(
                course_id=cid,
                target_chapters=target_chapters,
                simulate_worker_failure=simulate_failure,
            )
            return result.model_dump()

        elif action == "get_status":
            run_id = payload.get("swarm_run_id", "")
            res = swarm_coordinator.get_result(run_id)
            if not res:
                return {"status": "ERROR", "error": f"Swarm run '{run_id}' not found."}
            return {"status": res.status, "result": res.model_dump()}

        return {
            "status": "ERROR",
            "error": f"Unsupported action '{action}' for ParallelSwarmAgent.",
        }


lab8_agent = ParallelSwarmAgent()
lab_registry.register_agent("lab8", lab8_agent)
