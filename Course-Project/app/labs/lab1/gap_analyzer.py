"""Gap analyzer for detecting missing course information and generating clarification questions."""

import re
import uuid
from app.core.constants import CANONICAL_COURSE_CODE, CANONICAL_COURSE_NAME
from app.models.lab1_models import (
    FacultyCourseRequest,
    ClarificationQuestion,
    MissingInfoCategory,
)


class GapAnalyzer:
    """Analyzes faculty prompts to detect missing course workspace dimensions and generates clarification questions."""

    def analyze(self, request: FacultyCourseRequest) -> list[ClarificationQuestion]:
        """Examine faculty prompt and produce at least two targeted clarification questions."""
        prompt_lower = request.raw_prompt.lower()
        detected_gaps: list[MissingInfoCategory] = []

        # Check intent characteristics
        is_chapter_or_material_request = any(
            kw in prompt_lower for kw in [
                "chapter 1", "chapter 2", "chapter 3", "chapter 4",
                "organize my", "learning material", "notes", "study guide"
            ]
        ) and not any(kw in prompt_lower for kw in ["full syllabus", "grade distribution", "grading weights", "with weekly labs"])

        user_asked_grading = any(kw in prompt_lower for kw in ["grade", "grading", "weight", "percentage", "rubric", "exam", "midterm"])
        user_asked_assignments = any(kw in prompt_lower for kw in ["homework", "lab", "assignment", "problem set", "deliverable", "project"])
        has_duration = bool(re.search(r"\b(\d{1,2}[\s\-]*weeks?|\d{1,2}[\s\-]*months?|semester|quarter)\b", prompt_lower))

        if is_chapter_or_material_request and not user_asked_grading and not user_asked_assignments:
            # For chapter learning material organization, the genuine unknowns are:
            # 1. Pacing/Duration format (modular vs scheduled weeks)
            # 2. Conceptual focus/depth
            if not has_duration:
                detected_gaps.append(MissingInfoCategory.SCHEDULE_PACING)
            detected_gaps.append(MissingInfoCategory.MATERIALS_PREREQUISITES)
        else:
            # Full course / syllabus workspace request
            # 1. Check Schedule & Duration
            if not has_duration:
                detected_gaps.append(MissingInfoCategory.SCHEDULE_PACING)

            # 2. Check Materials & Prerequisites
            has_prereqs = any(kw in prompt_lower for kw in ["prereq", "prerequisite", "prior knowledge", "assumed background", "sophomore", "junior", "senior", "freshman", "beginner", "advanced"])
            has_materials = any(kw in prompt_lower for kw in ["textbook", "reading", "lecture notes", "slides", "papers", "book"])
            if not (has_prereqs and has_materials):
                detected_gaps.append(MissingInfoCategory.MATERIALS_PREREQUISITES)

            # 3. Check Assignments & Labs
            has_cadence = any(kw in prompt_lower for kw in ["weekly", "biweekly", "milestone", "due"])
            has_assignments = user_asked_assignments
            if user_asked_assignments or not (has_assignments and has_cadence):
                detected_gaps.append(MissingInfoCategory.ASSIGNMENTS_LABS)

            # 4. Check Grading Weights & Distribution (only if requested or in comprehensive syllabus design)
            has_percentages = bool(re.search(r"\b\d{1,2}%\b", prompt_lower))
            if user_asked_grading or not has_percentages:
                detected_gaps.append(MissingInfoCategory.GRADING_WEIGHTS)

            # 5. Check TA & Staffing
            has_ta = any(kw in prompt_lower for kw in ["ta", "teaching assistant", "office hours", "grading staff", "tutors", "mentors"])
            if not has_ta and not is_chapter_or_material_request:
                detected_gaps.append(MissingInfoCategory.TA_SUPPORT)

        # Ensure we always generate at least two meaningful clarification questions
        if len(detected_gaps) < 2:
            all_categories = [
                MissingInfoCategory.SCHEDULE_PACING,
                MissingInfoCategory.MATERIALS_PREREQUISITES,
                MissingInfoCategory.ASSIGNMENTS_LABS,
                MissingInfoCategory.GRADING_WEIGHTS,
                MissingInfoCategory.TA_SUPPORT,
            ]
            for cat in all_categories:
                if cat not in detected_gaps:
                    # Don't add grading to chapter notes organization if not asked
                    if is_chapter_or_material_request and cat == MissingInfoCategory.GRADING_WEIGHTS and not user_asked_grading:
                        continue
                    detected_gaps.append(cat)
                if len(detected_gaps) >= 2:
                    break

        # Generate structured questions based on detected gaps
        questions: list[ClarificationQuestion] = []
        for gap in detected_gaps:
            q = self._create_question_for_gap(gap, request, is_chapter_or_material_request)
            if q:
                questions.append(q)

        # Ensure at least 2 questions are returned
        return questions[:4]

    def _create_question_for_gap(
        self,
        gap: MissingInfoCategory,
        request: FacultyCourseRequest,
        is_chapter_or_material_request: bool = False,
    ) -> ClarificationQuestion:
        """Create a targeted clarification question with suggested choices."""
        prompt_lower = request.raw_prompt.lower()
        topic_hint = request.course_title_hint or f"{CANONICAL_COURSE_NAME} ({CANONICAL_COURSE_CODE})"

        if gap == MissingInfoCategory.SCHEDULE_PACING:
            if is_chapter_or_material_request:
                return ClarificationQuestion(
                    question_id=f"q-{uuid.uuid4().hex[:6]}",
                    category=MissingInfoCategory.SCHEDULE_PACING,
                    question_text="What schedule or pacing should be used to organize this learning material?",
                    rationale="Determines whether the course notes are structured as an unscheduled modular concept sequence, an intensive study block, or an extended multi-week schedule.",
                    suggested_options=[
                        "Modular Concept Structure: Organize strictly by source sections without an artificial weekly schedule",
                        "4-Week Intensive Plan: 2 core modules per week with focus checkpoints",
                        "6-Week In-Depth Study: Paced weekly exploration of foundational theory, planning loops, and scalability",
                        "10-Week Semester Schedule: Spread across a standard academic term with reflection checkpoints",
                    ],
                )
            return ClarificationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:6]}",
                category=MissingInfoCategory.SCHEDULE_PACING,
                question_text="What is the planned course pacing and total duration in weeks?",
                rationale="Required to schedule weekly lecture modules, reading materials, and assignment due dates evenly.",
                suggested_options=[
                    "10 Weeks (Standard Quarter System): Fast-paced quarter term schedule",
                    "12 Weeks (Accelerated Semester): Balanced weekly cadence with midterm checkpoint",
                    "15 Weeks (Full Academic Semester): In-depth coverage with dedicated review and project presentation weeks",
                ],
            )

        elif gap == MissingInfoCategory.MATERIALS_PREREQUISITES:
            if is_chapter_or_material_request:
                return ClarificationQuestion(
                    question_id=f"q-{uuid.uuid4().hex[:6]}",
                    category=MissingInfoCategory.MATERIALS_PREREQUISITES,
                    question_text=f"What organizational focus and conceptual depth do you want for the {topic_hint} material?",
                    rationale="Determines whether to cover all 8 core foundational sections from the notes or focus heavily on specific reasoning/lifecycle mechanisms.",
                    suggested_options=[
                        "Comprehensive Foundations: Cover all 8 source sections (Intro, Agency Pillars, Architecture, Lifecycle, Decomposition, Reasoning, Scalability, Scenarios)",
                        "Reasoning & Planning Deep-Dive: Focus heavily on CoT, ReAct (Reason+Act), Tree of Thoughts, and Plan-and-Execute",
                        "Systems & Architecture Focus: Focus on Perception-Reasoning-Action components, single vs multi-agent systems, and production guardrails",
                    ],
                )
            return ClarificationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:6]}",
                category=MissingInfoCategory.MATERIALS_PREREQUISITES,
                question_text=f"What prerequisite background and core learning materials should be anchored in the {topic_hint} curriculum?",
                rationale="Determines whether weekly lecture notes and readings start from foundational fundamentals or jump directly into advanced topics.",
                suggested_options=[
                    "Foundational: Assumes GenAI & basic Python; utilize official Chapter 1-2 lecture notes, academic papers, and interactive notebooks.",
                    "Advanced: Assumes async programming & API integration; utilize research papers on ReAct, LangGraph, and Model Context Protocol (MCP).",
                    "Applied Systems: Assumes software engineering experience; focus on sandboxed tool execution and autonomous agent architectures.",
                ],
            )

        elif gap == MissingInfoCategory.GRADING_WEIGHTS:
            return ClarificationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:6]}",
                category=MissingInfoCategory.GRADING_WEIGHTS,
                question_text="What assessment and grading weight distribution should be established for your syllabus?",
                rationale="The official Agentic AI course notes do not establish university grading policy. If grading weights are desired, please specify your distribution.",
                suggested_options=[
                    "User-Provided Balanced: 30% Weekly Labs, 20% Homework, 20% Midterm Exam, 30% Capstone Project",
                    "User-Provided Project-Heavy: 45% Team Milestone Project, 35% Hands-on Labs, 20% Quizzes & Participation",
                    "User-Provided Equal Distribution: 25% Labs, 25% Homework, 25% Midterm, 25% Final Project",
                    "Unestablished: Do not establish grading weights at this time",
                ],
            )

        elif gap == MissingInfoCategory.ASSIGNMENTS_LABS:
            return ClarificationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:6]}",
                category=MissingInfoCategory.ASSIGNMENTS_LABS,
                question_text="What format and tooling should practical assignments and programming labs require?",
                rationale="Specifies assignment deliverables, submission requirements, and automated testing environments.",
                suggested_options=[
                    "Weekly Individual Coding Labs with automated unit test grading + 1 Multi-Week Team Project",
                    "Bi-weekly Comprehensive Problem Sets with peer code review and live demonstrations",
                    "Milestone-Driven Scaffolding: Each lab builds directly toward the final end-to-end course application",
                ],
            )

        elif gap == MissingInfoCategory.TA_SUPPORT:
            return ClarificationQuestion(
                question_id=f"q-{uuid.uuid4().hex[:6]}",
                category=MissingInfoCategory.TA_SUPPORT,
                question_text="What TA staffing capacity and office hours model will support student lab grading?",
                rationale="Allocates weekly TA hours and determines the feasibility of manual grading vs automated testing.",
                suggested_options=[
                    "Standard Staffing: 10 hours/week dedicated to lab grading and weekly open office hours",
                    "Intensive Staffing: 20 hours/week for 1-on-1 code walkthroughs and debugging support",
                    "Lightweight / Automated: 5 hours/week primarily assisting with automated grading appeals",
                ],
            )

        # Fallback question
        return ClarificationQuestion(
            question_id=f"q-{uuid.uuid4().hex[:6]}",
            category=MissingInfoCategory.MATERIALS_PREREQUISITES,
            question_text="What are the primary learning goals and outcomes expected of students by the end of this course?",
            rationale="Clarifies the core objectives to align weekly lecture notes and assignments.",
            suggested_options=[
                "Mastery of core algorithmic concepts and implementation proficiency in real-world environments",
                "Applied project development focusing on software engineering best practices and teamwork",
                "Theoretical grounding and problem-solving readiness for advanced upper-division courses",
            ],
        )


gap_analyzer = GapAnalyzer()
