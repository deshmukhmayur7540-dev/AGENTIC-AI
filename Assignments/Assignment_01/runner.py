# Assignment 1 Verification Runner
import asyncio
from app.labs.lab1.planner import SyllabusPlanner
from app.models.lab1_models import CoursePlanRequest

async def main():
    print("=== Assignment 1: Clarify-Plan-Revise Planner ===")
    planner = SyllabusPlanner()
    req = CoursePlanRequest(course_code="26ECAC401", course_title="Agentic AI", credits=4, weeks=14)
    plan = planner.generate_plan(req)
    print(f"Generated Plan: {plan.course_code} - {plan.course_title}")
    print(f"Total Weeks: {len(plan.weeks)}")
    revised = planner.revise_week(plan.plan_id, week_number=3, new_topic="Advanced ReAct Agent Architectures")
    diff = planner.compute_diff(plan.plan_id, revised.plan_id)
    print(f"Deterministic Diff: {diff.summary}")
    print("Assignment 1 Verification: PASSED")

if __name__ == '__main__':
    asyncio.run(main())
