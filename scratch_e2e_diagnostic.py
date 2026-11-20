import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_e2e_diagnostic():
    report = []
    
    # ----------------------------------------------------
    # Lab 1
    # ----------------------------------------------------
    res = client.post("/api/lab1/clarify", json={"prompt": "Build an AI agent syllabus"})
    report.append(("Lab 1 Clarify", res.status_code == 200 and res.json().get("success") is True, res.json()))
    
    res = client.post("/api/lab1/generate", json={
        "request_id": "req-1",
        "original_prompt": "Build an AI agent syllabus",
        "answers": [
            {"question_id": "q1", "category": "duration", "answer": "14 weeks"},
            {"question_id": "q2", "category": "depth", "answer": "Graduate"}
        ]
    })
    report.append(("Lab 1 Generate", res.status_code == 200 and res.json().get("success") is True, res.json()))
    plan_id = res.json()["data"]["plan"]["plan_id"] if res.status_code == 200 and res.json().get("data") else "dummy"
    
    res = client.post("/api/lab1/revise", json={
        "plan_id": plan_id,
        "revision_prompt": "Increase TA support to 12 hours"
    })
    report.append(("Lab 1 Revise", res.status_code == 200 and res.json().get("success") is True, res.json()))
    
    res = client.get(f"/api/lab1/history/{plan_id}")
    report.append(("Lab 1 History", res.status_code == 200 and res.json().get("success") is True, res.json()))

    # ----------------------------------------------------
    # Lab 2
    # ----------------------------------------------------
    res = client.post("/api/lab2/query", json={"request": "Search 26ECAC401 notes for ReAct"})
    report.append(("Lab 2 Query ReAct", res.status_code == 200 and res.json().get("success") is True, res.json()))

    res = client.post("/api/lab2/query", json={"request": "Show me rubric code quality for Assignment 1 in 26ECAC401"})
    trace_status = res.json().get("data", {}).get("status") if res.status_code == 200 else None
    report.append(("Lab 2 S5 Rubric Error Check", trace_status == "EXECUTION_ERROR", res.json()))

    res = client.post("/api/lab2/query", json={"request": "Audit UNKNOWN999 grading"})
    trace_status = res.json().get("data", {}).get("status") if res.status_code == 200 else None
    report.append(("Lab 2 S6 Unknown Course Check", trace_status == "EXECUTION_ERROR", res.json()))

    res = client.post("/api/lab2/tools/execute", json={"tool_name": "get_ta_policy", "parameters": {"course_id": "26ECAC401"}})
    report.append(("Lab 2 Direct Tool Execute", res.status_code == 200 and res.json().get("success") is True, res.json()))

    # ----------------------------------------------------
    # Lab 3
    # ----------------------------------------------------
    res = client.get("/api/lab3/skills")
    report.append(("Lab 3 List Skills", res.status_code == 200 and res.json().get("success") is True, res.json()))

    # Check what JS calls: /api/lab3/skills/execute
    res = client.post("/api/lab3/skills/execute", json={"skill_name": "course_planning_skill", "parameters": {"target_weeks": 12}})
    report.append(("Lab 3 JS Execute /api/lab3/skills/execute", res.status_code == 200 and res.json().get("success") is True, res.status_code))

    # Check alias names: planning_skill vs course_planning_skill
    res = client.post("/api/lab3/execute", json={"skill_name": "planning_skill", "parameters": {"target_weeks": 12}})
    status = res.json().get("data", {}).get("status") if res.status_code == 200 else None
    report.append(("Lab 3 Alias 'planning_skill'", status == "SUCCESS", res.json()))

    # ----------------------------------------------------
    # Lab 4
    # ----------------------------------------------------
    sid = "session-demo-01"
    # JS calls /api/lab4/sessions/{sid}/turn
    res = client.post(f"/api/lab4/sessions/{sid}/turn", json={"role": "user", "content": "Hello agent"})
    report.append(("Lab 4 JS Append Turn /sessions/{sid}/turn", res.status_code == 200, res.status_code))

    # JS calls /api/lab4/sessions/{sid}
    res = client.get(f"/api/lab4/sessions/{sid}")
    report.append(("Lab 4 JS Get Session /sessions/{sid}", res.status_code == 200, res.status_code))

    # JS calls /api/lab4/sessions/{sid}/scratchpad
    res = client.post(f"/api/lab4/sessions/{sid}/scratchpad", json={"key": "preferred_weeks", "value": 14})
    report.append(("Lab 4 JS Scratchpad /sessions/{sid}/scratchpad", res.status_code == 200, res.status_code))

    # JS calls /api/lab4/query with {"request": "...", "session_id": sid, "course_id": "26ECAC401"}
    res = client.post("/api/lab4/query", json={"request": "What is ReAct?", "session_id": sid, "course_id": "26ECAC401"})
    report.append(("Lab 4 JS Agent Query with 'request' key", res.status_code == 200 and res.json().get("success") is True, res.status_code))

    # ----------------------------------------------------
    # Lab 5
    # ----------------------------------------------------
    res = client.post("/api/lab5/execute", json={
        "source_id": "sqlite_source",
        "operation": "WRITE",
        "resource_path": "assignments",
        "parameters": {"id": "lab_diag", "title": "Diag Lab", "max_points": 100},
        "client_role": "FACULTY"
    })
    report.append(("Lab 5 Faculty Write", res.status_code == 200 and res.json().get("success") is True, res.json()))

    res = client.post("/api/lab5/execute", json={
        "source_id": "sqlite_source",
        "operation": "WRITE",
        "resource_path": "rubrics",
        "parameters": {"id": "bad", "criterion": "Hacked"},
        "client_role": "STUDENT"
    })
    is_blocked = (res.status_code == 403 or (res.status_code == 200 and res.json().get("data", {}).get("success") is False))
    report.append(("Lab 5 Student Write Blocked", is_blocked, res.json()))

    # Delete non-existent record
    res = client.post("/api/lab5/execute", json={
        "source_id": "sqlite_source",
        "operation": "DELETE",
        "resource_path": "assignments",
        "parameters": {"id": "non_existent_id_99999"},
        "client_role": "FACULTY"
    })
    del_ok = res.json().get("data", {}).get("data", {}).get("status") if res.status_code == 200 else None
    report.append(("Lab 5 Delete Non-existent Not Reported Success", del_ok != "RECORD_DELETED", res.json()))

    # ----------------------------------------------------
    # Lab 6
    # ----------------------------------------------------
    # JS calls /api/lab6/start
    res = client.post("/api/lab6/start", json={"task": "Synthesize plan", "budget": {"max_steps": 6}})
    report.append(("Lab 6 JS /api/lab6/start", res.status_code == 200, res.status_code))

    # JS calls /api/lab6/step
    run_id = res.json().get("data", {}).get("run_id") if res.status_code == 200 else "r1"
    res = client.post("/api/lab6/step", json={"run_id": run_id})
    report.append(("Lab 6 JS /api/lab6/step", res.status_code == 200, res.status_code))

    # JS calls /api/lab6/decision without gate_id
    res = client.post("/api/lab6/decision", json={"run_id": run_id, "approved": True})
    report.append(("Lab 6 JS /api/lab6/decision without gate_id", res.status_code == 200, res.status_code))

    # ----------------------------------------------------
    # Lab 7
    # ----------------------------------------------------
    res = client.get("/api/lab7/topology")
    report.append(("Lab 7 Topology", res.status_code == 200, res.status_code))

    res = client.post("/api/lab7/run", json={"user_request": "Create plan", "course_id": "26ECAC401", "simulate_failure": True})
    report.append(("Lab 7 Self Healing Run", res.status_code == 200, res.json().get("data", {}).get("status") if res.status_code == 200 else res.status_code))

    # ----------------------------------------------------
    # Lab 8
    # ----------------------------------------------------
    # JS calls /api/lab8/dispatch with simulate_failure boolean
    res = client.post("/api/lab8/dispatch", json={"course_id": "26ECAC401", "simulate_failure": True})
    report.append(("Lab 8 JS Dispatch with boolean simulate_failure", res.status_code == 200, res.status_code))

    # Unknown course
    res = client.post("/api/lab8/dispatch", json={"course_id": "UNKNOWN_COURSE_999"})
    c_status = res.json().get("data", {}).get("status") if res.status_code == 200 else None
    report.append(("Lab 8 Unknown Course Handling", res.status_code != 200 or c_status != "MERGED", res.json()))

    for name, passed, detail in report:
        print(f"[{'PASS' if passed else 'FAIL'}] {name} -> {str(detail)[:120]}")

if __name__ == "__main__":
    run_e2e_diagnostic()
