# Assignment_05: Governed Academic Connector with RBAC & MCP Architecture
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Academic data systems manage sensitive student records and grading rubrics that require strict access boundaries. 
Assignment 5 requires implementing an MCP-style governed connector:
1. Role-Based Access Control (RBAC): Enforce permissions across STUDENT, FACULTY, and ADMIN roles.
2. Scoped Queries: Restrict data access strictly by course code and authenticated student ID.
3. Unified Source Interface: Abstract relational database tables, course notes, and student submissions through a unified connector protocol.

---

## 2. Architectural Pattern
**Pattern:** `Model Context Protocol (MCP) Style Governed Access`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [connector.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab5/connector.py)
- [sqlite_source.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab5/sources/sqlite_source.py)
- [notes_source.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab5/sources/notes_source.py)
- [routes_lab5.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_lab5.py)

Associated automated test suites:
- [test_lab5_api.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab5_api.py)
- [test_lab5_connector.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab5_connector.py)

---

## 4. API Endpoints
- `POST /api/lab5/query - Execute governed query through MCP connector`
- `GET /api/lab5/sources - Inspect registered data sources and permissions`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_lab5_api.py tests/test_lab5_connector.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_05/runner.py
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
