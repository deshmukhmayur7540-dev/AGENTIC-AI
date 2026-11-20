# CourseAgentAI Architecture Specification

**Course:** 26ECAC401: Agentic AI  
**Academic Year:** 2026  
**Document Status:** Repository architecture description; not a blanket verification claim  

---

## 1. High-Level Architecture Overview

`CourseAgentAI` is a layered local academic demonstration that separates knowledge extraction, deterministic lab workflows, execution tools, governance, and the interactive UI. “Agent” and “swarm” names do not imply that every workflow is model-driven; most current labs use deterministic Python services.

```
                           +-----------------------------------------------+
                           | Authenticated Responsive Frontend (UI)        |
                           | Course, knowledge, lab, and submission views |
                           +-----------------------+-----------------------+
                                                   | HTTP JSON-RPC / REST
                                                   v
                           +-----------------------------------------------+
                           |          FastAPI REST API Layer               |
                           | /api/auth, labs, knowledge, submissions, etc. |
                           +-----------------------+-----------------------+
                                                   |
           +--------------------+------------------+-------------------+--------------------+
           |                    |                                      |                    |
           v                    v                                      v                    v
  +-----------------+  +-----------------+                    +-----------------+  +-----------------+
  |  Lab 1 Planner  |  |   Lab 2 Agent   |                    |   Lab 3 Skills  |  |  Lab 4 Memory   |
  | Clarify -> Plan |  | ReAct Loop &    |                    | Planning,       |  | Ephemeral vs    |
  | -> Revise       |  | Typed Tools (9) |                    | Research, Format|  | Grounded RAG    |
  +-----------------+  +-----------------+                    +-----------------+  +-----------------+
           |                    |                                      |                    |
           v                    v                                      v                    v
  +-----------------+  +-----------------+                    +-----------------+  +-----------------+
  | Lab 5 Connector |  |  Lab 6 Runtime  |                    |   Lab 7 Graph   |  |   Lab 8 Swarm   |
  | Governed Sources|  | Checkpoints &   |                    | Specialist Nodes|  | Async Fan-Out   |
  | RBAC Governance |  | Approval Gates  |                    | ialist DAG      |  | & Fan-In Merge  |
  +-----------------+  +-----------------+                    +-----------------+  +-----------------+
           |                    |                                      |                    |
           +--------------------+------------------+-------------------+--------------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           |           Canonical Knowledge Layer           |
                           | Notes (Ch 1-4) | SQLite DB | Files | Registrar|
                           +-----------------------------------------------+
```

---

## 2. Laboratory Architectural Patterns

### Lab 1: Clarify &rarr; Plan &rarr; Revise
- **Pipeline:** Raw Faculty Intent &rarr; `IntentParser` &rarr; `GapAnalyzer` (generates targeted clarification questions) &rarr; `PlanGenerator` (synthesizes structured 14-week plan) &rarr; `PlanRevisionEngine` (computes semantic diffs across plan versions).
- **Key Guarantee:** Full provenance tracking, deterministic diffing, and zero loss of previously configured units upon revision.

### Lab 2: Tool-Using Agent & Auditable Trace Auditor
- **Tool Registry:** Global, typed registry holding 9 deterministic Pydantic tools (`get_course_metadata`, `get_course_syllabus`, `search_course_notes`, `get_lab_worklet_requirements`, `get_ta_policy`, `calculate_grade_breakdown_total`, `validate_rubric_sum`, `compute_workload_hours`, `verify_assignment_prerequisites`).
- **Audit Trace:** Enforces the ReAct loop: *Thought &rarr; Action &rarr; Observation*. Zero private chain-of-thought tokens: every internal calculation, query parameter, output, and execution latency is recorded and displayed.

### Lab 3: Reusable Skills Center
- **Skill Abstraction:** Subclasses of `BaseSkill` with strictly typed Pydantic input and output models.
  - `PlanningSkill`: Synthesizes course duration, milestone schedules, and weekly distributions.
  - `ResearchSkill`: Retrieves grounded conceptual notes from Chapters 1–4.
  - `FormattingSkill`: Transforms structured curriculum into student handouts, assignment briefs, and schedule tables.
- **Skill Registry:** Decoupled registry providing declarative JSON schema inspection (`/api/lab3/skills/inspect`) and direct execution.
- **Skill-Using Agent:** Intelligently chains multiple skills based on natural language intent.
- **Sandbox defaults:** The planning sandbox starts with the same `course_code`, `target_weeks`, and `focus_chapters` contract used by the registered planning skill; an empty form is initialized from registry metadata rather than a stale hand-maintained example.

### Lab 2: Catalog-backed Assignment and Rubric Retrieval
- The Lab 2 UI obtains the authenticated user's course assignments from `/api/assignments` and sends the selected assignment ID with the query.
- Assignment and rubric tools first use established canonical fixtures, then query persisted `assignments`/`rubrics` rows constrained by both `course_id` and `assignment_id`.
- Natural-language ordinals such as "Assignment 1" are not silently converted to `hw1`; the caller selects an actual course record, and absent IDs/rubrics remain explicit errors.
- The negative `UNKNOWN999` scenario is labeled as an intentional invalid-course safety check. It is not a successful catalog lookup.

### Lab 4: Ephemeral Session vs Long-Term Knowledge
- **Dual-Tier Memory:**
  - *Short-Term Session Store:* SQLite-backed conversation turns, current request, and working scratchpad, isolated by authenticated user and course. Session state expires after 24 hours and can be cleared or deleted; it is never promoted to long-term knowledge automatically.
  - *Long-Term Course Knowledge:* The existing BM25 index is rebuilt from persistent source documents and authorized course materials. Retrieval supports course/chapter/tag filters and returns source-document and location citations.
  - *Explicit User Memories:* Separately stored user- and course-scoped reference records can be saved, tagged, searched by local TF-IDF or optional local semantic cosine, and deleted. Prior submissions support both modes using metadata only; student SQL candidates are restricted to the authenticated student and course before ranking, while faculty candidates are restricted to their authorized course. Repository source code is not fetched or analyzed, and similarity is not plagiarism detection.
  - *Embedding lifecycle:* `LocalEmbeddingService` lazily loads the pinned `sentence-transformers/all-MiniLM-L6-v2` revision from `COURSEAGENTAI_LAB4_EMBEDDING_MODEL_PATH` on CPU with local-files-only loading and remote code disabled. It never downloads on startup. `scripts/download_lab4_embedding_model.py` is the explicit model setup command; `scripts/index_lab4_embeddings.py` explicitly rebuilds embeddings in batches and requires a database path while refusing the governed database path.
  - *Embedding persistence:* `lab4_memory_embeddings` and `lab4_submission_embeddings` store float32 vectors and model/revision/dimension, source text hash, owner/course scope, and timestamps; each source key is a foreign key with cascading deletion. A changed text hash or model revision triggers re-embedding. Eligible rows are selected by owner/course in SQL before vector loading or ranking. If the local model is unavailable, the API reports an explicit reason and labels its lexical fallback.
  - *Retrieval modes:* Similar-memory and similar-submission APIs use `retrieval_mode="lexical"` by default to preserve prior behavior; `"semantic"` requests the local normalized-vector cosine score. Result limits and the configured `COURSEAGENTAI_LAB4_EMBEDDING_SIMILARITY_THRESHOLD` are enforced. No hybrid score is used. Course-document retrieval remains the existing BM25 system and retains source citations.
  - *Operational evidence:* The tested CPU environment is PyTorch `2.8.0+cpu`, Sentence Transformers `5.2.3`, Transformers `5.23.0`, and Hugging Face Hub `2.4.0`. On the recorded Windows 11 / i5-12450H host, the model folder measured 91,587,680 bytes (28 files), load time was 0.533 s after dependency imports, warmed single-query latency was 11.881 ms median / 13.064 ms p95, and peak process working set was 492,355,584 bytes. These figures are local measurements, not portable guarantees. The model declares Apache-2.0. Inference was verified offline with network socket connections blocked.

### Lab 5: MCP-Style Governed Connector & RBAC
- **Architecture:** Modeled after Model Context Protocol (MCP), providing a single governed entry point across heterogeneous data sources:
  1. `notes_source`: Lecture notes from Chapters 1–4.
  2. `sqlite_source`: SQLite database for course offerings, assignments, and grades.
  3. `file_source`: Worklet build books and lab instructions.
  4. `academic_api_source`: Simulated registrar course catalog.
- **Role-Based Access Control (RBAC):** Requests through `/api/lab5/execute` derive role, agent label, and actor user ID from the authenticated server session; caller-supplied values are overwritten. Student access to submission/audit tables uses the dedicated student APIs. Submission and submission-audit list/read/search operations require a course predicate in SQL. Connector audit entries currently live in process memory and are not a durable immutable audit store; the registrar source is a local mock, and the connector is MCP-style rather than a verified MCP protocol server.

### Lab 6: Controlled Agent Runtime & Checkpointing
- **Engine:** `ControlledRuntimeEngine` manages task runs with step, expected tool-call, elapsed-time, and consequential-action budgets.
- **Persistence:** `lab6_runtime_runs` stores run snapshots/creator/course metadata; `lab6_runtime_checkpoints` stores recovery snapshots; `lab6_runtime_audit_events` stores append-only action records. A fresh process can reload a paused run and resume from its latest persisted checkpoint. These are additive tables created by explicit DB initialization.
- **Authorization:** Every run lifecycle endpoint requires an authenticated Faculty/Admin session and course access. Creator, action actor, approval decision maker, and role are derived from the verified session rather than request-body identity.
- **Human-in-the-Loop Gates:** Pauses execution when a consequential action is reached, requiring explicit faculty `APPROVAL` before proceeding. The current action sequence is a deterministic demonstration, not yet the integrated Course Project workflow.

### Lab 7: Agentic Specialist Node Graph DAG
- **Topology:** The graph declares `coordinator`, `planning`, `notes_repo`, `assignment_dist`, `submission_col`, `grading_org`, `milestones`, `validation`, `faculty_approval`, and `publish`. The validation edge retries grading with a bounded attempt count; approval gates publication.
- **Authorization and state safety:** Run, step, state, and approval routes require authenticated Faculty/Admin sessions and course access. Mutations are serialized under a reentrant lock, and returned state is a deep snapshot to prevent callers from mutating shared internal state.
- **Limitations:** Runs remain process-local and are lost on restart. Several node outputs are deterministic demo data and are not composed with the materials, submission, similarity, grading, and project services. Approval attribution is recorded in the in-memory state, not a durable audit ledger.

### Lab 8: Parallel Swarm & Dynamic Fan-Out
- **Orchestration:** `ParallelSwarmCoordinator` uses `asyncio.gather` to fan out selected Chapter 1–4 knowledge tasks to specialist workers. Requests reject empty, duplicate, or unsupported chapters, and each worker has a bounded timeout.
- **Fan-In validation:** Successful worker output is checked against the selected unit's chapter, title, topics, deliverable and locked-plan hash; at least one source-provenance record is required before merge. Invalid outputs are excluded and reported as failures. Returned/stored result objects are deep-copy snapshots.
- **Current worker roles:**
  - Unit 1: Foundations Specialist.
  - Unit 2: Frameworks & Tools Specialist.
  - Unit 3: Multi-Agent Specialist.
  - Unit 4: Safety & Governance Specialist.
- **Limitations:** The inputs are fixed chapter-unit specs, not plan-derived assignment submissions. Results and status are process-local. `sequential_estimated_ms` sums observed worker durations; it is not a controlled sequential execution/quality comparison, so the official "same or better quality at lower wall-clock time" criterion is unverified.

---

## 3. Student GitHub Assignment Submission & Review Architecture

### 3.1 Domain Model & Persistent Relational Schema
The submission engine is integrated with the `SqliteDataSource` managed under the Lab 5 Governed Connector framework:

```
                    +--------------------+
                    |    assignments     |
                    +--------------------+
                    | id (PK)            |
                    | course_id          |
                    | title              |
                    | max_points         |
                    | due_date           |
                    | late_policy        |
                    | submission_rules   |
                    | status             |
                    +---------+----------+
                              | 1
                              |
                              | N
+--------------------+        |        +-------------------------+
|      students      |        +------->|       submissions       |
+--------------------+ 1               +-------------------------+
| id (PK)            |---------------->| id (PK)                 |
| name               |        N        | assignment_id (FK)      |
| email              |                 | student_id (FK)         |
| course_id          |                 | repository_url          |
| created_at         |                 | normalized_url          |
+--------------------+                 | repo_owner              |
                                       | repo_name               |
                                       | submission_timestamp    |
                                       | attempt_number          |
                                       | status                  |
                                       | is_latest (Boolean)     |
                                       | review_status           |
                                       | review_score            |
                                       | review_feedback         |
                                       | reviewed_by             |
                                       | reviewed_at             |
                                       +-------------------------+
```

### 3.2 Submission Service & Versioning Engine
1. **Student Enrollment & Eligibility Verification:** Validates that `student_id` exists in `students` and that `assignment_id` is currently `OPEN`.
2. **Attempt Tracking:** Counts existing submissions for `(student_id, assignment_id)`. New attempt is assigned `attempt_number = max(existing) + 1`.
3. **Latest Pointer (`is_latest`):** Atomically marks previous submissions for this student-assignment pair as `is_latest = 0` and sets the new record to `is_latest = 1`.
4. **Deadline & Late Calculation:** Compares current UTC timestamp against configured `due_date`. If past due date, status is assigned `LATE` and `validation_details.is_late = True`.
5. **Truthful Grounds:** If no due date or late policy is configured, it remains `None` without fabricating imaginary dates or rules.

### 3.3 Defense-in-Depth GitHub URL Validation & SSRF Defense
The validation engine (`app/services/github_validator.py`) enforces strict boundaries:
- **HTTPS Only:** Strictly checks `parsed.scheme == 'https'`.
- **Hostname Whitelist:** Rejects any host other than `github.com` or `www.github.com`.
- **Deceptive Lookalike Protection:** Rejects typosquatting domains (e.g. `g1thub.com`, `github.com.attacker.com`).
- **SSRF Target Blocking:** Rejects `localhost`, loopback IPs (`127.0.0.1`), link-local metadata targets (`169.254.169.254`), and IPv6 addresses.
- **Embedded Credential Stripping:** Immediately rejects any URL containing `user:pass@` or authentication tokens.
- **Root Repository Enforcement:** Requires exactly `/owner/repo` paths; rejects subpaths (`/tree/`, `/blob/`, `/issues`).
- **Safe Reachability Check:** Asynchronously probes public GitHub repository visibility with a 3.0s timeout, gracefully returning a warning if offline or private without crashing or exposing tokens.

## 4. Labs 9–14: Course Overview Evidence and Current Capabilities

A course overview was found in slide 9 of `knowledge/agentic_ai/chapter_1/Agentic AI - Three Sentence Notes.pptx`. It names the labs and one-line scopes below. The slide is an overview, not a detailed lab specification. No companion manuals for Labs 9–12 are in the workspace; chapter DOCX files for Chapters 2–4 explicitly refer to companion lab manuals that are absent from the file inventory.

- **Lab 9 — Deep Research Agent:** the overview says “AI topic briefing, evidence table.” `EvidenceVerifier` retrieves lexical evidence candidates with citations. It does not orchestrate deep research or synthesize a briefing.
- **Lab 10 — Cloud Operations Agent:** the overview says “Failed deployment: diagnose & fix.” A thread-safe local simulator diagnoses a bounded failure and supports explicitly approved simulated repair and rollback. It retains operation events only in memory; no cloud provider is contacted and transitions are not persisted to the audit log. The bounded grade-weight repair preview changes only a request-local draft, allows at most three attempts, and never mutates course records.
- **Lab 11 — Agentic SDLC Factory:** the overview says “Requirement → tested implementation.” `BenchmarkFactory` runs five fixed service smoke checks; it does not generate and test an implementation from a requirement.
- **Lab 12 — Safety & Governance:** the overview says “Risk, approval, eval, rollback plan.” `GovernedChangeStore` persists proposals, decisions, governed resource values, and audit events in configured SQLite, and supports approval/rejection and rollback. Risk assessment/evaluation planning are not included; governance mutations require an authenticated administrator session.
- **Lab 13 — Discipline-Specific Agents:** `app/labs/lab13/specialists.py` registers theory, lab, and project profiles. Outputs are deterministic scaffolds with observable structural checks and source citations retrieved from the authorized local course index. The profiles do not invent faculty objectives or rubrics and are not autonomous domain experts.
- **Lab 14 — Integrated Course Capstone:** `app/labs/lab14/capstone.py` persists a coordinator run containing live course materials, cited retrieval evidence, assignment/rubric, latest submissions, similarity candidate report, and project milestone summaries. Required checks are a hard gate. A scoped Faculty decision publishes the approved package as a versioned release; rollback deactivates the current release and restores the preceding eligible one. Runs, releases, and audit events use additive SQLite tables. Student release reads remove individual submission/grade records and similarity pairs. The workflow does not inspect repository contents, perform grading, or call external services.

Until the complete course manuals are supplied, no detailed workflow beyond those overview phrases can safely be asserted as an official requirement. The UI and registry describe the currently available tools and their scope.

## 5. Knowledge Files and Retrieval Boundary

The original-file catalog recursively scans configured `KNOWLEDGE_ROOT` for a fixed allow-list of document extensions, skips common development/cache directories, assigns IDs derived from relative paths, confines resolved paths to the root, and serves original bytes through `FileResponse`. Listing/download formats include PDF, DOC/DOCX, PPT/PPTX, TXT, Markdown, and HTML. See [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md) for the current supported discovery/index formats and access controls. Index initialization is in-process and does not persist a separate retrieval index.

The 2026-10-26 recursive inventory found 17 downloadable files in nested chapter directories, including a nested TXT file with spaces in its filename. Original-file downloads are tested against source bytes. A download is still available if text extraction or indexing is unavailable.

## 6. Runtime, Persistence, and Security Boundaries

- `python run.py` is the canonical local launcher and serves the frontend/API at `http://127.0.0.1:8000` by default. `COURSEAGENTAI_HOST`, `COURSEAGENTAI_PORT`, and `COURSEAGENTAI_DEBUG` configure it.
- `DATABASE_PATH` and `KNOWLEDGE_ROOT` override centralized defaults in `config.py`. SQLite initialization/migrations occur during explicit application startup or initialization. Use a disposable DB for tests and experiments; back it up and verify the active path before schema changes. The governed academic DB is never a test target.
- Labs 1–8 use the existing coordinator/agent/route pattern. Labs 9–11 are separate project-derived API services. Lab 6 runtime state, checkpoints and audit records and Lab 12 governance state use configured SQLite; they are separate services, not yet a unified coordinator-owned transaction.
- Assignment records and submission lifecycle states persist in SQLite. Student/faculty identity is derived from the verified session; approval/publication are faculty-only and course-scoped.
- The Submissions hub renders distinct Student, Faculty, and Admin experiences. Admin sees configured assignment records but cannot enter the Faculty grading/release portal; the frontend role display does not grant API permissions.
- Submission lifecycle audit events are persisted alongside review/approval/publication writes. Coordinator and several lab histories remain process-local; the application does not yet have a single complete audit ledger for every mutation.
- Submissions undergo URL syntax/host checks and a bounded optional reachability probe. Syntax or reachability is not proof of repository authorship or correctness. Repository code is never executed.
- `/api/health` establishes only process/configuration liveness; it does not establish health of every workflow.

### 3.4 Role-Based Access Control (RBAC) & Student Isolation
- **Verified identity:** Account identity and role are derived from a verified database-backed session; caller-supplied `X-Student-Id` and `X-User-Role` headers are not identity credentials.
- **Student isolation:** A student can access only their linked student record and own assignment/project data. Draft grades and unpublished feedback are not student-visible.
- **Faculty evaluation rights:** Only authenticated `FACULTY` users with the relevant course scope can review, approve, or publish grades. `ADMIN` and `STUDENT` do not inherit grading permissions.
- **Administrator operations:** Administrative governance and system audit access are separately restricted to authenticated administrators.
- **Session/CSRF boundary:** Passwords are Argon2id hashes; opaque database-backed sessions expire, and logging out revokes the current session. Unsafe methods require an exact trusted Origin; cookie-authenticated mutations also require the CSRF token pair.
- **Knowledge content access:** Catalog, preview, and download reads require an authenticated user with access to the course; file paths remain confined to the configured knowledge root.
- **Unhandled exceptions:** Full details are logged server-side; clients receive a sanitized generic error rather than raw exception text.
- **Audit:** Grading transition events record the authenticated actor. Audit implementation remains distributed across services and is not yet a complete application-wide event ledger.
