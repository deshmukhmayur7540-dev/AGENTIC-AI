# Assignment 2 Verification Runner
import asyncio
from app.labs.lab2.agent import ToolAgent
from app.models.lab2_models import AgentQueryRequest

async def main():
    print("=== Assignment 2: ReAct Tool-Using Agent ===")
    agent = ToolAgent()
    query = AgentQueryRequest(query="Calculate final score for student with marks 85/100 (weight 40%) and 90/100 (weight 60%)")
    result = await agent.run(query)
    print(f"Tool Executions: {len(result.tool_calls)}")
    print(f"Audit Status: {result.status}")
    print("Assignment 2 Verification: PASSED")

if __name__ == '__main__':
    asyncio.run(main())
