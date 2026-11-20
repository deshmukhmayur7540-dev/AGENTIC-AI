"""API routers package for CourseAgentAI."""

from app.api.routes_lab1 import router as lab1_router
from app.api.routes_lab2 import router as lab2_router
from app.api.routes_system import router as system_router

__all__ = ["lab1_router", "lab2_router", "system_router"]
