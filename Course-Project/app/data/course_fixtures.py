"""Canonical course knowledge fixtures for CourseAgentAI (26ECAC401: Agentic AI).

Grounded strictly in the authoritative Agentic AI course notes:
- Chapter 1: Foundations of Agentic AI
- Chapter 2: Agent Frameworks, Tools, Skills & Memory
"""

from typing import Any, Optional

# =========================================================================
# Canonical Course Syllabus Fixtures
# Note: Grading percentages, assignment deadlines, and exact weeks are NOT
# fabricated; unsupported values are represented as unavailable/unestablished.
# =========================================================================
CANONICAL_SYLLABI: dict[str, dict[str, Any]] = {
    "26ECAC401": {
        "course_id": "26ECAC401",
        "course_name": "Agentic AI",
        "description": (
            "Comprehensive university curriculum covering the Foundations of Agentic AI, "
            "Autonomous Agent Characteristics, Agent Frameworks, Typed Tools & Function Calling, "
            "Reusable Skills, Memory & Retrieval Architectures, and Autonomous Multi-Agent Systems."
        ),
        "duration_weeks": None,
        "target_audience": "Not specified in supplied course material.",
        "prerequisites": [],
        "modules": [
            {
                "chapter": 1,
                "week": None,
                "title": "Chapter 1: Foundations of Agentic AI",
                "topics": [
                    "Evolution from Generative AI to Agentic AI",
                    "Autonomous Agent Characteristics (Perception, Reasoning, Learning, Action)",
                    "Agent Architecture & Core Loops (Plan–Act–Observe–Revise)",
                    "Goal Decomposition & Reasoning Paradigms (CoT, ReAct, Tree of Thoughts, Plan-and-Execute)",
                    "Scalable & Reliable Agent Design",
                ],
                "readings": [
                    "Chapter 1: Foundations of Agentic AI Course Notes",
                    "ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al.)",
                    "Tree of Thoughts: Deliberate Problem Solving with Large Language Models (Yao et al.)",
                ],
            },
            {
                "chapter": 2,
                "week": None,
                "title": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
                "topics": [
                    "Agent Frameworks & Orchestration (LangChain, LangGraph)",
                    "Tools and Function Calling (Typed Tool Schemas, API Orchestration, Sandboxing)",
                    "Reusable Skills in Agent Architectures",
                    "Memory Architectures (Short-Term Session State vs Long-Term Retrieval / RAG)",
                    "Model Context Protocol (MCP) & Unified Runtime Patterns",
                ],
                "readings": [
                    "Chapter 2: Agent Frameworks, Tools, Skills & Memory Course Notes",
                    "LangGraph: Multi-Agent Stateful Orchestration Architecture",
                    "Model Context Protocol (MCP) Open Specification",
                ],
            },
            {
                "chapter": 3,
                "week": None,
                "title": "Chapter 3: Multi-Agent Orchestration",
                "topics": [
                    "Multi-Agent System Architectures & Collaboration Topologies",
                    "Coordination Strategies (Hierarchical, Peer-to-Peer, Blackboard)",
                    "Communication Protocols and Shared Memory Channels",
                    "Consensus Mechanisms, Conflict Resolution & Negotiation",
                    "Production Multi-Agent Patterns (Feature Factories, Swarms)",
                ],
                "readings": [
                    "Chapter 3: Multi-Agent Orchestration Course Notes",
                    "Autonomous Multi-Agent Systems & Communication Protocols",
                ],
            },
            {
                "chapter": 4,
                "week": None,
                "title": "Chapter 4: Learning, Deployment, Safety & Governance",
                "topics": [
                    "Agentic Learning Paradigms & Reinforcement Learning (RLHF/RLAIF)",
                    "Deployment Patterns, Sandboxed Runtime Environments & Monitoring",
                    "Deterministic Safety Guardrails, Rate Limiting & Resource Quotas",
                    "Governance, Alignment & Algorithmic Accountability",
                    "Autonomous Incident Remediation & Production Safety Case Studies",
                ],
                "readings": [
                    "Chapter 4: Learning, Deployment, Safety & Governance Course Notes",
                    "Safe and Governed Deployment Architectures for Autonomous AI",
                ],
            },
        ],
        "grading_weights": [],
        "grading_policy_status": "Unavailable in supplied course notes (not established)",
    }
}


# =========================================================================
# Canonical Course Notes & Chapter Evidence Repository
# Grounded strictly in Chapter 1 and Chapter 2 course notes.
# =========================================================================
CANONICAL_NOTES: dict[str, list[dict[str, Any]]] = {
    "26ECAC401": [
        # Chapter 1: Foundations of Agentic AI
        {
            "chapter": 1,
            "section": "1.1",
            "topic": "Evolution from Generative AI to Agentic AI",
            "content": (
                "Agentic AI represents a fundamental paradigm shift from passive generative AI models to autonomous systems. "
                "While generative AI produces content strictly in response to immediate prompts without persistent agency, "
                "agentic systems proactively pursue high-level goals, maintain execution state across multi-turn interactions, "
                "interact with external environments through tools, and iteratively adapt actions based on environmental feedback."
            ),
            "source": "Chapter 1: Foundations of Agentic AI - Section 1.1",
            "source_document": "Chapter 1: Foundations of Agentic AI",
            "source_chapter": 1,
            "tags": ["foundations", "evolution", "generative-ai", "agentic-ai", "autonomy"],
            "version": "1.0",
        },
        {
            "chapter": 1,
            "section": "1.2",
            "topic": "Autonomous Agent Characteristics (Perception, Reasoning, Learning, Action)",
            "content": (
                "An autonomous agent is characterized by four interconnected capabilities: "
                "1) Perception: Receiving and processing inputs from users, APIs, and environmental observations; "
                "2) Reasoning: Interpreting context, evaluating hypotheses, making trade-offs, and formulating plans; "
                "3) Learning: Incorporating feedback, reflection, and task outcomes to improve future trajectories; "
                "4) Action: Executing concrete operations in digital or physical environments via tool calls, APIs, and code execution."
            ),
            "source": "Chapter 1: Foundations of Agentic AI - Section 1.2",
            "source_document": "Chapter 1: Foundations of Agentic AI",
            "source_chapter": 1,
            "tags": ["characteristics", "perception", "reasoning", "learning", "action", "autonomy"],
            "version": "1.0",
        },
        {
            "chapter": 1,
            "section": "1.3",
            "topic": "Agent Architecture & Core Loops (Plan–Act–Observe–Revise)",
            "content": (
                "The core operational cycle of an autonomous agent is the Plan–Act–Observe–Revise loop: "
                "The agent clarifies objectives, constructs an action plan, acts by invoking tools or external endpoints, "
                "observes the verified execution results and environment states, and revises its plan if discrepancies "
                "or new information arise. This cyclical feedback loop prevents open-loop drift and grounds decisions in verified reality."
            ),
            "source": "Chapter 1: Foundations of Agentic AI - Section 1.3",
            "source_document": "Chapter 1: Foundations of Agentic AI",
            "source_chapter": 1,
            "tags": ["architecture", "loop", "plan-act-observe-revise", "clarify", "plan", "revise"],
            "version": "1.0",
        },
        {
            "chapter": 1,
            "section": "1.4",
            "topic": "Goal Decomposition & Reasoning Paradigms (CoT, ReAct, Tree of Thoughts, Plan-and-Execute)",
            "content": (
                "Agents employ formal reasoning paradigms for goal decomposition: "
                "Chain-of-Thought (CoT) enables sequential intermediate step formulation; "
                "ReAct (Reason + Act) interleaves verbal reasoning traces with targeted tool actions and observations; "
                "Tree of Thoughts (ToT) explores multiple reasoning branches with heuristic evaluation and backtracking; "
                "Plan-and-Execute separates global task breakdown from individual sub-task tool execution."
            ),
            "source": "Chapter 1: Foundations of Agentic AI - Section 1.4",
            "source_document": "Chapter 1: Foundations of Agentic AI",
            "source_chapter": 1,
            "tags": ["reasoning", "cot", "react", "tree-of-thoughts", "plan-and-execute", "goal-decomposition"],
            "version": "1.0",
        },
        {
            "chapter": 1,
            "section": "1.5",
            "topic": "Scalable & Reliable Agent Design",
            "content": (
                "Reliable agent design requires deterministic constraints, bounded execution loops to prevent infinite cycles, "
                "transparent audit logging, strict input/output schema validation, and defensive error containment. "
                "Agents must separate private deliberation traces from verified public facts and return explicit error states "
                "rather than hallucinating missing domain knowledge."
            ),
            "source": "Chapter 1: Foundations of Agentic AI - Section 1.5",
            "source_document": "Chapter 1: Foundations of Agentic AI",
            "source_chapter": 1,
            "tags": ["reliability", "scalability", "safety", "bounded-loops", "error-containment", "audit"],
            "version": "1.0",
        },

        # Chapter 2: Agent Frameworks, Tools, Skills & Memory
        {
            "chapter": 2,
            "section": "2.1",
            "topic": "Agent Frameworks and Tool Integration (LangChain, LangGraph)",
            "content": (
                "Modern agent systems utilize frameworks like LangChain for primitive abstractions and LangGraph for "
                "stateful, cyclic multi-agent graph workflows. Graph-based orchestration models nodes as reasoning agents "
                "or tools, edges as conditional routing transitions, and shared state channels for coordinated data flow."
            ),
            "source": "Chapter 2: Agent Frameworks, Tools, Skills & Memory - Section 2.1",
            "source_document": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
            "source_chapter": 2,
            "tags": ["frameworks", "langchain", "langgraph", "graphs", "orchestration"],
            "version": "1.0",
        },
        {
            "chapter": 2,
            "section": "2.2",
            "topic": "Tools and Function Calling (Typed Tool Schemas, API Orchestration, Sandboxing)",
            "content": (
                "Tools extend an LLM's capabilities beyond static weights. Function calling relies on strictly typed "
                "Pydantic schemas describing tool inputs, outputs, and constraints. Tool execution must occur in sandboxed "
                "environments with parameter validation, execution timing, error trapping, and defensive schema verification."
            ),
            "source": "Chapter 2: Agent Frameworks, Tools, Skills & Memory - Section 2.2",
            "source_document": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
            "source_chapter": 2,
            "tags": ["tools", "function-calling", "schemas", "sandboxing", "api-orchestration"],
            "version": "1.0",
        },
        {
            "chapter": 2,
            "section": "2.3",
            "topic": "Reusable Skills in Agent Architectures",
            "content": (
                "Reusable skills represent modular, specialized capabilities packaged with instructions, prompt formats, "
                "and execution logic. Skills are dynamically discovered, loaded on demand, and shared across agents to "
                "promote code reusability and modular agent architecture without bloating the agent's core runtime."
            ),
            "source": "Chapter 2: Agent Frameworks, Tools, Skills & Memory - Section 2.3",
            "source_document": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
            "source_chapter": 2,
            "tags": ["skills", "modular-skills", "reusability", "capabilities"],
            "version": "1.0",
        },
        {
            "chapter": 2,
            "section": "2.4",
            "topic": "Memory Architectures: Short-Term Session State vs Long-Term Retrieval / RAG",
            "content": (
                "A robust agent architecture cleanly separates ephemeral short-term session state from stored long-term knowledge. "
                "Short-term memory maintains active dialogue turns, intermediate reasoning steps, and runtime variables within the context window. "
                "Long-term memory uses vector databases and Retrieval-Augmented Generation (RAG) to persist and recall historical facts, "
                "policies, and domain documentation across distinct sessions."
            ),
            "source": "Chapter 2: Agent Frameworks, Tools, Skills & Memory - Section 2.4",
            "source_document": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
            "source_chapter": 2,
            "tags": ["memory", "short-term-memory", "long-term-memory", "rag", "retrieval", "session-state"],
            "version": "1.0",
        },
        {
            "chapter": 2,
            "section": "2.5",
            "topic": "Model Context Protocol (MCP) & Unified Runtime Patterns",
            "content": (
                "The Model Context Protocol (MCP) provides an open, standardized protocol for connecting AI agents to external "
                "data sources, tools, and developmental environments. MCP establishes governed, typed client-server communication, "
                "enabling consistent tool exposure, security boundaries, and plug-and-play capability discovery across agent runtimes."
            ),
            "source": "Chapter 2: Agent Frameworks, Tools, Skills & Memory - Section 2.5",
            "source_document": "Chapter 2: Agent Frameworks, Tools, Skills & Memory",
            "source_chapter": 2,
            "tags": ["mcp", "model-context-protocol", "runtime", "protocols", "governance"],
            "version": "1.0",
        },
    ]
}


# =========================================================================
# Assignments & Rubrics (Unestablished in lecture notes)
# No assignments or rubrics are fabricated; queries for them return None.
# =========================================================================
CANONICAL_ASSIGNMENTS: dict[str, dict[str, dict[str, Any]]] = {
    "26ECAC401": {}
}

CANONICAL_RUBRICS: dict[str, dict[str, dict[str, Any]]] = {
    "26ECAC401": {}
}


# =========================================================================
# Course Configuration & Parameters
# =========================================================================
CANONICAL_CONFIGS: dict[str, dict[str, Any]] = {
    "26ECAC401": {
        "course_id": "26ECAC401",
        "course_name": "Agentic AI",
        "duration_weeks": None,
        "enrollment_limit": None,
        "ta_ratio_policy": "Unavailable in supplied course notes (not established)",
        "students_per_ta": None,
        "prerequisites": [],
        "grading_policy": "Unavailable in supplied course notes (not established)",
        "lab_environment": "Python 3.10+, LLM APIs (Gemini/OpenAI), Agent Sandboxes, LangGraph",
        "hours_per_ta_per_week": None,
        "source": "Agentic AI Course Specification 26ECAC401",
    }
}


from app.core.course_identity import normalize_course_id

# =========================================================================
# Repository Lookup Functions
# =========================================================================
def get_canonical_syllabus_data(course_id: str) -> Optional[dict[str, Any]]:
    """Retrieve structured canonical course syllabus fixture by course_id (case-insensitive)."""
    norm_id = normalize_course_id(course_id)
    if not norm_id:
        return None
    return CANONICAL_SYLLABI.get(norm_id)


def search_canonical_notes_data(course_id: str, query: str) -> Optional[dict[str, Any]]:
    """Search course notes directly from the document knowledge index.
    
    Reads from the indexed Chapter 1-4 actual course documents rather than hardcoded copies.
    Returns None if course_id is not 26ECAC401 to prevent hallucination for unknown courses.
    """
    norm_id = normalize_course_id(course_id)
    if norm_id != "26ECAC401":
        return None

    from app.knowledge.service import knowledge_service

    search_result = knowledge_service.search(query=query, course_id=norm_id, top_k=6)
    matches = []
    for m in search_result.matches:
        matches.append({
            "chapter": m.chapter,
            "week": None,
            "topic": m.topic,
            "matched_text": m.matched_text,
            "source": m.source,
            "source_document": m.source_document,
            "source_chapter": m.source_chapter,
            "tags": m.tags,
            "version": m.version,
        })

    return {
        "course_id": norm_id,
        "query": query,
        "matches": matches,
        "match_count": len(matches),
        "source": search_result.source,
    }


def get_canonical_assignment_data(course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
    """Retrieve structured assignment specification by course_id and assignment_id.
    
    Returns None if assignments are not established in supplied course notes.
    """
    norm_course = normalize_course_id(course_id)
    if not norm_course:
        return None
    norm_assignment = assignment_id.strip().lower()
    course_assignments = CANONICAL_ASSIGNMENTS.get(norm_course)
    if course_assignments is None:
        return None
    return course_assignments.get(norm_assignment)


def get_canonical_rubric_data(course_id: str, assignment_id: str) -> Optional[dict[str, Any]]:
    """Retrieve structured rubric breakdown by course_id and assignment_id.
    
    Returns None if rubrics are not established in supplied course notes.
    """
    norm_course = normalize_course_id(course_id)
    if not norm_course:
        return None
    norm_assignment = assignment_id.strip().lower()
    course_rubrics = CANONICAL_RUBRICS.get(norm_course)
    if course_rubrics is None:
        return None
    return course_rubrics.get(norm_assignment)


def get_canonical_config_data(course_id: str) -> Optional[dict[str, Any]]:
    """Retrieve course configuration parameters by course_id."""
    norm_id = normalize_course_id(course_id)
    if not norm_id:
        return None
    return CANONICAL_CONFIGS.get(norm_id)


def get_canonical_ta_policy_data(course_id: str, enrollment: int) -> Optional[dict[str, Any]]:
    """Calculate deterministic TA policy requirements for a course based on enrollment.
    
    Returns None if TA staffing policy is not established in the supplied notes.
    """
    norm_id = normalize_course_id(course_id)
    if not norm_id:
        return None
    config = CANONICAL_CONFIGS.get(norm_id)
    if config is None:
        return None

    students_per_ta = config.get("students_per_ta")
    hours_per_ta = config.get("hours_per_ta_per_week")
    if students_per_ta is None or hours_per_ta is None:
        return None

    import math
    required_ta_count = max(1, math.ceil(enrollment / students_per_ta))
    required_hours = required_ta_count * hours_per_ta

    return {
        "course_id": norm_id,
        "enrollment": enrollment,
        "required_ta_count": required_ta_count,
        "required_hours_per_week": float(required_hours),
        "policy_ratio": f"1 TA per {students_per_ta} students (1:{students_per_ta})",
        "formula_applied": f"max(1, ceil({enrollment} / {students_per_ta})) = {required_ta_count} TAs @ {hours_per_ta} hrs/wk each",
        "source": f"Department Policy Guide ({norm_id})",
    }
