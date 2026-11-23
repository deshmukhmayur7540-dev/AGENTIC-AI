# CourseAgentAI Demo Guide

**Course:** 26ECAC401 — Agentic AI  
**Purpose:** Safe, reproducible local demonstration of the current application.  
**Evidence boundary:** This guide describes present behavior and limitations; it does not certify production readiness or compliance with unavailable course handouts.

## 1. Safety and prerequisites

- Use an isolated, disposable SQLite database for demonstrations that write data. Do not use `app/data/governed_academic.db` unless its owner explicitly approves the writes.
- No demo accounts or passwords are seeded. Use only accounts provisioned by an authorized operator. Do not invent credentials or share passwords in logs, screenshots, or reports.
- Student and assignment records must be present in the selected database before demonstrating student submissions. A newly created empty database is useful for a login-page smoke check but is not a populated course demo.
- For the student/faculty workflows, use separate accounts and a faculty account scoped to the course being demonstrated. Administrators do not receive grade-review or publication permissions.
- Use a public repository only when its owner has authorized the accessibility check. The application does not inspect or execute submitted repository code.
- The governed database was not changed during the 2026-11-16 audit. See [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md) for the read-only snapshot and limitations.

## 2. Start a disposable local instance

From PowerShell in the project root:

```powershell
$env:DATABASE_PATH = Join-Path $env:TEMP ("CourseAgentAI-demo-" + [guid]::NewGuid().ToString("N") + ".db")
$env:COURSEAGENTAI_HOST = "127.0.0.1"
$env:COURSEAGENTAI_PORT = "8000"
$env:COURSEAGENTAI_CORS_ORIGINS = "http://127.0.0.1:8000"
python run.py
```

Keep the same PowerShell window open while the server is running. Open `http://127.0.0.1:8000/`. If port 8000 is occupied, choose a free port and change both `COURSEAGENTAI_PORT` and `COURSEAGENTAI_CORS_ORIGINS` to match that exact origin. The new database is initially empty; it is not seeded with demo users or assignments.

The canonical dependency, database, and account-initialization instructions are in [README.md](README.md). Never point the bootstrap utility at a database unless you are authorized to create accounts in it.

## 3. Authentication and role-specific workflows

1. Sign in with an operator-provisioned account. Check that the account is the expected Student, Faculty, or Administrator before showing role-specific operations.
2. Refresh the browser and verify that the current session remains active; then sign out and verify protected API access is denied.
3. Use a dedicated student account to demonstrate only that student's records. Do not attempt to demonstrate another student's private data with real records.
4. Use a faculty account with the appropriate course scope for review. A faculty member without that scope and an administrator are not authorized to review, approve, or publish grades.
5. Demonstrate a submission and the supported lifecycle:

   `SUBMITTED → UNDER_REVIEW → DRAFT_GRADED → APPROVED → PUBLISHED`

   Draft marks and feedback remain private to faculty; publication requires approval. The student-facing result is visible only after publication. Use a disposable fixture and verify the saved state in both the table and review form.
6. Do not describe a valid GitHub URL as proof of authorship, correctness, or successful access to private repository contents. Reachability can be inconclusive because of network conditions or repository privacy.

The browser audit in this workspace used explicitly initialized temporary Student and Faculty accounts in a disposable database. It verified login, role identity, refresh persistence, the Faculty Review portal, the Student submissions portal, student denial from the administrator audit endpoint, and faculty logout invalidation. After later UI/API changes, a Student session also persisted across an application restart; the notifications/announcements view loaded, and Lab 4 created an authenticated owner-bound session and returned cited RAG results. The Student was correctly denied the faculty-only Lab 10 simulator with HTTP 403. The fixture had no assignments or submissions, so a full grade publication journey was not performed. No administrator browser login, post-change Faculty Cloud Ops browser workflow, or production-cookie configuration was tested.

## 4. Lab demonstration sequence

Labs 1–8 have implementations and automated tests. Most are deterministic educational workflows rather than model-driven autonomous agents. Lab 8 uses asynchronous worker concurrency; that does not make the workers independent LLM agents.

1. **Lab 1 — Planner:** show clarification, structured planning, and revision/diff. Do not imply that deterministic output is an LLM-generated plan.
2. **Lab 2 — Tools:** inspect typed tools and an observable execution trace. The trace is tool activity, not private chain-of-thought.
3. **Lab 3 — Skills:** inspect and run the registered typed skills. Execution history is process-local.
4. **Lab 4 — Memory and RAG:** contrast SQLite-backed, owner/course-scoped short-term session state with separately saved long-term memories and cited course-note retrieval. Session state expires and is not promoted to long-term knowledge automatically. The embedding model is opt-in/offline for saved-memory or submission-metadata similarity; course-document retrieval remains BM25.
5. **Lab 5 — Governed connector:** demonstrate role-aware operations against local/simulated sources. It is not an external MCP server or institutional registrar integration.
6. **Lab 6 — Runtime:** step through bounded work and its approval gate. Run snapshots, checkpoints, and audit events persist in SQLite and fresh-process recovery is tested; the current action sequence is still a deterministic demonstration, and crash/failure behavior is simulated.
7. **Lab 7 — Node graph:** show bounded retry and the faculty approval gate. Named nodes are deterministic handlers; run state is in memory.
8. **Lab 8 — Swarm:** dispatch concurrent workers and show merge/failure containment. Worker failure is simulated.
9. **Lab 9 — Deep Research:** show lexical evidence candidates and citations. It does not evaluate semantic entailment or create the stated research briefing.
10. **Lab 10 — Cloud Operations:** run the local simulated failed-deployment diagnosis, review the proposed bounded repair, explicitly approve it, then demonstrate rollback. It is an in-memory simulation only; it does not persist audit events or contact a cloud provider. The grade-weight utility remains a separate feature.
11. **Lab 11 — Agentic SDLC:** run the fixed smoke checks, then submit a structured requirement to the spec builder. It returns a deterministic, cited artifact and structural acceptance results. It does not generate or execute arbitrary source code.
12. **Lab 12 — Safety and Governance:** an authorized administrator can stage, approve/reject, and roll back a generic proposal. State and governance audit events persist in SQLite. Lab 14 separately adds course-Faculty release approval, evaluation counts, risk notes, versions, and rollback; this is not application-wide risk evaluation.
13. **Lab 13 — Course specialists:** select Theory, Lab, or Project and enter a work item supported by course material. Inspect the cited evidence and structural checks. Outputs are scaffolds, not autonomous subject-matter judgments or invented rubrics.
14. **Lab 14 — Integrated capstone:** use a scoped Faculty account and a disposable course populated with at least one uploaded/indexed material, one assignment whose rubric points equal the assignment maximum and whose weights total 100%, at least two latest submissions for that assignment, and at least two project milestones. Prepare a run and inspect every validation check. A missing requirement yields `VALIDATION_FAILED` and the API refuses approval. Faculty approval creates a versioned release; a subsequent release can be rolled back. Open the current release as a Student and verify individual submissions, scores, and similarity pairs are redacted. This integrates existing local services; it is not a live LMS, repository-content, cloud, or external integration.

The detailed official Course Project worklet and available Lab 1–14 progression were inspected from the Build Book. Detailed companion manuals for selected later labs remain unavailable; the [official audit](OFFICIAL_14_LAB_COMPLIANCE_AUDIT.md) distinguishes Build Book criteria from other assumptions. Do not claim a partial scaffold satisfies an entire lab simply because its screen or endpoint runs.

## 5. Knowledge demo

- The Knowledge catalog recursively lists allowed original files under the configured root.
- Default RAG discovery recursively processes extractable DOCX, PPTX, TXT, Markdown, PDF, and CSV files in chapter 1–4 paths under `knowledge/agentic_ai`. Unsupported/unextractable files and other knowledge subtrees are skipped.
- A file being listed or downloadable does not establish that it was indexed.
- Search results use lexical retrieval and provide source metadata/citations. They do not prove semantic support or entailment.
- The index is in memory; verify any direct filesystem change with an explicit reindex rather than assuming it refreshed automatically.

## 6. Verification

Run from the project root:

```powershell
$env:LAB4_RUN_MODEL_INTEGRATION_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests scripts
node --check app\static\app.js
.\.venv\Scripts\python.exe -m pip check
```

The tests use disposable SQLite state; do not override the test fixture to point at a user or production database. See [TEST_RESULTS.md](TEST_RESULTS.md) for exact executed counts and browser evidence.

## 7. Security and operational limitations

Authentication uses database-backed password hashes and opaque expiring session cookies. Unsafe requests require an exact trusted Origin; cookie-authenticated mutations also require the CSRF cookie/header pair. Student isolation and faculty course scope are enforced by backend authorization. Automated verification does not replace institutional identity lifecycle controls, MFA, operational monitoring, protected database backups, HTTPS deployment configuration, or a production security review.

The service is a local academic demonstration. Do not use it to process real grades or sensitive student information without a separate institutional security and privacy approval.
