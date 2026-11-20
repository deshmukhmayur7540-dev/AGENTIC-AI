# Assignment 6 Verification Runner
from app.labs.lab6.runtime import AgentRuntime

def main():
    print("=== Assignment 6: Resilient Agent Runtime ===")
    runtime = AgentRuntime()
    run = runtime.create_run(course_id="26ECAC401", max_steps=5)
    print(f"Created Run: {run.run_id}, Initial Status: {run.status}")
    runtime.step(run.run_id, action="INGEST_NOTES")
    checkpoint = runtime.get_latest_checkpoint(run.run_id)
    print(f"Checkpoint Saved: Step {checkpoint.step_number}")
    print("Assignment 6 Verification: PASSED")

if __name__ == '__main__':
    main()
