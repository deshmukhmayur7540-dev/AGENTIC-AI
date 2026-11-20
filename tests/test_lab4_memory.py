"""Unit and integration tests for Lab 4: Memory & Retrieval Architecture."""

import hashlib
import os
import socket
import uuid
from pathlib import Path

import numpy as np
import pytest
from app.data.db import get_db_connection
from app.knowledge.service import KnowledgeService
from app.labs.lab4.session_store import ShortTermSessionStore, short_term_store
from app.labs.lab4.knowledge_store import LongTermKnowledgeStore, long_term_store
from app.labs.lab4.embedding_service import EmbeddingUnavailableError, LocalEmbeddingService
from app.labs.lab4.agent import MemoryAndRetrievalAgent
from app.models.lab4_models import LongTermRetrievalQuery
from config import settings


class FakeEmbeddingService:
    model_id = "test/local-model"
    model_revision = "test-revision-1"
    dimension = 3

    def __init__(self) -> None:
        self.encoded_texts = []

    def encode(self, texts):
        self.encoded_texts.extend(texts)
        return np.asarray(
            [
                [0.0, 1.0, 0.0] if "unrelated" in text.casefold() else [1.0, 0.0, 0.0]
                for text in texts
            ],
            dtype=np.float32,
        )


# =============================================================================
# 1. Short-Term Memory / Session State Tests
# =============================================================================
def test_session_lifecycle():
    """Verify session creation, turn appending, scratchpad updates, and clearing."""
    store = ShortTermSessionStore()
    sess = store.create_session(user_id="prof_alice", course_id="26ECAC401")
    assert sess.session_id.startswith("sess-")
    assert sess.user_id == "prof_alice"
    assert len(sess.dialogue_turns) == 0

    # Append turns
    store.append_turn(sess.session_id, role="faculty", content="Let's plan Lab 4.")
    store.append_turn(sess.session_id, role="agent", content="Ready to configure memory stores.")

    updated_sess = store.get_session(sess.session_id)
    assert len(updated_sess.dialogue_turns) == 2
    assert updated_sess.dialogue_turns[0].content == "Let's plan Lab 4."
    assert updated_sess.dialogue_turns[1].role == "agent"

    # Scratchpad
    store.set_scratchpad_variable(sess.session_id, "selected_pacing", "12_weeks")
    assert store.get_session(sess.session_id).scratchpad.get("selected_pacing") == "12_weeks"

    # Clear session
    cleared = store.clear_session(sess.session_id)
    assert cleared is True
    post_clear = store.get_session(sess.session_id)
    assert len(post_clear.dialogue_turns) == 0
    assert len(post_clear.scratchpad) == 0
    assert post_clear.session_id == sess.session_id  # Session ID preserved


def test_session_isolation():
    """Verify distinct sessions maintain independent isolated states."""
    store = ShortTermSessionStore()
    s1 = store.create_session("session-1")
    s2 = store.create_session("session-2")

    store.append_turn(s1.session_id, role="faculty", content="Turn in session 1")
    assert len(store.get_session(s1.session_id).dialogue_turns) == 1
    assert len(store.get_session(s2.session_id).dialogue_turns) == 0


def test_session_state_survives_store_recreation_and_expired_state_is_cleaned():
    store = ShortTermSessionStore()
    session_id = f"durable-{uuid.uuid4().hex}"
    session = store.create_session(session_id, user_id="lab4-owner", course_id="26ECAC401")
    store.append_turn(session_id, role="user", content="draft context", expected_user_id="lab4-owner")
    store.set_scratchpad_variable(session_id, "draft", "private work", expected_user_id="lab4-owner")

    restarted_store = ShortTermSessionStore()
    restored = restarted_store.get_session(session_id)
    assert restored is not None
    assert restored.user_id == "lab4-owner"
    assert restored.course_id == "26ECAC401"
    assert restored.dialogue_turns[0].content == "draft context"
    assert restored.scratchpad["draft"] == "private work"
    assert restored.expires_at and restored.expires_at > session.created_at
    with pytest.raises(KeyError, match="Session not found"):
        restarted_store.get_or_create_session(
            session_id,
            user_id="another-owner",
            course_id="26ECAC401",
        )

    with get_db_connection(immediate=True) as conn:
        conn.execute(
            "UPDATE lab4_sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE session_id = ?",
            (session_id,),
        )
    assert restarted_store.get_session(session_id) is None
    with get_db_connection() as conn:
        assert conn.execute(
            "SELECT 1 FROM lab4_session_turns WHERE session_id = ?",
            (session_id,),
        ).fetchone() is None


def test_explicit_memories_are_durable_tag_filtered_and_similarity_ranked():
    store = LongTermKnowledgeStore()
    user_id = f"memory-owner-{uuid.uuid4().hex}"
    course_id = "26ECAC401"
    relevant = store.save_memory(
        user_id=user_id,
        course_id=course_id,
        title="Rubric feedback notes",
        content="Rubric criterion feedback should explain the grade and reference the assignment evidence.",
        tags=["grading", "rubric"],
    )
    store.save_memory(
        user_id=user_id,
        course_id=course_id,
        title="Unrelated campus event",
        content="The science fair schedule is posted in the student center.",
        tags=["events"],
    )

    restarted_store = LongTermKnowledgeStore()
    result = restarted_store.search_similar_memories(
        user_id=user_id,
        course_id=course_id,
        query="rubric grade feedback criterion",
        tags=["GRADING"],
        top_k=5,
    )
    assert result["match_count"] == 1
    match = result["matches"][0]
    assert match["memory_id"] == relevant["memory_id"]
    assert match["similarity_score"] > 0
    assert match["citation"]["source_location"] == f"lab4-memory://{relevant['memory_id']}"
    assert result["retrieval_method"] == "local_tfidf_cosine_lexical"
    assert result["embedding_similarity"] is False


def test_session_content_is_not_promoted_to_long_term_memory():
    session_id = f"boundary-{uuid.uuid4().hex}"
    secret = f"zxqvblorp{uuid.uuid4().hex}"
    short_term_store.create_session(session_id, user_id="boundary-owner", course_id="26ECAC401")
    short_term_store.append_turn(session_id, role="user", content=secret)

    result = long_term_store.search_similar_memories(
        user_id="boundary-owner",
        course_id="26ECAC401",
        query=secret,
    )
    assert result["match_count"] == 0
    assert long_term_store.search(LongTermRetrievalQuery(query=secret)).match_count == 0


def test_semantic_memory_embeddings_persist_and_scope_candidates_before_encoding():
    encoder = FakeEmbeddingService()
    store = LongTermKnowledgeStore(embedding_service=encoder)
    owner_id = f"semantic-owner-{uuid.uuid4().hex}"
    private_text = f"out-of-scope-private-{uuid.uuid4().hex}"
    saved = store.save_memory(
        user_id=owner_id,
        course_id="26ECAC401",
        title="Reference A",
        content="A reference about adapting an agent from feedback.",
        tags=["agent"],
    )
    store.save_memory(
        user_id=f"other-owner-{uuid.uuid4().hex}",
        course_id="26ECAC401",
        title="Private unrelated",
        content=private_text,
        tags=["agent"],
    )

    result = store.search_similar_memories(
        user_id=owner_id,
        course_id="26ECAC401",
        query="How should an agent adapt after feedback?",
        retrieval_mode="semantic",
    )
    assert result["retrieval_method"] == "local_sentence_transformer_cosine"
    assert result["embedding_similarity"] is True
    assert result["matches"][0]["memory_id"] == saved["memory_id"]
    assert result["matches"][0]["citation"]["source_location"] == f"lab4-memory://{saved['memory_id']}"
    assert private_text not in encoder.encoded_texts

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM lab4_memory_embeddings WHERE memory_id = ?",
            (saved["memory_id"],),
        ).fetchone()
        assert row is not None
        assert row["embedding_dimension"] == 3
        assert len(row["embedding"]) == 12
        assert row["text_hash"] == hashlib.sha256(
            b"Reference A\nA reference about adapting an agent from feedback."
        ).hexdigest()

    restarted_encoder = FakeEmbeddingService()
    restarted = LongTermKnowledgeStore(embedding_service=restarted_encoder)
    repeated = restarted.search_similar_memories(
        user_id=owner_id,
        course_id="26ECAC401",
        query="How should an agent adapt after feedback?",
        retrieval_mode="semantic",
    )
    assert repeated["matches"][0]["memory_id"] == saved["memory_id"]
    assert restarted_encoder.encoded_texts == ["How should an agent adapt after feedback?"]
    with get_db_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM lab4_memory_embeddings WHERE memory_id = ?",
            (saved["memory_id"],),
        ).fetchone()[0] == 1


def test_semantic_embeddings_rebuild_when_text_or_model_revision_changes_and_cascade_on_delete():
    first_encoder = FakeEmbeddingService()
    store = LongTermKnowledgeStore(embedding_service=first_encoder)
    memory = store.save_memory(
        user_id="embedding-revision-owner",
        course_id="26ECAC401",
        title="Versioned reference",
        content="Initial reference content.",
        tags=[],
    )
    store.search_similar_memories(
        user_id="embedding-revision-owner",
        course_id="26ECAC401",
        query="reference query",
        retrieval_mode="semantic",
    )

    with get_db_connection(immediate=True) as conn:
        conn.execute(
            "UPDATE lab4_memory_records SET content = ? WHERE memory_id = ?",
            ("Revised reference content.", memory["memory_id"]),
        )
    second_encoder = FakeEmbeddingService()
    second_encoder.model_revision = "test-revision-2"
    revised_store = LongTermKnowledgeStore(embedding_service=second_encoder)
    revised_store.search_similar_memories(
        user_id="embedding-revision-owner",
        course_id="26ECAC401",
        query="reference query",
        retrieval_mode="semantic",
    )
    assert "Versioned reference\nRevised reference content." in second_encoder.encoded_texts

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT model_revision, text_hash FROM lab4_memory_embeddings WHERE memory_id = ?",
            (memory["memory_id"],),
        ).fetchone()
        assert row["model_revision"] == "test-revision-2"
        assert row["text_hash"] == hashlib.sha256(
            b"Versioned reference\nRevised reference content."
        ).hexdigest()

    assert revised_store.delete_memory(
        memory_id=memory["memory_id"],
        user_id="embedding-revision-owner",
        course_id="26ECAC401",
    )
    with get_db_connection() as conn:
        assert conn.execute(
            "SELECT 1 FROM lab4_memory_embeddings WHERE memory_id = ?",
            (memory["memory_id"],),
        ).fetchone() is None


def test_embedding_batch_rebuild_is_bounded_and_idempotent():
    store = LongTermKnowledgeStore(embedding_service=FakeEmbeddingService())
    owner_id = f"batch-owner-{uuid.uuid4().hex}"
    for index in range(3):
        store.save_memory(
            user_id=owner_id,
            course_id="26ECAC401",
            title=f"Batch record {index}",
            content=f"Stored reference content {index}.",
            tags=[],
        )

    first = store.rebuild_embeddings(course_id="26ECAC401", batch_size=2)
    second = store.rebuild_embeddings(course_id="26ECAC401", batch_size=2)
    assert first["memory_records"] >= 3
    assert first["embeddings_updated"] >= 3
    assert second["embeddings_updated"] == 0


def test_missing_local_embedding_model_falls_back_to_explicitly_labeled_lexical_search(tmp_path):
    store = LongTermKnowledgeStore(
        embedding_service=LocalEmbeddingService(model_path=tmp_path / "missing-model")
    )
    store.save_memory(
        user_id="fallback-owner",
        course_id="26ECAC401",
        title="Rubric notes",
        content="The rubric feedback explains grading criteria.",
        tags=["rubric"],
    )
    result = store.search_similar_memories(
        user_id="fallback-owner",
        course_id="26ECAC401",
        query="rubric feedback",
        retrieval_mode="semantic",
    )
    assert result["retrieval_method"] == "local_tfidf_cosine_lexical"
    assert result["embedding_similarity"] is False
    assert result["requested_retrieval_mode"] == "semantic"
    assert "directory is missing" in result["fallback_reason"]


def test_corrupt_local_embedding_model_returns_a_clear_unavailable_error(tmp_path):
    model_dir = tmp_path / "corrupt-model"
    model_dir.mkdir()
    (model_dir / "model.safetensors").write_bytes(b"not-a-model")
    (model_dir / "modules.json").write_text("invalid json", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "courseagentai_model.json").write_text(
        (
            '{"model_id":"sentence-transformers/all-MiniLM-L6-v2",'
            '"revision":"1110a243fdf4706b3f48f1d95db1a4f5529b4d41","dimension":384}'
        ),
        encoding="utf-8",
    )
    service = LocalEmbeddingService(model_path=model_dir)
    assert service.status()["available"] is True
    assert service.status()["loaded"] is False
    with pytest.raises(EmbeddingUnavailableError, match="Could not load local embedding model"):
        service.encode(["test input"])


@pytest.mark.skipif(
    os.getenv("LAB4_RUN_MODEL_INTEGRATION_TESTS") != "1",
    reason="Set LAB4_RUN_MODEL_INTEGRATION_TESTS=1 to run the explicit local-model integration test.",
)
def test_real_local_model_semantic_ranking_cpu_and_offline(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    def block_network(*args, **kwargs):
        raise AssertionError("The offline model integration test must not use a network connection.")

    monkeypatch.setattr(socket.socket, "connect", block_network)
    monkeypatch.setattr(socket.socket, "connect_ex", block_network)
    monkeypatch.setattr(socket, "create_connection", block_network)

    service = LocalEmbeddingService()
    assert service.status()["available"] is True
    assert service.status()["loaded"] is False
    query = "How can the agent learn from consequences and make better decisions in later steps?"
    relevant = (
        "An autonomous program selects a task, executes it, assesses the result, "
        "and adjusts future behavior based on observations."
    )
    unrelated = "The water cycle moves moisture through evaporation, condensation, precipitation, and collection."
    vectors = service.encode([query, relevant, unrelated])
    assert vectors.shape == (3, 384)
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    assert str(service._model.device) == "cpu"

    store = LongTermKnowledgeStore(embedding_service=service)
    user_id = f"real-model-owner-{uuid.uuid4().hex}"
    relevant_record = store.save_memory(
        user_id=user_id,
        course_id="26ECAC401",
        title="Reference one",
        content=relevant,
        tags=["agent"],
    )
    unrelated_record = store.save_memory(
        user_id=user_id,
        course_id="26ECAC401",
        title="Reference two",
        content=unrelated,
        tags=["agent"],
    )
    semantic = store.search_similar_memories(
        user_id=user_id,
        course_id="26ECAC401",
        query=query,
        retrieval_mode="semantic",
    )
    lexical = store.search_similar_memories(
        user_id=user_id,
        course_id="26ECAC401",
        query=query,
        retrieval_mode="lexical",
    )
    assert semantic["matches"][0]["memory_id"] == relevant_record["memory_id"]
    assert all(item["memory_id"] != unrelated_record["memory_id"] for item in semantic["matches"])
    assert semantic["matches"][0]["citation"]["source_location"].endswith(relevant_record["memory_id"])
    assert lexical["matches"][0]["memory_id"] == unrelated_record["memory_id"]


def test_persistent_reference_documents_are_retrievable_after_service_recreation():
    source_dir = Path(settings.knowledge_root) / "agentic_ai"
    first_service = KnowledgeService(base_dir=source_dir, include_course_materials=False)
    first_result = first_service.search("Plan Act Observe Revise agent loop", top_k=3)
    restarted_service = KnowledgeService(base_dir=source_dir, include_course_materials=False)
    restarted_result = restarted_service.search("Plan Act Observe Revise agent loop", top_k=3)

    assert first_result.match_count > 0
    assert restarted_result.match_count > 0
    assert restarted_result.matches[0].source_document == first_result.matches[0].source_document
    assert restarted_result.matches[0].source_location
    assert restarted_result.matches[0].source


# =============================================================================
# 2. Long-Term Knowledge Store Tests
# =============================================================================
def test_long_term_retrieval_chapter_1():
    """Verify Chapter 1 retrieval for Plan-Act-Observe-Revise loop."""
    query = LongTermRetrievalQuery(query="What is the Plan-Act-Observe-Revise loop?")
    res = long_term_store.search(query)
    assert res.match_count >= 1
    assert any(m.chapter == 1 for m in res.matches)
    ch1_match = next(m for m in res.matches if m.chapter == 1)
    lower_text = ch1_match.matched_text.lower()
    assert "plan" in lower_text and "observe" in lower_text
    assert ch1_match.source_document != ""


def test_long_term_retrieval_chapter_2():
    """Verify Chapter 2 retrieval for LangChain tool integration."""
    query = LongTermRetrievalQuery(query="What is LangChain tool integration and function calling?")
    res = long_term_store.search(query)
    assert res.match_count >= 1
    assert any(m.chapter == 2 for m in res.matches)
    ch2_match = next(m for m in res.matches if m.chapter == 2)
    assert "tool" in ch2_match.matched_text.lower() or "langchain" in ch2_match.matched_text.lower()


def test_long_term_retrieval_chapter_3():
    """Verify Chapter 3 retrieval for LangGraph and multi-agent orchestration."""
    query = LongTermRetrievalQuery(query="What is LangGraph and multi-agent orchestration?")
    res = long_term_store.search(query)
    assert res.match_count >= 1
    assert any(m.chapter in [2, 3] for m in res.matches)


def test_long_term_retrieval_chapter_4():
    """Verify Chapter 4 retrieval for safety guardrails and approval gates."""
    query = LongTermRetrievalQuery(query="What are safety guardrails, quotas and governance?")
    res = long_term_store.search(query)
    assert res.match_count >= 1
    assert any(m.chapter == 4 for m in res.matches)


def test_long_term_retrieval_chapter_filter():
    """Verify chapter filter restricts matches exclusively to the specified chapter."""
    query = LongTermRetrievalQuery(query="autonomous agents", chapter=1)
    res = long_term_store.search(query)
    assert res.match_count >= 1
    assert all(m.chapter == 1 for m in res.matches)


def test_long_term_retrieval_anti_hallucination():
    """Unknown concepts return 0 matches with zero hallucination."""
    query = LongTermRetrievalQuery(query="quantum gravity in medieval alchemy")
    res = long_term_store.search(query)
    assert res.match_count == 0
    assert len(res.matches) == 0


def test_long_term_retrieval_unknown_course():
    """Querying an unknown course returns zero matches with explicit boundary message."""
    query = LongTermRetrievalQuery(query="syllabus", course_id="CS101")
    res = long_term_store.search(query)
    assert res.match_count == 0
    assert "not indexed" in res.source


# =============================================================================
# 3. Architectural Separation Tests
# =============================================================================
def test_short_and_long_term_memory_separation():
    """Verify short-term memory dialogue turns are NEVER stored in the long-term knowledge index."""
    unique_secret = "SECRET_FACULTY_PRIVATE_NOTE_98765"
    s = short_term_store.create_session("boundary-test-session")
    short_term_store.append_turn(s.session_id, role="faculty", content=unique_secret)

    # Search long-term store for the secret
    res = long_term_store.search(LongTermRetrievalQuery(query=unique_secret))
    assert res.match_count == 0
    assert len(res.matches) == 0


# =============================================================================
# 4. MemoryAndRetrievalAgent End-to-End Tests
# =============================================================================
@pytest.mark.asyncio
async def test_memory_agent_query_flow():
    """Verify agent dialogue creates short-term turns and retrieves long-term evidence."""
    agent = MemoryAndRetrievalAgent()
    payload = {
        "query": "Explain the autonomous Plan-Act-Observe-Revise cycle in 26ECAC401",
    }
    result = await agent.execute("query", payload)
    assert result["long_term_matches_found"] >= 1
    lower_ans = result["grounded_answer"].lower()
    assert "plan" in lower_ans and "observe" in lower_ans
    assert result["short_term_turn_count"] >= 2  # 1 faculty prompt + 1 agent response

    # Query again in the same session
    sid = result["session_id"]
    payload2 = {
        "session_id": sid,
        "query": "What are the four agent characteristics in Chapter 1?",
    }
    result2 = await agent.execute("query", payload2)
    assert result2["session_id"] == sid
    assert result2["short_term_turn_count"] >= 4


@pytest.mark.asyncio
async def test_memory_agent_prefers_session_scratchpad_over_rag():
    """Explicit session memory must override long-term knowledge retrieval for context questions."""
    agent = MemoryAndRetrievalAgent()
    session = short_term_store.create_session("lab4-scratch-memory")
    short_term_store.set_scratchpad_variable(session.session_id, "selected_pacing", "12_weeks")

    result = await agent.execute("query", {"session_id": session.session_id, "query": "What pacing did I choose?"})

    assert "12_weeks" in result["grounded_answer"]
    assert result["session_id"] == session.session_id
