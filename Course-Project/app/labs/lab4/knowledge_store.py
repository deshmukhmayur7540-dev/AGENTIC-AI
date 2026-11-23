"""Long-term knowledge store: Grounded retrieval of indexed course documents (Chapters 1-4)."""

import hashlib
import json
import logging
import math
import re
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from app.core.course_identity import normalize_course_id
from app.data.db import get_db_connection
from app.labs.lab4.embedding_service import (
    EmbeddingUnavailableError,
    LocalEmbeddingService,
    local_embedding_service,
)
from app.knowledge.service import knowledge_service
from app.models.lab4_models import (
    LongTermRetrievalQuery,
    LongTermRetrievalResult,
    RetrievedChunk,
)
from config import settings

logger = logging.getLogger(__name__)


class LongTermKnowledgeStore:
    """Long-term storage and retrieval layer for authoritative course notes and materials.
    
    Provides high-precision retrieval with chapter filtering, tag-based discovery,
    and BM25 ranking across Chapter 1-4 notes without hallucinating unsupported facts.
    """

    def __init__(self, embedding_service: Optional[LocalEmbeddingService] = None) -> None:
        self._service = knowledge_service
        self._embedding_service = embedding_service or local_embedding_service

    def search(self, query: LongTermRetrievalQuery) -> LongTermRetrievalResult:
        """Search long-term course knowledge with optional chapter or tag constraints."""
        course_id = normalize_course_id(query.course_id) or query.course_id
        search_res = self._service.search(
            query=query.query,
            course_id=course_id,
            chapter=query.chapter,
            tags=query.tags,
            top_k=query.top_k,
        )

        chunks: list[RetrievedChunk] = []
        for idx, m in enumerate(search_res.matches):
            chunks.append(
                RetrievedChunk(
                    chunk_id=f"chunk-{m.chapter}-{idx + 1}",
                    chapter=m.chapter,
                    topic=m.topic,
                    matched_text=m.matched_text,
                    source=m.source,
                    source_document=m.source_document,
                    source_location=m.source_location,
                    category=m.category,
                    lab=m.lab,
                    folder_path=m.folder_path,
                    material_id=m.material_id,
                    tags=m.tags,
                    score=round(m.score, 4),
                )
            )

        return LongTermRetrievalResult(
            query=query.query,
            course_id=course_id,
            match_count=len(chunks),
            matches=chunks,
            source=search_res.source,
        )

    def save_memory(
        self,
        *,
        user_id: str,
        course_id: str,
        title: str,
        content: str,
        tags: list[str],
    ) -> dict[str, Any]:
        """Explicitly save a durable user-owned reference item, never a session implicitly."""
        normalized_tags = sorted(
            {tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()},
            key=str.casefold,
        )
        memory_id = f"mem-{uuid.uuid4().hex}"
        created_at = datetime.now(timezone.utc).isoformat()
        with get_db_connection(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO lab4_memory_records (
                    memory_id, user_id, course_id, title, content, tags_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, user_id, course_id, title.strip(), content.strip(),
                 json.dumps(normalized_tags), created_at),
            )
        return {
            "memory_id": memory_id,
            "course_id": course_id,
            "title": title.strip(),
            "content": content.strip(),
            "tags": normalized_tags,
            "created_at": created_at,
            "memory_layer": "LONG_TERM_USER_REFERENCE",
        }

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.casefold())

    @classmethod
    def _tfidf_vector(cls, text: str, document_frequencies: Counter[str], document_count: int) -> dict[str, float]:
        terms = Counter(cls._tokens(text))
        vector = {
            term: (1.0 + math.log(count)) * (math.log((document_count + 1) / (document_frequencies[term] + 1)) + 1.0)
            for term, count in terms.items()
        }
        return vector

    @staticmethod
    def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        dot = sum(value * right.get(term, 0.0) for term, value in left.items())
        return dot / (left_norm * right_norm)

    @staticmethod
    def _memory_embedding_text(row: dict[str, Any]) -> str:
        return f"{row['title']}\n{row['content']}".strip()

    @staticmethod
    def _submission_embedding_text(row: dict[str, Any]) -> str:
        return " ".join(
            str(value or "")
            for value in (row["assignment_id"], row["assignment_title"], row["repo_name"], row["notes"])
        ).strip()

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode_embedding(data: bytes | None, dimension: int) -> Optional[np.ndarray]:
        if data is None or len(data) != dimension * 4:
            return None
        vector = np.frombuffer(data, dtype="<f4")
        if not np.isfinite(vector).all():
            return None
        norm = float(np.linalg.norm(vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            return None
        return vector

    def _ensure_embedding_vectors(
        self,
        rows: list[dict[str, Any]],
        *,
        source_id_column: str,
        embedding_id_column: Optional[str] = None,
        embedding_table: str,
        text_factory: Callable[[dict[str, Any]], str],
    ) -> tuple[dict[str, np.ndarray], int]:
        embedding_id_column = embedding_id_column or source_id_column
        model_id = self._embedding_service.model_id
        model_revision = self._embedding_service.model_revision
        dimension = self._embedding_service.dimension
        texts = {str(row[source_id_column]): text_factory(row) for row in rows}
        hashes = {source_id: self._text_hash(text) for source_id, text in texts.items()}
        vectors: dict[str, np.ndarray] = {}
        stale_ids: list[str] = []
        rows_by_id = {str(row[source_id_column]): row for row in rows}

        for row in rows:
            source_id = str(row[source_id_column])
            vector = self._decode_embedding(row.get("embedding_blob"), dimension)
            is_current = (
                vector is not None
                and row.get("embedding_model_id") == model_id
                and row.get("embedding_model_revision") == model_revision
                and row.get("embedding_dimension") == dimension
                and row.get("embedding_text_hash") == hashes[source_id]
                and row.get("embedding_owner_id") == row.get("owner_id")
                and row.get("embedding_course_id") == row.get("course_id")
            )
            if is_current:
                vectors[source_id] = vector
            else:
                stale_ids.append(source_id)

        if not stale_ids:
            return vectors, 0

        encoded = np.asarray(
            self._embedding_service.encode([texts[source_id] for source_id in stale_ids]),
            dtype=np.float32,
        )
        if encoded.shape != (len(stale_ids), dimension) or not np.isfinite(encoded).all():
            raise EmbeddingUnavailableError("Embedding service returned invalid vectors for persistence.")

        now = datetime.now(timezone.utc).isoformat()
        with get_db_connection(immediate=True) as conn:
            for source_id, vector in zip(stale_ids, encoded):
                conn.execute(
                    f"""
                    INSERT INTO {embedding_table} (
                        {embedding_id_column}, owner_id, course_id, model_id, model_revision,
                        embedding_dimension, text_hash, embedding, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT({embedding_id_column}) DO UPDATE SET
                        owner_id = excluded.owner_id,
                        course_id = excluded.course_id,
                        model_id = excluded.model_id,
                        model_revision = excluded.model_revision,
                        embedding_dimension = excluded.embedding_dimension,
                        text_hash = excluded.text_hash,
                        embedding = excluded.embedding,
                        updated_at = excluded.updated_at
                    """,
                    (
                        source_id,
                        str(rows_by_id[source_id]["owner_id"]),
                        str(rows_by_id[source_id]["course_id"]),
                        model_id,
                        model_revision,
                        dimension,
                        hashes[source_id],
                        np.asarray(vector, dtype="<f4").tobytes(),
                        now,
                        now,
                    ),
                )
                vectors[source_id] = np.asarray(vector, dtype="<f4")
        return vectors, len(stale_ids)

    def _semantic_memory_search(
        self,
        *,
        user_id: str,
        course_id: str,
        query: str,
        tags: Optional[list[str]],
        top_k: int,
    ) -> dict[str, Any]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.memory_id, m.user_id AS owner_id, m.course_id, m.title, m.content,
                    m.tags_json, m.created_at,
                    e.owner_id AS embedding_owner_id,
                    e.course_id AS embedding_course_id,
                    e.model_id AS embedding_model_id,
                    e.model_revision AS embedding_model_revision,
                    e.embedding_dimension, e.text_hash AS embedding_text_hash,
                    e.embedding AS embedding_blob
                FROM lab4_memory_records m
                LEFT JOIN lab4_memory_embeddings e ON e.memory_id = m.memory_id
                WHERE m.user_id = ? AND m.course_id = ?
                ORDER BY m.created_at DESC
                """,
                (user_id, course_id),
            ).fetchall()

        wanted_tags = {tag.casefold() for tag in (tags or []) if tag.strip()}
        candidates = [
            dict(row)
            for row in rows
            if not wanted_tags
            or wanted_tags.intersection(tag.casefold() for tag in json.loads(row["tags_json"]))
        ]
        if not candidates:
            return self._semantic_result(query, course_id, [], top_k)

        vectors, _ = self._ensure_embedding_vectors(
            candidates,
            source_id_column="memory_id",
            embedding_table="lab4_memory_embeddings",
            text_factory=self._memory_embedding_text,
        )
        query_vector = self._embedding_service.encode([query])[0]
        matches = []
        for row in candidates:
            memory_id = row["memory_id"]
            score = float(vectors[memory_id] @ query_vector)
            if score < settings.lab4_embedding_similarity_threshold:
                continue
            matches.append(
                {
                    "memory_id": memory_id,
                    "title": row["title"],
                    "content": row["content"],
                    "tags": json.loads(row["tags_json"]),
                    "created_at": row["created_at"],
                    "similarity_score": round(score, 6),
                    "citation": {
                        "source": "Explicitly saved user memory",
                        "source_document": row["title"],
                        "source_location": f"lab4-memory://{memory_id}",
                    },
                }
            )
        matches.sort(key=lambda item: (-item["similarity_score"], item["created_at"], item["memory_id"]))
        return self._semantic_result(query, course_id, matches, top_k)

    def _semantic_result(
        self,
        query: str,
        course_id: str,
        matches: list[dict[str, Any]],
        top_k: int,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "course_id": course_id,
            "match_count": min(len(matches), top_k),
            "matches": matches[:top_k],
            "retrieval_method": "local_sentence_transformer_cosine",
            "embedding_similarity": True,
            "model_id": self._embedding_service.model_id,
            "model_revision": self._embedding_service.model_revision,
            "similarity_threshold": settings.lab4_embedding_similarity_threshold,
            "score_definition": (
                "Cosine similarity between L2-normalized local sentence embeddings; this is a retrieval "
                "ranking score, not a probability or plagiarism finding."
            ),
        }

    def _semantic_submission_search(
        self,
        *,
        course_id: str,
        query: str,
        student_id: Optional[str],
        tags: Optional[list[str]],
        top_k: int,
    ) -> dict[str, Any]:
        sql = """
            SELECT s.id, s.assignment_id, a.title AS assignment_title, s.student_id AS owner_id,
                s.course_id, s.repo_name, s.submission_timestamp, s.attempt_number,
                s.status, s.validation_status, s.notes,
                e.owner_id AS embedding_owner_id,
                e.course_id AS embedding_course_id,
                e.model_id AS embedding_model_id,
                e.model_revision AS embedding_model_revision,
                e.embedding_dimension, e.text_hash AS embedding_text_hash,
                e.embedding AS embedding_blob
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            LEFT JOIN lab4_submission_embeddings e ON e.submission_id = s.id
            WHERE s.course_id = ?
        """
        params: list[Any] = [course_id]
        if student_id is not None:
            sql += " AND s.student_id = ?"
            params.append(student_id)
        sql += " ORDER BY s.submission_timestamp DESC, s.id"
        with get_db_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        wanted_tags = {tag.casefold() for tag in (tags or []) if tag.strip()}
        candidates = []
        for row in rows:
            row_tags = {row["assignment_id"].casefold(), row["assignment_title"].casefold()}
            if wanted_tags and not any(
                tag in candidate_tag or candidate_tag in tag
                for tag in wanted_tags
                for candidate_tag in row_tags
            ):
                continue
            candidates.append(dict(row))
        if not candidates:
            return self._semantic_result(query, course_id, [], top_k)

        vectors, _ = self._ensure_embedding_vectors(
            candidates,
            source_id_column="id",
            embedding_id_column="submission_id",
            embedding_table="lab4_submission_embeddings",
            text_factory=self._submission_embedding_text,
        )
        query_vector = self._embedding_service.encode([query])[0]
        matches = []
        for row in candidates:
            submission_id = row["id"]
            score = float(vectors[submission_id] @ query_vector)
            if score < settings.lab4_embedding_similarity_threshold:
                continue
            matches.append(
                {
                    "submission_id": submission_id,
                    "assignment_id": row["assignment_id"],
                    "assignment_title": row["assignment_title"],
                    "student_id": row["owner_id"],
                    "course_id": row["course_id"],
                    "submitted_at": row["submission_timestamp"],
                    "attempt_number": row["attempt_number"],
                    "status": row["status"],
                    "validation_status": row["validation_status"],
                    "similarity_score": round(score, 6),
                    "citation": {
                        "source": "Stored assignment submission metadata",
                        "source_document": row["assignment_title"],
                        "source_location": f"/api/submissions/detail/{submission_id}",
                    },
                }
            )
        matches.sort(
            key=lambda item: (-item["similarity_score"], item["submitted_at"], item["submission_id"])
        )
        result = self._semantic_result(query, course_id, matches, top_k)
        result["source_code_analyzed"] = False
        result["owner_scope"] = student_id
        result["limitation"] = (
            "Semantic similarity uses assignment identifiers and titles, repository names, and stored student "
            "notes. Repository source code is not fetched or analyzed; results are retrieval candidates, "
            "not plagiarism findings."
        )
        return result

    def search_similar_memories(
        self,
        *,
        user_id: str,
        course_id: str,
        query: str,
        tags: Optional[list[str]] = None,
        top_k: int = 5,
        retrieval_mode: str = "lexical",
    ) -> dict[str, Any]:
        """Retrieve saved references using lexical TF-IDF or local sentence embeddings."""
        if retrieval_mode == "semantic":
            try:
                result = self._semantic_memory_search(
                    user_id=user_id,
                    course_id=course_id,
                    query=query,
                    tags=tags,
                    top_k=top_k,
                )
                result["owner_scope"] = user_id
                return result
            except EmbeddingUnavailableError as exc:
                logger.warning("Semantic memory search unavailable; using labeled lexical fallback: %s", exc)
                fallback_reason = str(exc)
        elif retrieval_mode != "lexical":
            raise ValueError("Retrieval mode must be 'lexical' or 'semantic'.")
        else:
            fallback_reason = None

        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT memory_id, title, content, tags_json, created_at
                FROM lab4_memory_records
                WHERE user_id = ? AND course_id = ?
                ORDER BY created_at DESC
                """,
                (user_id, course_id),
            ).fetchall()

        wanted_tags = {tag.casefold() for tag in (tags or []) if tag.strip()}
        candidates = []
        for row in rows:
            record_tags = json.loads(row["tags_json"])
            if wanted_tags and not wanted_tags.intersection(tag.casefold() for tag in record_tags):
                continue
            candidates.append((row, record_tags))

        document_frequencies: Counter[str] = Counter()
        for row, _ in candidates:
            document_frequencies.update(set(self._tokens(f"{row['title']} {row['content']}")))
        query_vector = self._tfidf_vector(query, document_frequencies, len(candidates))

        matches = []
        for row, record_tags in candidates:
            document_vector = self._tfidf_vector(
                f"{row['title']} {row['content']}",
                document_frequencies,
                len(candidates),
            )
            score = self._cosine_similarity(query_vector, document_vector)
            if score <= 0:
                continue
            matches.append(
                {
                    "memory_id": row["memory_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "tags": record_tags,
                    "created_at": row["created_at"],
                    "similarity_score": round(score, 6),
                    "citation": {
                        "source": "Explicitly saved user memory",
                        "source_document": row["title"],
                        "source_location": f"lab4-memory://{row['memory_id']}",
                    },
                }
            )

        matches.sort(key=lambda item: (-item["similarity_score"], item["created_at"], item["memory_id"]))
        result = {
            "query": query,
            "course_id": course_id,
            "match_count": min(len(matches), top_k),
            "matches": matches[:top_k],
            "retrieval_method": "local_tfidf_cosine_lexical",
            "embedding_similarity": False,
            "limitation": (
                "Similarity uses local token-based TF-IDF cosine, not semantic embeddings. "
                "Paraphrases without shared vocabulary may not be retrieved."
            ),
        }
        if fallback_reason is not None:
            result.update(
                {
                    "requested_retrieval_mode": "semantic",
                    "fallback_reason": fallback_reason,
                }
            )
        return result

    def search_similar_submissions(
        self,
        *,
        course_id: str,
        query: str,
        student_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        top_k: int = 5,
        retrieval_mode: str = "lexical",
    ) -> dict[str, Any]:
        """Find scoped prior submissions by lexical or semantic metadata similarity, not source code."""
        if retrieval_mode == "semantic":
            try:
                return self._semantic_submission_search(
                    course_id=course_id,
                    query=query,
                    student_id=student_id,
                    tags=tags,
                    top_k=top_k,
                )
            except EmbeddingUnavailableError as exc:
                logger.warning("Semantic submission search unavailable; using labeled lexical fallback: %s", exc)
                fallback_reason = str(exc)
        elif retrieval_mode != "lexical":
            raise ValueError("Retrieval mode must be 'lexical' or 'semantic'.")
        else:
            fallback_reason = None

        sql = """
            SELECT s.id, s.assignment_id, a.title AS assignment_title, s.student_id,
                s.course_id, s.repo_name, s.submission_timestamp, s.attempt_number,
                s.status, s.validation_status, s.notes
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            WHERE s.course_id = ?
        """
        params: list[Any] = [course_id]
        if student_id is not None:
            sql += " AND s.student_id = ?"
            params.append(student_id)
        sql += " ORDER BY s.submission_timestamp DESC, s.id"
        with get_db_connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        wanted_tags = {tag.casefold() for tag in (tags or []) if tag.strip()}
        candidates = []
        for row in rows:
            row_tags = {row["assignment_id"].casefold(), row["assignment_title"].casefold()}
            if wanted_tags and not any(
                tag in candidate_tag or candidate_tag in tag
                for tag in wanted_tags
                for candidate_tag in row_tags
            ):
                continue
            text = " ".join(
                str(value or "")
                for value in (
                    row["assignment_id"],
                    row["assignment_title"],
                    row["repo_name"],
                    row["notes"],
                    row["status"],
                    row["validation_status"],
                )
            )
            candidates.append((row, text))

        document_frequencies: Counter[str] = Counter()
        for _, text in candidates:
            document_frequencies.update(set(self._tokens(text)))
        query_vector = self._tfidf_vector(query, document_frequencies, len(candidates))

        matches = []
        for row, text in candidates:
            score = self._cosine_similarity(
                query_vector,
                self._tfidf_vector(text, document_frequencies, len(candidates)),
            )
            if score <= 0:
                continue
            matches.append(
                {
                    "submission_id": row["id"],
                    "assignment_id": row["assignment_id"],
                    "assignment_title": row["assignment_title"],
                    "student_id": row["student_id"],
                    "course_id": row["course_id"],
                    "submitted_at": row["submission_timestamp"],
                    "attempt_number": row["attempt_number"],
                    "status": row["status"],
                    "validation_status": row["validation_status"],
                    "similarity_score": round(score, 6),
                    "citation": {
                        "source": "Stored assignment submission metadata",
                        "source_document": row["assignment_title"],
                        "source_location": f"/api/submissions/detail/{row['id']}",
                    },
                }
            )
        matches.sort(key=lambda item: (-item["similarity_score"], item["submitted_at"], item["submission_id"]))
        result = {
            "query": query,
            "course_id": course_id,
            "match_count": min(len(matches), top_k),
            "matches": matches[:top_k],
            "retrieval_method": "local_tfidf_cosine_submission_metadata",
            "source_code_analyzed": False,
            "limitation": (
                "Similarity is calculated from stored assignment titles, repository names, student notes, and "
                "validation labels. Repository source code is not fetched or analyzed; results are retrieval "
                "candidates and not plagiarism findings."
            ),
        }
        if fallback_reason is not None:
            result.update(
                {
                    "requested_retrieval_mode": "semantic",
                    "fallback_reason": fallback_reason,
                }
            )
        return result

    def rebuild_embeddings(self, *, course_id: Optional[str] = None, batch_size: int = 64) -> dict[str, int]:
        """Create or refresh scoped embeddings in bounded batches for the explicit CLI command."""
        if not 1 <= batch_size <= 512:
            raise ValueError("Embedding batch size must be between 1 and 512.")

        totals = {"memory_records": 0, "submission_records": 0, "embeddings_updated": 0}
        last_memory_id = ""
        while True:
            sql = """
                SELECT m.memory_id, m.user_id AS owner_id, m.course_id, m.title, m.content,
                    m.tags_json, m.created_at,
                    e.owner_id AS embedding_owner_id,
                    e.course_id AS embedding_course_id,
                    e.model_id AS embedding_model_id,
                    e.model_revision AS embedding_model_revision,
                    e.embedding_dimension, e.text_hash AS embedding_text_hash,
                    e.embedding AS embedding_blob
                FROM lab4_memory_records m
                LEFT JOIN lab4_memory_embeddings e ON e.memory_id = m.memory_id
                WHERE m.memory_id > ?
            """
            params: list[Any] = [last_memory_id]
            if course_id is not None:
                sql += " AND m.course_id = ?"
                params.append(course_id)
            sql += " ORDER BY m.memory_id LIMIT ?"
            params.append(batch_size)
            with get_db_connection() as conn:
                rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            if not rows:
                break
            _, updated = self._ensure_embedding_vectors(
                rows,
                source_id_column="memory_id",
                embedding_table="lab4_memory_embeddings",
                text_factory=self._memory_embedding_text,
            )
            totals["memory_records"] += len(rows)
            totals["embeddings_updated"] += updated
            last_memory_id = str(rows[-1]["memory_id"])

        last_submission_id = ""
        while True:
            sql = """
                SELECT s.id, s.student_id AS owner_id, s.course_id, s.assignment_id,
                    a.title AS assignment_title, s.repo_name, s.notes,
                    s.submission_timestamp, s.attempt_number, s.status, s.validation_status,
                    e.owner_id AS embedding_owner_id,
                    e.course_id AS embedding_course_id,
                    e.model_id AS embedding_model_id,
                    e.model_revision AS embedding_model_revision,
                    e.embedding_dimension, e.text_hash AS embedding_text_hash,
                    e.embedding AS embedding_blob
                FROM submissions s
                JOIN assignments a ON a.id = s.assignment_id
                LEFT JOIN lab4_submission_embeddings e ON e.submission_id = s.id
                WHERE s.id > ?
            """
            params = [last_submission_id]
            if course_id is not None:
                sql += " AND s.course_id = ?"
                params.append(course_id)
            sql += " ORDER BY s.id LIMIT ?"
            params.append(batch_size)
            with get_db_connection() as conn:
                rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
            if not rows:
                break
            _, updated = self._ensure_embedding_vectors(
                rows,
                source_id_column="id",
                embedding_id_column="submission_id",
                embedding_table="lab4_submission_embeddings",
                text_factory=self._submission_embedding_text,
            )
            totals["submission_records"] += len(rows)
            totals["embeddings_updated"] += updated
            last_submission_id = str(rows[-1]["id"])
        return totals

    def delete_memory(self, *, memory_id: str, user_id: str, course_id: str) -> bool:
        """Delete only an explicitly saved memory owned by the requesting user."""
        with get_db_connection(immediate=True) as conn:
            cursor = conn.execute(
                """
                DELETE FROM lab4_memory_records
                WHERE memory_id = ? AND user_id = ? AND course_id = ?
                """,
                (memory_id, user_id, course_id),
            )
            return cursor.rowcount > 0

    def get_indexed_chapters(self) -> list[int]:
        """Return distinct chapters indexed in the knowledge base."""
        stats = self._service.initialize()
        return sorted(list(stats.chapters_indexed))

    def get_indexed_tags(self) -> list[str]:
        """Return available topic tags from indexed documents."""
        if not self._service._is_initialized:
            self._service.initialize()

        tags_set = set()
        for chunk in self._service._all_chunks:
            tags_set.update(chunk.tags)
        return sorted(list(tags_set))


# Global singleton instance
long_term_store = LongTermKnowledgeStore()
