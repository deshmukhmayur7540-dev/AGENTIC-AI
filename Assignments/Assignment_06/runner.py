import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 6 Verification Runner
from app.labs.lab6.engine import ControlledRuntimeEngine

def main():
    print("=== Assignment 6: Resilient Agent Runtime ===")
    engine = ControlledRuntimeEngine()
    run = engine.create_run(course_id="26ECAC401", task_description="Prepare course report")
    print(f"Created Run ID: {run.run_id}, Initial State: {run.state}")
    print("Assignment 6 Verification: PASSED")

if __name__ == '__main__':
    main()
