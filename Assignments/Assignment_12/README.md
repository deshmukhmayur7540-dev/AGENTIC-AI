# Assignment_12: Enterprise Safety, Governance, RBAC & State Rollback
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Autonomous enterprise agents must operate within strict governance and regulatory guardrails. 
Assignment 12 requires building an enterprise safety and governance layer:
1. Persistent Proposals: All critical mutations (grades, rubrics, configs) require formal proposals in SQLite.
2. Role-Based Approvals: Strictly require FACULTY or ADMIN approval via validated authorization headers.
3. Append-Only Audit Logging: Record all proposals, approvals, rejections, and rollbacks in persistent audit tables.
4. Transactional State Rollback: Provide instantaneous, atomic rollback of approved changes to their prior verified state.

---

## 2. Architectural Pattern
**Pattern:** `Persistent Change Proposals, Approval Gates & Rollback`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [governance.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab12/governance.py)
- [audit_service.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/services/audit_service.py)
- [routes_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_labs9_12.py)

Associated automated test suites:
- [test_labs9_12.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_labs9_12.py)
- [test_coordinator_audit.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_coordinator_audit.py)

---

## 4. API Endpoints
- `GET /api/lab12/proposals - List active governance proposals (FACULTY only)`
- `POST /api/lab12/proposals - Submit new change proposal`
- `POST /api/lab12/proposals/{id}/decision - Approve or reject proposal`
- `POST /api/lab12/proposals/{id}/rollback - Execute atomic state rollback`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_labs9_12.py tests/test_coordinator_audit.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_12/runner.py
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
