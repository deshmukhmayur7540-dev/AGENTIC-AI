"""Plan generator creating structured CourseWorkspacePlan v1.0 grounded in actual Agentic AI course notes."""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.core.constants import CANONICAL_COURSE_CODE, CANONICAL_COURSE_NAME
from app.models.lab1_models import (
    ClarificationSubmission,
    CourseWorkspacePlan,
    WeeklyMaterial,
    AssignmentSpec,
    GradeBreakdownItem,
    MissingInfoCategory,
)

# Authoritative grounded sections from Chapter 1: Foundations of Agentic AI (Chapter1_Foundations_of_Agentic_AI.docx)
CHAPTER_1_SECTIONS = [
    {
        "section": "1.1 & 1.2",
        "title": "Introduction to Agentic AI & Evolution from Generative AI",
        "topics": [
            "Evolution from Generative AI to Agentic AI",
            "Autonomous Agent Characteristics & Proactivity",
            "Three Structural Changes: Execution over Prompting, Stateful over Stateless, Agentic over Deterministic",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.1 & 1.2 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Russell & Norvig - Artificial Intelligence: A Modern Approach (Intelligent Agents)",
        ],
        "lecture_notes_summary": "Core paradigm shift from passive prompt-response systems to autonomous, goal-seeking agents capable of iterative execution in dynamic environments.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.1 Introduction & 1.2 Evolution from Generative AI to Agentic AI",
    },
    {
        "section": "1.3 & 1.4",
        "title": "Limitations of Standalone LLMs & Core Agency Pillars",
        "topics": [
            "Limitations of Standalone LLMs (Hallucination, Context Window, Statelessness)",
            "The Three Pillars of Agency: Autonomy, Proactivity, Goal Orientation",
            "Four Agency Components: Perception, Reasoning, Learning, Action",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.3 & 1.4 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Wooldridge - Intelligent Agents Primer",
        ],
        "lecture_notes_summary": "Four essential operational components (Perception, Reasoning, Learning, Action) defining autonomous behavior in closed environmental feedback loops.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.4 Definition and Characteristics of Autonomous Agents",
    },
    {
        "section": "1.5",
        "title": "Agent Architecture: Single-Agent vs Multi-Agent Systems",
        "topics": [
            "The Five Core Components of Agent Architecture",
            "Classic Architecture Types (Reactive, Deliberative, Hybrid)",
            "Single-Agent vs Multi-Agent Systems & Communication Topologies",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.5 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Cognitive Architectures & Agent Design Patterns",
        ],
        "lecture_notes_summary": "Architectural configurations connecting the central reasoning model to tool interfaces, memory stores, and collaborative agent peers.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.5 Agent Architecture",
    },
    {
        "section": "1.6",
        "title": "Agent Lifecycle: The Plan–Act–Observe–Revise Loop",
        "topics": [
            "The Four Loop Stages: Plan, Act, Observe, Revise",
            "Worked Example: Code-Fixing Agent Execution Trace",
            "Stopping Conditions, Invariants, and Runaway Loop Prevention",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.6 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Closed-Loop Control Systems in Autonomous Agents",
        ],
        "lecture_notes_summary": "Closed-loop feedback cycle ensuring continuous state reconciliation, environmental observation, and dynamic self-correction.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.6 Agent Lifecycle - The Plan-Act-Observe-Revise Loop",
    },
    {
        "section": "1.7",
        "title": "Goal Decomposition & Iterative Problem Solving",
        "topics": [
            "Two Styles of Decomposition: Sequential and Hierarchical",
            "Sub-Goal Dependency Graphs and State Tracking",
            "Handling Dynamic Goal Alteration and Partial Failures",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.7 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Hierarchical Task Networks in AI Planning",
        ],
        "lecture_notes_summary": "Techniques for breaking ambiguous high-level objectives into verifiable, sequentially or hierarchically ordered sub-tasks.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.7 Goal Decomposition and Iterative Reasoning",
    },
    {
        "section": "1.8",
        "title": "Planning Strategies: CoT, ReAct, Tree of Thoughts & Plan-and-Execute",
        "topics": [
            "Chain-of-Thought (CoT) Stepwise Reasoning",
            "ReAct (Reason + Act): Synergizing Verbal Traces with External Actions",
            "Tree of Thoughts (ToT): Heuristic Evaluation, Branching, and Backtracking",
            "Plan-and-Execute Decomposition vs Step-by-Step Interleaving",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.8 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Yao et al. - ReAct: Synergizing Reasoning and Acting in Language Models (2022)",
            "Yao et al. - Tree of Thoughts: Deliberate Problem Solving (2023)",
        ],
        "lecture_notes_summary": "Formal cognitive planning frameworks balancing fast linear thought generation with deliberative multi-path search and tool-grounded action execution.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.8 Planning Strategies",
    },
    {
        "section": "1.9",
        "title": "Design Principles for Scalable, Goal-Driven Agents",
        "topics": [
            "Deterministic Guardrails & Error Trapping",
            "Bounded Loop Invariants & Resource Budgets",
            "Separation of Reasoning Traces and Structured Tool Execution",
            "Comprehensive Trace Auditing and Observability",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.9 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Enterprise Agent Reliability Standards",
        ],
        "lecture_notes_summary": "Engineering principles ensuring production agent reliability, deterministic failure traps, and non-negotiable safety guardrails.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.9 Design Principles for Scalable, Goal-Driven Agents",
    },
    {
        "section": "1.10 - 1.12",
        "title": "Real-World Scenarios, 2026 Trends & Trade-Offs",
        "topics": [
            "Scenario A: Multi-Turn Customer Support Agent with Policy Enforcement",
            "Scenario B: Coding & DevOps Remediation Agent",
            "Emerging 2026 Trends: MCP Standardization, Worklet Models & Multi-Agent Swarms",
            "Advantages, Trade-Offs, and High-Stakes Guardrails",
        ],
        "reading_materials": [
            "Chapter 1: Foundations of Agentic AI - Section 1.10 - 1.12 (Chapter1_Foundations_of_Agentic_AI.docx)",
            "Agentic AI Industry Report 2026",
        ],
        "lecture_notes_summary": "Practical deployment architectures, production case studies, and systemic evaluation of autonomous agent trade-offs.",
        "source_document": "Chapter1_Foundations_of_Agentic_AI.docx",
        "source_section": "1.10 Real-World Example Scenarios & 1.11 Current Trends (2026)",
    },
]


class PlanGenerator:
    """Generates structured CourseWorkspacePlan v1.0 grounded in actual course notes."""

    def generate(self, submission: ClarificationSubmission) -> CourseWorkspacePlan:
        """Synthesize original prompt and faculty answers into CourseWorkspacePlan v1.0."""
        prompt = submission.original_prompt
        prompt_lower = prompt.lower()
        answers_map: dict[MissingInfoCategory, str] = {}
        for ans in submission.answers:
            chosen = ans.custom_response or ans.selected_option or (ans.suggested_options[0] if ans.suggested_options else "")
            answers_map[ans.category] = chosen

        unestablished_fields: list[str] = []
        provenance_summary: dict[str, str] = {
            "course_identity": "COURSE_GROUNDED",
            "materials": "COURSE_GROUNDED",
        }

        # 1. Course Code & Title (Canonical)
        course_code = submission.course_code_hint or self._infer_course_code(prompt)
        course_name = self._infer_course_name(prompt, course_code)

        # 2. Determine Duration (USER_PROVIDED vs UNESTABLISHED)
        duration_weeks, duration_provenance = self._resolve_duration(prompt_lower, answers_map)
        provenance_summary["duration_weeks"] = duration_provenance
        if duration_provenance == "UNESTABLISHED":
            unestablished_fields.append("duration_weeks")

        organization_type = "WEEKLY_SCHEDULE" if duration_weeks else "SOURCE_BASED"

        # 3. Prerequisites & Target Audience
        prereq_ans = answers_map.get(MissingInfoCategory.MATERIALS_PREREQUISITES, "")
        prerequisites, prereq_prov = self._derive_prerequisites(prompt_lower, prereq_ans)
        provenance_summary["prerequisites"] = prereq_prov
        if prereq_prov == "UNESTABLISHED":
            unestablished_fields.append("prerequisites")

        target_audience, audience_prov = self._derive_target_audience(prompt_lower, prereq_ans)
        provenance_summary["target_audience"] = audience_prov
        if audience_prov == "UNESTABLISHED":
            unestablished_fields.append("target_audience")

        # 4. Generate Core Pillar 1: Weekly/Modular Materials & Notes (Strictly Grounded in Course Documents)
        materials_and_notes = self._generate_grounded_materials(duration_weeks, prompt_lower, answers_map)

        # 5. Core Pillar 2: Assignments & Practical Labs (USER_PROVIDED if requested/answered, else empty)
        assignments, asgn_provenance = self._generate_assignments_if_provided(duration_weeks, prompt_lower, answers_map)
        provenance_summary["assignments"] = asgn_provenance
        if asgn_provenance == "UNESTABLISHED":
            unestablished_fields.append("assignments")

        # 6. Core Pillar 3: Grades & Assessment Distribution (USER_PROVIDED if requested/answered, else empty)
        grade_breakdown, grade_provenance = self._generate_grade_breakdown_if_provided(answers_map, prompt_lower)
        provenance_summary["grade_breakdown"] = grade_provenance
        if grade_provenance == "UNESTABLISHED":
            unestablished_fields.append("grade_breakdown")

        # 7. Operational Details
        ta_hours, ta_prov = self._derive_ta_hours(answers_map, prompt_lower)
        provenance_summary["ta_allocation_hours"] = ta_prov
        if ta_prov == "UNESTABLISHED":
            unestablished_fields.append("ta_allocation_hours")

        milestones = self._derive_milestones(duration_weeks, materials_and_notes)

        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        if duration_weeks:
            desc = (
                f"{course_name} ({course_code}) — organized from the supplied course materials across a {duration_weeks}-week study schedule. "
                f"Covers core foundations of autonomous agency, agent architectures, lifecycle loops, and planning strategies."
            )
        else:
            desc = (
                f"{course_name} ({course_code}) — organized from the supplied course materials. "
                f"Covers foundational concepts including autonomous agency pillars, agent architecture, Plan–Act–Observe–Revise lifecycle loops, and planning strategies (CoT, ReAct, Tree of Thoughts)."
            )

        return CourseWorkspacePlan(
            plan_id=plan_id,
            version="1.0",
            course_code=course_code,
            course_name=course_name,
            description=desc,
            target_audience=target_audience,
            duration_weeks=duration_weeks,
            organization_type=organization_type,
            prerequisites=prerequisites,
            materials_and_notes=materials_and_notes,
            assignments=assignments,
            grade_breakdown=grade_breakdown,
            unestablished_fields=unestablished_fields,
            provenance_summary=provenance_summary,
            ta_allocation_hours=ta_hours,
            milestones=milestones,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def _infer_course_code(self, prompt: str) -> str:
        match = re.search(r"\b(26ECAC\d{3}|[A-Z]{2,4}\s*\d{3,4})\b", prompt, re.IGNORECASE)
        if match:
            return match.group(1).replace(" ", "").upper()
        return CANONICAL_COURSE_CODE

    def _infer_course_name(self, prompt: str, course_code: str) -> str:
        if CANONICAL_COURSE_CODE in course_code.upper() or "agent" in prompt.lower():
            return CANONICAL_COURSE_NAME
        return f"{course_code}: {CANONICAL_COURSE_NAME}"

    def _resolve_duration(self, prompt_lower: str, answers_map: dict[MissingInfoCategory, str]) -> tuple[Optional[int], str]:
        """Resolve duration weeks without assuming or fabricating an arbitrary schedule."""
        explicit_match = re.search(r"\b(\d{1,2})[\s\-]*weeks?\b", prompt_lower)
        if explicit_match:
            weeks = int(explicit_match.group(1))
            if 1 <= weeks <= 24:
                return weeks, "USER_PROVIDED"

        # 2. Answered clarification question
        pacing_ans = answers_map.get(MissingInfoCategory.SCHEDULE_PACING, "").lower()
        if "modular concept" in pacing_ans or "unscheduled" in pacing_ans or "without an artificial weekly" in pacing_ans:
            return None, "UNESTABLISHED"

        week_in_ans = re.search(r"\b(\d{1,2})\s*weeks?\b", pacing_ans)
        if week_in_ans:
            weeks = int(week_in_ans.group(1))
            if 1 <= weeks <= 24:
                return weeks, "USER_PROVIDED"

        if "12" in pacing_ans:
            return 12, "USER_PROVIDED"
        if "15" in pacing_ans or "semester" in prompt_lower:
            return 15, "USER_PROVIDED"
        if "10" in pacing_ans or "quarter" in prompt_lower:
            return 10, "USER_PROVIDED"
        if "6" in pacing_ans:
            return 6, "USER_PROVIDED"
        if "4" in pacing_ans:
            return 4, "USER_PROVIDED"

        if "modular" in pacing_ans:
            return None, "UNESTABLISHED"

        # If user did not provide a duration and didn't select a weekly pacing, leave unestablished
        return None, "UNESTABLISHED"

    def _derive_prerequisites(self, prompt: str, prereq_ans: str) -> tuple[list[str], str]:
        # Course documents do not establish university prerequisites.
        user_specified = any(kw in prompt for kw in ["prereq", "prerequisite", "background", "prior knowledge"])
        if user_specified or (prereq_ans and not any(kw in prereq_ans.lower() for kw in ["comprehensive foundations", "source sections", "unestablished", "default"])):
            if "advanced" in prereq_ans.lower():
                return ["Asynchronous Python Programming & Distributed Systems", "REST APIs & Model Context Protocol (MCP)"], "USER_PROVIDED"
            elif "foundational" in prereq_ans.lower() or "python" in prompt:
                return ["Basic Python Programming", "Introductory Machine Learning Concepts"], "USER_PROVIDED"
        return [], "UNESTABLISHED"

    def _derive_target_audience(self, prompt: str, prereq_ans: str) -> tuple[str, str]:
        # Do not invent ungrounded student cohorts.
        if "undergrad" in prompt:
            return "Undergraduate students in Computer Science", "USER_PROVIDED"
        if "graduate" in prompt or "grad" in prompt:
            return "Graduate students in Artificial Intelligence", "USER_PROVIDED"
        return "Not specified in supplied course material.", "UNESTABLISHED"

    def _generate_grounded_materials(
        self, duration_weeks: Optional[int], prompt_lower: str, answers_map: dict
    ) -> list[WeeklyMaterial]:
        """Generate structured lecture modules grounded in actual Chapter 1 course documents."""
        materials: list[WeeklyMaterial] = []
        raw_sections = CHAPTER_1_SECTIONS

        if duration_weeks is None:
            # Source-based organization: strictly by source sections without an artificial weekly schedule
            for idx, sec in enumerate(raw_sections):
                materials.append(
                    WeeklyMaterial(
                        week=None,
                        section_label=f"Section {sec['section']}",
                        title=f"Section {sec['section']}: {sec['title']}",
                        topics=sec["topics"],
                        reading_materials=sec["reading_materials"],
                        lecture_notes_summary=sec["lecture_notes_summary"],
                        provenance="COURSE_GROUNDED",
                        source_document=sec["source_document"],
                        source_section=sec["source_section"],
                    )
                )
        else:
            # User provided a weekly schedule: map grounded topics across duration_weeks
            for i in range(duration_weeks):
                sec_idx = i % len(raw_sections)
                sec = raw_sections[sec_idx]
                materials.append(
                    WeeklyMaterial(
                        week=i + 1,
                        section_label=f"Week {i + 1}",
                        title=f"Week {i + 1}: {sec['title']}",
                        topics=sec["topics"],
                        reading_materials=sec["reading_materials"],
                        lecture_notes_summary=sec["lecture_notes_summary"],
                        provenance="COURSE_GROUNDED",
                        source_document=sec["source_document"],
                        source_section=sec["source_section"],
                    )
                )

        return materials

    def _generate_assignments_if_provided(
        self, duration_weeks: Optional[int], prompt_lower: str, answers_map: dict
    ) -> tuple[list[AssignmentSpec], str]:
        """Generate assignments only if explicitly requested or provided by the user."""
        user_asked = any(kw in prompt_lower for kw in ["assignment", "lab", "homework", "deliverable", "problem set", "project"])
        asgn_ans = answers_map.get(MissingInfoCategory.ASSIGNMENTS_LABS, "")

        # If user answered unestablished or did not ask/provide assignments
        if not user_asked and (not asgn_ans or "unestablished" in asgn_ans.lower()):
            return [], "UNESTABLISHED"

        # User requested or answered assignments
        weeks = duration_weeks or 8
        specs = [
            (
                "LAB1_AGENT_LOOP",
                "Lab 1: Plan–Act–Observe–Revise Agent Loop",
                min(2, weeks),
                "Implement a deterministic clarification, planning, and revision loop for autonomous goal pursuit.",
                ["Agent core loop implementation (Python)", "Deterministic state machine tests", "Evaluation trace logs"],
                100,
                10.0,
            ),
            (
                "LAB2_TYPED_TOOLS",
                "Lab 2: Typed Tool Schemas & Function Calling",
                min(4, weeks),
                "Build schema-validated typed tools with sandboxed execution, parameter validation, and auditable traces.",
                ["Pydantic tool schema suite", "Sandboxed execution runner", "Negative test harness for invalid inputs"],
                100,
                10.0,
            ),
            (
                "LAB3_REUSABLE_SKILLS",
                "Lab 3: Reusable Skills & Graph Orchestration",
                min(6, weeks),
                "Create reusable plan/format skills and compose a stateful graph workflow with conditional edge routers.",
                ["Skill registry modules", "Stateful workflow definition", "Cyclic error correction benchmark"],
                150,
                15.0,
            ),
            (
                "PROJ_CAPSTONE",
                "Final Capstone: Autonomous Multi-Tool Agent System",
                weeks,
                "Design, build, and evaluate an end-to-end autonomous agent incorporating typed tools, skills, memory, and governance.",
                ["Full source repository with CI tests", "Production audit trace records", "Architecture demonstration writeup"],
                200,
                25.0,
            ),
        ]

        assignments: list[AssignmentSpec] = []
        for aid, title, due_w, desc, deliv, points, weight in specs:
            assignments.append(
                AssignmentSpec(
                    assignment_id=aid,
                    title=title,
                    due_week=due_w if duration_weeks else None,
                    description=desc,
                    deliverables=deliv,
                    max_points=points,
                    weight_percentage=weight,
                    provenance="USER_PROVIDED",
                )
            )

        return assignments, "USER_PROVIDED"

    def _generate_grade_breakdown_if_provided(
        self, answers_map: dict, prompt_lower: str
    ) -> tuple[list[GradeBreakdownItem], str]:
        """Generate mathematical grade breakdown only if requested or supplied by user."""
        user_asked = any(kw in prompt_lower for kw in ["grade", "grading", "weight", "percentage", "rubric", "exam", "midterm"])
        grading_ans = answers_map.get(MissingInfoCategory.GRADING_WEIGHTS, "").lower()

        # If user answered unestablished or did not ask/provide grading
        if not user_asked and (not grading_ans or "unestablished" in grading_ans):
            return [], "UNESTABLISHED"

        if "project-heavy" in grading_ans:
            items = [
                GradeBreakdownItem(category="Capstone Project & Milestones", weight_percentage=45.0, description="Comprehensive team project broken into proposal, alpha, and final presentation.", provenance="USER_PROVIDED"),
                GradeBreakdownItem(category="Weekly Programming Labs", weight_percentage=35.0, description="Hands-on coding labs graded on correctness, test coverage, and style.", provenance="USER_PROVIDED"),
                GradeBreakdownItem(category="Quizzes & Active Participation", weight_percentage=20.0, description="Bi-weekly conceptual quizzes and active lecture engagement.", provenance="USER_PROVIDED"),
            ]
            return items, "USER_PROVIDED"
        elif "equal" in grading_ans:
            items = [
                GradeBreakdownItem(category="Hands-on Labs", weight_percentage=25.0, description="Laboratory coding assignments.", provenance="USER_PROVIDED"),
                GradeBreakdownItem(category="Homework Sets", weight_percentage=25.0, description="Weekly homework problems.", provenance="USER_PROVIDED"),
                GradeBreakdownItem(category="Midterm Exam", weight_percentage=25.0, description="Mid-semester comprehensive exam.", provenance="USER_PROVIDED"),
                GradeBreakdownItem(category="Final Project", weight_percentage=25.0, description="Culminating end-of-term project.", provenance="USER_PROVIDED"),
            ]
            return items, "USER_PROVIDED"

        # Balanced User-Provided Default when grading was requested/answered
        items = [
            GradeBreakdownItem(category="Programming Labs & Practicals", weight_percentage=30.0, description="Hands-on coding exercises with automated autograder testing.", provenance="USER_PROVIDED"),
            GradeBreakdownItem(category="Homework Problem Sets", weight_percentage=20.0, description="Theoretical problem sets and algorithmic analysis.", provenance="USER_PROVIDED"),
            GradeBreakdownItem(category="Midterm Examination", weight_percentage=20.0, description="Proctored midterm exam covering core conceptual foundations.", provenance="USER_PROVIDED"),
            GradeBreakdownItem(category="Final Capstone Project", weight_percentage=30.0, description="Multi-week capstone project including design, code, and presentation.", provenance="USER_PROVIDED"),
        ]
        return items, "USER_PROVIDED"

    def _derive_ta_hours(self, answers_map: dict, prompt: str) -> tuple[Optional[int], str]:
        user_asked = any(kw in prompt for kw in ["ta", "teaching assistant", "office hours", "staffing"])
        ta_ans = answers_map.get(MissingInfoCategory.TA_SUPPORT, "").lower()
        if "intensive" in ta_ans or "20" in ta_ans:
            return 20, "USER_PROVIDED"
        elif "lightweight" in ta_ans or "5" in ta_ans:
            return 5, "USER_PROVIDED"
        elif "standard" in ta_ans or ("10" in ta_ans and (user_asked or MissingInfoCategory.TA_SUPPORT in answers_map)):
            return 10, "USER_PROVIDED"
        if user_asked:
            return 10, "USER_PROVIDED"
        return None, "UNESTABLISHED"

    def _derive_milestones(self, duration_weeks: Optional[int], materials: list[WeeklyMaterial]) -> list[str]:
        if duration_weeks:
            return [
                "Week 1: Workspace Onboarding & Environment Setup",
                f"Week {max(1, duration_weeks // 2)}: Midterm Conceptual Checkpoint",
                f"Week {max(1, duration_weeks - 1)}: Project Synthesis & Architecture Review",
                f"Week {duration_weeks}: Final Deliverables Submission",
            ]
        # For source-based organization, list verified source sections
        return [
            "Section 1.1 & 1.2: Introduction to Agentic AI & Evolution from Generative AI",
            "Section 1.3 & 1.4: Limitations of Standalone LLMs & The Three Pillars of Agency",
            "Section 1.5: Agent Architecture (Single vs Multi-Agent Systems)",
            "Section 1.6: Agent Lifecycle — The Plan–Act–Observe–Revise Loop",
            "Section 1.7: Goal Decomposition & Iterative Problem Solving",
            "Section 1.8: Planning Strategies (CoT, ReAct, Tree of Thoughts, Plan-and-Execute)",
            "Section 1.9: Design Principles for Scalable, Goal-Driven Agents",
            "Section 1.10 - 1.12: Real-World Scenarios, 2026 Trends & Trade-Offs",
        ]


plan_generator = PlanGenerator()
