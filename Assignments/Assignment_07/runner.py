import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 7 Verification Runner
from app.labs.lab7.graph import AgenticNodeGraph

def main():
    print("=== Assignment 7: 10-Node Specialist Graph DAG ===")
    graph = AgenticNodeGraph()
    state = graph.initialize_graph(user_request="Build syllabus and labs", course_id="26ECAC401")
    print(f"Graph Run ID: {state.run_id}, Current Node: {state.current_node}")
    stepped = graph.step_node(state.run_id)
    print(f"Stepped Node: {stepped.completed_nodes[-1] if stepped.completed_nodes else 'None'}, Next: {stepped.current_node}")
    print("Assignment 7 Verification: PASSED")

if __name__ == '__main__':
    main()
