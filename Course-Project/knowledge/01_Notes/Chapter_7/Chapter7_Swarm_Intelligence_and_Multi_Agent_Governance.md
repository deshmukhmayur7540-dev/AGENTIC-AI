# Chapter 7: Swarm Intelligence, Parallel Fan-Out & Alignment Governance
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