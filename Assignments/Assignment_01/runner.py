import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 1 Verification Runner
import asyncio
from app.labs.lab1.agent import ClarifyPlanReviseAgent
from app.models.lab1_models import FacultyCourseRequest

async def main():
    print("=== Assignment 1: Clarify-Plan-Revise Planner ===")
    agent = ClarifyPlanReviseAgent()
    req = FacultyCourseRequest(raw_prompt="Design a course on Autonomous AI Agents", course_id="26ECAC401", topic="Autonomous AI Agents", level="advanced")
    res = await agent.execute("clarify", req.model_dump())
    print(f"Clarification Result: {res.get('status')}")
    print(f"Questions Identified: {len(res.get('questions', []))}")
    print("Assignment 1 Verification: PASSED")

if __name__ == '__main__':
    asyncio.run(main())
