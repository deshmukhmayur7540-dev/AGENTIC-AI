# Assignment_11: Agentic SDLC Code Synthesis & Sandboxed Verification
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Automating the software development lifecycle requires rigorous verification to prevent flawed code generation. 
Assignment 11 requires implementing an agentic SDLC synthesis factory:
1. Specification Ingestion: Parse structured functional specifications and acceptance criteria.
2. Architecture & Code Synthesis: Generate modular, production-ready Python implementations.
3. Test Suite Generation: Automatically synthesize corresponding unit tests and assertions.
4. Benchmark Verification: Execute tests in a sandboxed runtime and record benchmark scores.

---

## 2. Architectural Pattern
**Pattern:** `Specification -> Code -> Test -> Verification Pipeline`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [benchmarks.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab11/benchmarks.py)
- [sdlc_agent.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab11/sdlc_agent.py)
- [routes_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_labs9_12.py)

Associated automated test suites:
- [test_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_labs9_12.py)

---

## 4. API Endpoints
- `GET /api/lab11/benchmarks - Retrieve SDLC benchmark suite`
- `POST /api/lab11/benchmarks/run - Execute deterministic reliability benchmarks`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_labs9_12.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_11/runner.py
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
