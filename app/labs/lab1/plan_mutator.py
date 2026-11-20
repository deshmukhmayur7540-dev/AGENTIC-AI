"""Plan mutator applying structured change intents to CourseWorkspacePlan objects."""

import copy
from typing import Any
from app.models.lab1_models import (
    CourseWorkspacePlan,
    WeeklyMaterial,
    AssignmentSpec,
    GradeBreakdownItem,
)
from app.labs.lab1.intent_parser import (
    BaseChangeIntent,
    DurationChangeIntent,
    AssignmentAdditionIntent,
    AssignmentScheduleIntent,
    GradeWeightChangeIntent,
    MaterialChangeIntent,
    DeliverableAdditionIntent,
    StaffingChangeIntent,
)


class PlanMutator:
    """Applies structured change intents to mutate a deep copy of CourseWorkspacePlan."""

    # Curated extension topics for expanding course length
    EXPANSION_TOPICS = [
        ("Concurrency & Asynchronous Systems", ["Threading, Asyncio & Multiprocessing", "Race Conditions & Mutex Locks", "Concurrent Event Loops"], ["Fluent Python - Ch 18", "Async Python In-Depth"], "Deep dive into asynchronous programming, concurrency models, and non-blocking I/O."),
        ("Performance Optimization & Profiling", ["Memory Profiling & CPU Bottlenecks", "C-Extensions & Cython", "Benchmarking Methodologies"], ["High Performance Python Ch 1-3", "Profiling Docs"], "Techniques for measuring, benchmarking, and profiling system memory and execution bottlenecks."),
        ("Cloud Native Deployment & CI/CD Pipelines", ["Containerization with Docker", "GitHub Actions Automated CI/CD", "Cloud Infrastructure Deployment"], ["Kubernetes & Docker in Action", "Cloud Deployment Patterns"], "Automated test integration, containerized deployments, and production runtime environments."),
        ("Security Best Practices & Defensive Engineering", ["Input Sanitization & Injection Prevention", "Authentication, JWT & OAuth2", "Defensive Code Audits"], ["OWASP Top 10 Guidelines", "Secure Software Engineering"], "Identifying vulnerabilities, securing APIs, and defensive programming patterns."),
        ("System Architecture & Final Synthesis", ["Monolith to Microservices Evolution", "CAP Theorem & Scalability Tradeoffs", "Capstone Architecture Reviews"], ["Designing Data-Intensive Applications", "Clean Architecture"], "Holistic synthesis of system architecture trade-offs, scalability invariants, and final capstone review."),
    ]

    def mutate(self, current_plan: CourseWorkspacePlan, intents: list[BaseChangeIntent]) -> dict[str, Any]:
        """Apply all intents sequentially to a deep-copied plan dictionary."""
        plan_dict = copy.deepcopy(current_plan.model_dump())

        for intent in intents:
            if isinstance(intent, DurationChangeIntent):
                self._apply_duration_change(plan_dict, intent)
            elif isinstance(intent, AssignmentAdditionIntent):
                self._apply_assignment_addition(plan_dict, intent)
            elif isinstance(intent, AssignmentScheduleIntent):
                self._apply_assignment_scheduling(plan_dict, intent)
            elif isinstance(intent, GradeWeightChangeIntent):
                self._apply_grade_weight_change(plan_dict, intent)
            elif isinstance(intent, MaterialChangeIntent):
                self._apply_material_change(plan_dict, intent)
            elif isinstance(intent, DeliverableAdditionIntent):
                self._apply_deliverable_addition(plan_dict, intent)
            elif isinstance(intent, StaffingChangeIntent):
                self._apply_staffing_change(plan_dict, intent)

        return plan_dict

    def _apply_duration_change(self, plan_dict: dict[str, Any], intent: DurationChangeIntent) -> None:
        """Modify duration weeks and adjust weekly materials array accordingly."""
        current_weeks = plan_dict.get("duration_weeks", 10)
        
        if intent.target_weeks is not None:
            new_weeks = intent.target_weeks
        elif intent.delta_weeks is not None:
            new_weeks = current_weeks + intent.delta_weeks
        else:
            return

        new_weeks = max(1, min(24, new_weeks))
        plan_dict["duration_weeks"] = new_weeks

        materials = plan_dict.get("materials_and_notes", [])
        
        # If duration expanded, synthesize high-quality weekly modules for added weeks
        if new_weeks > len(materials):
            start_week = len(materials) + 1
            for w in range(start_week, new_weeks + 1):
                topic_idx = (w - start_week) % len(self.EXPANSION_TOPICS)
                t_title, t_subtopics, t_readings, t_notes = self.EXPANSION_TOPICS[topic_idx]
                materials.append({
                    "week": w,
                    "title": f"Week {w}: {t_title}",
                    "topics": t_subtopics,
                    "reading_materials": t_readings,
                    "lecture_notes_summary": t_notes,
                })
        elif new_weeks < len(materials):
            materials = materials[:new_weeks]

        plan_dict["materials_and_notes"] = materials

        # Cap assignment due dates at new duration
        assignments = plan_dict.get("assignments", [])
        for asgn in assignments:
            if asgn.get("due_week") is not None and asgn["due_week"] > new_weeks:
                asgn["due_week"] = new_weeks

    def _apply_assignment_addition(self, plan_dict: dict[str, Any], intent: AssignmentAdditionIntent) -> None:
        """Add a new assignment specification to the assignments list."""
        assignments = plan_dict.get("assignments", [])
        duration_weeks = plan_dict.get("duration_weeks", 10)

        existing_labs = [a for a in assignments if "LAB" in a["assignment_id"].upper()]
        lab_num = len(existing_labs) + 1

        if intent.topic_hint:
            title = f"Lab {lab_num}: Practical {intent.topic_hint.title()} Implementation"
            desc = f"Hands-on programming laboratory focusing on practical implementation and empirical validation of {intent.topic_hint}."
            deliverables = [
                f"Source code implementation module for {intent.topic_hint}",
                "Automated test suite with 90%+ branch coverage",
                "Technical lab report and benchmarking results (PDF)",
            ]
        elif intent.assignment_type == "lab":
            title = f"Lab {lab_num}: Advanced Hands-on Programming Practical"
            desc = "Comprehensive laboratory implementation reinforcing modular software architecture and rigorous testing."
            deliverables = [
                "Modular source code repository with CI configuration",
                "Automated unit and integration test suite",
                "Execution output logs and design rationale writeup",
            ]
        else:
            title = f"Assignment {len(assignments) + 1}: Problem Set & Design Exercise"
            desc = "Theoretical problem set and architectural modeling exercise."
            deliverables = ["Written problem set solutions (PDF)", "Code validation scripts"]

        # Position due week sensibly before final week
        due_week = intent.due_week or min(duration_weeks - 1, max(2, duration_weeks // 2 + 1))

        new_assignment = {
            "assignment_id": f"LAB_PRACTICAL_{lab_num}" if intent.assignment_type == "lab" else f"HW_{len(assignments) + 1}",
            "title": title,
            "due_week": due_week,
            "description": desc,
            "deliverables": deliverables,
            "max_points": 100,
            "weight_percentage": 10.0,
        }

        # Insert before final project if exists
        project_idx = next((i for i, a in enumerate(assignments) if "project" in a["title"].lower() or "capstone" in a["title"].lower()), -1)
        if project_idx != -1:
            assignments.insert(project_idx, new_assignment)
        else:
            assignments.append(new_assignment)

        plan_dict["assignments"] = assignments

    def _apply_assignment_scheduling(self, plan_dict: dict[str, Any], intent: AssignmentScheduleIntent) -> None:
        """Reschedule assignment due date."""
        assignments = plan_dict.get("assignments", [])
        duration_weeks = plan_dict.get("duration_weeks", 10)
        target_week = max(1, min(duration_weeks, intent.target_week))

        matched = False
        for asgn in assignments:
            if (intent.assignment_hint.lower() in asgn["assignment_id"].lower() or
                intent.assignment_hint.lower() in asgn["title"].lower()):
                asgn["due_week"] = target_week
                matched = True
                break

        # If not matched by exact name, match by type (e.g. "lab 2")
        if not matched:
            for asgn in assignments:
                if intent.assignment_hint.lower() in asgn["title"].lower():
                    asgn["due_week"] = target_week
                    break

    def _apply_grade_weight_change(self, plan_dict: dict[str, Any], intent: GradeWeightChangeIntent) -> None:
        """Modify category grade weight and rebalance other categories to preserve exact 100% total."""
        grades = plan_dict.get("grade_breakdown", [])
        hint = intent.category_hint.lower()

        # Find matching grade breakdown category
        matched_idx = -1
        for idx, item in enumerate(grades):
            cat_name = item["category"].lower()
            if (hint in cat_name or
                (hint == "capstone" and "project" in cat_name) or
                (hint == "project" and "capstone" in cat_name) or
                (hint == "final" and "project" in cat_name) or
                (hint == "exam" and ("midterm" in cat_name or "exam" in cat_name)) or
                (hint == "hw" and "homework" in cat_name)):
                matched_idx = idx
                break

        if matched_idx == -1:
            # If no direct match, match first item that contains substring
            for idx, item in enumerate(grades):
                if any(w in item["category"].lower() for w in hint.split()):
                    matched_idx = idx
                    break

        if matched_idx != -1:
            target_item = grades[matched_idx]
            old_weight = target_item["weight_percentage"]

            if intent.delta_percentage_points is not None:
                new_weight = old_weight + intent.delta_percentage_points
            elif intent.target_weight is not None:
                new_weight = intent.target_weight
            else:
                return

            new_weight = max(5.0, min(80.0, round(new_weight, 1)))
            target_item["weight_percentage"] = new_weight

            # Rebalance other categories to preserve exact sum = 100.0%
            if intent.rebalance_others:
                other_indices = [i for i in range(len(grades)) if i != matched_idx]
                if other_indices:
                    delta = new_weight - old_weight
                    remaining_pool = 100.0 - new_weight
                    current_others_sum = sum(grades[i]["weight_percentage"] for i in other_indices)

                    if current_others_sum > 0:
                        for i in other_indices:
                            proportion = grades[i]["weight_percentage"] / current_others_sum
                            grades[i]["weight_percentage"] = round(remaining_pool * proportion, 1)

                    # Ensure exact 100.0% sum by adjusting rounding difference on first other item
                    current_sum = sum(g["weight_percentage"] for g in grades)
                    diff = round(100.0 - current_sum, 1)
                    if diff != 0 and other_indices:
                        grades[other_indices[0]]["weight_percentage"] = round(grades[other_indices[0]]["weight_percentage"] + diff, 1)

    def _apply_material_change(self, plan_dict: dict[str, Any], intent: MaterialChangeIntent) -> None:
        """Add or update lecture notes, modules, or sections with source grounding."""
        materials = plan_dict.get("materials_and_notes", [])
        duration_weeks = plan_dict.get("duration_weeks")

        # Determine if prompt/intent maps to Chapter 1 or other grounded documents
        topic_lower = (intent.topic_title + " " + " ".join(intent.topics)).lower()
        if "react" in topic_lower or "tree of thoughts" in topic_lower or "reasoning" in topic_lower:
            source_doc = "Chapter1_Foundations_of_Agentic_AI.docx"
            source_sec = "1.8 Planning Strategies"
        elif "mcp" in topic_lower or "model context protocol" in topic_lower:
            source_doc = "Chapter_2_Agent_Frameworks_Tools_Skills_Memory.docx"
            source_sec = "2.5 Model Context Protocol (MCP)"
        elif "langgraph" in topic_lower or "graph" in topic_lower:
            source_doc = "Chapter_2_Agent_Frameworks_Tools_Skills_Memory.docx"
            source_sec = "2.1 Agent Frameworks and Tool Integration"
        elif "multi-agent" in topic_lower or "orchestration" in topic_lower:
            source_doc = "Chapter_3_Multi_Agent_Orchestration.docx"
            source_sec = "3.1 Multi-Agent Systems"
        elif "safety" in topic_lower or "governance" in topic_lower or "ethics" in topic_lower:
            source_doc = "Chapter_4_Learning_Deployment_Safety_Governance.docx"
            source_sec = "4.1 Safety & Governance"
        else:
            source_doc = "Chapter1_Foundations_of_Agentic_AI.docx"
            source_sec = "1.8 Planning Strategies"

        # Case 1: Source-based organization (duration_weeks is None)
        if duration_weeks is None:
            # Check if user targeted an existing section title
            matched_mat = None
            for mat in materials:
                if any(kw in mat["title"].lower() for kw in topic_lower.split() if len(kw) > 4):
                    # Only match if not an explicit "add one more section" / "add section" request
                    if "add" not in intent.topic_title.lower() and "add" not in topic_lower:
                        matched_mat = mat
                        break

            if matched_mat:
                if intent.topic_title:
                    matched_mat["title"] = intent.topic_title
                if intent.topics:
                    for t in intent.topics:
                        if t not in matched_mat["topics"]:
                            matched_mat["topics"].append(t)
                if intent.reading_materials:
                    for r in intent.reading_materials:
                        if r not in matched_mat["reading_materials"]:
                            matched_mat["reading_materials"].append(r)
                if intent.notes_summary:
                    matched_mat["lecture_notes_summary"] = intent.notes_summary
            else:
                # Append new grounded section
                sec_num = len(materials) + 1
                sec_label = f"Section 1.{sec_num}"
                clean_title = re.sub(r"^Week\s+\d+:\s*", "", intent.topic_title).strip()
                if not clean_title.startswith("Section"):
                    final_title = f"{sec_label}: {clean_title}"
                else:
                    final_title = clean_title

                new_section = {
                    "week": None,
                    "section_label": sec_label,
                    "title": final_title,
                    "topics": intent.topics or [clean_title],
                    "reading_materials": intent.reading_materials or [f"{source_doc} - {source_sec}"],
                    "lecture_notes_summary": intent.notes_summary or f"Deep-dive module covering {clean_title}.",
                    "provenance": "COURSE_GROUNDED",
                    "source_document": source_doc,
                    "source_section": source_sec,
                }
                materials.append(new_section)

            plan_dict["materials_and_notes"] = materials
            return

        # Case 2: Weekly schedule organization (duration_weeks is not None)
        target_w = intent.target_week
        matched_mat = None
        if target_w is not None:
            for mat in materials:
                if mat.get("week") == target_w:
                    matched_mat = mat
                    break

        if matched_mat:
            clean_title = intent.topic_title
            matched_mat["title"] = clean_title
            if intent.topics:
                for t in intent.topics:
                    if t not in matched_mat["topics"]:
                        matched_mat["topics"].append(t)
            if intent.reading_materials:
                for r in intent.reading_materials:
                    if r not in matched_mat["reading_materials"]:
                        matched_mat["reading_materials"].append(r)
            if intent.notes_summary:
                matched_mat["lecture_notes_summary"] = intent.notes_summary
        else:
            # Append new week and increment duration_weeks to preserve validator invariant
            new_week = len(materials) + 1
            clean_title = re.sub(r"^Week\s+\d+:\s*", "", intent.topic_title).strip()
            new_mat = {
                "week": new_week,
                "section_label": f"Week {new_week}",
                "title": f"Week {new_week}: {clean_title}",
                "topics": intent.topics or [clean_title],
                "reading_materials": intent.reading_materials or [f"{source_doc} - {source_sec}"],
                "lecture_notes_summary": intent.notes_summary or f"Weekly module covering {clean_title}.",
                "provenance": "COURSE_GROUNDED",
                "source_document": source_doc,
                "source_section": source_sec,
            }
            materials.append(new_mat)
            plan_dict["duration_weeks"] = len(materials)

        plan_dict["materials_and_notes"] = materials

    def _apply_deliverable_addition(self, plan_dict: dict[str, Any], intent: DeliverableAdditionIntent) -> None:
        """Add required deliverable artifact to project or practical assignments."""
        assignments = plan_dict.get("assignments", [])
        hint = intent.target_assignment_hint.lower()

        for asgn in assignments:
            if hint == "all" or hint in asgn["title"].lower() or hint in asgn["assignment_id"].lower():
                if intent.deliverable_text not in asgn["deliverables"]:
                    asgn["deliverables"].append(intent.deliverable_text)

    def _apply_staffing_change(self, plan_dict: dict[str, Any], intent: StaffingChangeIntent) -> None:
        """Modify weekly TA allocation hours."""
        plan_dict["ta_allocation_hours"] = intent.ta_hours


plan_mutator = PlanMutator()
