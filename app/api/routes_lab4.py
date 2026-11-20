"""FastAPI routes for Lab 4: Memory & Retrieval Architecture."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from app.auth import AuthenticatedUser, get_current_user, require_course_access
from app.core.coordinator import coordinator
from app.labs.lab4.knowledge_store import long_term_store
from app.labs.lab4.session_store import short_term_store
from app.models.common import APIEnvelope
from app.models.lab4_models import (
    LongTermMemoryCreateRequest,
    LongTermRetrievalQuery,
    MemoryAgentQueryRequest,
    SimilarMemoryQuery,
    SimilarSubmissionQuery,
)

router = APIRouter(prefix="/api/lab4", tags=["Lab 4: Memory & Retrieval"])


def _owned_session(session_id: str, user: AuthenticatedUser):
    session = short_term_store.get_session(session_id)
    if session is None or session.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Session not found.")
    require_course_access(user, session.course_id)
    return session


LAB4_EVALUATOR_SCENARIOS = [
    {
        "scenario_id": "lab4-ch1-loop",
        "title": "Scenario 1: Chapter 1 Plan-Act-Observe-Revise Retrieval",
        "category": "Long-Term Knowledge Retrieval",
        "query": "What is the Plan-Act-Observe-Revise loop?",
        "expected_chapter": 1,
        "description": "Searches long-term indexed notes and returns Chapter 1 autonomous agent loop evidence.",
    },
    {
        "scenario_id": "lab4-ch2-langchain-tools",
        "title": "Scenario 2: Chapter 2 Tool Integration & Function Calling",
        "category": "Long-Term Knowledge Retrieval",
        "query": "What is LangChain tool integration and typed function calling?",
        "expected_chapter": 2,
        "description": "Searches long-term indexed notes and returns Chapter 2 tool integration evidence.",
    },
    {
        "scenario_id": "lab4-ch3-langgraph",
        "title": "Scenario 3: Chapter 3 LangGraph & Multi-Agent Orchestration",
        "category": "Long-Term Knowledge Retrieval",
        "query": "What is LangGraph and multi-agent orchestration?",
        "expected_chapter": 3,
        "description": "Searches long-term indexed notes and returns Chapter 3 multi-agent collaboration evidence.",
    },
    {
        "scenario_id": "lab4-ch4-safety",
        "title": "Scenario 4: Chapter 4 Safety Guardrails & Approval Gates",
        "category": "Long-Term Knowledge Retrieval",
        "query": "What are approval gates and audit logs in agent governance?",
        "expected_chapter": 4,
        "description": "Searches long-term indexed notes and returns Chapter 4 deployment and safety evidence.",
    },
    {
        "scenario_id": "lab4-anti-hallucination",
        "title": "Scenario 5: Anti-Hallucination on Unknown Concept",
        "category": "Defensive Retrieval",
        "query": "Explain quantum gravity and medieval alchemy in Agentic AI",
        "expected_chapter": None,
        "description": "Verifies that unestablished topics return 0 matches with zero hallucination.",
    },
    {
        "scenario_id": "lab4-session-turns",
        "title": "Scenario 6: Short-Term Conversational Memory Tracking",
        "category": "Short-Term Session Memory",
        "query": "Remember that I prefer 12-week course pacing with 4 programming labs.",
        "expected_chapter": None,
        "description": "Demonstrates short-term session state tracking across multi-turn interactions.",
    },
]


@router.post("/session/create", response_model=APIEnvelope[dict[str, Any]])
@router.post("/sessions/create", response_model=APIEnvelope[dict[str, Any]])
async def create_session(
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new short-term session state."""
    sid = payload.get("session_id")
    course_id = payload.get("course_id", "26ECAC401")
    require_course_access(user, course_id)
    if sid:
        existing = short_term_store.get_session(sid)
        if existing:
            if existing.user_id != user.user_id:
                raise HTTPException(status_code=404, detail="Session not found.")
            raise HTTPException(status_code=409, detail="Session already exists.")
    try:
        session = short_term_store.create_session(
            session_id=sid,
            user_id=user.user_id,
            course_id=course_id,
        )
    except ValueError:
        existing = short_term_store.get_session(sid)
        if existing is None or existing.user_id != user.user_id:
            raise HTTPException(status_code=404, detail="Session not found.")
        raise HTTPException(status_code=409, detail="Session already exists.")
    return APIEnvelope(
        success=True,
        data=session.model_dump(),
        error=None,
        trace_id=f"sess-create-{session.session_id}",
    )


@router.get("/session/{session_id}", response_model=APIEnvelope[dict[str, Any]])
@router.get("/sessions/{session_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_session(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve active session state including dialogue turns and scratchpad."""
    session = _owned_session(session_id, user)
    return APIEnvelope(
        success=True,
        data={"status": "SUCCESS", "session": session.model_dump(), **session.model_dump()},
        error=None,
        trace_id=f"sess-get-{session_id}",
    )


@router.post("/session/{session_id}/turn", response_model=APIEnvelope[dict[str, Any]])
@router.post("/sessions/{session_id}/turn", response_model=APIEnvelope[dict[str, Any]])
async def append_turn(
    session_id: str,
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Append a dialogue turn to the session short-term buffer."""
    _owned_session(session_id, user)
    role = payload.get("role", "user")
    content = payload.get("content", "")
    metadata = payload.get("metadata", {})
    try:
        turn = short_term_store.append_turn(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
            expected_user_id=user.user_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = short_term_store.get_session(session_id)
    return APIEnvelope(
        success=True,
        data={
            "turn": turn.model_dump(),
            "session": session.model_dump() if session else None,
            "turn_count": len(session.dialogue_turns) if session else 1,
        },
        error=None,
        trace_id=f"sess-turn-{session_id}",
    )


@router.post("/session/{session_id}/scratchpad", response_model=APIEnvelope[dict[str, Any]])
@router.post("/sessions/{session_id}/scratchpad", response_model=APIEnvelope[dict[str, Any]])
async def set_scratchpad(
    session_id: str,
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Update transient scratchpad variables in the active session."""
    _owned_session(session_id, user)
    key = payload.get("key", "")
    val = payload.get("value")
    try:
        short_term_store.set_scratchpad_variable(
            session_id=session_id,
            key=key,
            value=val,
            expected_user_id=user.user_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = short_term_store.get_session(session_id)
    return APIEnvelope(
        success=True,
        data={
            "key": key,
            "value": val,
            "scratchpad": session.scratchpad if session else {key: val},
        },
        error=None,
        trace_id=f"sess-scratch-{session_id}",
    )


@router.post("/session/{session_id}/clear", response_model=APIEnvelope[dict[str, Any]])
@router.post("/sessions/{session_id}/clear", response_model=APIEnvelope[dict[str, Any]])
async def clear_session(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Clear short-term memory buffer for a session."""
    _owned_session(session_id, user)
    success = short_term_store.clear_session(session_id, expected_user_id=user.user_id)
    return APIEnvelope(
        success=success,
        data={"session_id": session_id, "cleared": success},
        error=None if success else {"code": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found."},
        trace_id=f"sess-clear-{session_id}",
    )


@router.delete("/session/{session_id}", response_model=APIEnvelope[dict[str, Any]])
@router.delete("/sessions/{session_id}", response_model=APIEnvelope[dict[str, Any]])
async def delete_session(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Completely remove an owned short-term session."""
    _owned_session(session_id, user)
    deleted = short_term_store.delete_session(session_id, expected_user_id=user.user_id)
    return APIEnvelope(
        success=deleted,
        data={"session_id": session_id, "deleted": deleted},
        error=None,
        trace_id=f"sess-delete-{session_id}",
    )


@router.get("/sessions", response_model=APIEnvelope[list[dict[str, Any]]])
async def list_sessions(user: AuthenticatedUser = Depends(get_current_user)):
    """List summary overview of active sessions."""
    require_course_access(user, "26ECAC401")
    sessions = short_term_store.list_sessions(user_id=user.user_id, course_id="26ECAC401")
    return APIEnvelope(
        success=True,
        data=sessions,
        error=None,
        trace_id="lab4-list-sessions",
    )


@router.post("/retrieval/search", response_model=APIEnvelope[dict[str, Any]])
async def search_knowledge(
    query: LongTermRetrievalQuery,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Execute high-precision search across long-term stored course notes."""
    require_course_access(user, query.course_id)
    envelope = await coordinator.dispatch(
        lab_id="lab4",
        action="search_knowledge",
        payload=query.model_dump(),
    )
    return envelope


@router.post("/retrieval/memories", response_model=APIEnvelope[dict[str, Any]])
async def save_long_term_memory(
    request: LongTermMemoryCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Explicitly save a durable user-owned reference; session turns are never promoted."""
    require_course_access(user, request.course_id)
    memory = long_term_store.save_memory(
        user_id=user.user_id,
        course_id=request.course_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
    )
    return APIEnvelope(
        success=True,
        data=memory,
        error=None,
        trace_id=f"lab4-memory-{memory['memory_id']}",
    )


@router.post("/retrieval/memories/similar", response_model=APIEnvelope[dict[str, Any]])
async def search_similar_memories(
    request: SimilarMemoryQuery,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Find similar prior items owned by this user in the authorized course."""
    require_course_access(user, request.course_id)
    result = long_term_store.search_similar_memories(
        user_id=user.user_id,
        course_id=request.course_id,
        query=request.query,
        tags=request.tags,
        top_k=request.top_k,
        retrieval_mode=request.retrieval_mode,
    )
    return APIEnvelope(
        success=True,
        data=result,
        error=None,
        trace_id="lab4-memory-similarity",
    )


@router.post("/retrieval/submissions/similar", response_model=APIEnvelope[dict[str, Any]])
async def search_similar_submissions(
    request: SimilarSubmissionQuery,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Search only the authenticated student's history or faculty-authorized course submissions."""
    require_course_access(user, request.course_id)
    student_id = user.student_id if user.role == "STUDENT" else None
    result = long_term_store.search_similar_submissions(
        course_id=request.course_id,
        query=request.query,
        student_id=student_id,
        tags=request.tags,
        top_k=request.top_k,
        retrieval_mode=request.retrieval_mode,
    )
    return APIEnvelope(
        success=True,
        data=result,
        error=None,
        trace_id="lab4-submission-similarity",
    )


@router.delete("/retrieval/memories/{memory_id}", response_model=APIEnvelope[dict[str, Any]])
async def delete_long_term_memory(
    memory_id: str,
    course_id: str = "26ECAC401",
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an explicitly saved memory only when owned by the authenticated user."""
    require_course_access(user, course_id)
    deleted = long_term_store.delete_memory(
        memory_id=memory_id,
        user_id=user.user_id,
        course_id=course_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return APIEnvelope(
        success=True,
        data={"memory_id": memory_id, "deleted": True},
        error=None,
        trace_id=f"lab4-memory-delete-{memory_id}",
    )


@router.get("/retrieval/chapters", response_model=APIEnvelope[list[int]])
async def get_chapters(user: AuthenticatedUser = Depends(get_current_user)):
    """Get list of indexed chapters."""
    require_course_access(user, "26ECAC401")
    chapters = long_term_store.get_indexed_chapters()
    return APIEnvelope(
        success=True,
        data=chapters,
        error=None,
        trace_id="lab4-chapters",
    )


@router.get("/retrieval/tags", response_model=APIEnvelope[list[str]])
async def get_tags(user: AuthenticatedUser = Depends(get_current_user)):
    """Get list of topic tags across all indexed course documents."""
    require_course_access(user, "26ECAC401")
    tags = long_term_store.get_indexed_tags()
    return APIEnvelope(
        success=True,
        data=tags,
        error=None,
        trace_id="lab4-tags",
    )


@router.post("/query", response_model=APIEnvelope[dict[str, Any]])
async def agent_query(
    request: MemoryAgentQueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Conversational agent query maintaining short-term state and querying long-term knowledge."""
    require_course_access(user, request.course_id)
    payload = request.model_dump()
    if request.session_id:
        session = _owned_session(request.session_id, user)
        if session.course_id != request.course_id:
            raise HTTPException(status_code=403, detail="Session course does not match the requested course.")
    else:
        session = short_term_store.create_session(user_id=user.user_id, course_id=request.course_id)
        payload["session_id"] = session.session_id
    payload["user_id"] = user.user_id
    envelope = await coordinator.dispatch(
        lab_id="lab4",
        action="query",
        payload=payload,
    )
    return envelope


@router.get("/scenarios", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_scenarios(user: AuthenticatedUser = Depends(get_current_user)):
    """Retrieve preset evaluator scenarios for Lab 4."""
    require_course_access(user, "26ECAC401")
    return APIEnvelope(
        success=True,
        data=LAB4_EVALUATOR_SCENARIOS,
        error=None,
        trace_id="lab4-scenarios",
    )
