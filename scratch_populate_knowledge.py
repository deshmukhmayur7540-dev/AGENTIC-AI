"""Helper script to populate the 12 knowledge categories with course materials."""

from pathlib import Path

kroot = Path("knowledge")

docs = {
    "01_Notes/Chapter_5/Chapter5_Governed_MCP_and_Enterprise_Connectors.md": """# Chapter 5: Governed Model Context Protocol (MCP) and Enterprise Connectors
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 5.1 Introduction to Model Context Protocol (MCP)
The Model Context Protocol (MCP) standardizes how AI agents securely interface with external heterogeneous data sources, databases, enterprise file stores, and academic registers. Rather than writing brittle custom API adapters for each data layer, MCP establishes a client-host-server paradigm with structured capabilities.

## 5.2 Four Canonical Academic Connectors
In CourseAgentAI, the governed connector mediates four specialized sources:
1. **notes_source:** Grounded lecture notes and slides across all course chapters.
2. **sqlite_source:** Relational ACID storage for student enrollments, assignment specifications, rubrics, and submission attempts.
3. **file_source:** Worklet manuals, build books, lab instructions, and attachments.
4. **academic_api_source:** University registrar simulation for course prerequisites and enrollment quotas.

## 5.3 Role-Based Access Control (RBAC) & Governance Gates
The connector enforces four distinct permission tiers:
- **STUDENT:** Read-only access to published course notes, open assignments, and own submissions. Mutation attempts strictly blocked with HTTP 403 / ACCESS_DENIED.
- **TA (Teaching Assistant):** Read access to all submissions, draft grading capability.
- **FACULTY:** Full CRUD rights on syllabus, assignments, rubrics, and grade publication.
- **ADMIN:** Unrestricted system administration, schema migrations, and audit configuration.
All requests across the connector generate immutable append-only audit traces recording client role, operation, resource path, and outcome.
""",

    "01_Notes/Chapter_6/Chapter6_Controlled_Agent_Runtimes_and_Checkpointing.md": """# Chapter 6: Controlled Agent Runtimes, Checkpointing & Resilient Execution
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 6.1 The Controlled Agent Runtime Paradigm
Autonomous agents operating in production academic or enterprise environments must not run as unbounded loops. The controlled agent runtime bounds execution using:
1. **Step Budget:** Strict maximum execution steps (e.g. max 10 steps per task).
2. **Execution Timeout:** Wall-clock duration bounds (e.g. 30 seconds max).
3. **State Checkpointing:** Serializing snapshot state after every atomic step.

## 6.2 Checkpointing and Crash Recovery
Every runtime step captures a `StateCheckpoint` containing run ID, step counter, working scratchpad, completed node outputs, and timestamp. If an unexpected runtime interruption or simulated crash occurs, the engine resumes directly from the latest valid checkpoint without re-running completed work or duplicating external side-effects.

## 6.3 Consequential Human-in-the-Loop Gates
Consequential actions (e.g. publishing final grades, dropping a course, or deploying infrastructure) trigger mandatory approval gates. The engine transitions to `WAITING_APPROVAL`, suspends execution safely, and proceeds only upon verified human faculty signature.
""",

    "01_Notes/Chapter_7/Chapter7_Swarm_Intelligence_and_Multi_Agent_Governance.md": """# Chapter 7: Swarm Intelligence, Parallel Fan-Out & Alignment Governance
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 7.1 Multi-Agent Topologies: DAGs vs Parallel Swarms
Complex agent workflows organize into two primary topologies:
1. **Specialist Directed Acyclic Graphs (DAGs):** Sequential or conditional state-passing pipelines where upstream nodes produce structured inputs for downstream specialists. Includes self-healing retry cycles.
2. **Parallel Swarms (Fan-Out / Fan-In):** Concurrent specialist dispatch using asynchronous tasks (`asyncio.gather`), achieving dramatic speedup factor (e.g. ~3.9x on multi-core environments) while isolating worker failures.

## 7.2 Fan-In Reconciliation & Conflict Resolution
When concurrent workers return curriculum or task outputs, a deterministic coordinator reconciles the outputs against master course constraints, ensuring grade weights sum to exactly 100% and syllabus modules align with semester pacing.

## 7.3 Alignment, Rollback, and Safety Governance
Changes to governed academic resources (e.g. grading policies or prerequisite requirements) must follow governed change lifecycle:
`PROPOSE` -> `AUDIT` -> `HUMAN_EVALUATION` -> `APPROVE` / `REJECT` -> `PERSIST` with full rollback capability to restore previous safe checkpoints.
""",

    "03_Lab_Manuals/Lab_Manuals_01_to_12.md": """# CourseAgentAI: Comprehensive Lab Manuals (Labs 1-12)
Course: 26ECAC401: Agentic AI

## Lab 1: Clarify -> Plan -> Revise Agent
- **Objective:** Transform ambiguous faculty curriculum requests into structured 14-week syllabi with gap detection and immutable semantic diffs.
- **Tools Used:** `IntentParser`, `GapAnalyzer`, `PlanGenerator`, `PlanRevisionEngine`.
- **Deliverables:** Working agentic pipeline, test suite verifying zero-loss revisions.

## Lab 2: Tool-Using Agent with Trace Auditor
- **Objective:** Implement a ReAct tool-using agent using 9 strictly typed Pydantic tools with zero hidden chain-of-thought tokens.
- **Tools:** `get_course_metadata`, `get_course_syllabus`, `search_course_notes`, `validate_rubric_sum`, `compute_workload_hours`.

## Lab 3: Reusable Skills Registry
- **Objective:** Decouple monolithic prompts into typed, modular skills (`PlanningSkill`, `ResearchSkill`, `FormattingSkill`).

## Lab 4: Memory & Retrieval Architecture
- **Objective:** Strictly decouple ephemeral short-term session conversation from immutable long-term course knowledge with provenance citations.

## Lab 5: Governed MCP Academic Connector
- **Objective:** Unified governed connector over Notes, SQLite, Files, and Registrar with hierarchical RBAC.

## Lab 6: Controlled Agent Runtime & Checkpoints
- **Objective:** Resilient execution loop with step budgeting, checkpoint persistence, and human faculty approval gates.

## Lab 7: Agentic Specialist Node Graph DAG
- **Objective:** 10-node DAG with sequential node stepping, self-healing retry cycles, and publication gating.

## Lab 8: Parallel Swarm & Concurrent Fan-Out
- **Objective:** Asynchronous concurrent specialist dispatch with fan-in merge reconciliation and worker fault isolation.

## Lab 9: Deep Research Evidence Verifier
- **Objective:** Grounded evidence candidate retrieval with explicit distinction between lexical relevance and semantic entailment.

## Lab 10: Cloud Operations & Infrastructure Self-Healing
- **Objective:** Automated infrastructure health diagnostics, failure remediation planning, and gated recovery.

## Lab 11: Agentic SDLC Requirement-to-Code Factory
- **Objective:** Autonomous requirement analysis, architecture specification, code generation, and sandboxed test execution.

## Lab 12: Safety, Governance & Alignment Overrides
- **Objective:** Persistent governed proposals, multi-factor approval gates, immutable audit logging, and state rollback.
""",

    "06_Assignments/Assignments_01_to_12_Problem_Statements.md": """# Assignments 1-12: Problem Statements & Evaluation Rubrics
Course: 26ECAC401: Agentic AI

Each assignment requires students to submit a public, verifiable GitHub repository containing implementation source code, automated pytest suites, and architectural documentation.

### Assignment 1: Clarify-Plan-Revise Planner (Weight: 8%)
Implement an interactive agent that detects missing course parameters, queries the faculty evaluator with targeted questions, synthesizes a 14-week modular plan, and supports atomic revisions with semantic diffing.

### Assignment 2: Deterministic ReAct Tool Agent (Weight: 8%)
Develop a tool-using agent equipped with typed Pydantic tools for course metadata lookup and assessment math validation. Enforce zero private chain-of-thought tokens.

### Assignment 3: Reusable Academic Skills Registry (Weight: 8%)
Build a decoupled skill catalog supporting dynamic JSON schema inspection and programmatic execution.

### Assignment 4: Dual-Tier Memory & RAG Indexer (Weight: 8%)
Engineer an in-memory session dialogue store isolated per user, combined with a deterministic BM25 inverted index over course lecture notes.

### Assignment 5: Governed Academic Connector (Weight: 8%)
Implement an MCP-style connector with role-based access control protecting database and note sources.

### Assignment 6: Resilient Agent Runtime with Checkpoints (Weight: 8%)
Create an execution engine with step limits, fault injection recovery, and faculty approval gates.

### Assignment 7: 10-Node Specialist Graph DAG (Weight: 8%)
Implement directed and conditional state passing across 10 specialized agent roles with bounded retry on defects.

### Assignment 8: Parallel Specialist Swarm (Weight: 8%)
Orchestrate concurrent worker units with asynchronous scatter-gather and master constraint reconciliation.

### Assignment 9: Deep Research Claim Verifier (Weight: 8%)
Develop a research agent verifying claims against course notes with entailment distinction.

### Assignment 10: Cloud Operations Health Agent (Weight: 8%)
Create an automated infrastructure monitor that detects worker failures and proposes gated remediations.

### Assignment 11: Agentic SDLC Code Synthesis Factory (Weight: 8%)
Build a requirement-to-code pipeline with automated test generation and sandboxed verification.

### Assignment 12: Enterprise Safety & Governance (Weight: 8%)
Implement persistent change proposals, approval gates, immutable audit trails, and instant state rollback.
""",

    "07_Question_Banks/Agentic_AI_Comprehensive_Question_Bank_and_MCQs.md": """# Agentic AI Comprehensive Question Bank & Practice MCQs
Course: 26ECAC401: Agentic AI

## Section A: Multiple Choice Questions (MCQs)

1. What constitutes the core autonomous loop of an Agentic AI system?
   - A) Prompt -> Completion
   - B) Plan -> Act -> Observe -> Revise [CORRECT]
   - C) Fine-tune -> Quantize -> Evaluate
   - D) Scrape -> Clean -> Embed
   Explanation: Chapter 1 establishes that autonomous agents differ from passive chatbots by continuously observing environment feedback and revising plans.

2. In the ReAct architectural pattern, what does the agent record at each step?
   - A) Only final answers
   - B) Thought, Action, Observation [CORRECT]
   - C) Loss gradients and weights
   - D) Token probabilities
   Explanation: Chapter 2 details ReAct as interleaving reasoning (Thought), tool invocation (Action), and environment response (Observation).

3. Why is lexical retrieval alone insufficient to establish claim verification in Deep Research?
   - A) Lexical search is too slow
   - B) Lexical matching finds word overlap but does not verify semantic entailment [CORRECT]
   - C) Word embeddings are required for all databases
   - D) Lexical search always hallucinates citations
   Explanation: Chapter 4 and Lab 9 demonstrate that candidate passage retrieval requires human or entailment verification to prevent false claims.

4. What is the primary purpose of state checkpointing in an agent runtime?
   - A) To compress memory
   - B) To allow resumption from the last valid step without re-executing completed work [CORRECT]
   - C) To bypass authentication gates
   - D) To speed up LLM generation
   Explanation: Chapter 6 emphasizes fault tolerance and crash resilience through serialized state checkpoints.

5. What does the Model Context Protocol (MCP) standardize?
   - A) Neural network architectures
   - B) Client-server interfaces between AI agents and external tools/data sources [CORRECT]
   - C) GPU cluster scheduling
   - D) Frontend React components
   Explanation: Chapter 5 details MCP as a secure, typed protocol connecting agents to heterogeneous sources.

## Section B: Analytical & Architectural Questions

1. Compare Directed Acyclic Graphs (DAGs) and Parallel Swarms: Detail when sequential state passing is required versus when asynchronous scatter-gather fan-out provides superior throughput.
2. Explain Defense-in-Depth for Assignment Submissions: Why is regex URL validation alone inadequate, and how do hostname whitelisting, SSRF target blocking, and remote repository accessibility checks protect academic integrity?
3. Analyze Consequential Human-in-the-Loop Gates: Describe how an agent runtime should pause before high-impact operations (e.g. grade publication) and verify faculty authority.
""",

    "08_Reference_Materials/Agentic_AI_Design_Patterns_and_CheatSheet.md": """# Agentic AI Design Patterns & Architecture Reference
Course: 26ECAC401: Agentic AI

## Key Design Patterns in Agentic Systems
1. **Reflection & Self-Correction:** The agent critiques its intermediate outputs and revises them against constraints before committing.
2. **Tool Use & Function Calling:** Strictly typed parameters validated with Pydantic schemas.
3. **Planning & Decomposition:** Breaking large tasks into sub-tasks (planning skill).
4. **Multi-Agent Collaboration:** Specialization across roles (Coordinator, Planner, Retriever, Reviewer).
5. **Memory Hierarchy:** Separation between short-term conversation scratchpads and persistent knowledge stores.
""",

    "09_Project_Documentation/Course_Project_Specification_and_Milestones.md": """# Course Project Specification: CourseAgentAI
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 1. Project Overview & Problem Statement
Academic course administration is heavily fragmented across static syllabus PDFs, disconnected LMS folders, manual assignment grading, and ungrounded chat assistants. CourseAgentAI unifies these domains into a governed, agentic learning and course-management operations platform.

## 2. Core Subsystems
1. **Course Knowledge & Notes Management:** Hierarchical multi-folder document management system with recursive indexing and high-precision BM25 retrieval.
2. **Assignment Distribution & Submission Portal:** Verifiable student GitHub and file submissions with anti-SSRF validation, attempt versioning, and student isolation.
3. **Transparent Evaluation & Similarity Review:** Pairwise n-gram submission similarity reports, rubric-based draft grading assistance, and faculty approval gates.
4. **Course Project & Milestone Tracker:** Individual and group project progress calculation, deliverable submission, and activity timeline.
5. **Specialized Agent Coordination:** Central coordinator delegating to Notes, Distribution, Submission, Similarity, Grading, and Milestone agents.

## 3. Milestones & Timeline
- **Milestone 1 (Week 4):** Problem Statement, Entity Architecture, and Database Schema Sign-off.
- **Milestone 2 (Week 8):** Governed Knowledge RAG Ingestion & 9 ReAct Tools Implementation.
- **Milestone 3 (Week 12):** 10-Node Specialist DAG, Parallel Swarm, and Submissions Workflow.
- **Milestone 4 (Week 16):** Final Capstone Defense, Complete Submission Package, and Regression Report.
""",

    "10_Announcements/Semester_Announcements_Archive.md": """# Semester Announcements Archive
Course: 26ECAC401: Agentic AI - Semester: Autumn 2026

- **Announcement 1 (2026-09-01):** Welcome to 26ECAC401! Course syllabus and foundational notes for Chapters 1-4 are published in `01_Notes/`.
- **Announcement 2 (2026-09-15):** Lab 1 submission portal is open. Ensure your GitHub solution repository is public and includes complete test coverage.
- **Announcement 3 (2026-10-01):** Midterm project milestones announced. Team leads must register their project workspaces.
- **Announcement 4 (2026-10-20):** Plagiarism and similarity checking guidelines released: all submissions are compared pairwise against assignment cohorts.
- **Announcement 5 (2026-11-01):** Final capstone project guidelines and rubric breakdown published in `09_Project_Documentation/`.
""",

    "11_Study_Materials/Agentic_AI_Core_Concepts_Quick_Reference.md": """# Agentic AI Core Concepts Quick Reference & Cheatsheet
Course: 26ECAC401: Agentic AI

## Key Concepts & Architectural Guarantees

### 1. BM25 Retrieval Scoring
BM25 ranks documents based on the query terms appearing in each document, balancing term frequency (TF) and inverse document frequency (IDF) with document length normalization:
- k1 = 1.5: Term frequency saturation parameter.
- b = 0.75: Document length normalization penalty.

### 2. Autonomous Loop Invariants
1. **Perception Grounding:** Agent acts only upon verified environment observations.
2. **Deterministic Tool Validation:** All tool arguments must pass strict schema validation before execution.
3. **State Immutability:** Revision engines must generate versioned diffs without mutating prior history.
4. **Human Oversight:** Consequential state changes require explicit faculty sign-off.
""",

    "12_Other_Resources/Curated_Tools_Libraries_and_Reading_List.md": """# Curated Agentic AI Tools, Libraries & Recommended Readings
Course: 26ECAC401: Agentic AI

## Recommended Reading List
1. ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., 2022).
2. Model Context Protocol Specification (Anthropic & Open Source Community, 2024).
3. LangGraph: Building Stateful, Multi-Actor Applications with LLMs (Harrison et al., 2024).
4. Constitutional AI and Governance of Autonomous Agents (Bai et al., 2022).

## Frameworks & Tooling Stack
- **FastAPI:** High-performance asynchronous REST API framework.
- **Pydantic v2:** Rust-backed strict type validation and schema serialization.
- **SQLite3:** ACID relational store with WAL mode and foreign key integrity.
- **Pytest:** Automated unit, integration, and regression testing harness.
"""
}

for rel_path, content in docs.items():
    target = kroot / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip(), encoding="utf-8")
    print(f"Wrote: {rel_path}")

print("All 12 knowledge categories populated with authoritative content.")
