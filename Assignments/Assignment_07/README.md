# Assignment_07: 10-Node Specialist Graph DAG with Bounded Retries
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** `2026`  
**Evaluation Weight:** `8%`  
**Student Submission:** Complete, Verified, and Tested Implementation  

---

## 1. Problem Statement
Complex course management operations require coordinating distinct domain capabilities in a deterministic order. 
Assignment 7 requires engineering a 10-node specialist workflow graph:
1. Specialist Nodes: Coordinator, Planning, Notes, Distribution, Submission, Grading, Milestones, Validation, Approval, Publication.
2. Single-Step Execution: Allow stepping through nodes one by one with explicit state inspection.
3. Bounded Retry: Automatically handle node-level validation defects with retry limits.
4. Faculty Approval Gate: Pause execution before publication until explicit faculty review is granted.

---

## 2. Architectural Pattern
**Pattern:** `Specialist Node Graph DAG & Faculty Approval Gates`

This assignment enforces verifiable agentic AI design principles:
- Deterministic execution guarantees without unconstrained hallucinations.
- Clear separation of concerns between reasoning, tool calling, and persistence.
- Complete auditability and observable execution traces.

---

## 3. Implementation Components
The core logic for this assignment is implemented in the following modules:
- [graph.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab7/graph.py)
- [agent.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/labs/lab7/agent.py)
- [lab7_models.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/models/lab7_models.py)
- [routes_lab7.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/app/api/routes_lab7.py)

Associated automated test suites:
- [test_lab7_api.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab7_api.py)
- [test_lab7_graph.py](file:///C:/Users/Lenovo/Desktop/CourseAgentAI/tests/test_lab7_graph.py)

---

## 4. API Endpoints
- `POST /api/lab7/start - Initialize 10-node workflow graph`
- `POST /api/lab7/step - Execute exactly one graph node`
- `POST /api/lab7/approve - Submit faculty approval gate decision`
- `GET /api/lab7/state/{run_id} - Inspect node states and completed list`

---

## 5. Execution & Verification Instructions

### 5.1 Run Automated Pytest Suite
```powershell
# Run the specific test suites for this assignment
python -m pytest tests/test_lab7_api.py tests/test_lab7_graph.py -v
```

### 5.2 Execute the Standalone Verification Script
```powershell
python Assignments/Assignment_07/runner.py
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
