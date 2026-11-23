# CourseAgentAI: Comprehensive Lab Manuals (Labs 1-12)
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