"""Live end-to-end API test for CourseAgentAI."""
import urllib.request
import json


BASE = "http://127.0.0.1:8000"


def post(endpoint, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + endpoint, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get(endpoint):
    with urllib.request.urlopen(BASE + endpoint) as r:
        return json.loads(r.read())


# ===== LAB 1 =====
print("=== LAB 1 ===")
clarify = post("/api/lab1/clarify", {"raw_prompt": "Create Agentic AI course 26ECAC401", "course_title_hint": "26ECAC401"})
questions = clarify["data"]["questions"]
print(f"Clarify OK: {len(questions)} questions")

answers = [{**q, "selected_option": q["suggested_options"][0] if q["suggested_options"] else None, "custom_response": None} for q in questions]
gen = post("/api/lab1/generate", {"request_id": "req-test-123", "original_prompt": "Create Agentic AI course 26ECAC401", "course_code_hint": "26ECAC401", "answers": answers})
plan = gen["data"]
pid = plan["plan_id"]
print(f"Generate OK: plan_id={pid}, version={plan['version']}, course={plan['course_code']}")
print(f"  Materials: {len(plan['materials_and_notes'])}, Assignments: {len(plan['assignments'])}, Grades: {len(plan['grade_breakdown'])}")

rev = post("/api/lab1/revise", {"plan_id": pid, "revision_prompt": "Add 2 more programming labs and reduce total to 10 weeks"})
rev_data = rev["data"]
print(f"Revise OK: v{rev_data['previous_version']} -> v{rev_data['current_version']}, diffs: {len(rev_data['structured_diffs'])}")

hist = get(f"/api/lab1/history/{pid}")
print(f"History OK: versions={len(hist['data']['versions'])}, revisions={len(hist['data']['revisions'])}")

# ===== LAB 2 =====
print("\n=== LAB 2 ===")
q2 = post("/api/lab2/query", {"query": "Audit 26ECAC401 grading breakdown - do weights sum to 100?", "course_id": "26ECAC401"})
trace = q2["data"]
print(f"Query OK: status={trace.get('status')}, steps={len(trace.get('steps', []))}, verified_facts={trace.get('verified_facts_count', 0)}")

tools = get("/api/lab2/tools")
print(f"Tools OK: {len(tools['data'])} tools registered")

# Direct tool execution
tool_exec = post("/api/lab2/tools/execute", {"tool_name": "read_course_syllabus", "parameters": {"course_id": "26ECAC401"}})
print(f"Tool Execute OK: {tool_exec['data']['status']}")

# ===== LAB 3 =====
print("\n=== LAB 3 ===")
skills = get("/api/lab3/skills")
print(f"Skills OK: {len(skills['data'])} skills")

skill_exec = post("/api/lab3/execute", {"skill_name": "course_planning_skill", "parameters": {"course_code": "26ECAC401", "course_name": "Agentic AI", "target_weeks": 12, "focus_chapters": [1, 2, 3, 4]}})
print(f"Skill Execute OK: status={skill_exec['data'].get('status')}")

# ===== LAB 4 =====
print("\n=== LAB 4 ===")
sess = post("/api/lab4/session/create", {"session_id": "test-sess-001", "course_id": "26ECAC401"})
print(f"Session Create OK: id={sess['data']['session_id']}")

rag = post("/api/lab4/retrieval/search", {"query": "Plan-Act-Observe-Revise", "course_id": "26ECAC401", "chapter_filter": None, "top_k": 3})
print(f"RAG Search OK: matches={rag['data']['total_matches']}")

q4 = post("/api/lab4/query", {"query": "What is LangGraph?", "session_id": "test-sess-001", "course_id": "26ECAC401"})
print(f"Agent Query OK: answer_len={len(q4['data'].get('answer', ''))}")

# ===== LAB 5 =====
print("\n=== LAB 5 ===")
sources = get("/api/lab5/sources")
print(f"Sources OK: {len(sources['data'])} sources")

exec5 = post("/api/lab5/execute", {"source_id": "notes_source", "operation": "SEARCH", "parameters": {"query": "autonomous agents", "course_id": "26ECAC401"}, "client_role": "FACULTY"})
print(f"Connector Execute OK: status={exec5['data'].get('status')}, matches={exec5['data'].get('data', {}).get('total_matches', 'N/A')}")

# Student write blocked
exec5b = post("/api/lab5/execute", {"source_id": "sqlite_source", "operation": "WRITE", "parameters": {"table": "rubrics", "id": "x"}, "client_role": "STUDENT"})
print(f"Student Write Blocked: status={exec5b['data'].get('status')}")

# ===== LAB 6 =====
print("\n=== LAB 6 ===")
run6 = post("/api/lab6/run", {"task": "Compile 26ECAC401 course workspace", "budget": {"max_steps": 10, "max_tool_calls": 20, "max_duration_seconds": 120}})
run_id = run6["data"]["run_id"]
print(f"Run Start OK: run_id={run_id}, status={run6['data']['status']}")

# Step through
for i in range(5):
    step = post(f"/api/lab6/run/{run_id}/step", {})
    if not step["success"]:
        print(f"  Step {i+1} failed: {step['error']}")
        break
    print(f"  Step {i+1}: status={step['data']['status']}")
    if step["data"]["status"] in ("WAITING_APPROVAL", "COMPLETED", "BUDGET_EXCEEDED"):
        break

# ===== LAB 7 =====
print("\n=== LAB 7 ===")
topo = get("/api/lab7/topology")
print(f"Topology OK: nodes={len(topo['data']['nodes'])}, edges={len(topo['data']['edges'])}")

run7 = post("/api/lab7/run", {"user_request": "Assemble 26ECAC401 workspace", "course_id": "26ECAC401", "target_weeks": 12, "simulate_validation_failure": False})
run7_id = run7["data"]["run_id"]
print(f"Graph Run OK: run_id={run7_id}, status={run7['data']['status']}, nodes_executed={len(run7['data'].get('execution_history', []))}")

# Approve if waiting
if run7["data"]["status"] == "WAITING_APPROVAL":
    approve = post(f"/api/lab7/approve/{run7_id}", {"approved": True, "comments": "Looks good", "decision_by": "test_faculty"})
    print(f"Approval OK: status={approve['data']['status']}")

# ===== LAB 8 =====
print("\n=== LAB 8 ===")
swarm = post("/api/lab8/dispatch", {"course_id": "26ECAC401", "target_chapters": [1, 2, 3, 4], "simulate_worker_failure": None})
sw_data = swarm["data"]
print(f"Swarm OK: run_id={sw_data.get('swarm_run_id')}, status={sw_data.get('swarm_status')}, workers={sw_data.get('total_workers')}")
print(f"  Succeeded={sw_data.get('succeeded_count')}, Failed={sw_data.get('failed_count')}, Duration={sw_data.get('total_duration_ms', 0):.0f}ms")

# Failure scenario
swarm_fail = post("/api/lab8/dispatch", {"course_id": "26ECAC401", "target_chapters": [1, 2, 3, 4], "simulate_worker_failure": 3})
sf = swarm_fail["data"]
print(f"Swarm Partial Fail OK: succeeded={sf.get('succeeded_count')}, failed={sf.get('failed_count')}")

print("\n=== ALL TESTS COMPLETE ===")
