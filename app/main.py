"""FastAPI application factory, middleware, and route mounting for CourseAgentAI."""

import os
import math
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder

from config import settings
from app.data.db import init_database
from app.auth import csrf_rejection
from app.labs.lab5.governed_connector import governed_connector
from app.labs.lab12.governance import governed_change_store
from app.api.routes_lab1 import router as lab1_router
from app.api.routes_lab2 import router as lab2_router
from app.api.routes_lab3 import router as lab3_router
from app.api.routes_lab4 import router as lab4_router
from app.api.routes_lab5 import router as lab5_router
from app.api.routes_lab6 import router as lab6_router
from app.api.routes_lab7 import router as lab7_router
from app.api.routes_lab8 import router as lab8_router
from app.api.routes_labs9_12 import router as labs9_12_router
from app.api.routes_submissions import router as submissions_router
from app.api.routes_system import router as system_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_course_materials import router as course_materials_router
from app.api.routes_projects import router as projects_router
from app.api.routes_similarity import router as similarity_router
from app.api.routes_auth import router as auth_router
from app.api.routes_notifications import router as notifications_router
from app.api.routes_capstone import router as capstone_router
from app.models.common import APIEnvelope, ErrorDetail

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_database()
    governed_connector.initialize()
    governed_change_store.initialize()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_cookie_csrf(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        rejection = csrf_rejection(request)
    else:
        rejection = None
    if rejection is not None:
        return rejection
    return await call_next(request)


# Mount API Routers
app.include_router(lab1_router)
app.include_router(lab2_router)
app.include_router(lab3_router)
app.include_router(lab4_router)
app.include_router(lab5_router)
app.include_router(lab6_router)
app.include_router(lab7_router)
app.include_router(lab8_router)
app.include_router(labs9_12_router)
app.include_router(submissions_router)
app.include_router(system_router)
app.include_router(knowledge_router)
app.include_router(course_materials_router)
app.include_router(projects_router)
app.include_router(similarity_router)
app.include_router(auth_router)
app.include_router(notifications_router)
app.include_router(capstone_router)


def _json_safe_validation_errors(value):
    if isinstance(value, float) and not math.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {key: _json_safe_validation_errors(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_validation_errors(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Keep invalid non-finite numbers from breaking the JSON error response."""
    return JSONResponse(
        status_code=422,
        content={"detail": _json_safe_validation_errors(jsonable_encoder(exc.errors()))},
    )


@app.get("/api/health", include_in_schema=True)
async def health_check():
    """Process liveness check. Success here does not prove every lab works."""
    knowledge_root = Path(settings.knowledge_root)
    db_path = Path(settings.database_path)
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "course_code": "26ECAC401",
        "course_name": "Agentic AI",
        "database_exists": db_path.exists(),
        "knowledge_root_exists": knowledge_root.exists(),
        "llm_provider": settings.llm_provider,
    }

# Mount Static Files
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the Single Page Application dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={"message": f"{settings.app_name} API is running. UI not found at /static/index.html"},
        status_code=200,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log unexpected failures and return a sanitized standardized APIEnvelope."""
    logger.exception("Unhandled exception while processing %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content=APIEnvelope(
            success=False,
            data=None,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. Please try again later.",
            ),
            trace_id="global-error-trace",
        ).model_dump(mode="json", exclude={"error": {"target", "details"}}),
    )
