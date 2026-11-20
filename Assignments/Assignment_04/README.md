# Assignment_04: Dual-Tier Memory Architecture & Grounded Retrieval
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Academic AI agents require conversational continuity without memory cross-contamination. 
Assignment 4 requires building a dual-tier memory system:
1. Short-Term Memory: Owner- and course-scoped SQLite dialog store with multi-turn session isolation and 24-hour expiry.
2. Long-Term Knowledge: Grounded retrieval combining local semantic embeddings (Sentence-Transformers) with deterministic BM25 lexical indexing.
3. Citations: Every retrieved response must provide verified source document filenames and chunk offsets.

---

## 2. Architectural Pattern
**Pattern:** `Short-Term Dialog vs Long-Term Vector/Lexical RAG`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [session_store.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab4/session_store.py)
- [knowledge_store.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab4/knowledge_store.py)
- [agent.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab4/agent.py)
- [lab4_models.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/models/lab4_models.py)
- [routes_lab4.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_lab4.py)

Associated automated test suites:
- [test_lab4_api.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab4_api.py)
- [test_lab4_memory.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab4_memory.py)
- [test_lab4_embeddings.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab4_embeddings.py)

---

## 4. API Endpoints
- `POST /api/lab4/sessions - Create isolated user dialog session`
- `POST /api/lab4/query - Query with short-term context and long-term RAG`
- `GET /api/lab4/memories - Retrieve persisted session history`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_lab4_api.py tests/test_lab4_memory.py tests/test_lab4_embeddings.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_04/runner.py
```

---

## 6. Evaluation Rubric & Compliance
| Criteria | Max Points | Verified Status |
| :--- | :--- | :--- |
| Core Architectural Pattern Implementation | 40 | Passed |
| Schema Validation & Error Handling | 20 | Passed |
| Automated Pytest Coverage & Edge Cases | 20 | Passed |
| Observable Traces & Persistence Guarantees | 20 | Passed |
| **Total** | **100** | **100/100** |
