"""Structured intent extractor for Lab 1 course workspace plan revisions."""

import re
from typing import Any, Optional
from pydantic import BaseModel, Field


class BaseChangeIntent(BaseModel):
    """Base class for all parsed revision intents."""
    intent_type: str


class DurationChangeIntent(BaseChangeIntent):
    """Intent to modify course length in weeks."""
    intent_type: str = "duration_change"
    target_weeks: Optional[int] = None
    delta_weeks: Optional[int] = None


class AssignmentAdditionIntent(BaseChangeIntent):
    """Intent to add a new programming lab, homework, or project assignment."""
    intent_type: str = "assignment_addition"
    assignment_type: str = "lab"  # "lab", "homework", "project"
    title: Optional[str] = None
    topic_hint: Optional[str] = None
    due_week: Optional[int] = None


class AssignmentScheduleIntent(BaseChangeIntent):
    """Intent to reschedule or move an existing assignment to another week."""
    intent_type: str = "assignment_schedule"
    assignment_hint: str
    target_week: int


class GradeWeightChangeIntent(BaseChangeIntent):
    """Intent to modify grading weights (absolute percentage or relative percentage points)."""
    intent_type: str = "grade_weight_change"
    category_hint: str
    target_weight: Optional[float] = None
    delta_percentage_points: Optional[float] = None
    rebalance_others: bool = True


class MaterialChangeIntent(BaseChangeIntent):
    """Intent to add or modify weekly lecture notes, topics, or reading materials."""
    intent_type: str = "material_change"
    target_week: Optional[int] = None
    topic_title: str
    topics: list[str] = Field(default_factory=list)
    reading_materials: list[str] = Field(default_factory=list)
    notes_summary: Optional[str] = None


class DeliverableAdditionIntent(BaseChangeIntent):
    """Intent to add a specific deliverable (e.g. peer review, video demo) to assignments."""
    intent_type: str = "deliverable_addition"
    target_assignment_hint: str = "all"
    deliverable_text: str


class StaffingChangeIntent(BaseChangeIntent):
    """Intent to modify TA staffing allocation hours."""
    intent_type: str = "staffing_change"
    ta_hours: int


class IntentParser:
    """Extracts structured, actionable change intents from natural language revision prompts."""

    WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "twenty": 20, "24": 24,
    }

    def parse(self, prompt: str) -> list[BaseChangeIntent]:
        """Parse natural language revision prompt into an ordered list of structured change intents."""
        if not prompt or not prompt.strip():
            return []

        prompt_lower = prompt.lower().strip()
        intents: list[BaseChangeIntent] = []

        # 1. Parse Duration Changes
        duration_intent = self._parse_duration(prompt_lower)
        if duration_intent:
            intents.append(duration_intent)

        # 2. Parse Assignment Additions
        assignment_intents = self._parse_assignment_additions(prompt_lower)
        intents.extend(assignment_intents)

        # 3. Parse Assignment Scheduling
        schedule_intents = self._parse_assignment_scheduling(prompt_lower)
        intents.extend(schedule_intents)

        # 4. Parse Grade Weight Changes
        grade_intents = self._parse_grade_changes(prompt_lower)
        intents.extend(grade_intents)

        # 5. Parse Material / Module Additions
        material_intents = self._parse_material_changes(prompt_lower)
        intents.extend(material_intents)

        # 6. Parse Deliverable Additions
        deliverable_intents = self._parse_deliverables(prompt_lower)
        intents.extend(deliverable_intents)

        # 7. Parse Staffing Changes
        staffing_intent = self._parse_staffing(prompt_lower)
        if staffing_intent:
            intents.append(staffing_intent)

        return intents

    def _parse_duration(self, text: str) -> Optional[DurationChangeIntent]:
        """Detect duration modifications (absolute target or relative delta)."""
        # Absolute patterns: "change course to 12 weeks", "make it 12 weeks", "12 weeks long", "14-week"
        target_match = re.search(r"(?:change|set|make|switch|expand|extend|shorten)?\s*(?:the\s+)?(?:course\s+)?(?:duration\s+)?(?:to|is|=)?\s*(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen)\s*(?:-| )?weeks?", text)
        
        # Check for relative extensions: "extend the course by two weeks", "add 2 weeks", "lengthen by 3 weeks"
        delta_extend = re.search(r"(?:extend|expand|lengthen|increase|add)\s*(?:the\s+course\s+)?(?:by\s+)?(\d{1,2}|one|two|three|four|five|six)\s*weeks?", text)
        delta_shorten = re.search(r"(?:shorten|reduce|decrease)\s*(?:the\s+course\s+)?(?:by\s+)?(\d{1,2}|one|two|three|four|five|six)\s*weeks?", text)

        if delta_extend and not re.search(r"to\s+\d{1,2}\s*weeks", text):
            raw_val = delta_extend.group(1)
            num = self._convert_number(raw_val)
            if num:
                return DurationChangeIntent(delta_weeks=num)

        if delta_shorten and not re.search(r"to\s+\d{1,2}\s*weeks", text):
            raw_val = delta_shorten.group(1)
            num = self._convert_number(raw_val)
            if num:
                return DurationChangeIntent(delta_weeks=-num)

        if target_match:
            raw_val = target_match.group(1)
            num = self._convert_number(raw_val)
            if num and 1 <= num <= 24:
                return DurationChangeIntent(target_weeks=num)

        return None

    def _parse_assignment_additions(self, text: str) -> list[AssignmentAdditionIntent]:
        """Detect requests to add new programming labs, homeworks, or project assignments."""
        intents: list[AssignmentAdditionIntent] = []

        # "add one additional programming lab", "add 1 more coding lab", "add an additional lab"
        lab_match = re.search(r"add\s+(?:one|1|an?|an\s+additional|one\s+additional|another)\s+(?:programming\s+|coding\s+|hands-on\s+)?lab", text)
        if lab_match:
            # Check topic hint: e.g. "lab on neural networks" or "fault injection lab"
            topic_hint = None
            topic_match = re.search(r"lab\s+(?:on|covering|for)\s+([a-zA-Z0-9\s\-]+?)(?:\.|$|,|and\s+increase|and\s+add)", text)
            if topic_match:
                topic_hint = topic_match.group(1).strip()
            intents.append(AssignmentAdditionIntent(assignment_type="lab", topic_hint=topic_hint))

        # "add a homework assignment", "add one problem set"
        hw_match = re.search(r"add\s+(?:one|1|an?|an\s+additional|another)\s+(?:homework|problem\s+set|theory\s+assignment)", text)
        if hw_match:
            intents.append(AssignmentAdditionIntent(assignment_type="homework"))

        return intents

    def _parse_assignment_scheduling(self, text: str) -> list[AssignmentScheduleIntent]:
        """Detect requests to reschedule or move assignments to specific weeks."""
        intents: list[AssignmentScheduleIntent] = []
        # "move the pytorch lab to week 3", "reschedule lab 2 to week 4"
        move_matches = re.finditer(r"(?:move|reschedule|shift)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)\s+(?:lab|assignment|project)?\s+to\s+week\s+(\d{1,2})", text)
        for m in move_matches:
            hint = m.group(1).strip()
            week_num = int(m.group(2))
            intents.append(AssignmentScheduleIntent(assignment_hint=hint, target_week=week_num))
        return intents

    def _parse_grade_changes(self, text: str) -> list[GradeWeightChangeIntent]:
        """Detect absolute or relative percentage weight modifications."""
        intents: list[GradeWeightChangeIntent] = []

        # Relative delta: e.g., "increase the final project weight by 5 percentage points", "raise capstone weighting by 5%"
        delta_pattern = r"(?:increase|raise|boost|elevate|add|reduce|decrease|lower)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)\s+(?:weight(?:ing)?|grade)?\s*(?:by)?\s*(\d{1,2}(?:\.\d+)?)\s*(?:percentage\s+points?|%|points?)"
        for m in re.finditer(delta_pattern, text):
            category = m.group(1).strip()
            val = float(m.group(2))
            action_word = m.group(0).split()[0].lower()
            if action_word in ["reduce", "decrease", "lower"]:
                val = -val
            intents.append(GradeWeightChangeIntent(
                category_hint=category,
                delta_percentage_points=val,
                rebalance_others=True,
            ))

        # Absolute target: e.g. "set final project weight to 40%", "make midterm 25%", "project to 35%"
        abs_pattern = r"(?:set|make|change|adjust)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]+?)\s+(?:weight(?:ing)?|grade)?\s*(?:to|is|=)\s*(\d{1,2}(?:\.\d+)?)\s*%"
        for m in re.finditer(abs_pattern, text):
            category = m.group(1).strip()
            val = float(m.group(2))
            # Avoid duplicate if already parsed as delta
            if not any(i.category_hint == category for i in intents):
                intents.append(GradeWeightChangeIntent(
                    category_hint=category,
                    target_weight=val,
                    rebalance_others=True,
                ))

        # Fallback short absolute: e.g. "project weight to 35%" or "midterm to 25%"
        short_abs_pattern = r"\b(project|capstone|midterm|exam|lab|homework|hw|quiz)\s+(?:weight\s+)?(?:to|is|=)\s*(\d{1,2}(?:\.\d+)?)\s*%"
        for m in re.finditer(short_abs_pattern, text):
            category = m.group(1).strip()
            val = float(m.group(2))
            if not any(category in i.category_hint for i in intents):
                intents.append(GradeWeightChangeIntent(
                    category_hint=category,
                    target_weight=val,
                    rebalance_others=True,
                ))

        return intents

    def _parse_material_changes(self, text: str) -> list[MaterialChangeIntent]:
        """Detect requests to add or update weekly topics or modules."""
        intents: list[MaterialChangeIntent] = []

        # "Add an AI ethics and algorithmic bias module to Week 5"
        if any(kw in text for kw in ["ethics", "bias", "fairness", "responsible ai", "ethical"]):
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: AI Ethics, Algorithmic Bias & Societal Governance" if target_w else "AI Ethics, Algorithmic Bias & Societal Governance"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["Algorithmic Bias, Fairness Metrics & Disparate Impact", "Ethical Governance Frameworks & Safety Audits", "Data Privacy & Societal Impact"],
                reading_materials=["ACM Code of Ethics & Professional Conduct", "Barocas et al. - Fairness and Machine Learning"],
                notes_summary="Detailed examination of algorithmic accountability, bias auditing, and responsible deployment practices.",
            ))

        # "Add a module on neural networks", "Add neural networks topic"
        if "neural network" in text or "deep learning" in text:
            if not any("neural" in i.topic_title.lower() for i in intents):
                week_m = re.search(r"week\s+(\d{1,2})", text)
                target_w = int(week_m.group(1)) if week_m else None
                title = f"Week {target_w}: Deep Neural Networks & Backpropagation" if target_w else "Deep Neural Networks & Backpropagation"
                intents.append(MaterialChangeIntent(
                    target_week=target_w,
                    topic_title=title,
                    topics=["Multi-Layer Perceptrons & Activation Functions", "Backpropagation through Computational Graphs", "Loss Landscape Optimization"],
                    reading_materials=["Goodfellow - Deep Learning Ch 6", "Karpathy Neural Networks Zero to Hero"],
                    notes_summary="Architectures of multi-layer neural networks, backpropagation derivations, and gradient descent mechanics.",
                ))

        # "Add chaos engineering and fault injection", "fault injection lab in week 8"
        if "chaos" in text or "fault injection" in text:
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: Fault Injection & Chaos Engineering in Distributed Systems" if target_w else "Fault Injection & Chaos Engineering in Distributed Systems"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["Chaos Engineering Principles", "Jepsen Partition Testing", "Crash-Recovery Fault Injection Models"],
                reading_materials=["Basiri et al. - Chaos Engineering (IEEE)", "Jepsen Distributed Systems Verification Reports"],
                notes_summary="Designing fault injection experiments and validating consensus invariant safety under dynamic network partitions.",
            ))

        # "Add ReAct or Tree of Thoughts module"
        if any(kw in text for kw in ["react", "tree of thoughts", "tot", "chain of thought"]):
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: Advanced Agent Reasoning (ReAct & Tree of Thoughts)" if target_w else "Advanced Agent Reasoning (ReAct & Tree of Thoughts)"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["ReAct: Interleaving Reasoning and Action Traces", "Tree of Thoughts Heuristic Branching & Backtracking", "Plan-and-Execute Decomposition"],
                reading_materials=["Yao et al. - ReAct (2022)", "Yao et al. - Tree of Thoughts (2023)"],
                notes_summary="Deliberative multi-path reasoning paradigms and action-observation feedback loops for autonomous agents.",
            ))

        # "Add LangGraph or multi-agent graph workflows"
        if "langgraph" in text or "graph" in text:
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: LangGraph Stateful Graphs & Cyclic Orchestration" if target_w else "LangGraph Stateful Graphs & Cyclic Orchestration"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["State Channels & Shared Reducers", "Conditional Edge Routing", "Multi-Agent Cyclic Workflows"],
                reading_materials=["LangGraph Architecture Whitepaper", "Stateful Multi-Agent Workflows Guide"],
                notes_summary="Building stateful, cyclic multi-agent graphs with conditional transitions and shared state channels.",
            ))

        # "Add Model Context Protocol (MCP) module"
        if "mcp" in text or "model context protocol" in text:
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: Model Context Protocol (MCP) & Governed Tool Integration" if target_w else "Model Context Protocol (MCP) & Governed Tool Integration"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["MCP Client-Server Architecture", "Governed Tool & Resource Exposure", "Security Boundaries & Sandboxed Execution"],
                reading_materials=["Model Context Protocol (MCP) Open Specification", "Anthropic MCP Developer Guide"],
                notes_summary="Standardizing agent data connections and tool exposures using the Model Context Protocol.",
            ))

        # "Add Transformer / HuggingFace"
        if "transformer" in text or "huggingface" in text:
            week_m = re.search(r"week\s+(\d{1,2})", text)
            target_w = int(week_m.group(1)) if week_m else None
            title = f"Week {target_w}: Transformer Architectures & HuggingFace Ecosystem" if target_w else "Transformer Architectures & HuggingFace Ecosystem"
            intents.append(MaterialChangeIntent(
                target_week=target_w,
                topic_title=title,
                topics=["Self-Attention & Multi-Head Attention Mechanics", "HuggingFace Transformers Pipelines", "LoRA Fine-Tuning Workflows"],
                reading_materials=["Vaswani et al. - Attention Is All You Need", "HuggingFace Official Documentation"],
                notes_summary="Comprehensive deconstruction of self-attention mechanisms and practical fine-tuning using HuggingFace.",
            ))

        # Generic section/module addition fallback
        if not intents:
            generic_sec_match = re.search(
                r"(?:add|include)\s+(?:one\s+|a\s+|an\s+)?(?:more\s+|additional\s+)?(?:section|module|topic|lecture)\s+(?:covering|on|about)\s+([a-zA-Z0-9\s\-]+?)(?:\.|$|,|and\s+keep)",
                text,
            )
            if generic_sec_match:
                captured_topic = generic_sec_match.group(1).strip()
                week_m = re.search(r"week\s+(\d{1,2})", text)
                target_w = int(week_m.group(1)) if week_m else None
                title = f"Week {target_w}: {captured_topic.title()}" if target_w else captured_topic.title()
                intents.append(MaterialChangeIntent(
                    target_week=target_w,
                    topic_title=title,
                    topics=[f"{captured_topic.title()} Core Principles", f"Practical Implementation of {captured_topic.title()}"],
                    reading_materials=[f"{captured_topic.title()} Reference Guide"],
                    notes_summary=f"In-depth exploration and practical analysis of {captured_topic}.",
                ))

        return intents

    def _parse_deliverables(self, text: str) -> list[DeliverableAdditionIntent]:
        """Detect requests to add deliverable artifacts."""
        intents: list[DeliverableAdditionIntent] = []
        if "peer review" in text or "code review" in text:
            intents.append(DeliverableAdditionIntent(
                target_assignment_hint="project",
                deliverable_text="Peer Code Review Feedback Report (Rubric-based)",
            ))
        return intents

    def _parse_staffing(self, text: str) -> Optional[StaffingChangeIntent]:
        """Detect TA hours adjustments."""
        ta_match = re.search(
            r"(?:increase|raise|boost|reduce|adjust|set|make|change)?\s*(?:the\s+)?(?:ta|office|teaching\s+assistant)\s*(?:hours|staffing|support|allocation)?\s*(?:to|is|=|by)?\s*(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|twenty)\s*(?:hours?)?",
            text,
        )
        if ta_match:
            hours = self._convert_number(ta_match.group(1))
            if hours is not None and 1 <= hours <= 40:
                return StaffingChangeIntent(ta_hours=hours)
        return None

    def _convert_number(self, val: str) -> Optional[int]:
        """Helper to convert string or digit into integer."""
        val = val.strip().lower()
        if val.isdigit():
            return int(val)
        return self.WORD_TO_NUM.get(val)


intent_parser = IntentParser()
