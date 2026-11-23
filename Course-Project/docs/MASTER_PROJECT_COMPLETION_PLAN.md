# CourseAgentAI Master Project Completion Plan

**Status:** Active execution plan; not a completion claim  
**Prepared:** 2026-11-17  
**Workspace:** `C:\Users\Lenovo\Desktop\CourseAgentAI`  
**Curriculum basis:** Official Build Book at `C:\Users\Lenovo\Downloads\Agentic_AI_15_Worklets_14Lab_Build_Book.docx`, Chapter 2 Course Project worklet and Lab 1-14 progression, as transcribed and assessed in [OFFICIAL_14_LAB_COMPLIANCE_AUDIT.md](../OFFICIAL_14_LAB_COMPLIANCE_AUDIT.md).

## 1. Current baseline and guardrails

- Latest full regression verification after Lab 10 and similarity-audit follow-up: `LAB4_RUN_MODEL_INTEGRATION_TESTS=1 .\.venv\Scripts\python.exe -m pytest -q` — **330 passed, 1 pytest-asyncio deprecation warning, 80.15 s**.
- Latest `python -m compileall -q app tests scripts`, `node --check app\static\app.js`, and `python -m pip check` passed.
- Lab 4's local pinned model, offline test, source scoping, durable vectors, lexical fallback, and preserved BM25 behavior are implemented; Lab 4 was not reworked in this phase.
- The project is not a Git repository; exact staged/unstaged changes cannot be reported.
- Tests use the private disposable database created in `tests/conftest.py`. Any ad hoc app, migration, demo, or CLI run must set `DATABASE_PATH` to an explicitly disposable path before importing application code.
- Never initialize, migrate, reset, seed, test against, or write `app/data/governed_academic.db`; preserve its separate existing backup. Before each DB-affecting phase, verify the active path and back up only the disposable target.
- At plan creation the governed DB and preserved backup both read as 405,504 bytes with SHA-256 `A6D98C12D50B96F4996C4016953239A368D7683A7613815E2BA337B322B67AEC`; this is the current starting reference and must be rechecked before final acceptance.
- Never send course/student content to hosted models. Do not claim real cloud, LMS, registrar, source-code similarity, team ownership, or faculty acceptance without direct evidence.
- The inspected tree currently has only `docs/LAB4_LOCAL_EMBEDDING_EVALUATION.md` under `docs/`; all other requested final docs remain deliverables.

## 2. Lab-by-lab current status and acceptance targets

Status is the evidence-based status in the latest official audit, updated for the verified Lab 4 Phase 2 work. Acceptance targets follow the official Chapter 2 worklet, not the mere existence of a page or API.

| Lab | Current status | Acceptance target | Key missing work / dependencies |
|---|---|---|---|
| 1 — Agent vs Chatbot: organised course workspace planner loop | **COMPLETE** for incremental criteria | Vague request elicits at least two clarifying questions; produces an editable plan and supports revise/version/diff. | Preserve tested flow; independently close unauthenticated private-data routes before capstone integration. |
| 2 — Tool-Using Agent: call data & compute | **COMPLETE** for incremental criteria | Facts/calculations are obtained through typed tools; final conclusions depend on tool results. | Preserve; connect future shared data boundary without duplicating tools. |
| 3 — Skill Creation: reusable plan & format skills | **COMPLETE** for incremental criteria | Same callable schema-typed skills work on multiple distinct inputs without code changes. | Preserve; expose explicit skill contracts to runtime/specialists. |
| 4 — Memory & Retrieval: state vs stored | **COMPLETE** for incremental criteria | Isolate ephemeral session state from durable memory; tag-filter and retrieve similar prior items using real embeddings; retain provenance and access isolation. | Already verified. Course-document RAG remains BM25; submission similarity covers metadata, not repository source. |
| 5 — MCP-Style Connector: one server for all sources | **PARTIAL** | Typed authenticated connector mediates every data-facing agent; source replacement does not require agent changes; failures/health are observable. | Server-derived role/actor attribution and SQL-level course predicates for submission/audit list/read/search are covered by regression tests. Production features still bypass it; registrar is mock; connector audit listing is process-local. |
| 6 — Runtime: skills, tools, memory, audit | **PARTIAL** | Bounded run lifecycle with input/output audit, scoped owner/course state, durable checkpoint/resume after process restart, and non-bypassable human gates. | Run snapshots/checkpoints/audit persist in SQLite; fresh-process recovery, budgets, Faculty/Admin authorization and actor context are tested. Workflow remains a deterministic demonstration not composed with Lab 4/5/course-project services. |
| 7 — Node Graph: parallel, branching, hard gates | **PARTIAL** | Validate graph, execute dependencies/branches in order, persist accurate per-node states, report failures, and prevent review/publication when gates fail. | Lifecycle routes now require Faculty/Admin and course access; state mutations are serialized and returned snapshots isolated. Concurrent steps and authorization are tested. Graph state remains in-memory and several nodes are deterministic demos, not real service integrations. |
| 8 — Parallel Swarm: fan-out/fan-in | **PARTIAL** | Bounded independent workers, aligned result selection/aggregation, provenance, partial-failure containment, limits/timeouts, and no duplicate work where practical. | Chapter demos now enforce unique chapter inputs, worker timeouts, locked-plan output checks, provenance presence, and result snapshot isolation. Still not assignment-level work; no sequential-quality benchmark or durable run history. Depends on real Lab 7 plan/work items. |
| 9 — Deep Research: evidence candidates and synthesis | **PARTIAL** | Multi-step research uses approved sources, retains evidence/provenance, structures findings and citations, separates evidence from interpretation, and reports insufficient evidence. | BM25 evidence table now returns real chunk/source citations, bounds claims, and never claims entailment from keywords. Still no multi-step synthesis, approved rubric/syllabus source binding, or graph rejection gate. Depends on scoped connector and citations. |
| 10 — Cloud Operations: failed deployment diagnose & fix | **PARTIAL / SIMULATED** | Real supported provider workflow only with credentials; otherwise honest local simulation with operation health, state, errors and recovery. | Thread-safe simulator has target-component diagnosis, in-memory event history, simulated approved repair/rollback, and a request-local grade-weight repair preview capped at three attempts. No provider contact, durable operation audit, restart recovery, or course-record mutation. Depends on governance and runtime. |
| 11 — SDLC Factory: spec to tested output | **PARTIAL** | Locked plan/spec plus acceptance tests gates any artifact; controlled workspace write, actual tests and review evidence; human approval before publish/deploy. | Current implementation is five fixed smoke checks, not requirement-to-code; no sandboxed workspace/build gate. Depends on graph, local workspace boundaries and governance. |
| 12 — Safety & Governance: approval, eval, rollback | **PARTIAL** | Confidentiality, actual actor authorization, policy validation, evaluation metrics, human approval, audit, versioned release and reversible rollback. | Generic admin governance is not integrated with Course Project releases; risk/evaluation plan and consistent actual actor audit are missing. Depends on actual identities and durable run context. |
| 13 — Discipline-Specific Agents: domain specialisation | **MISSING** | Registry of course-type specialists producing domain-appropriate, structured, checkable, evidence-grounded outputs with uncertainty/citations and scoped tools. | No module/API/tests. Build only official theory/lab/project profiles; do not invent faculty rubric. Depends on shared contracts, retrieval, runtime, and governance. |
| 14 — Capstone: team-owned system | **PARTIAL** | One end-to-end faculty-approved, validated, published worklet run and dashboard, with sources, gates, recovery, audit, and demonstrable real components. | No integrated coordinator/pilot; no confirmed team identity or real faculty approval. Depends on Labs 5-13 and available accounts. |

Lab detail, source references, and the original evidence remain in the official audit. Completion requires testable acceptance, not just endpoint coverage.

## 3. Course Project worklet status and target

**Current: PARTIAL.** Existing materials, assignments/submissions, similarity flags, grading lifecycle, project milestones, notifications, and faculty/admin views are useful constituent services. The missing system behavior is the shared coordinator-owned workflow that prepares an evidence-backed workspace, hard-validates it, routes it to the correct faculty, requires explicit approval, publishes a versioned release, and supports audit/rollback.

Target pilot sequence, using disposable demo records only:

1. Faculty uploads approved notes/materials; recursive indexing retains category, folder, and source citations.
2. Student can only browse authorized materials and receives cited answers grounded in those sources.
3. Faculty configures/releases an assignment and rubric; release, due dates, and reminders must have explicit behavior rather than placeholder seed claims.
4. Student submission records immutable timestamp/attempt and validated repository URL.
5. Collection and allowed similarity workflow record evidence and clearly disclose limitations.
6. Grading assistance produces a rubric-aligned draft with criterion evidence; it does not publish autonomously.
7. Project milestones/checkpoints and notifications update from recorded evidence.
8. A single coordinator run checks official hard gates, records inputs/outputs and citations, and pauses for the authorized course faculty.
9. Approval publishes a versioned workspace/grade; rejection, bounded repair, and rollback remain auditable.
10. Browser demonstration uses disposable accounts/data and reports exactly which outside services are simulated.

Do not treat repository URL validation as repository access; do not claim plagiarism detection from metadata; do not treat a smoke test as generated-code validation.

## 4. Dependencies and implementation order

1. **Baseline and safety:** preserve Lab 4; record disposable test configuration and governed DB reference; run full suite; create this plan.
2. **Labs 5-6 and cross-cutting identity:** Lab 5 course-scope/actor issues are patched but universal connector use remains. Lab 6 run/checkpoint/audit persistence and server-derived actor/course authorization are implemented and restart-tested. Continue shared contracts, source health, error/timeout handling, and connector mediation.
3. **Labs 7-8:** Lab 7 lifecycle authorization and serialized state/snapshot correctness are implemented; graph persistence/recovery and real service composition remain. Lab 8 now has bounded inputs/timeouts and strict output/provenance checks, but needs plan-derived assignment work, durable run context, cancellation/failure behavior, and measured sequential-quality comparison.
4. **Labs 9-10:** build evidence-grounded research only over approved local sources; distinguish evidence from synthesis. Keep cloud operations explicitly simulated unless a supported provider and credentials are available; add durable operation records and recovery for simulation.
5. **Labs 11-12:** create a controlled local build workspace with requirement/test evidence; prevent writes outside that workspace; ensure test-green and policy gates before review/publish; integrate actual actor, risk/metrics, approval, version and rollback records.
6. **Lab 13:** add specialist interfaces/registry with at least two differentiated specialists, distinct tools/tasks, structured output, citations, uncertainty, and authorization tests.
7. **Lab 14 + Course Project:** compose existing services through a coordinator; implement the hard validation gate, bounded repair/escalation, human course-faculty approval, versioned publish/rollback, and integrated demo dashboard. Avoid rewriting services already passing tests.
8. **Frontend integration and final evidence:** make workflows discoverable and honest; run focused and full regressions; use browser tests with disposable data; update requested docs, guide and demonstration script.
9. **Final safety decision:** compare governed DB SHA-256 to a recorded pre-execution reference; report hashes and any mismatch, exact test outcomes, live-vs-simulated integrations, and acceptance gaps. Do not claim full completion when any mandatory criterion is blocked/unverified.

Actual prerequisites: runtime needs the connector and authenticated identity; graph needs runtime; swarm execution needs run/graph context; research needs approved source connectors; SDLC must feed the governance gate; specialists depend on common contracts and authorized retrieval; capstone depends on these stages. Keep unrelated work independent when a genuine blocker occurs.

## 5. Per-phase verification requirements

Before any database-writing command, print/inspect `DATABASE_PATH`, resolve it, and verify it is not the governed DB or any alias; create and verify a backup of the disposable DB. Tests use the established `tests/conftest.py` temporary DB. Browser demonstrations must use a separate disposable DB and storage root.

| Phase | Minimum verification |
|---|---|
| Connector/runtime | Unit/API success, timeout/failure, unavailable source, permission denial, forged role/actor rejection, course isolation, checkpoint and restart recovery, cancellation/budget/gate behavior. |
| Graph/swarm | Invalid/cyclic graph rejection where cycles unsupported, topological order, independent branches, truthful node states, bounded concurrency, partial failure, cancellation/retry, persisted progress. |
| Research/operations | Citation maps to a real local source; no evidence yields explicit insufficiency; distinguish simulation fields from real provider contact; simulate operation lifecycle/recovery without cloud credentials. |
| SDLC/governance | Tests run against a temporary controlled workspace, failed test blocks artifact/publish, traversal/protected DB writes denied, approval is bound to authenticated faculty, audit actor correct, rollback restores the prior disposable release. |
| Specialists/capstone | Two specialists differentiated by type/task/tools; schema and citations validated; authorization cannot be bypassed; full Course Project path covers material, assignment, submission, review, milestone, notifications, approval and audit. |
| Final | Focused suites, full `pytest`, `compileall`, `node --check`, browser E2E for available workflows, dependency check, DB hash/size/FK/integrity read-only checks. Report exact commands and outputs. |

## 6. Risks and explicit blockers

- The active official Build Book is available at the path above. If it disappears, use the existing audited extracts and do not invent details.
- No institution-specific provider credentials, production endpoints, team names/IDs, or faculty evaluation input are assumed. These limit real integrations and team-owned/faculty-acceptance claims, but independent local implementations can proceed.
- A local test suite can demonstrate deterministic service correctness, not deployed uptime or institutional acceptance.
- Persistence improvements require schema additions. Never migrate the governed DB; migrations must be exercised only with disposable DBs and explicit backup/rollback checks.
- Lab 1 plan routes remain unauthenticated; the Lab 5 connector and Lab 6/7 lifecycle authorization changes address known identity/scope gaps in those surfaces. `routes_similarity.py` still labels every actor as `FACULTY`, regardless of authenticated role.
- A security-review follow-up found cross-course submission disclosure via the generic Lab 5 connector and spoofable connector audit agent identity; both were patched with regression tests. The latest full suite passes, but the unrelated similarity actor-role issue remains on the security backlog and security acceptance is not globally clear.
- This workspace is not a Git repository. Preserve files, maintain the continuation checklist/handoff, and do not claim a Git diff exists.
- The UI/repository currently lack several requested final docs and a clean submission rubric. Create only honest documentation and do not invent team members or official folder requirements.

## 7. Final demonstration and acceptance

The final demo should be reproducible from a disposable SQLite DB and temporary materials directory, resettable without touching user data, and scripted from actual APIs/UI. It must show student and faculty boundaries, citations, submission/late metadata, similarity caveats, grading draft vs approval vs publication, milestone/notifications, governance history, failure/recovery, and the system's simulated external services. Capture browser screenshots only from a real run and remove secrets/student PII.

The project-wide decision remains **INCOMPLETE** until all official lab criteria and the Course Project pilot are either objectively implemented/verified or documented with concrete external blockers. A passing test suite alone is insufficient.
