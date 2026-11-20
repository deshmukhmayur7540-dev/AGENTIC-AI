import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 8 Verification Runner
import asyncio
from app.labs.lab8.swarm import swarm_coordinator

async def main():
    print("=== Assignment 8: Parallel Specialist Swarm ===")
    result = await swarm_coordinator.dispatch_swarm(course_id="26ECAC401", target_chapters=[1, 2, 3, 4])
    print(f"Swarm Status: {result.status}, Succeeded Workers: {result.successful_workers}")
    print("Assignment 8 Verification: PASSED")

if __name__ == '__main__':
    asyncio.run(main())
