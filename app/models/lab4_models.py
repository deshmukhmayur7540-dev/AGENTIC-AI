"""Pydantic schemas and contracts for Lab 4: Memory & Retrieval."""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class DialogueTurn(BaseModel):
    """Ephemeral short-term conversational turn."""
    turn_id: str
    role: str = Field(description="Role: user, agent, or system")
    content: str = Field(description="Message or prompt content")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    """Short-term session state with a bounded lifetime.
    
    Contains transient user requests, active dialogue turns, clarification answers,
    and scratchpad variables for the current session. It is persisted only for recovery
    and is never automatically promoted to long-term knowledge.
    """
    session_id: str
    user_id: str = "faculty_reviewer"
    course_id: str = "26ECAC401"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    current_request: Optional[str] = None
    active_plan_id: Optional[str] = None
    clarification_answers: list[dict[str, Any]] = Field(default_factory=list)
    scratchpad: dict[str, Any] = Field(default_factory=dict)
    dialogue_turns: list[DialogueTurn] = Field(default_factory=list)
    memory_layer: str = "SHORT_TERM_SESSION_STATE"


class RetrievedChunk(BaseModel):
    """Long-term knowledge chunk retrieved with complete source provenance."""
    chunk_id: str
    chapter: int
    topic: str
    matched_text: str
    source: str
    source_document: str
    source_location: Optional[str] = None
    category: Optional[str] = None
    lab: Optional[int] = None
    folder_path: Optional[str] = None
    material_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0


class LongTermRetrievalQuery(BaseModel):
    """Query model for searching the long-term course knowledge base."""
    query: str = Field(description="Search terms or question")
    course_id: str = Field(default="26ECAC401", description="Target course ID")
    chapter: Optional[int] = Field(default=None, ge=1, le=4, description="Optional chapter filter (1-4)")
    tags: Optional[list[str]] = Field(default=None, description="Optional tag filters")
    top_k: int = Field(default=5, ge=1, le=20, description="Max matching chunks to return")


class LongTermRetrievalResult(BaseModel):
    """Result returned from querying long-term stored course knowledge."""
    query: str
    course_id: str
    match_count: int
    matches: list[RetrievedChunk]
    memory_layer: str = "LONG_TERM_KNOWLEDGE_STORE"
    source: str
    searched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LongTermMemoryCreateRequest(BaseModel):
    """Explicitly saved long-term memory; session dialogue is never saved implicitly."""

    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=12000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title", "content")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must contain non-whitespace text.")
        return value


class SimilarMemoryQuery(BaseModel):
    """Owner- and course-scoped lexical or semantic query for explicitly saved items."""

    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    top_k: int = Field(default=5, ge=1, le=20)
    retrieval_mode: Literal["lexical", "semantic"] = "lexical"

    @field_validator("query")
    @classmethod
    def require_non_whitespace_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must contain non-whitespace text.")
        return value


class SimilarSubmissionQuery(BaseModel):
    """Course- and student-scoped retrieval over prior submission metadata."""

    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)
    top_k: int = Field(default=5, ge=1, le=20)
    retrieval_mode: Literal["lexical", "semantic"] = "lexical"

    @field_validator("query")
    @classmethod
    def require_non_whitespace_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must contain non-whitespace text.")
        return value


from pydantic import model_validator


class MemoryAgentQueryRequest(BaseModel):
    """Request model for sending a query to the memory-aware agent."""
    session_id: Optional[str] = None
    query: Optional[str] = Field(default=None, description="User prompt or question")
    request: Optional[str] = Field(default=None, description="User prompt or question alias")
    course_id: str = Field(default="26ECAC401", description="Course context")
    chapter_filter: Optional[int] = Field(default=None, ge=1, le=4)

    @model_validator(mode="before")
    @classmethod
    def map_request_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q = data.get("query") or data.get("request") or ""
            data["query"] = q
            data["request"] = q
        return data
