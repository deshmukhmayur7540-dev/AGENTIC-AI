"""Action planner and deterministic intent router for Lab 2 ToolUsingAgent."""

import re
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.core.constants import CANONICAL_COURSE_CODE
from app.models.lab2_models import AuditableTraceStep, ToolExecutionStatus


class ToolAction(BaseModel):
    """Declarative action selected by the agent."""
    tool_name: str = Field(description="Name of the registered tool to invoke")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Validated input parameter dictionary")
    rationale: str = Field(description="Concise, public rationale for taking this action")


class ActionPlanner:
    """Interprets requests and determines sequential tool execution steps.

    Cleanly decouples request interpretation, tool selection, and dependency chaining.
    """

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extract course codes, assignment IDs, numbers, and topics from natural language."""
        entities: dict[str, Any] = {}

        # 1. Course ID extraction (e.g. 26ECAC401, UNKNOWN999, BADCOURSE, CS101)
        # Note: Subject prefixes require 1-4 digits (e.g. CS101, AI301). Standalone "AI"
        # without digits is natural language and never extracted as a course ID.
        stop_words = {"FOR", "AND", "THE", "WITH", "FROM", "OVER", "PER", "SUM", "HOW", "SHOW", "WHAT", "CHECK", "DOES", "ARE", "HAS", "NOT", "CAN", "BUT", "AI"}
        for course_match in re.finditer(
            r"\b(26ECAC\d{3}|TEST_[A-Za-z0-9]+|UNKNOWN\d*|BADCOURSE\d*|(?:CS|AI|DS|SE|SWE|IT|MATH|STAT|ENG|ECE|EE|PHYS|CHEM)\s*\d{1,4}|[A-Z]{2,4}\s*\d{3,4})\b",
            text,
            re.IGNORECASE,
        ):
            candidate = re.sub(r"\s+", "", course_match.group(1)).upper()
            letter_prefix = re.match(r"^([A-Z]+)", candidate)
            if letter_prefix and letter_prefix.group(1) in stop_words:
                continue
            if candidate == "AI":
                continue
            entities["course_id"] = candidate
            break

        # 2. Assignment ID extraction
        # e.g. "Assignment 1" -> "hw1", "Assignment 2" -> "hw2", "hw1", "lab1", "midterm", "capstone"
        named_assign_match = re.search(
            r"\b(hw\d+|lab\d+|midterm|capstone|custom_hw|hw\w+)\b",
            text,
            re.IGNORECASE,
        )
        if named_assign_match:
            entities["assignment_id"] = named_assign_match.group(1).lower()

        # 3. Enrollment extraction
        enroll_match = re.search(
            r"(?:for|with|of|has)\s*(\d+)\s*students?\b|(\d+)\s*students?\b|enrollment(?:\s*count)?\s*(?:of|is|:)?\s*(\d+)\b",
            text,
            re.IGNORECASE,
        )
        if enroll_match:
            val = next(v for v in enroll_match.groups() if v is not None)
            entities["enrollment_count"] = int(val)

        # 4. Assignment count extraction
        assign_count_match = re.search(r"(\d+)\s*assignments?\b", text, re.IGNORECASE)
        if assign_count_match:
            entities["assignments_count"] = int(assign_count_match.group(1))

        # 5. Grading minutes extraction
        mins_match = re.search(r"(\d+(?:\.\d+)?)\s*minutes?\b", text, re.IGNORECASE)
        if mins_match:
            entities["grading_minutes"] = float(mins_match.group(1))

        # 6. Topic/Query extraction for notes
        # A. Explicit search notes for pattern
        notes_search_match = re.search(
            r"\b(?:search|find)\s+.*?\bnotes\s+(?:on|about|for)\s+(.+?)(?:\?|\.|$)",
            text.strip(),
            re.IGNORECASE,
        )
        if notes_search_match:
            entities["notes_query"] = notes_search_match.group(1).strip()

        # B. Check natural question / explain intent
        if "notes_query" not in entities:
            q_match = re.search(
                r"^(?:what\s+(?:is|are|does)|explain|tell\s+me\s+about|describe|how\s+does|what\s+about|find|search(?:\s+for)?)\s+(.+?)(?:\?|\.|$)",
                text.strip(),
                re.IGNORECASE,
            )
            if q_match:
                raw_q = q_match.group(1).strip()
                # Clean common wrappers and filler phrases
                raw_q = re.sub(r"\b(?:in|for|from|of)\s+(?:26ECAC401|Agentic\s+AI|AI)\b", "", raw_q, flags=re.IGNORECASE)
                raw_q = re.sub(r"^(?:the|a|an)\s+", "", raw_q.strip(), flags=re.IGNORECASE)
                raw_q = re.sub(r"\b(?:course\s+notes|notes|course|material|materials|concepts|concept)\b", "", raw_q, flags=re.IGNORECASE).strip()
                if raw_q:
                    entities["notes_query"] = raw_q

        if "notes_query" not in entities:
            topic_match = re.search(
                r"(?:cover(?:s)?\s+about|notes\s+(?:on|about|for)|about|search\s+(?:notes\s+for\s+)?)\s+([a-zA-Z0-9\s\-_]{3,45}?)(?:\s*,\s*and|\s+in\s+[A-Z0-9]|\?|$)",
                text,
                re.IGNORECASE,
            )
            if topic_match:
                query_raw = topic_match.group(1).strip()
                query_clean = re.sub(r"^(the|a|an)\s+", "", query_raw, flags=re.IGNORECASE)
                entities["notes_query"] = query_clean

        if "notes_query" not in entities:
            # Fallback keyword extraction for Agentic AI topics
            for kw in [
                "react", "tree of thoughts", "chain of thought", "plan-act-observe-revise",
                "langgraph", "langchain", "mcp", "model context protocol",
                "memory", "tools", "skills", "perception", "reasoning", "learning",
                "function calling", "sandboxing", "runtime", "evolution",
                "multi-agent orchestration", "multi-agent", "safety", "governance",
            ]:
                if kw in text.lower():
                    entities["notes_query"] = kw
                    break

        return entities

    def plan_next_action(
        self,
        user_request: str,
        context: dict[str, Any],
        verified_facts: dict[str, Any],
        steps: list[AuditableTraceStep],
    ) -> Optional[ToolAction]:
        """Determine the next tool action to take, or None if sufficient evidence is gathered."""
        entities = self.extract_entities(user_request)
        course_id = entities.get("course_id") or context.get("course_id") or CANONICAL_COURSE_CODE
        assignment_id = (
            context.get("assignment_id")
            or entities.get("assignment_id")
        )
        req_lower = user_request.lower()

        executed_tools = [s.tool_call.tool_name for s in steps if s.tool_call]

        # ---------------------------------------------------------------------
        # Scenario 4: Workload & TA Staffing Sufficiency (Multi-Tool: TA Policy -> Workload)
        # ---------------------------------------------------------------------
        if (
            "workload" in req_lower
            or "sufficient" in req_lower
            or ("minutes" in req_lower and "grading" in req_lower)
            or ("staffing" in req_lower and "assignments" in req_lower)
        ):
            enrollment = entities.get("enrollment_count", 120)
            assign_count = entities.get("assignments_count", 4)
            grading_mins = entities.get("grading_minutes", 15.0)

            if "get_ta_policy" not in executed_tools:
                return ToolAction(
                    tool_name="get_ta_policy",
                    parameters={"course_id": course_id, "enrollment_count": enrollment},
                    rationale=f"Retrieve official TA staffing headcount and weekly capacity for {enrollment} students in {course_id}.",
                )

            if "compute_workload_hours" not in executed_tools:
                return ToolAction(
                    tool_name="compute_workload_hours",
                    parameters={
                        "enrollment": enrollment,
                        "assignments_count": assign_count,
                        "grading_minutes_per_submission": grading_mins,
                    },
                    rationale=f"Compute total grading workload hours for {enrollment} submissions across {assign_count} assignments at {grading_mins} min/submission.",
                )

            return None

        # ---------------------------------------------------------------------
        # Scenario 5: Notes Coverage + Assignment Application
        # ---------------------------------------------------------------------
        if ("cover" in req_lower or "notes" in req_lower) and ("assignment" in req_lower or "apply" in req_lower):
            query = entities.get("notes_query", "react")
            assign_id = assignment_id or ""

            if "search_course_notes" not in executed_tools:
                return ToolAction(
                    tool_name="search_course_notes",
                    parameters={"course_id": course_id, "query": query},
                    rationale=f"Search {course_id} course notes and weekly materials for coverage of '{query}'.",
                )

            if "get_assignment_spec" not in executed_tools:
                return ToolAction(
                    tool_name="get_assignment_spec",
                    parameters={"course_id": course_id, "assignment_id": assign_id},
                    rationale=f"Retrieve specification for assignment '{assign_id}' in {course_id} to verify concept application.",
                )

            return None

        # ---------------------------------------------------------------------
        # Scenario 2: Rubric Inquiry
        # ---------------------------------------------------------------------
        if "rubric" in req_lower or "code quality" in req_lower or "criteria" in req_lower:
            assign_id = assignment_id or ""
            if "get_rubric_breakdown" not in executed_tools:
                return ToolAction(
                    tool_name="get_rubric_breakdown",
                    parameters={"course_id": course_id, "assignment_id": assign_id},
                    rationale=f"Retrieve structured grading rubric breakdown for {course_id} assignment '{assign_id}'.",
                )
            return None

        # ---------------------------------------------------------------------
        # Scenario 3: TA Policy Inquiry (Single-tool)
        # ---------------------------------------------------------------------
        if any(k in req_lower for k in ["ta hours", "ta policy", "teaching assistant", "how many ta", "ta staffing"]):
            enrollment = entities.get("enrollment_count", 120)
            if "get_ta_policy" not in executed_tools:
                return ToolAction(
                    tool_name="get_ta_policy",
                    parameters={"course_id": course_id, "enrollment_count": enrollment},
                    rationale=f"Calculate required TA headcount and weekly hours for {enrollment} students in {course_id}.",
                )
            return None

        # ---------------------------------------------------------------------
        # Scenario 1: Grading Breakdown Audit (Multi-Tool: Syllabus -> Calculator)
        # ---------------------------------------------------------------------
        if any(k in req_lower for k in ["grading", "grade", "breakdown", "weights", "sum to 100", "audit"]):
            # If we haven't fetched syllabus yet:
            if "read_course_syllabus" not in executed_tools:
                return ToolAction(
                    tool_name="read_course_syllabus",
                    parameters={"course_id": course_id},
                    rationale=f"Retrieve canonical course syllabus and authoritative grading breakdown weights for {course_id}.",
                )

            # If syllabus succeeded and has grading weights, calculate total:
            if "read_course_syllabus" in executed_tools and "calculate_grade_breakdown_total" not in executed_tools:
                last_step = next((s for s in steps if s.tool_call and s.tool_call.tool_name == "read_course_syllabus"), None)
                if last_step and last_step.tool_call and last_step.tool_call.status == ToolExecutionStatus.SUCCESS and last_step.tool_call.output_data:
                    grading_weights_data = last_step.tool_call.output_data.get("grading_weights", [])
                    if grading_weights_data:
                        raw_weights = [gw["weight_percentage"] for gw in grading_weights_data]
                        return ToolAction(
                            tool_name="calculate_grade_breakdown_total",
                            parameters={"weights": raw_weights},
                            rationale=f"Calculate the exact total percentage and validity delta for the {len(raw_weights)} extracted grading weights.",
                        )

            return None

        # ---------------------------------------------------------------------
        # Notes Search (Single-tool)
        # ---------------------------------------------------------------------
        if (
            "notes" in req_lower
            or "search" in req_lower
            or "notes_query" in entities
            or any(kw in req_lower for kw in ["what is", "what are", "explain", "describe", "tell me", "concept", "orchestration", "calling", "governance", "safety"])
        ):
            query = entities.get("notes_query") or user_request.strip()
            if "search_course_notes" not in executed_tools:
                return ToolAction(
                    tool_name="search_course_notes",
                    parameters={"course_id": course_id, "query": query},
                    rationale=f"Search {course_id} course notes and materials for query keyword '{query}'.",
                )
            return None

        # ---------------------------------------------------------------------
        # Assignment Spec (Single-tool)
        # ---------------------------------------------------------------------
        if "assignment" in req_lower or "deliverables" in req_lower or "spec" in req_lower:
            assign_id = assignment_id or ""
            if "get_assignment_spec" not in executed_tools:
                return ToolAction(
                    tool_name="get_assignment_spec",
                    parameters={"course_id": course_id, "assignment_id": assign_id},
                    rationale=f"Retrieve specification and deliverables for {course_id} assignment '{assign_id}'.",
                )
            return None

        # ---------------------------------------------------------------------
        # Course Config (Single-tool)
        # ---------------------------------------------------------------------
        if "config" in req_lower or "environment" in req_lower or "prerequisites" in req_lower or "policy" in req_lower:
            if "get_course_config" not in executed_tools:
                return ToolAction(
                    tool_name="get_course_config",
                    parameters={"course_id": course_id},
                    rationale=f"Retrieve configuration parameters, prerequisites, and lab environment for {course_id}.",
                )
            return None

        # Fallback 1: Syllabus inspection if requested
        if any(k in req_lower for k in ["syllabus", "module", "modules", "overview", "chapter", "curriculum"]):
            if "read_course_syllabus" not in executed_tools:
                return ToolAction(
                    tool_name="read_course_syllabus",
                    parameters={"course_id": course_id},
                    rationale=f"Retrieve canonical course syllabus for {course_id}.",
                )
            return None

        # Fallback 2: General course notes search
        if "search_course_notes" not in executed_tools:
            query = entities.get("notes_query") or user_request.strip()
            return ToolAction(
                tool_name="search_course_notes",
                parameters={"course_id": course_id, "query": query},
                rationale=f"Search {course_id} course notes for '{query}'.",
            )

        return None
