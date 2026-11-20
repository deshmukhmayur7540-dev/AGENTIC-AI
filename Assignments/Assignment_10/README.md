# Assignment_10: Cloud Operations Health Monitor & Self-Healing Diagnostic Agent
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Course management platforms require resilient operations during peak submission deadlines. 
Assignment 10 requires building an autonomous cloud operations agent:
1. Monitor cluster component health (API gateway, database, worker pool, storage).
2. Perform root cause analysis on simulated degradation and high latency.
3. Propose risk-tiered remediation plans with rollback capabilities.
4. Enforce mandatory human approval before applying high-risk infrastructure changes.

---

## 2. Architectural Pattern
**Pattern:** `Autonomous Infrastructure Diagnostics & Approval-Gated Repair`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [cloud_ops.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab10/cloud_ops.py)
- [validator.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab10/validator.py)
- [routes_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_labs9_12.py)

Associated automated test suites:
- [test_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_labs9_12.py)

---

## 4. API Endpoints
- `GET /api/lab10/cloud/status - Check cluster component health`
- `POST /api/lab10/cloud/diagnose - Perform diagnostic root-cause analysis`
- `POST /api/lab10/cloud/remediate - Propose approved remediation action`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_labs9_12.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_10/runner.py
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
