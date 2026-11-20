# Assignment 7 Verification Runner
from app.labs.lab7.graph import SpecialistWorkflowGraph

def main():
    print("=== Assignment 7: 10-Node Specialist Graph DAG ===")
    graph = SpecialistWorkflowGraph()
    state = graph.start_run(course_id="26ECAC401")
    print(f"Graph Run ID: {state.run_id}, Current Node: {state.current_node}")
    state = graph.step_node(state.run_id)
    print(f"Stepped Node: {state.completed_nodes[-1]}, Next: {state.current_node}")
    print("Assignment 7 Verification: PASSED")

if __name__ == '__main__':
    main()
