"""MemoryAndRetrievalAgent for Lab 4: Explicit separation of Short-Term and Long-Term Memory."""

from typing import Any, Optional
from app.core.base_agent import BaseAgent
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID
from app.core.registry import lab_registry
from app.labs.lab4.knowledge_store import long_term_store
from app.labs.lab4.session_store import short_term_store
from app.models.lab4_models import LongTermRetrievalQuery


class MemoryAndRetrievalAgent(BaseAgent):
    """Agent demonstrating strict separation of ephemeral session state and long-term knowledge."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="lab4_memory_agent",
            name="Memory & Retrieval Agent",
            description="Maintains conversational session state while retrieving authoritative grounding from the long-term knowledge base.",
        )

    async def initialize(self) -> None:
        """Ensure knowledge service is initialized."""
        long_term_store.get_indexed_chapters()

    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch action to memory layer or agent logic."""
        if action == "query":
            return self._handle_query(payload)

        elif action == "search_knowledge":
            query_str = payload.get("query", "")
            course_id = payload.get("course_id", CANONICAL_COURSE_ID)
            chapter = payload.get("chapter")
            tags = payload.get("tags")
            top_k = payload.get("top_k", 5)

            retrieval_query = LongTermRetrievalQuery(
                query=query_str,
                course_id=course_id,
                chapter=chapter,
                tags=tags,
                top_k=top_k,
            )
            result = long_term_store.search(retrieval_query)
            return result.model_dump()

        elif action == "get_session":
            sid = payload.get("session_id", "")
            session = short_term_store.get_session(sid)
            if session and session.user_id != payload.get("user_id", "faculty_reviewer"):
                session = None
            if not session:
                return {"status": "ERROR", "error": f"Session '{sid}' not found."}
            return {"status": "SUCCESS", "session": session.model_dump()}

        elif action == "clear_session":
            sid = payload.get("session_id", "")
            success = short_term_store.clear_session(
                sid,
                expected_user_id=payload.get("user_id", "faculty_reviewer"),
            )
            return {"status": "SUCCESS" if success else "ERROR", "session_id": sid, "cleared": success}

        elif action == "list_sessions":
            sessions = short_term_store.list_sessions(
                user_id=payload.get("user_id", "faculty_reviewer"),
                course_id=payload.get("course_id", CANONICAL_COURSE_ID),
            )
            return {"status": "SUCCESS", "sessions": sessions}

        return {
            "status": "ERROR",
            "error": f"Action '{action}' is not supported by MemoryAndRetrievalAgent.",
        }

    def _resolve_scratchpad_memory(self, session: Any, query: str) -> Optional[str]:
        """Prefer explicit short-term session memory before any long-term knowledge lookup."""
        if not session or not session.scratchpad:
            return None

        query_lower = query.lower()
        relevant_parts = []
        for key, value in session.scratchpad.items():
            key_str = str(key).lower()
            value_str = str(value).lower()
            if (
                key_str in query_lower
                or value_str in query_lower
                or any(word in query_lower for word in ("remember", "prefer", "choose", "selected", "pacing", "weeks", "my"))
            ):
                relevant_parts.append(f"{key.replace('_', ' ')} = {value}")

        if not relevant_parts:
            return None

        return "From your session memory: " + "; ".join(relevant_parts) + "."

    def _handle_query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute conversational query with short-term state tracking and long-term grounding."""
        session_id = payload.get("session_id")
        query = (payload.get("query") or payload.get("request") or "").strip()
        course_id = normalize_course_id(payload.get("course_id") or query) or CANONICAL_COURSE_ID
        chapter_filter = payload.get("chapter_filter")
        user_id = payload.get("user_id", "faculty_reviewer")

        # 1. Retrieve or create session state (Short-Term Memory)
        session = short_term_store.get_or_create_session(
            session_id,
            user_id=user_id,
            course_id=course_id,
        )
        short_term_store.append_turn(
            session.session_id,
            role="user",
            content=query,
            expected_user_id=user_id,
        )
        short_term_store.set_current_request(
            session.session_id,
            query,
            expected_user_id=user_id,
        )

        scratchpad_answer = self._resolve_scratchpad_memory(session, query)
        if scratchpad_answer is not None:
            short_term_store.append_turn(
                session.session_id,
                role="agent",
                content=scratchpad_answer,
                metadata={"memory_source": "scratchpad", "scratchpad_keys": list(session.scratchpad.keys())},
                expected_user_id=user_id,
            )
            session = short_term_store.get_session(session.session_id)
            return {
                "session_id": session.session_id,
                "query": query,
                "course_id": course_id,
                "short_term_turn_count": len(session.dialogue_turns),
                "session_turns_used": len(session.dialogue_turns),
                "long_term_matches_found": 0,
                "grounded_answer": scratchpad_answer,
                "answer": scratchpad_answer,
                "response": scratchpad_answer,
                "retrieved_evidence": [],
                "citations": [],
                "provenance_source": "session_scratchpad",
                "memory_source": "scratchpad",
            }

        # 2. Query Long-Term Knowledge Store
        retrieval_query = LongTermRetrievalQuery(
            query=query,
            course_id=course_id,
            chapter=chapter_filter,
            top_k=4,
        )
        knowledge_res = long_term_store.search(retrieval_query)

        # 3. Formulate grounded conclusion
        if knowledge_res.match_count > 0:
            evidence_summaries = []
            for m in knowledge_res.matches[:2]:
                evidence_summaries.append(f"Chapter {m.chapter} ({m.topic}): {m.matched_text[:200]}...")

            grounded_answer = (
                f"Grounded Response for {course_id}:\n" + "\n\n".join(evidence_summaries)
            )
        else:
            grounded_answer = (
                f"No verified course facts found in {course_id} notes for '{query}'. "
                f"The system avoids hallucinating unestablished topics."
            )

        # 4. Record agent answer to Short-Term Memory
        short_term_store.append_turn(
            session.session_id,
            role="agent",
            content=grounded_answer,
            metadata={"match_count": knowledge_res.match_count, "course_id": course_id},
            expected_user_id=user_id,
        )
        session = short_term_store.get_session(session.session_id)

        return {
            "session_id": session.session_id,
            "query": query,
            "course_id": course_id,
            "short_term_turn_count": len(session.dialogue_turns),
            "session_turns_used": len(session.dialogue_turns),
            "long_term_matches_found": knowledge_res.match_count,
            "grounded_answer": grounded_answer,
            "answer": grounded_answer,
            "response": grounded_answer,
            "retrieved_evidence": [m.model_dump() for m in knowledge_res.matches],
            "citations": [m.model_dump() for m in knowledge_res.matches],
            "provenance_source": knowledge_res.source,
        }


lab4_agent = MemoryAndRetrievalAgent()
lab_registry.register_agent("lab4", lab4_agent)
