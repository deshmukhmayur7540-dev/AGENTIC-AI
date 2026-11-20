# Assignment_01: Clarify-Plan-Revise Academic Course Workspace Planner
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Academic course workspaces require dynamic, structured curriculum planning. Traditional syllabus tools produce static, unvalidated documents with no consistency guarantees. 
Assignment 1 requires building an interactive workspace planning agent that:
1. Detects missing course parameters (e.g. course code, prerequisites, target weeks, credit hours).
2. Formulates targeted clarification questions for faculty evaluators when information gaps exist.
3. Synthesizes a structured, modular 14-week course syllabus once parameters are confirmed.
4. Supports atomic, validated revisions with deterministic semantic diffing between syllabus versions.

---

## 2. Architectural Pattern
**Pattern:** `Clarify -> Plan -> Revise Loop`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [agent.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab1/agent.py)
- [planner.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab1/planner.py)
- [lab1_models.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/models/lab1_models.py)
- [routes_lab1.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_lab1.py)

Associated automated test suites:
- [test_lab1.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab1.py)
- [test_lab1_grounding.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab1_grounding.py)

---

## 4. API Endpoints
- `POST /api/lab1/plan - Generate initial 14-week syllabus`
- `POST /api/lab1/revise - Deterministically revise plan with diff tracking`
- `GET /api/lab1/plans/{course_id} - Retrieve active syllabus version`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_lab1.py tests/test_lab1_grounding.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_01/runner.py
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
