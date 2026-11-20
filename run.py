"""CourseAgentAI entrypoint launcher."""

import uvicorn
from config import settings

if __name__ == "__main__":
    print(f"==================================================")
    print(f"  Starting {settings.app_name} (v{settings.app_version})")
    print(f"  Workspace Planner & Tool/Agent Auditor")
    print(f"  Access Dashboard at: http://{settings.host}:{settings.port}")
    print(f"==================================================")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
