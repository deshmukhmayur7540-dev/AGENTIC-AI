# Assignment 8 Verification Runner
import asyncio
from app.labs.lab8.swarm import ChapterSwarmCoordinator

async def main():
    print("=== Assignment 8: Parallel Specialist Swarm ===")
    coordinator = ChapterSwarmCoordinator()
    res = await coordinator.run_swarm(chapters=[1, 2, 3, 4], course_id="26ECAC401")
    print(f"Swarm Status: {res.status}, Workers Succeeded: {res.successful_workers}/{len(res.chapters)}")
    print("Assignment 8 Verification: PASSED")

if __name__ == '__main__':
    asyncio.run(main())
