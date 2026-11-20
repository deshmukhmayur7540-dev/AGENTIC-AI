"""ToolUsingAgent for Lab 2: Executes registered typed tools and generates transparent auditable traces."""

import time
from typing import Any, Optional

from app.core.base_agent import BaseAgent
from app.core.constants import CANONICAL_COURSE_CODE
from app.labs.lab2.planner import ActionPlanner, ToolAction
from app.labs.lab2.tools.registry import ToolRegistry, tool_registry
from app.models.lab2_models import (
    AuditableExecutionTrace,
    AuditableTraceStep,
    ToolCallRecord,
    ToolExecutionStatus,
)


class ToolUsingAgent(BaseAgent):
    """Lab 2 Agent that plans, dispatches, and verifies typed tool calls into an auditable trace."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        planner: Optional[ActionPlanner] = None,
        max_tool_calls: int = 10,
    ) -> None:
        super().__init__(
            agent_id="lab2",
            name="Tool-Using Agent",
            description="Executes strictly typed tools for course materials, rubrics, configurations, and mathematical calculations with full observability.",
        )
        self.registry = registry or tool_registry
        self.planner = planner or ActionPlanner()
        self.max_tool_calls = max_tool_calls

    async def initialize(self) -> None:
        """Initialize agent resources and verify registry readiness."""
        pass

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Coordinator entrypoint: execute user request and return structured trace dict."""
        user_request = (
            payload.get("request")
            or payload.get("query")
            or payload.get("user_request")
            or action
        )
        course_id = payload.get("course_id") or CANONICAL_COURSE_CODE
        trace = self.run(
            user_request,
            course_id=course_id,
            assignment_id=payload.get("assignment_id"),
        )
        return trace.model_dump()

    def run(
        self,
        user_request: str,
        course_id: Optional[str] = None,
        assignment_id: Optional[str] = None,
    ) -> AuditableExecutionTrace:
        """Bounded agent loop executing sequential typed tools and synthesizing verified facts."""
        start_time = time.perf_counter()
        steps: list[AuditableTraceStep] = []
        verified_facts: dict[str, Any] = {}
        target_course = course_id or CANONICAL_COURSE_CODE
        context: dict[str, Any] = {
            "user_request": user_request,
            "course_id": target_course,
        }
        if assignment_id:
            context["assignment_id"] = assignment_id

        call_count = 0
        step_number = 1

        while call_count < self.max_tool_calls:
            # Step A & B: Action Planning / Selection
            next_action: Optional[ToolAction] = self.planner.plan_next_action(
                user_request=user_request,
                context=context,
                verified_facts=verified_facts,
                steps=steps,
            )

            if next_action is None:
                # Evidence gathering complete
                break

            call_count += 1

            # Step C: Tool Execution through ToolRegistry
            tool_record: ToolCallRecord = self.registry.execute_tool(
                next_action.tool_name,
                next_action.parameters,
            )

            # Step D & E: Result Validation & Evidence Collection
            if tool_record.status == ToolExecutionStatus.SUCCESS and tool_record.output_data is not None:
                validation_result = "SUCCESS: Output conforms to schema and is verified"
                if next_action.tool_name == "search_course_notes":
                    matches = tool_record.output_data.get("matches", [])
                    source_docs = sorted(list({m["source_document"] for m in matches if m.get("source_document")}))
                    if source_docs:
                        evidence_source = f"Agentic AI Document Store ({', '.join(source_docs)})"
                    else:
                        evidence_source = tool_record.output_data.get("source", "Course Knowledge Store")
                else:
                    evidence_source = (
                        tool_record.output_data.get("source")
                        or tool_record.output_data.get("evidence")
                        or f"{next_action.tool_name} output"
                    )
                intermediate_summary = self._summarize_step_output(
                    next_action.tool_name,
                    tool_record.output_data,
                )
                self._update_verified_facts(
                    verified_facts=verified_facts,
                    context=context,
                    tool_name=next_action.tool_name,
                    output_data=tool_record.output_data,
                )
            else:
                validation_result = f"FAILED ({tool_record.status.value}): {tool_record.error}"
                evidence_source = "Tool Error / Repository Rejection"
                intermediate_summary = f"Tool '{next_action.tool_name}' failed: {tool_record.error}"
                context["error"] = tool_record.error
                context["failed_tool"] = next_action.tool_name

            # Step F: Record Trace Step (No private chain-of-thought)
            trace_step = AuditableTraceStep(
                step_number=step_number,
                selected_action=next_action.rationale,
                tool_call=tool_record,
                validation_result=validation_result,
                evidence_source=str(evidence_source),
                intermediate_summary=intermediate_summary,
            )
            steps.append(trace_step)
            step_number += 1

            # If tool execution failed, stop further dependent execution
            if tool_record.status != ToolExecutionStatus.SUCCESS:
                break

        if call_count >= self.max_tool_calls:
            context["limit_reached"] = True

        # Step G: Synthesize Final Conclusion from verified facts only
        final_conclusion = self._synthesize_conclusion(user_request, verified_facts, steps, context)
        total_duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        # Determine overall trace status: if any step failed, reflect that error status
        trace_status = ToolExecutionStatus.SUCCESS
        for step in steps:
            if step.tool_call and step.tool_call.status != ToolExecutionStatus.SUCCESS:
                trace_status = step.tool_call.status
                break
        if not steps and context.get("error"):
            trace_status = ToolExecutionStatus.EXECUTION_ERROR

        # If execution failed or resulted in error, verified facts must strictly be zero
        if trace_status != ToolExecutionStatus.SUCCESS:
            verified_facts = {}

        return AuditableExecutionTrace(
            user_request=user_request,
            steps=steps,
            verified_facts=verified_facts,
            final_conclusion=final_conclusion,
            total_duration_ms=total_duration_ms,
            status=trace_status,
        )

    def _update_verified_facts(
        self,
        verified_facts: dict[str, Any],
        context: dict[str, Any],
        tool_name: str,
        output_data: dict[str, Any],
    ) -> None:
        """Incorporate only verified outputs into verified_facts."""
        if tool_name == "read_course_syllabus":
            verified_facts["course_id"] = output_data.get("course_id")
            verified_facts["course_name"] = output_data.get("course_name")
            verified_facts["duration_weeks"] = output_data.get("duration_weeks")
            verified_facts["grading_weights"] = output_data.get("grading_weights", [])
            verified_facts["modules"] = output_data.get("modules", [])
            context["course_id"] = output_data.get("course_id")

        elif tool_name == "calculate_grade_breakdown_total":
            verified_facts["calculated_total_percentage"] = output_data.get("total_percentage")
            verified_facts["is_valid_grade_breakdown"] = output_data.get("is_valid")
            verified_facts["grade_delta_from_hundred"] = output_data.get("delta_from_hundred")

        elif tool_name == "get_rubric_breakdown":
            verified_facts["course_id"] = output_data.get("course_id")
            verified_facts["assignment_id"] = output_data.get("assignment_id")
            verified_facts["rubric_criteria"] = output_data.get("rubric_criteria", [])
            verified_facts["rubric_total_points"] = output_data.get("total_points")

        elif tool_name == "get_course_config":
            verified_facts["course_id"] = output_data.get("course_id")
            verified_facts["course_name"] = output_data.get("course_name")
            verified_facts["duration_weeks"] = output_data.get("duration_weeks")
            verified_facts["enrollment_limit"] = output_data.get("enrollment_limit")
            verified_facts["students_per_ta"] = output_data.get("students_per_ta")
            verified_facts["ta_ratio_policy"] = output_data.get("ta_ratio_policy")
            verified_facts["lab_environment"] = output_data.get("lab_environment")

        elif tool_name == "get_ta_policy":
            verified_facts["course_id"] = output_data.get("course_id")
            verified_facts["enrollment"] = output_data.get("enrollment")
            verified_facts["required_ta_count"] = output_data.get("required_ta_count")
            verified_facts["required_hours_per_week"] = output_data.get("required_hours_per_week")
            verified_facts["policy_ratio"] = output_data.get("policy_ratio")
            verified_facts["formula_applied"] = output_data.get("formula_applied")

        elif tool_name == "compute_workload_hours":
            verified_facts["enrollment"] = output_data.get("enrollment")
            verified_facts["assignments_count"] = output_data.get("assignments_count")
            verified_facts["grading_minutes_per_submission"] = output_data.get("grading_minutes_per_submission")
            verified_facts["total_grading_hours"] = output_data.get("total_grading_hours")
            verified_facts["hours_per_assignment"] = output_data.get("hours_per_assignment")

        elif tool_name == "search_course_notes":
            verified_facts["course_id"] = output_data.get("course_id")
            verified_facts["notes_query"] = output_data.get("query")
            verified_facts["notes_matches"] = output_data.get("matches", [])
            verified_facts["notes_match_count"] = output_data.get("match_count")

        elif tool_name == "get_assignment_spec":
            verified_facts["assignment_spec"] = output_data

    def _summarize_step_output(self, tool_name: str, data: dict[str, Any]) -> str:
        """Create a clear, non-opaque summary of the step's verified result."""
        if tool_name == "read_course_syllabus":
            return f"Retrieved syllabus for {data.get('course_id')}: {len(data.get('modules', []))} modules, {len(data.get('grading_weights', []))} grading components."
        elif tool_name == "calculate_grade_breakdown_total":
            status_text = "valid (equals 100%)" if data.get("is_valid") else f"invalid (delta = {data.get('delta_from_hundred')}%)"
            return f"Calculated grade weights total: {data.get('total_percentage')}% - {status_text}."
        elif tool_name == "get_rubric_breakdown":
            return f"Retrieved rubric for {data.get('assignment_id')} in {data.get('course_id')} with {len(data.get('rubric_criteria', []))} criteria ({data.get('total_points')} total points)."
        elif tool_name == "get_course_config":
            return f"Retrieved config for {data.get('course_id')}: {data.get('duration_weeks')} weeks, capacity {data.get('enrollment_limit')}, ratio {data.get('ta_ratio_policy')}."
        elif tool_name == "get_ta_policy":
            return f"Calculated TA staffing for {data.get('enrollment')} students: {data.get('required_ta_count')} TAs, {data.get('required_hours_per_week')} hrs/wk ({data.get('policy_ratio')})."
        elif tool_name == "compute_workload_hours":
            return f"Computed workload: {data.get('total_grading_hours')} total hours ({data.get('hours_per_assignment')} hrs/batch) for {data.get('enrollment')} students and {data.get('assignments_count')} assignments."
        elif tool_name == "search_course_notes":
            return f"Found {data.get('match_count')} note matches for query '{data.get('query')}' in {data.get('course_id')}."
        elif tool_name == "get_assignment_spec":
            return f"Retrieved spec for '{data.get('assignment_id')}': {data.get('title')} (due Week {data.get('due_week')}, {data.get('max_points')} pts)."
        return f"Tool {tool_name} returned verified output."

    def _synthesize_conclusion(
        self,
        user_request: str,
        verified_facts: dict[str, Any],
        steps: list[AuditableTraceStep],
        context: dict[str, Any],
    ) -> str:
        """Synthesize authoritative conclusion derived exclusively from verified facts."""
        if context.get("error"):
            return f"Unable to complete audit: {context['error']}. No verified facts could be established."

        if context.get("limit_reached"):
            return f"Execution reached maximum tool-call limit ({self.max_tool_calls}) before conclusion could be finalized."

        course_id = verified_facts.get("course_id", "Course")
        req_lower = user_request.lower()

        # 1. Grading Breakdown Audit
        if "calculated_total_percentage" in verified_facts:
            total = verified_facts["calculated_total_percentage"]
            is_valid = verified_facts["is_valid_grade_breakdown"]
            delta = verified_facts["grade_delta_from_hundred"]
            weights = verified_facts.get("grading_weights", [])
            breakdown_str = ", ".join(f"{gw['weight_percentage']}% {gw['category']}" for gw in weights)

            if is_valid:
                return (
                    f"The {course_id} grading breakdown sums to {total:.1f}% ({breakdown_str}). "
                    f"The grading distribution is valid with a 0.0% deviation from 100%."
                )
            else:
                return (
                    f"The {course_id} grading breakdown sums to {total:.1f}% ({breakdown_str}). "
                    f"The grading distribution is INVALID with a {delta:.1f}% deviation from 100%."
                )
        elif "grading_weights" in verified_facts and not verified_facts.get("grading_weights"):
            modules = verified_facts.get("modules", [])
            if modules:
                mod_titles = ", ".join(m.get("title", "") for m in modules)
                mod_desc = f"{len(modules)} course modules/chapters are established ({mod_titles})"
            else:
                mod_desc = "course modules are established across Chapters 1-4"
            return (
                f"For {course_id}, the canonical syllabus was retrieved: {mod_desc}. "
                f"Official university grading breakdown percentages are not published in the supplied course notes. "
                f"No grading breakdown was hallucinated."
            )

        # 2. Workload Sufficiency Audit
        if "total_grading_hours" in verified_facts and "required_hours_per_week" in verified_facts:
            enrollment = verified_facts.get("enrollment")
            ta_count = verified_facts.get("required_ta_count")
            weekly_ta_hours = verified_facts.get("required_hours_per_week")
            total_hours = verified_facts.get("total_grading_hours")
            batch_hours = verified_facts.get("hours_per_assignment")
            assign_count = verified_facts.get("assignments_count")
            mins = verified_facts.get("grading_minutes_per_submission")

            is_sufficient = (batch_hours or 0) <= (weekly_ta_hours or 0)
            utilization = round(((batch_hours or 0) / weekly_ta_hours) * 100.0, 1) if weekly_ta_hours else 0.0
            status_text = "sufficient" if is_sufficient else "insufficient"

            return (
                f"TA staffing analysis for {enrollment} students in {course_id}: {ta_count} TAs provide {weekly_ta_hours:.1f} weekly hours. "
                f"Grading {assign_count} assignments at {mins:.0f} min/submission requires {total_hours:.1f} total hours "
                f"({batch_hours:.1f} hours per batch). Staffing is {status_text} as each grading batch utilizes {utilization}% of weekly TA capacity."
            )

        # 3. TA Policy Inquiry
        if "required_ta_count" in verified_facts:
            enrollment = verified_facts.get("enrollment")
            ta_count = verified_facts.get("required_ta_count")
            ta_hours = verified_facts.get("required_hours_per_week")
            ratio = verified_facts.get("policy_ratio")
            formula = verified_facts.get("formula_applied")
            return (
                f"For an enrollment of {enrollment} students in {course_id}, the policy ({ratio}) requires "
                f"{ta_count} Teaching Assistants for a total of {ta_hours:.1f} TA hours per week (formula: {formula})."
            )

        # 4. Notes + Assignment Synthesis
        if "notes_matches" in verified_facts and "assignment_spec" in verified_facts:
            matches = verified_facts.get("notes_matches", [])
            assign_spec = verified_facts.get("assignment_spec", {})
            query = verified_facts.get("notes_query", "topic")

            def _format_match_item(m):
                prefix = f"Chapter {m['chapter']}" if m.get("chapter") else (f"Week {m['week']}" if m.get("week") else "Topic")
                return f"{prefix} ({m['topic']}): '{m['matched_text']}'"

            topic_desc = (
                _format_match_item(matches[0])
                if matches
                else f"No notes explicitly matching '{query}'"
            )
            assign_desc = (
                f"Assignment '{assign_spec.get('assignment_id')}' ({assign_spec.get('title')}, due Week {assign_spec.get('due_week')}, "
                f"deliverables: {assign_spec.get('deliverables')})"
            )
            return (
                f"Course Notes Evidence: {course_id} covers {query} in {topic_desc}. "
                f"Assignment Application: Students first apply this concept in {assign_desc}."
            )

        # 5. Rubric Breakdown Inquiry
        if "rubric_criteria" in verified_facts:
            criteria = verified_facts.get("rubric_criteria", [])
            total_pts = verified_facts.get("rubric_total_points")
            assign_id = verified_facts.get("assignment_id")

            # Check if user asked about specific criterion (e.g. code quality)
            if "code quality" in req_lower:
                cq_crit = next((c for c in criteria if "code quality" in c.get("criterion_name", "").lower()), None)
                if cq_crit:
                    return (
                        f"For {course_id} Assignment '{assign_id}', the '{cq_crit['criterion_name']}' criterion is allocated "
                        f"{cq_crit['points']} out of {total_pts} total points: \"{cq_crit['description']}\"."
                    )

            criteria_summary = ", ".join(f"{c['criterion_name']} ({c['points']} pts)" for c in criteria)
            return (
                f"The grading rubric for {course_id} Assignment '{assign_id}' totals {total_pts} points across {len(criteria)} criteria: "
                f"{criteria_summary}."
            )

        # 6. Course Config Inquiry
        if "enrollment_limit" in verified_facts:
            weeks = verified_facts.get("duration_weeks")
            limit = verified_facts.get("enrollment_limit")
            ratio = verified_facts.get("ta_ratio_policy")
            env = verified_facts.get("lab_environment")
            return (
                f"{course_id} Course Configuration: Duration is {weeks} weeks with enrollment cap of {limit} students. "
                f"Staffing policy is {ratio}, and the designated lab environment is: {env}."
            )

        # 7. Notes Search Only
        if "notes_matches" in verified_facts:
            matches = verified_facts.get("notes_matches", [])
            query = verified_facts.get("notes_query")
            if not matches:
                return (
                    f"No lecture notes or materials in {course_id} match the query '{query}'. "
                    f"This concept is unsupported by the 26ECAC401 curriculum."
                )

            def _format_match(m):
                prefix = f"Chapter {m['chapter']}" if m.get("chapter") else (f"Week {m['week']}" if m.get("week") else "Section")
                doc_part = f" [{m['source_document']}]" if m.get("source_document") else ""
                return f"{prefix} ({m['topic']}){doc_part}"

            match_summaries = "; ".join(_format_match(m) for m in matches[:3])
            return f"Found {len(matches)} note match(es) for '{query}' in {course_id}: {match_summaries}."

        return f"Verified evidence collected for {course_id} across {len(steps)} tool step(s)."


# Global instance
lab2_agent = ToolUsingAgent()
