# Agentic AI Core Concepts Quick Reference & Cheatsheet
Course: 26ECAC401: Agentic AI

## Key Concepts & Architectural Guarantees

### 1. BM25 Retrieval Scoring
BM25 ranks documents based on the query terms appearing in each document, balancing term frequency (TF) and inverse document frequency (IDF) with document length normalization:
- k1 = 1.5: Term frequency saturation parameter.
- b = 0.75: Document length normalization penalty.

### 2. Autonomous Loop Invariants
1. **Perception Grounding:** Agent acts only upon verified environment observations.
2. **Deterministic Tool Validation:** All tool arguments must pass strict schema validation before execution.
3. **State Immutability:** Revision engines must generate versioned diffs without mutating prior history.
4. **Human Oversight:** Consequential state changes require explicit faculty sign-off.