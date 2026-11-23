# CourseAgentAI — Verification Results

## UI/workflow repair verification (2026-11-17)

| Check | Result |
|---|---|
| `LAB4_RUN_MODEL_INTEGRATION_TESTS=1 .\.venv\Scripts\python.exe -m pytest -q` | **339 passed in 122.50s; 1 pytest-asyncio fixture-loop-scope deprecation warning** |
| `pytest -q tests\test_lab2_api.py tests\test_lab2_tools.py tests\test_lab7_api.py tests\test_lab8_api.py tests\test_ui_endpoints.py` | **60 passed in 23.66s; 1 Starlette httpx/TestClient deprecation warning** |
| `pytest -q tests\test_submissions.py tests\test_ui_endpoints.py` | **35 passed in 5.56s; 1 Starlette httpx/TestClient deprecation warning** |
| `.\.venv\Scripts\python.exe -m compileall -q app tests scripts` | Passed |
| `node --check app\static\app.js` | Passed |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| Protected governed database and preserved backup, read-only after test run | Both **405,504 bytes**, matching SHA-256 `A6D98C12D50B96F4996C4016953239A368D7683A7613815E2BA337B322B67AEC` |
| Browser Lab 2 catalog-backed rubric scenario | **SUCCESS**; selected `lab1`, displayed persisted rubric criteria |
| Browser Lab 3 direct planning sandbox | **SUCCESS**; schema-valid 14-week schedule |
| Browser Lab 7 approval lifecycle | **COMPLETED**; ten node badges `DONE`; published artifact visible |
| Browser Lab 8 swarm | **MERGED**; four workers `COMPLETED`; initial worker state shown as `IDLE / Not dispatched` |
| Browser Admin submissions view | Admin overview visible; Faculty review and Student portal hidden; 13 disposable course assignment records shown |

The browser checks used the existing disposable live application database. The Lab 7/8 outputs and assignment contents are synthetic seed/demo data, not official faculty acceptance. The complete pytest suite includes the opt-in real-model Lab 4 offline integration test. The sole warning in the full run is pytest-asyncio's unset fixture-loop-scope deprecation notice.

## Assignment overview layout repair (2026-11-18)

- Browser verified the Admin assignment overview at 1050 px and 390 px widths. Assignment titles and metadata now occupy separate, spaced rows/cards; summary metrics are distinct cards. At 1050 px, the header brand, actions, and scrollable navigation occupy separate rows instead of overlapping.
- `pytest -q tests\test_ui_endpoints.py`: **3 passed in 1.33s**, with one existing Starlette TestClient deprecation warning.
- `node --check app\static\app.js` and `python -m compileall -q app tests scripts`: passed.

## Latest autonomous continuation verification

The latest Lab 11/13/14 implementation, frontend navigation patch, and Lab 1 route authorization have been re-verified. The completed disposable browser check reached a Faculty-approved release and a Student-safe read. Exact latest full-suite results are recorded above.

| Command/check | Result |
|---|---|
| `LAB4_RUN_MODEL_INTEGRATION_TESTS=1 .\.venv\Scripts\python.exe -m pytest -q` | **336 passed in 125.56s; 1 pytest-asyncio deprecation warning** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_lab1.py tests\test_lab1_grounding.py tests\test_regression_audit.py -q` | **35 passed in 9.18s; 1 pytest-asyncio deprecation warning** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_ui_endpoints.py tests\test_lab1_grounding.py -q` | **11 passed in 1.24s; 1 pytest-asyncio deprecation warning** |
| `.\.venv\Scripts\python.exe -m compileall -q app tests scripts` | Passed |
| `node --check app\static\app.js` | Passed |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| Governed DB and preserved backup, read-only size/hash check | Both **405,504 bytes**; both SHA-256 `A6D98C12D50B96F4996C4016953239A368D7683A7613815E2BA337B322B67AEC` |
| `.\.venv\Scripts\python.exe -m pytest tests\test_labs9_12.py tests\test_similarity_api.py tests\test_ui_endpoints.py -q` | **19 passed in 6.57s** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_similarity_api.py -q` | **1 passed in 1.15s** after strengthening the insufficient-submission assertion |
| `.\.venv\Scripts\python.exe -m pytest tests\test_lab7_graph.py tests\test_lab7_api.py -q` | **13 passed in 5.84s** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_lab7_graph.py tests\test_lab7_api.py tests\test_ui_endpoints.py -q` | **16 passed in 6.03s** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_lab8_swarm.py tests\test_lab8_api.py -q` | **12 passed in 6.16s** |
| `.\.venv\Scripts\python.exe -m pytest tests\test_labs9_12.py -q` | **12 passed in 6.37s** |
| Focused Lab 5/6/submission/auth regression suite | **86 passed** |
| `.\.venv\Scripts\python.exe -m compileall -q app tests` | Passed |
| `node --check app\static\app.js` | Passed |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements |
| Governed DB and preserved backup, read-only size/hash check | Both **405,504 bytes**; both SHA-256 `A6D98C12D50B96F4996C4016953239A368D7683A7613815E2BA337B322B67AEC` |

Lab 7 tests verify authenticated Faculty/Admin course-scoped run/state/step/approval operations, student denial, trusted approval actor attribution, isolated read snapshots, serialized concurrent steps, bounded retry, and approval gating. Lab 8 tests verify request validation, per-worker timeout, locked-plan/provenance checks, failure containment, and result snapshots. Lab 9 tests verify citations and evidence-table shape, unsupported-evidence reporting, removal of keyword-based entailment claims, and claim bounds. Lab 10 tests verify bounded simulated repair and cloud operations; the new similarity API regression verifies student denial and server-derived Faculty/Admin audit attribution, including insufficient-submission attempts. Lab 6 process-restart recovery uses a fresh Python process and disposable DB. All test/migration activity used disposable databases. No application startup, test, migration, reset, seed, or write targeted the governed DB or preserved backup. The warning is pytest-asyncio's notice that the default fixture event-loop scope will change in a future release.

Lab 7 graph state and Lab 8 swarm results remain process-local; neither has restart recovery or durable run audit. Lab 9 remains lexical candidate retrieval rather than deep research or entailment assessment. Lab 10 remains a simulation with process-local state and no provider integration. Lab 13 is deterministic scaffolding and Lab 14 is a persistent preparation/release workflow, not a full agent graph. Test results are not a claim that Labs 5–14 or the integrated Course Project are complete.

### Disposable browser demonstration (2026-11-17)

- Used a dedicated temporary SQLite database and materials directory at `C:\Users\Lenovo\AppData\Local\Temp\CourseAgentAI-e2e-b3f69c14bd2041baa2532ee63386f131`; no governed database or backup was used.
- Faculty ran Lab 14 preparation. The first attempt correctly failed the validation gate because the disposable seeded Lab 1 rubric totaled 200 points and 140% weight against a 100-point assignment. The demo DB rubric rows alone were adjusted to total 100 points and 100%; the next run passed all 8 checks and reached `READY_FOR_FACULTY_APPROVAL`.
- Faculty approved and published release version 1 and loaded the current release.
- After Student sign-in, the UI loaded the current release. The API response omitted individual submission rows and instead returned a submission-count notice; similarity pairs/details were omitted and replaced with a candidate-evidence summary.
- This was a browser verification of a synthetic local workflow only. It is not a real course-faculty acceptance, production deployment, external integration, complete assignment cycle, or grade publication demonstration.

## Final continuation verification (2026-11-16)

| Command/check | Result |
|---|---|
| Baseline `python -m pytest -q` (before continuation code edits) | **277 passed, 1 warning** |
| Final `python -m pytest -q` | **289 passed, 1 warning, 22.70 s** |
| `python -m pytest -q tests\test_auth.py tests\test_knowledge_downloads.py tests\test_lab4_api.py` | **34 passed, 1 warning** |
| `python -m pytest -q tests\test_lab4_api.py tests\test_ui_endpoints.py` | **11 passed, 1 warning** |
| `python -m compileall -q app tests scripts` | **Passed** |
| `node --check app\static\app.js` | **Passed** |
| Governed SQLite read-only check | **0 foreign-key violations**; no database writes performed |
| Temporary app `/api/health` | **HTTP 200** using a disposable database |
| Browser authentication/authorization | Earlier checks verified temporary Faculty/Student login, identity, refresh persistence, role-specific portals, Student **403** on the administrator audit endpoint, and Faculty logout followed by **401** on a protected audit request. After current changes, the Student session survived an app restart; the notifications/announcements view loaded; Lab 4 created an owner-bound session and returned cited Chapter 1 RAG results; the Student received **403** when attempting the faculty-only Lab 10 simulation. |
| Development cookie headers | Session cookie: `HttpOnly`, `SameSite=Strict`, `Max-Age=28800`, `Secure=false` on local HTTP. CSRF cookie: readable by same-origin JavaScript, `SameSite=Strict`, eight-hour max age. Production Secure-cookie behavior was not browser-tested. |
| Browser responsive layout | No document-level horizontal overflow at **320, 390, or 1280 px** after refreshing the stylesheet. The Student and Faculty portals were rendered with empty disposable data. |

One full-suite attempt initially had **1 failure and 6 setup errors**: a rate-limit test left a login lockout in the shared test database and later tests sharing the TestClient address received HTTP 429. Test teardown now clears only disposable login-throttle rows between tests, preserving each test's in-test rate-limit assertions. The final rerun passed all 289 tests. The single warning is the existing Starlette deprecation warning about using `httpx` with `starlette.testclient`; the installed guidance recommends `httpx2`.

The disposable database contained no assignments or submissions, so a live submission/review/grade-publication journey was not performed. Live GitHub access, external cloud deployment, administrator browser login, post-change Faculty Cloud Ops browser workflow, production Secure-cookie configuration, and model-backed workflows are not claimed as browser-verified. See [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md) and [DEMO_GUIDE.md](DEMO_GUIDE.md) for the current evidence boundary.

### Governed database snapshot

The governed database was opened read-only. The observed counts were 14 assignments, 185 submissions, 4 students, 1 course project, 4 milestones, 3 notifications, and 2 submission-audit events. The `audit_events` table contained zero rows at that observation; other audit tables are separate. No write, reset, migration, or reseed was performed.

---

## Historical verification (2026-10-27; superseded)

**Verification date:** 2026-10-27  
**Environment:** Windows; Python 3.12; Node.js available.  
**Scope:** Repair regression suite, SQLite persistence/audit behavior, representative browser smoke checks, and frontend/Python syntax validation.

## Final automated checks

| Command/check | Result |
|---|---|
| `python -m pytest -q` | **250 passed, 1 warning, 9.42 s** |
| `python -m compileall -q app tests` | **Passed** |
| `node --check app\static\app.js` | **Passed** |

The single warning is the existing Starlette deprecation warning about using `httpx` with `starlette.testclient`; the installed guidance recommends `httpx2`.

The initial baseline run reported **240 passed, 3 failed, 1 warning**. The failures were investigated and repaired without weakening application behavior: an incorrect unsupported-operation fixture, a persistence test dependent on pre-existing database state, and a stale JavaScript variable name in a UI assertion. Tests now set a disposable `DATABASE_PATH` before app imports and disable remote GitHub reachability checks for endpoint tests.

## Browser smoke checks

The repaired app was exercised on port 8001 using a dedicated temporary SQLite database. The server and that temporary database directory have since been stopped and removed.

- Lab 8 completed with four workers; a simulated Worker 3 failure produced `PARTIAL_SUCCESS` with three successful workers and one failed worker.
- Lab 9 returned provenance-bearing candidate evidence, honored Chapter 2 filtering, and returned `NO_MATCHING_EVIDENCE_FOUND` for an unsupported query.
- Lab 10 displayed its scope notice; Lab 11's five-case application smoke utility passed and does not generate code from requirements.
- Lab 12 proposal, approval, rollback, and audit history showed the expected status transitions.
- A GitHub lookalike host was rejected with HTTP 400 before any external reachability check.
- The nested knowledge note was listed and its download action returned successfully.
- Coordinator history showed trace IDs, statuses, result statuses, duration, and completion time. Actor identity remains unavailable.

A live successful submission was not performed because it would invoke GitHub reachability. Submission, review, audit, and persistence paths were exercised through offline automated tests.

## Database and environment caveats

The initial baseline test suite ran against the configured database before isolation was added. A later read-only query found 184 submissions, but the database's pre-baseline state is unknown; the exact test-induced changes cannot be determined. Do not claim that the active database was untouched, restore an assumed snapshot, or overwrite it. Back up the current database before starting the repaired app against it; startup may create the new governance and submission-audit tables.

No app server is currently left running. Git was unavailable in this environment, so branch/worktree status and a source diff could not be verified.

## Remaining limitations

- Detailed companion specifications for Labs 9–12 were not present. The available tools and their scope are documented in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
- Demo role/student headers and client-supplied decision actors are not authenticated identities; do not use this demo authorization model with real student data.
- Lab 12 governance state is SQLite-persisted, but proposal actor identity is unavailable and decision actors are demo-supplied. Coordinator audit history remains process-local and actor identity is unavailable.
