"""CourseAgentAI Configuration Module."""

import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseModel):
    """Application settings and environment configurations."""
    app_name: str = "CourseAgentAI"
    app_version: str = "1.1.0"
    app_description: str = "Agentic AI Course Workspace & Operations System"
    debug: bool = os.getenv("COURSEAGENTAI_DEBUG", "true").lower() in {"1", "true", "yes"}
    environment: str = os.getenv("COURSEAGENTAI_ENV", "development").lower()
    auth_cookie_secure: bool = (
        os.getenv("COURSEAGENTAI_ENV", "development").lower() == "production"
        or os.getenv("COURSEAGENTAI_AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
    )
    auth_session_seconds: int = Field(default=int(os.getenv("COURSEAGENTAI_AUTH_SESSION_SECONDS", "28800")), gt=0)
    host: str = os.getenv("COURSEAGENTAI_HOST", "127.0.0.1")
    port: int = int(os.getenv("COURSEAGENTAI_PORT", "8000"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("COURSEAGENTAI_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
        if origin.strip()
    ]
    project_root: str = str(PROJECT_ROOT)
    knowledge_root: str = os.getenv(
        "KNOWLEDGE_ROOT",
        str(PROJECT_ROOT / "knowledge"),
    )
    database_path: str = os.getenv(
        "DATABASE_PATH",
        str(PROJECT_ROOT / "app" / "data" / "governed_academic.db"),
    )
    lab4_embedding_model_path: str = os.getenv(
        "COURSEAGENTAI_LAB4_EMBEDDING_MODEL_PATH",
        str(PROJECT_ROOT / "models" / "lab4" / "all-MiniLM-L6-v2"),
    )
    lab4_embedding_similarity_threshold: float = Field(
        default=float(os.getenv("COURSEAGENTAI_LAB4_EMBEDDING_SIMILARITY_THRESHOLD", "0.25")),
        ge=-1.0,
        le=1.0,
    )
    course_materials_root: str = os.getenv(
        "COURSEAGENTAI_MATERIALS_ROOT",
        str(Path(os.getenv(
            "DATABASE_PATH",
            str(PROJECT_ROOT / "app" / "data" / "governed_academic.db"),
        )).parent / "course_materials"),
    )
    course_material_max_upload_bytes: int = Field(
        default=int(os.getenv("COURSEAGENTAI_MATERIAL_MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))),
        gt=0,
    )
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "deterministic")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    @field_validator("cors_origins")
    @classmethod
    def require_explicit_cors_origins(cls, origins: list[str]) -> list[str]:
        if "*" in origins:
            raise ValueError("COURSEAGENTAI_CORS_ORIGINS must list explicit trusted origins; '*' is not allowed.")
        return origins


settings = Settings()
