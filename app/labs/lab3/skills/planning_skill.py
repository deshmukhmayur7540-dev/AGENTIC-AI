"""Course Planning Skill: Case-agnostic academic pacing and weekly breakdown generator."""

from typing import Any
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID, CANONICAL_COURSE_NAME
from app.data.course_fixtures import get_canonical_syllabus_data
from app.labs.lab3.base import BaseSkill
from app.models.lab3_models import (
    CoursePlanningInput,
    CoursePlanningOutput,
    WeeklyScheduleItem,
)


class CoursePlanningSkill(BaseSkill):
    """Generates structured weekly schedules and milestone tracks based on syllabus requirements."""

    name = "course_planning_skill"
    title = "Course Planning & Pacing Skill"
    description = (
        "Synthesizes an academic term schedule, mapping weekly modules, learning outcomes, "
        "and practical deliverables across specified course duration."
    )
    category = "planning"
    version = "1.0.0"
    input_model = CoursePlanningInput
    output_model = CoursePlanningOutput

    CHAPTER_TOPIC_MAPPING = {
        1: {
            "title": "Foundations of Agentic AI & Autonomous Loops",
            "topics": [
                "Evolution from Generative AI to Agentic AI",
                "Autonomous Agent Characteristics (Perception, Reasoning, Learning, Action)",
                "Plan-Act-Observe-Revise Cycle",
                "Goal Decomposition (CoT, ReAct, Tree of Thoughts)",
            ],
            "lab": "Lab 1: Clarify -> Plan -> Revise Agent Workflow",
        },
        2: {
            "title": "Agent Frameworks, Tools, Skills & Memory Architectures",
            "topics": [
                "Tool Calling & Pydantic Schema Validation",
                "Reusable Skill Discovery and Dynamic Execution",
                "Memory Architectures: Short-term Session State vs Long-term RAG",
                "Model Context Protocol (MCP) Governed Runtime",
            ],
            "lab": "Lab 2: Tool-Using Agent with Auditable Trace",
        },
        3: {
            "title": "Multi-Agent Orchestration & Stateful Graphs",
            "topics": [
                "Multi-Agent Topologies & Hierarchical Teams",
                "Communication Protocols & Shared Memory Channels",
                "LangGraph Stateful Cyclic Execution",
                "Conflict Resolution, Consensus & Negotiation",
            ],
            "lab": "Lab 7: Multi-Agent Stateful Graph Orchestration",
        },
        4: {
            "title": "Learning, Deployment, Safety & Governance",
            "topics": [
                "Agentic Learning Paradigms & Feedback Loops",
                "Safety Guardrails, Quotas & Resource Budgets",
                "Human-in-the-Loop Approval Gates & Audit Trails",
                "Autonomous Incident Remediation & SDLC Benchmarks",
            ],
            "lab": "Lab 6: Controlled Runtime with Human Approval Gates",
        },
    }

    def _run(self, validated_input: CoursePlanningInput) -> CoursePlanningOutput:
        course_id = normalize_course_id(validated_input.course_code) or validated_input.course_code
        weeks = validated_input.target_weeks
        chapters = validated_input.focus_chapters or [1, 2, 3, 4]

        # Distribute weeks across chosen chapters
        schedule: list[WeeklyScheduleItem] = []
        weeks_per_ch = max(1, weeks // len(chapters))

        current_week = 1
        for idx, ch_num in enumerate(chapters):
            ch_data = self.CHAPTER_TOPIC_MAPPING.get(
                ch_num,
                {
                    "title": f"Chapter {ch_num}: Advanced Topics",
                    "topics": [f"Core Module {ch_num} Principles", "Applied Implementation", "Evaluation"],
                    "lab": f"Lab {ch_num}: Specialist Exercise",
                },
            )
            # Allocate weeks for this chapter
            allocated = weeks_per_ch if idx < len(chapters) - 1 else (weeks - current_week + 1)
            for sub_w in range(allocated):
                if current_week > weeks:
                    break
                schedule.append(
                    WeeklyScheduleItem(
                        week_number=current_week,
                        chapter_mapped=ch_num,
                        module_title=f"{ch_data['title']} (Part {sub_w + 1})" if allocated > 1 else ch_data["title"],
                        core_topics=ch_data["topics"],
                        lab_assignment=ch_data["lab"] if sub_w == allocated - 1 else None,
                    )
                )
                current_week += 1

        # Generate milestones
        milestones = [
            f"Week 1: Orientation and Workspace Initialization ({course_id})",
            f"Week {max(2, weeks // 4)}: Foundational Autonomous Loop Verification",
            f"Week {max(3, weeks // 2)}: Midterm Architecture Evaluation & Tool Integration",
            f"Week {max(4, int(weeks * 0.75))}: Multi-Agent Orchestration & Stateful Graph Checkpoint",
            f"Week {weeks}: Capstone Project Review & Faculty Final Assessment",
        ]

        return CoursePlanningOutput(
            course_code=course_id,
            course_name=validated_input.course_name,
            total_weeks=weeks,
            schedule=schedule,
            milestones=milestones,
            provenance_source=f"CoursePlanningSkill (Curriculum 26ECAC401 Grounding)",
        )
