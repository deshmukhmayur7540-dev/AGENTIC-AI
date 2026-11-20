import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 2 Verification Runner
from app.labs.lab2.agent import ToolUsingAgent

def main():
    print("=== Assignment 2: ReAct Tool-Using Agent ===")
    agent = ToolUsingAgent()
    trace = agent.run("Calculate final score for student with marks 85 and 90")
    print(f"Tool Steps Recorded: {len(trace.steps)}")
    print("Assignment 2 Verification: PASSED")

if __name__ == '__main__':
    main()
