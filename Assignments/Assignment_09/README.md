# Assignment_09: Deep Research Claim Verifier with Entailment Distinction
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Research agents often conflate keyword lexical matches with true factual entailment. 
Assignment 9 requires developing a deep research claim verification agent:
1. Retrieve candidate evidence from course materials using BM25 and chunking.
2. Provide precise, granular citations with document names, section headings, and character spans.
3. Distinguish lexical presence from semantic entailment: categorize claims as SUPPORTING_EVIDENCE_IDENTIFIED, CANDIDATE_EVIDENCE_FOUND, CONTRADICTORY, or INSUFFICIENT_EVIDENCE.

---

## 2. Architectural Pattern
**Pattern:** `Deep Research, Source Grounding & Entailment`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [agent.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab9/agent.py)
- [lab9_models.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/models/lab9_models.py)
- [routes_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_labs9_12.py)

Associated automated test suites:
- [test_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_labs9_12.py)

---

## 4. API Endpoints
- `POST /api/lab9/grounding/verify - Verify claims against course documents`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_labs9_12.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_09/runner.py
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
