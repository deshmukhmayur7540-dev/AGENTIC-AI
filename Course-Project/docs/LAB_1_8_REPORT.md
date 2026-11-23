# CourseAgentAI: Labs 1–8 Comprehensive Engineering Report

> **Historical report — superseded:** This document contains earlier implementation claims, test counts, and security observations. Do not treat its “202/202 Tests Passing” count, claims of full course coverage, or spoofable-header description as current. Authentication, authorization, and CSRF behavior changed later. See [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md) and [TEST_RESULTS.md](TEST_RESULTS.md) for current evidence and limitations.

**Course Code:** `26ECAC401`  
**Course Name:** `Agentic AI`  
**Target:** Labs 1 through 8 Full Engineering Pass  
**Verification Status:** 202/202 Tests Passing (100%)  

---

## 1. Engineering Scope & Real Academic Grounding

The `CourseAgentAI` platform was developed to fulfill the complete laboratory curriculum for university course `26ECAC401: Agentic AI`.
Every laboratory implementation is grounded directly in the course lecture notes (`knowledge/agentic_ai/`) across Chapters 1 to 4:
- **Chapter 1:** Plan-Act-Observe-Revise loops, cognitive agent architectures, reasoning strategies.
- **Chapter 2:** Function calling, tool registry patterns, ReAct loops, deterministic arithmetic validation.
- **Chapter 3:** Multi-agent orchestration, supervisor patterns, parallel swarms, LangGraph / LangChain abstractions.
- **Chapter 4:** AI governance, Model Context Protocol (MCP), role-based access control, runtime budgets, checkpointing, and human-in-the-loop gates.

---

## 2. Lab-by-Lab Implementation Analysis

### Lab 1: Academic Course Workspace Planner (Clarify &rarr; Plan &rarr; Revise)
- **Problem Solved:** Transforming vague faculty course prompts into structured, verified syllabi without hallucinations.
- **Components:** `IntentParser`, `GapAnalyzer`, `PlanGenerator`, `PlanRevisionEngine`.
- **Validation:** Normalized course code extraction (`26ECAC401`), 14-week duration handling, unit balance (4 Units matching Chapters 1-4), grading policy arithmetic totaling 100%, and semantic diffing without `week: None` bugs.

### Lab 2: Tool-Using Agent & Auditable Trace Auditor
- **Problem Solved:** Grounding agent reasoning in deterministic tools with auditable, zero-private-token traces.
- **Components:** 9 Pydantic tools (`get_course_metadata`, `get_course_syllabus`, `search_course_notes`, `get_lab_worklet_requirements`, `get_ta_policy`, `calculate_grade_breakdown_total`, `validate_rubric_sum`, `compute_workload_hours`, `verify_assignment_prerequisites`).
- **Validation:** Bounded ReAct loop with explicit Thoughts, Actions, Observations; verified facts board tracking tool-confirmed domain facts only. Rejects `CS101` and unsupported policies with structured execution errors.

### Lab 3: Reusable Skills Center
- **Problem Solved:** Encapsulating reusable, stateless capabilities across different courses and contexts.
- **Components:** `PlanningSkill`, `ResearchSkill`, `FormattingSkill`, `SkillRegistry`, `SkillUsingAgent`.
- **Validation:** Schema inspection via Pydantic JSON schemas, direct execution sandbox, and natural language multi-skill routing. Case-agnostic parameters and strict input/output contract enforcement.

### Lab 4: Ephemeral Session vs Long-Term Knowledge
- **Problem Solved:** Cognitive separation between ephemeral conversational state and immutable course knowledge.
- **Components:** `SessionStore` (in-memory multi-turn history & KV scratchpad) and `LongTermKnowledgeStore` (grounded inverted index over Chapters 1-4).
- **Validation:** Session isolation, provenance citations, chapter-specific filtering, and strict anti-hallucination rejection on ungrounded queries (e.g., medieval quantum alchemy).

### Lab 5: MCP-Style Governed Academic Connector
- **Problem Solved:** Secure, governed access to heterogeneous academic data stores with role enforcement.
- **Components:** `NotesSource`, `SqliteSource`, `FileSource`, `AcademicApiSource`, `GovernedConnector`, `ConnectorAuditLog`.
- **Validation:** Role-based access control (`STUDENT`, `TA`, `FACULTY`, `ADMIN`). Verified that student mutation attempts are blocked with `ACCESS_DENIED` while faculty updates succeed. Immutable audit logging of all requests.

### Lab 6: Controlled Agent Runtime & Checkpoints
- **Problem Solved:** Preventing run-away agent loops and providing fault-tolerant recovery from unexpected failures.
- **Components:** `ControlledRuntimeEngine`, `RuntimeBudget`, `StateCheckpoint`, approval gate mechanisms.
- **Validation:** Enforces maximum budget steps and timeouts. Serializes checkpoints after every step. Injects and recovers from mid-run crashes via `resume_run`. Halts at critical approval gates for faculty signoff.

### Lab 7: Agentic Specialist Node Graph DAG
- **Problem Solved:** Deterministic multi-agent coordination without chaotic emergent behavior.
- **Components:** 10 specialist nodes (`INTENT_EXTRACTION` &rarr; `GAP_ANALYSIS` &rarr; `KNOWLEDGE_RETRIEVAL` &rarr; `SYLLABUS_SYNTHESIS` &rarr; `ASSIGNMENT_GENERATION` &rarr; `RUBRIC_SYNTHESIS` &rarr; `WORKLOAD_AUDITING` &rarr; `SELF_HEALING_VALIDATION` &rarr; `FACULTY_APPROVAL_GATE` &rarr; `WORKSPACE_PUBLICATION`).
- **Validation:** Validated DAG state flow, self-healing validation with bounded retries (up to 3 attempts), interactive Gate 9 approval suspension, and workspace publication.

### Lab 8: Parallel Swarm & Dynamic Fan-Out
- **Problem Solved:** Accelerating multi-unit curriculum synthesis through concurrent asynchronous agent workers.
- **Components:** `ParallelSwarmOrchestrator`, 4 concurrent unit specialists (`WorkerUnit1` to `WorkerUnit4`), dynamic fan-in reconciler.
- **Validation:** Concurrent `asyncio.gather` fan-out achieving ~3.9x speedup over sequential execution. Fault containment ensuring worker failures do not crash the swarm, with harmonious merging against the locked master specification.

---

## 3. Adversarial & Boundary Hardening

A dedicated adversarial test suite (`tests/test_adversarial.py`) validates:
1. Standalone query `"AI"` is never parsed as a course ID.
2. Random gibberish produces `None` for course ID.
3. Foreign course `"CS101"` is safely preserved and rejected with structured zero-match errors.
4. Grading calculator strictly detects weights summing to 110% or 120% as invalid.
5. Anti-hallucination queries outside the notes return 0 matches.
6. Non-existent chapter filters are blocked by Pydantic schema validation.
7. Calls to non-existent tools and skills return structured error envelopes.
8. Student role direct writes are blocked with `ACCESS_DENIED`.
9. Infinite loops are halted by the runtime budget.
10. Unapproved publishing in the node graph is blocked.

---

## 4. UI Quality & Accessibility

- Segmented navigation control across all 8 labs.
- Interactive live execution, direct sandboxes, schema inspectors, and visual DAG and worker dashboards.
- Zero dead buttons, full error boundary handling, and ARIA roles for screen readers.
- Keyboard accessibility with Escape handlers and accessible modal dialogs.
