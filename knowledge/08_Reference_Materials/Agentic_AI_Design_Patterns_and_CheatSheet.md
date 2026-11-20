# Agentic AI Design Patterns & Architecture Reference
Course: 26ECAC401: Agentic AI

## Key Design Patterns in Agentic Systems
1. **Reflection & Self-Correction:** The agent critiques its intermediate outputs and revises them against constraints before committing.
2. **Tool Use & Function Calling:** Strictly typed parameters validated with Pydantic schemas.
3. **Planning & Decomposition:** Breaking large tasks into sub-tasks (planning skill).
4. **Multi-Agent Collaboration:** Specialization across roles (Coordinator, Planner, Retriever, Reviewer).
5. **Memory Hierarchy:** Separation between short-term conversation scratchpads and persistent knowledge stores.