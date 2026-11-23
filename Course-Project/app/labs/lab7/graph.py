"""Agentic Node Graph: Explicit multi-agent graph orchestration with state passing, bounded retry, and approval gates."""

import logging
import threading
import time
import uuid
from typing import Any, Optional
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID, CANONICAL_COURSE_NAME
from app.labs.lab5.governed_connector import governed_connector
from app.labs.lab3.registry import skill_registry
from app.models.lab5_models import ConnectorOperation, ConnectorRequest, ConnectorRole
from app.models.lab7_models import (
    GraphTopologyEdge,
    GraphTopologyInfo,
    GraphTopologyNode,
    NodeExecutionStatus,
    NodeTraceRecord,
    WorkspaceGraphState,
)

logger = logging.getLogger(__name__)

_NON_RESUMABLE_STATUSES = {
    "WAITING_APPROVAL",
    "COMPLETED",
    "REJECTED",
    "RETRY_EXHAUSTED",
}


# =============================================================================
# Graph Topology Definition
# =============================================================================
GRAPH_TOPOLOGY = GraphTopologyInfo(
    nodes=[
        GraphTopologyNode(id="coordinator", label="Coordinator Node", role="Orchestration", description="Ingests request and establishes canonical course identity"),
        GraphTopologyNode(id="planning", label="Planning Specialist", role="Curriculum Pacing", description="Structures weekly module breakdown across term"),
        GraphTopologyNode(id="notes_repo", label="Notes Repository Agent", role="Knowledge Grounding", description="Retrieves and indexes Chapter 1-4 authoritative notes"),
        GraphTopologyNode(id="assignment_dist", label="Assignment Distribution Agent", role="Deliverables", description="Defines practical programming labs and specs"),
        GraphTopologyNode(id="submission_col", label="Submission Collection Agent", role="Student Workflow", description="Configures submission formats, deadlines, and policies"),
        GraphTopologyNode(id="grading_org", label="Grading Organization Agent", role="Assessment", description="Validates assessment weight distribution (sum == 100%)"),
        GraphTopologyNode(id="milestones", label="Project Milestone Agent", role="Milestone Tracking", description="Establishes capstone phases and progress checks"),
        GraphTopologyNode(id="validation", label="Validation Node", role="Integrity Gate", description="Validates complete state; triggers bounded retry on defect"),
        GraphTopologyNode(id="faculty_approval", label="Faculty Approval Gate", role="Governance Gate", description="Requires human faculty reviewer sign-off before publication"),
        GraphTopologyNode(id="publish", label="Publish / Assemble Node", role="Publication", description="Assembles and publishes finalized course workspace"),
    ],
    edges=[
        GraphTopologyEdge(source="coordinator", target="planning", edge_type="directed"),
        GraphTopologyEdge(source="planning", target="notes_repo", edge_type="directed"),
        GraphTopologyEdge(source="notes_repo", target="assignment_dist", edge_type="directed"),
        GraphTopologyEdge(source="assignment_dist", target="submission_col", edge_type="directed"),
        GraphTopologyEdge(source="submission_col", target="grading_org", edge_type="directed"),
        GraphTopologyEdge(source="grading_org", target="milestones", edge_type="directed"),
        GraphTopologyEdge(source="milestones", target="validation", edge_type="directed"),
        GraphTopologyEdge(source="validation", target="grading_org", condition="Validation Failed (Sum != 100%)", edge_type="retry"),
        GraphTopologyEdge(source="validation", target="faculty_approval", condition="Validation Passed", edge_type="conditional"),
        GraphTopologyEdge(source="faculty_approval", target="publish", condition="Faculty Approved", edge_type="conditional"),
    ],
)


# =============================================================================
# Agentic Node Graph Engine
# =============================================================================
class AgenticNodeGraph:
    """Explicit stateful multi-agent node graph.
    
    Architectural Guarantees:
    - Specialist nodes with dedicated responsibilities
    - Typed state passed along directed edges
    - Single-step and full-graph execution modes with live node state tracking
    - State validation with bounded retry (halts at max_retries to prevent infinite loops)
    - Consequential human faculty approval gate before publication
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[str, WorkspaceGraphState] = {}

    def get_topology(self) -> GraphTopologyInfo:
        """Return visual topology describing graph nodes and edges."""
        return GRAPH_TOPOLOGY

    def get_state(self, run_id: str) -> Optional[WorkspaceGraphState]:
        """Return an isolated snapshot of a graph state."""
        with self._lock:
            state = self._states.get(run_id)
            return state.model_copy(deep=True) if state else None

    def initialize_graph(
        self,
        user_request: str,
        course_id: str = "26ECAC401",
        target_weeks: int = 12,
        simulate_validation_failure: bool = False,
        owner_user_id: Optional[str] = None,
    ) -> WorkspaceGraphState:
        """Create and initialize a new graph execution state."""
        run_id = f"graph-{uuid.uuid4().hex[:8]}"
        cid = normalize_course_id(course_id or user_request) or CANONICAL_COURSE_ID
        cname = CANONICAL_COURSE_NAME if cid == CANONICAL_COURSE_ID else f"Course {cid}"

        initial_states = {n.id: "PENDING" for n in GRAPH_TOPOLOGY.nodes}

        state = WorkspaceGraphState(
            run_id=run_id,
            owner_user_id=owner_user_id,
            course_id=cid,
            course_name=cname,
            user_request=user_request,
            target_weeks=target_weeks,
            current_node="coordinator",
            completed_nodes=[],
            node_states=initial_states,
            retry_count=0,
            status="INITIALIZED",
        )
        if simulate_validation_failure:
            state.ingestion_data["simulate_defect"] = True

        with self._lock:
            self._states[run_id] = state
        return state

    def step_node(self, run_id: str) -> WorkspaceGraphState:
        """Execute exactly one node step in the graph and update state accordingly (Bug 1 repair)."""
        with self._lock:
            state = self._states.get(run_id)
            if not state:
                raise ValueError(f"Graph state '{run_id}' not found.")

            if state.status in _NON_RESUMABLE_STATUSES:
                return state.model_copy(deep=True)

            state.status = "RUNNING"
            self._execute_single_node(state)
            return state.model_copy(deep=True)

    def run_until_paused_or_complete(self, run_id: str) -> WorkspaceGraphState:
        """Execute nodes sequentially until an approval gate or completion is reached."""
        with self._lock:
            state = self._states.get(run_id)
            if not state:
                raise ValueError(f"Graph state '{run_id}' not found.")

            if state.status in _NON_RESUMABLE_STATUSES:
                return state.model_copy(deep=True)

            state.status = "RUNNING"
            while state.status == "RUNNING":
                should_continue = self._execute_single_node(state)
                if not should_continue:
                    break

            return state.model_copy(deep=True)

    def _execute_single_node(self, state: WorkspaceGraphState) -> bool:
        """Execute the current node and advance to the next directed/conditional target.
        
        Returns True if execution can immediately continue, or False if paused/halted.
        """
        current = state.current_node
        start_time = time.perf_counter()

        # Mark current node as running
        state.node_states[current] = "RUNNING"

        # ---------------------------------------------------------------------
        # Node 1: Coordinator
        # ---------------------------------------------------------------------
        if current == "coordinator":
            state.ingestion_data.update({
                "ingested_at": time.time(),
                "resolved_course_id": state.course_id,
                "target_weeks": state.target_weeks,
            })
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "coordinator", "Coordinator", NodeExecutionStatus.SUCCESS, "Ingest Request", f"Course {state.course_id}", elapsed, "planning")
            state.node_states["coordinator"] = "COMPLETED"
            if "coordinator" not in state.completed_nodes:
                state.completed_nodes.append("coordinator")
            state.current_node = "planning"
            return True

        # ---------------------------------------------------------------------
        # Node 2: Planning Specialist
        # ---------------------------------------------------------------------
        elif current == "planning":
            plan_res = skill_registry.execute_skill("course_planning_skill", {
                "course_code": state.course_id,
                "course_name": state.course_name,
                "target_weeks": state.target_weeks,
                "focus_chapters": [1, 2, 3, 4],
            })
            state.planning_schedule = plan_res.output_data.get("schedule", []) if plan_res.output_data else []
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "planning", "Planning Specialist", NodeExecutionStatus.SUCCESS, f"Pacing {state.target_weeks}w", f"{len(state.planning_schedule)} modules", elapsed, "notes_repo")
            state.node_states["planning"] = "COMPLETED"
            if "planning" not in state.completed_nodes:
                state.completed_nodes.append("planning")
            state.current_node = "notes_repo"
            return True

        # ---------------------------------------------------------------------
        # Node 3: Notes Repository Agent
        # ---------------------------------------------------------------------
        elif current == "notes_repo":
            notes_req = ConnectorRequest(
                source_id="notes_source",
                operation=ConnectorOperation.SEARCH,
                parameters={"query": "autonomous agents", "course_id": state.course_id, "top_k": 4},
                client_role=ConnectorRole.FACULTY,
            )
            notes_res = governed_connector.dispatch(notes_req)
            state.notes_repository = notes_res.data.get("matches", []) if notes_res.data else []
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "notes_repo", "Notes Repository Agent", NodeExecutionStatus.SUCCESS, "Search Grounding", f"{len(state.notes_repository)} notes", elapsed, "assignment_dist")
            state.node_states["notes_repo"] = "COMPLETED"
            if "notes_repo" not in state.completed_nodes:
                state.completed_nodes.append("notes_repo")
            state.current_node = "assignment_dist"
            return True

        # ---------------------------------------------------------------------
        # Node 4: Assignment Distribution Agent
        # ---------------------------------------------------------------------
        elif current == "assignment_dist":
            state.assignments_distribution = [
                {"assignment_id": "lab1", "title": "Lab 1: Clarify -> Plan -> Revise", "due_week": 3, "points": 100},
                {"assignment_id": "lab2", "title": "Lab 2: Tool-Using Agent with Trace", "due_week": 5, "points": 100},
                {"assignment_id": "lab3", "title": "Lab 3: Reusable Skills Registry", "due_week": 7, "points": 100},
                {"assignment_id": "lab4", "title": "Lab 4: Memory & Retrieval Architecture", "due_week": 9, "points": 100},
                {"assignment_id": "lab7", "title": "Lab 7: Multi-Agent Node Graph Orchestration", "due_week": 11, "points": 100},
            ]
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "assignment_dist", "Assignment Distribution Agent", NodeExecutionStatus.SUCCESS, "Distribute Labs", f"{len(state.assignments_distribution)} labs scheduled", elapsed, "submission_col")
            state.node_states["assignment_dist"] = "COMPLETED"
            if "assignment_dist" not in state.completed_nodes:
                state.completed_nodes.append("assignment_dist")
            state.current_node = "submission_col"
            return True

        # ---------------------------------------------------------------------
        # Node 5: Submission Collection Agent
        # ---------------------------------------------------------------------
        elif current == "submission_col":
            state.submission_policies = {
                "vcs_platform": "GitHub University Classroom",
                "format": "Python Package + Automated Pytest Suite + JSON Execution Trace",
                "late_penalty": "10% deduction per 24 hours up to 48 hours max",
                "integrity_check": "Deterministic trace verification against course groundings",
            }
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "submission_col", "Submission Collection Agent", NodeExecutionStatus.SUCCESS, "Submission Policies", "Git + Trace Policy established", elapsed, "grading_org")
            state.node_states["submission_col"] = "COMPLETED"
            if "submission_col" not in state.completed_nodes:
                state.completed_nodes.append("submission_col")
            state.current_node = "grading_org"
            return True

        # ---------------------------------------------------------------------
        # Node 6: Grading Organization Agent
        # ---------------------------------------------------------------------
        elif current == "grading_org":
            attempt = state.retry_counts.get("grading_org", 0) + 1
            state.retry_counts["grading_org"] = attempt
            state.retry_count = attempt - 1

            if state.ingestion_data.get("simulate_defect") and attempt == 1:
                state.grading_breakdown = [
                    {"category": "Programming Labs (Labs 1-8)", "weight": 60.0},
                    {"category": "Midterm Examination", "weight": 25.0},
                    {"category": "Final Capstone Project", "weight": 25.0},  # Sum = 110% defect
                ]
            else:
                state.grading_breakdown = [
                    {"category": "Programming Labs (Labs 1-8)", "weight": 50.0},
                    {"category": "Midterm Examination", "weight": 20.0},
                    {"category": "Final Capstone Project", "weight": 30.0},  # Sum = 100.0%
                ]

            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(
                state, "grading_org", "Grading Organization Agent", NodeExecutionStatus.SUCCESS,
                f"Weight Breakdown (Attempt {attempt})", f"Weights configured ({len(state.grading_breakdown)} categories)",
                elapsed, "milestones", attempt_num=attempt,
            )
            state.node_states["grading_org"] = "COMPLETED"
            if "grading_org" not in state.completed_nodes:
                state.completed_nodes.append("grading_org")
            state.current_node = "milestones"
            return True

        # ---------------------------------------------------------------------
        # Node 7: Project Milestone Agent
        # ---------------------------------------------------------------------
        elif current == "milestones":
            state.project_milestones = [
                "Week 2: Autonomous Loop Baseline Sign-off",
                "Week 6: Tool & Memory Architecture Evaluation",
                "Week 10: Multi-Agent Graph Integration Review",
                "Week 12: Final Capstone Defense & Code Demonstration",
            ]
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(state, "milestones", "Project Milestone Agent", NodeExecutionStatus.SUCCESS, "Define Milestones", f"{len(state.project_milestones)} milestones", elapsed, "validation")
            state.node_states["milestones"] = "COMPLETED"
            if "milestones" not in state.completed_nodes:
                state.completed_nodes.append("milestones")
            state.current_node = "validation"
            return True

        # ---------------------------------------------------------------------
        # Node 8: Validation Node (Integrity Gate with Bounded Retry)
        # ---------------------------------------------------------------------
        elif current == "validation":
            total_weight = sum(item.get("weight", 0.0) for item in state.grading_breakdown)
            issues = []

            if abs(total_weight - 100.0) > 0.01:
                issues.append(f"Grading weights sum to {total_weight:.1f}%, must equal exactly 100.0%.")

            if len(state.planning_schedule) < 4:
                issues.append("Curriculum schedule contains fewer than 4 weekly modules.")

            elapsed = (time.perf_counter() - start_time) * 1000

            if issues:
                state.validation_passed = False
                state.validation_issues = issues

                retries_done = state.retry_counts.get("grading_org", 1)
                state.retry_count = retries_done

                if retries_done >= state.max_retries:
                    state.status = "RETRY_EXHAUSTED"
                    state.node_states["validation"] = "FAILED"
                    self._record_trace(
                        state, "validation", "Validation Node", NodeExecutionStatus.ERROR,
                        "Validate State", f"Retry limit reached ({retries_done}/{state.max_retries}). Halting.",
                        elapsed, None,
                    )
                    return False

                # Route back to grading_org for self-healing
                self._record_trace(
                    state, "validation", "Validation Node", NodeExecutionStatus.RETRYING,
                    "Validate State", f"Issues detected: {', '.join(issues)}. Routing back to grading_org.",
                    elapsed, "grading_org",
                )
                state.node_states["validation"] = "RETRYING"
                state.node_states["grading_org"] = "RETRYING"
                if "grading_org" in state.completed_nodes:
                    state.completed_nodes.remove("grading_org")
                state.ingestion_data["simulate_defect"] = False
                state.current_node = "grading_org"
                return True

            else:
                state.validation_passed = True
                state.validation_issues.clear()
                self._record_trace(
                    state, "validation", "Validation Node", NodeExecutionStatus.SUCCESS,
                    "Validate State", "Integrity confirmed. Weight sum == 100.0%.",
                    elapsed, "faculty_approval",
                )
                state.node_states["validation"] = "COMPLETED"
                if "validation" not in state.completed_nodes:
                    state.completed_nodes.append("validation")
                state.current_node = "faculty_approval"
                return True

        # ---------------------------------------------------------------------
        # Node 9: Faculty Approval Gate (Human in the Loop)
        # ---------------------------------------------------------------------
        elif current == "faculty_approval":
            elapsed = (time.perf_counter() - start_time) * 1000
            if not state.faculty_approved:
                state.status = "WAITING_APPROVAL"
                state.node_states["faculty_approval"] = "WAITING_APPROVAL"
                self._record_trace(
                    state, "faculty_approval", "Faculty Approval Gate", NodeExecutionStatus.PENDING,
                    "Governance Gate", "Suspended awaiting human faculty verification and sign-off.",
                    elapsed, None,
                )
                return False
            else:
                self._record_trace(
                    state, "faculty_approval", "Faculty Approval Gate", NodeExecutionStatus.SUCCESS,
                    "Governance Gate", f"Sign-off confirmed by faculty: '{state.faculty_comments or 'Approved'}'.",
                    elapsed, "publish",
                )
                state.node_states["faculty_approval"] = "COMPLETED"
                if "faculty_approval" not in state.completed_nodes:
                    state.completed_nodes.append("faculty_approval")
                state.current_node = "publish"
                return True

        # ---------------------------------------------------------------------
        # Node 10: Assembly & Publication Node
        # ---------------------------------------------------------------------
        elif current == "publish":
            state.published_workspace = {
                "course_id": state.course_id,
                "course_name": state.course_name,
                "duration_weeks": state.target_weeks,
                "schedule_modules_count": len(state.planning_schedule),
                "assignments_count": len(state.assignments_distribution),
                "grading_policy_verified": True,
                "total_grade_weight": sum(i["weight"] for i in state.grading_breakdown),
                "faculty_approved": True,
                "published_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            }
            state.status = "COMPLETED"
            state.node_states["publish"] = "COMPLETED"
            if "publish" not in state.completed_nodes:
                state.completed_nodes.append("publish")
            elapsed = (time.perf_counter() - start_time) * 1000
            self._record_trace(
                state, "publish", "Publish Node", NodeExecutionStatus.SUCCESS,
                "Final Assembly", "Course Workspace published and locked for semester.",
                elapsed, None,
            )
            return False

        return False

    def submit_approval(
        self,
        run_id: str,
        approved: bool,
        comments: Optional[str] = None,
        decision_by: str = "course_faculty",
    ) -> WorkspaceGraphState:
        """Submit faculty approval decision and continue graph execution."""
        with self._lock:
            state = self._states.get(run_id)
            if not state:
                raise ValueError(f"Graph state '{run_id}' not found.")

            if state.status != "WAITING_APPROVAL":
                raise ValueError(f"Graph run '{run_id}' is not awaiting faculty approval.")

            if approved:
                state.faculty_approved = True
                state.faculty_comments = comments or f"Approved by {decision_by}"
                state.approval_actor_user_id = decision_by
                state.status = "RUNNING"
                return self.run_until_paused_or_complete(run_id)
            else:
                state.status = "REJECTED"
                state.faculty_approved = False
                state.node_states["faculty_approval"] = "REJECTED"
                state.faculty_comments = comments or f"Rejected by {decision_by}"
                state.approval_actor_user_id = decision_by
                return state.model_copy(deep=True)

    def _record_trace(
        self,
        state: WorkspaceGraphState,
        node_id: str,
        role: str,
        status: NodeExecutionStatus,
        in_summary: str,
        out_summary: str,
        duration_ms: float,
        transition: Optional[str],
        attempt_num: int = 1,
    ) -> None:
        """Record node execution record in the state history."""
        trace = NodeTraceRecord(
            node_id=node_id,
            node_role=role,
            status=status,
            input_summary=in_summary[:150],
            output_summary=out_summary[:150],
            duration_ms=round(duration_ms, 2),
            transition_to=transition,
            attempt_number=attempt_num,
        )
        state.execution_history.append(trace)


# Global singleton instance
agentic_graph = AgenticNodeGraph()
