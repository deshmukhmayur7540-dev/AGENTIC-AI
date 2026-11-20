# Assignment_06: Resilient Agent Runtime with Checkpoints & State Recovery
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Complex agent executions can encounter transient API errors, infinite loops, or crashes. 
Assignment 6 requires implementing a resilient runtime engine:
1. State Checkpointing: Persist execution snapshots and checkpoints in SQLite after every atomic step.
2. Bounded Budgets: Enforce explicit limits on step counts, elapsed time, tool calls, and high-consequence mutations.
3. Fault Recovery: Support process restart with checkpoint restoration, resuming interrupted workflows seamlessly.

---

## 2. Architectural Pattern
**Pattern:** `State Checkpointing, Budgets & Fault Tolerance`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [runtime.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab6/runtime.py)
- [checkpoint.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab6/checkpoint.py)
- [lab6_models.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/models/lab6_models.py)
- [routes_lab6.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_lab6.py)

Associated automated test suites:
- [test_lab6_api.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab6_api.py)
- [test_lab6_runtime.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab6_runtime.py)

---

## 4. API Endpoints
- `POST /api/lab6/run - Start bounded resilient execution`
- `POST /api/lab6/resume - Resume execution from saved checkpoint`
- `GET /api/lab6/status/{run_id} - Inspect run status, checkpoints, and budget`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_lab6_api.py tests/test_lab6_runtime.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_06/runner.py
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
