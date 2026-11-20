# CourseAgentAI — Forensic Audit & Implementation Plan

> **Historical implementation record — superseded:** This document contains earlier audit observations and implementation notes. Do not rely on its old authentication, database, test-count, or completion statements as current. The current evidence-based status is in [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md); current commands/results are in [TEST_RESULTS.md](TEST_RESULTS.md). Detailed companion specifications for Labs 9–12 and final submission requirements remain unavailable.

**Course:** 26ECAC401: Agentic AI  
**Academic System:** CourseAgentAI Workspace Planner & Tool Auditor  
**Audit & Implementation Date:** October 2026  
**Auditor / Implementer:** Antigravity Senior Engineering Team  

---

## 1. Forensic Audit & Defect Discovery

Prior to modifications, a comprehensive inspection of all codebase layers, SQLite schemas, and test suites was conducted. The following defects and integration gaps were identified and resolved:

### 1.1 Lab 6 Route Disconnect & Rejection Bypass
- **Defect:** The frontend dashboard in `app/static/app.js` invoked `/api/lab6/start`, `/api/lab6/step`, `/api/lab6/crash`, `/api/lab6/resume`, and `/api/lab6/decision`. However, the backend router in `app/api/routes_lab6.py` only exposed `/api/lab6/run/{run_id}/...`. This caused 404 Not Found errors on runtime actions.
- **Defect:** In `app/labs/lab6/engine.py`, when a human evaluator rejected a consequential approval gate, the engine failed to transition to a terminal `REJECTED` state; subsequent step calls generated duplicate approval gates rather than halting execution.
- **Resolution:** Added route aliases with normalized request/response envelopes (`APIEnvelope`), bound the approval decision to the active gate ID, and enforced immediate halt with `REJECTED` status upon gate rejection.

### 1.2 Lab 8 Course Normalization Defect
- **Defect:** In `app/labs/lab8/swarm.py`, unknown course IDs (such as `UNKNOWN_COURSE_999`) were silently coerced to `26ECAC401` or failed with Pydantic validation errors due to missing fields in the failure return object.
- **Resolution:** Updated `app/labs/lab8/swarm.py` to return a fully conformant `SwarmResult` with `status: FAILED` and zero fabricated verified facts when encountering unknown courses.

### 1.3 Unclosed DOM Element & Missing Handlers
- **Defect:** In `app/static/index.html`, `<main id="main-content">` was unclosed before modal overlays. Additionally, tab buttons `tab-btn-history` and `tab-btn-actiontrace` lacked dynamic content triggers when toggled.
- **Resolution:** Closed all HTML semantic containers properly and attached reactive tab switch listeners.

### 1.4 Hardcoded Database Path
- **Defect:** In `app/labs/lab5/sources/sqlite_source.py`, the SQLite file path was hardcoded in multiple places rather than centrally referenced from configuration.
- **Resolution:** Centralized `database_path` and `github_token` in `config.py` (`Settings`).

---

## 2. Mandatory Feature: Student GitHub Assignment Submissions

### 2.1 Domain & Security Architecture
A genuine, persistent student GitHub assignment submission and faculty review workflow was designed and implemented:

1. **Database Schema & Non-Destructive Migrations:**
   - Augmented the existing `assignments` table with `description`, `due_date`, `submission_rules`, `late_policy`, and `status` without destroying existing lab records.
   - Created `students` table holding enrolled identities (`std-001`, `std-002`, `std-003`).
   - Created `submissions` table tracking `id`, `assignment_id`, `student_id`, `repository_url`, `normalized_url`, `repo_owner`, `repo_name`, `attempt_number`, `status`, `validation_status`, `validation_details`, `is_latest`, `review_status`, `review_score`, `review_feedback`, `reviewed_by`, and `reviewed_at`.
   - Added foreign keys and composite indexes on `(student_id, assignment_id)` and `(assignment_id, is_latest)`.

2. **Defense-in-Depth GitHub URL Validation (`app/services/github_validator.py`):**
   - Strictly enforces `https://` scheme.
   - Enforces exact hostname matching: `github.com` or `www.github.com`.
   - Rejects deceptive lookalikes: `g1thub.com`, `github.com.attacker.com`, `gitlab.com`, `bitbucket.org`.
   - Rejects SSRF / private targets: `localhost`, `127.0.0.1`, `169.254.169.254`, IPv6 loopbacks.
   - Rejects embedded credentials: `user:pass@github.com`.
   - Requires repository root paths and rejects subpaths (`/tree/main`, `/blob/master`, `/issues`).
   - Normalizes URLs by stripping trailing slashes and `.git` extensions.
   - Performs non-blocking, safe remote repository reachability verification via public GitHub API with 3.0s timeout and zero credential leakage.

3. **Domain Service & Versioning (`app/services/submission_service.py`):**
   - Checks student enrollment and assignment openness.
   - Calculates deadline status: sets status to `LATE` if submitted after assignment `due_date`.
   - Handles resubmissions: increments `attempt_number` and atomically toggles previous submissions' `is_latest` to `False`.
   - Enforces Role-Based Access Control (RBAC): students can only inspect their own submissions; faculty can list all submissions and submit grades/evaluations.

4. **REST API Layer (`app/api/routes_submissions.py`):**
   - `GET /api/assignments`: Lists course assignments with metadata, deadlines, and policies.
   - `GET /api/assignments/{id}`: Detailed assignment specification.
   - `GET /api/students`: Enrolled student profiles.
   - `POST /api/submissions`: Submit solution repository URL.
   - `GET /api/submissions/student/{id}`: Student submission history (enforces student isolation).
   - `GET /api/submissions/detail/{id}`: Detailed single submission record.
   - `GET /api/submissions/faculty`: Faculty evaluation portal list.
   - `POST /api/submissions/{id}/review`: Faculty review, grade, and feedback recording.

5. **Apple-Grade Frontend UI:**
   - **Student Portal:** Student selector, assignment picker with dynamic brief card (rules, deadline, late policy), live regex validation feedback, one-click submission with duplicate-click protection, persistent confirmation receipt card, and attempt history table.
   - **Faculty Portal:** Filterable submissions table (by assignment and status), evaluation action modal dialog, score input (0-100), and qualitative feedback persistence.

---

## 3. Implementation Verification Matrix

### 3.1 Historical repository snapshot (superseded)

> The matrix and test counts below are retained as an October 2026 historical record. They predate trusted authentication, the later security fixes, and subsequent feature work; they are not current status claims. Use [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md) and [TEST_RESULTS.md](TEST_RESULTS.md) for the current assessment and verification.

| Requirement | Implementation / status | Automated evidence | Manual / remaining |
|---|---|---|---|
| Existing Labs 1–8 | Existing UI/API/service implementations preserved; scope checked against supplied project context, chapter notes, source, and tests | Existing per-lab tests; full suite rerun | Browser smoke covered Labs 1–8, with primary workflows for Labs 1–5, 7 and 8; Lab 6 approval/rejection tested. Detailed companion manuals are absent; exact compliance beyond the provided course overview cannot be established |
| Lab 1: clarify / plan / revise | Existing gap analysis, typed plan generation, revision and trace UI/API | Existing Lab 1 + grounding tests; full suite | Browser clarification was demonstrated; full plan/revision flow remains to be manually demonstrated |
| Lab 2: typed tools / verified facts | Existing tool registry, validation, execution trace and provenance | Existing Lab 2 API/tool/agent tests | Browser query returned SUCCESS |
| Lab 3: reusable skills | Existing skill registry, schemas, sandbox and agent routing | Existing Lab 3 tests | Browser skill query returned SUCCESS |
| Lab 4: session and retrieval | Existing transient session store and grounded retrieval; default demo session now created on first open | Existing Lab 4 tests + browser smoke | Browser append-turn flow verified; session state is intentionally ephemeral |
| Lab 5: governed connector | Existing connector/source boundary and role checks | Existing Lab 5 tests | Browser configured request returned visible output; role selector is only demo authorization |
| Lab 6: runtime/gates/recovery | Existing bounded step engine, checkpoints, gate, crash/resume logic; frontend integer/state schema mismatch repaired | Existing runtime/API tests + regression UI assertion | Browser advanced to gate, approved to completion, and separately rejected; post-rejection step remained REJECTED |
| Lab 7: graph workflow | Existing graph nodes, retry path and approval gate | Existing Lab 7 API/graph tests | Browser full workflow paused at approval and completed publication after approval |
| Lab 8: parallel swarm | Existing concurrent workers, merge and failure containment | Existing Lab 8 tests | Browser four-worker run returned MERGED |
| Official lab source | Chapter 1 PPTX slide 9 names one-line scopes; no companion detailed lab manual files found. Chapter 2–4 notes reference missing companion manuals | Whole workspace + DOCX/PPTX content search | Request the official manuals/specs from course staff; overview slide does not specify detailed acceptance criteria |
| Lab 9 Deep Research Agent | Lexical evidence candidate API with citations; no research orchestration or briefing synthesis | `tests/test_labs9_12.py` | Current browser candidate lookup was tested; the detailed manual is not available |
| Lab 10 Cloud Operations Agent | Grade-weight validation utility; no failed-deployment diagnosis/repair workflow | No Lab 10 workflow test | Obtain the detailed specification and a safe disposable deployment fixture |
| Lab 11 Agentic SDLC Factory | Five-case application smoke suite; no requirement-to-tested-code factory | `tests/test_labs9_12.py` | Current browser smoke utility was tested; the detailed manual is not available |
| Lab 12 Safety & Governance | SQLite-persisted approval/rejection/rollback with audit events; no risk assessment/evaluation plan; demo headers are not authenticated | `tests/test_labs9_12.py` | Persistence across store instances is tested; the detailed lab specification is not available |
| Recursive knowledge listing | 17 actual allowed-format files in nested chapter paths at audit | `tests/test_knowledge_downloads.py`, API inventory | Current browser listed all 17 files |
| Original note downloads | Stable server ID, root confinement, safe filename, original FileResponse | Exhaustive exact-byte and SHA-256 test covers all 17 listed notes | Browser click triggered HTTP 200; browser-fetch byte lengths for all 17 matched listed sizes; automation download-event not emitted |
| Knowledge indexing/retrieval | Current extractor/index covers DOCX and PPTX; TXT/MD/PDF/HTML and legacy DOC/PPT are listed/downloadable but not indexed | Existing knowledge layer tests | Unsupported formats remain download-only |
| GitHub submission workflow | SQLite persistence, attempt tracking, validation, review endpoints and UI remain | Existing submissions + E2E tests | Real auth is absent: do not use with real student data |
| Startup and health | Existing `python run.py` canonical launcher; `/api/health` liveness only | API/UI tests and direct browser requests | Port 8000 was already occupied; edited workspace was separately browser-tested on 8001 |
| Git preservation status | Git executable unavailable in this environment, so status/diff could not be read | `git` command lookup failed | Verify branch/worktree state in an environment with Git |
| Database preservation | The initial baseline suite (240 passed, 3 failed) ran against the configured database before test isolation was added; subsequent suites used a disposable `DATABASE_PATH` | Final suite passed with isolation; a later read-only query found 184 submissions, but no pre-baseline state is available | Exact baseline-induced changes cannot be determined; do not claim the configured database was untouched or restore/overwrite it |
| Tool and skill registries | Existing typed tool and reusable skill catalogs retained | Existing Lab 2/3 unit/API tests | No registry redesign performed |
| Runtime provenance and audit | Coordinator audit records completion/failure telemetry; Lab 5 and submission lifecycle audits remain separate | Coordinator/Lab 5/submission regression tests | Coordinator audit remains process-local and actor identity is unavailable |
| Assignment records and review | SQLite attempt/review writes record atomic latest-attempt updates and append-only lifecycle events | Isolated submission/E2E/persistence tests | Header-based identities are spoofable; not production authorization |
| Faculty authorization | Route checks compare caller-provided `X-User-Role` only | Existing tests verify role-header branches | Real login/identity provider is absent; genuine authorization remains a blocker for real student data |
| Frontend API feedback | Existing `apiCall` and action handlers retained; Lab 1 console-only errors now surface visibly | JavaScript syntax/UI tests; actual browser smoke | Not every individual control/error path was browser-clicked |
| Startup/configuration | Existing `run.py`, central `Settings`, routers and static mount retained | Compile/full tests/direct browser | Default port 8000 was occupied during audit; source run tested on 8001 |
| Regression documentation | README, architecture, implementation matrix, startup guide and manual checklist corrected; historical conflicting reports labeled | Documentation compared to current implementation/test evidence | Official Lab 9–12 specifications still required |

| Area | Verified Capability | Automated Tests | Result |
| :--- | :--- | :--- | :--- |
| **URL Security** | Valid HTTPS, scheme enforcement, lookalike rejection, SSRF protection, credential stripping, root repo enforcement | 7 tests | **PASSED** |
| **Assignments** | Listing, details, unestablished policy handling, 404 rejection | 2 tests | **PASSED** |
| **Students** | Enrolled student retrieval, isolation checks | 2 tests | **PASSED** |
| **Submissions** | Attempt counting, `is_latest` pointer update, deadline status calculation | 5 tests | **PASSED** |
| **RBAC** | Student-to-student access blocked (403), student faculty portal blocked (403) | 3 tests | **PASSED** |
| **Faculty Review**| Faculty submissions list, review submission, score persistence, status update | 3 tests | **PASSED** |
| **Persistence** | SQLite direct query verification across independent database connections | 1 test | **PASSED** |
| **Frontend Journey**| Full end-to-end HTTP simulation of app.js async lifecycle | 1 test | **PASSED** |
| **Core Labs 1–8** | Labs 1-8 APIs, agents, memory, tools, connector, runtime, graph, and swarm | 203 tests | **PASSED** |
| **Total Suite** | Entire automated regression and integration test suite | **227 tests** | **100% PASSED** |
