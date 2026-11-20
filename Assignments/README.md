# CourseAgentAI — All 12 Laboratory Assignments
**Course:** `26ECAC401: Agentic AI`  
**Institution:** University Academic Laboratory Coursework  
**Academic Year:** 2026  

This directory contains the complete source code references, standalone verification runners, test documentation, and evaluation rubrics for all 12 laboratory assignments.

## Assignments Directory Index

| Folder | Title | Architectural Pattern | Weight |
| :--- | :--- | :--- | :--- |
| [Assignment_01](Assignment_01/README.md) | Clarify-Plan-Revise Academic Course Workspace Planner | `Clarify -> Plan -> Revise Loop` | 8% |
| [Assignment_02](Assignment_02/README.md) | Deterministic ReAct Tool-Using Agent & Auditable Auditor | `ReAct / Tool Execution with Pydantic Validation` | 8% |
| [Assignment_03](Assignment_03/README.md) | Reusable Academic Skills Registry & Dynamic Routing | `Modular Skill Composition & Declarative Registry` | 8% |
| [Assignment_04](Assignment_04/README.md) | Dual-Tier Memory Architecture & Grounded Retrieval | `Short-Term Dialog vs Long-Term Vector/Lexical RAG` | 8% |
| [Assignment_05](Assignment_05/README.md) | Governed Academic Connector with RBAC & MCP Architecture | `Model Context Protocol (MCP) Style Governed Access` | 8% |
| [Assignment_06](Assignment_06/README.md) | Resilient Agent Runtime with Checkpoints & State Recovery | `State Checkpointing, Budgets & Fault Tolerance` | 8% |
| [Assignment_07](Assignment_07/README.md) | 10-Node Specialist Graph DAG with Bounded Retries | `Specialist Node Graph DAG & Faculty Approval Gates` | 8% |
| [Assignment_08](Assignment_08/README.md) | Parallel Specialist Swarm & Asynchronous Fan-Out/Fan-In | `Concurrent Scatter-Gather Swarm Orchestration` | 8% |
| [Assignment_09](Assignment_09/README.md) | Deep Research Claim Verifier with Entailment Distinction | `Deep Research, Source Grounding & Entailment` | 8% |
| [Assignment_10](Assignment_10/README.md) | Cloud Operations Health Monitor & Self-Healing Diagnostic Agent | `Autonomous Infrastructure Diagnostics & Approval-Gated Repair` | 8% |
| [Assignment_11](Assignment_11/README.md) | Agentic SDLC Code Synthesis & Sandboxed Verification | `Specification -> Code -> Test -> Verification Pipeline` | 8% |
| [Assignment_12](Assignment_12/README.md) | Enterprise Safety, Governance, RBAC & State Rollback | `Persistent Change Proposals, Approval Gates & Rollback` | 8% |


---

## Verification & Execution Instructions
Each assignment folder contains a dedicated `runner.py` script that can be executed directly from the project root:

```powershell
# Example: Verify Assignment 1
python Assignments/Assignment_01/runner.py

# Example: Run Pytest across all assignments
python -m pytest tests/ -q
```
