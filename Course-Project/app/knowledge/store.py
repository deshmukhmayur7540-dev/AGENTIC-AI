"""Local deterministic knowledge store and BM25 ranking index for course documents."""

import math
import re
from abc import ABC, abstractmethod
from typing import Optional

from app.knowledge.models import (
    CourseKnowledgeChunk,
    CourseKnowledgeMatch,
    KnowledgeIndexStats,
    KnowledgeQuery,
    KnowledgeSearchResult,
)


class BaseKnowledgeStore(ABC):
    """Abstract interface for storing and retrieving course knowledge chunks."""

    @abstractmethod
    def add_chunks(self, chunks: list[CourseKnowledgeChunk]) -> None:
        """Index a batch of knowledge chunks."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        """Retrieve the top-k matching chunks for a query."""
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> KnowledgeIndexStats:
        """Retrieve index statistics."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all indexed data."""
        raise NotImplementedError


class DeterministicBM25Index(BaseKnowledgeStore):
    """Local, deterministic BM25-based retrieval index with heading and tag weighting.

    Provides high-precision local search across course notes without requiring external
    paid embedding APIs. Architected cleanly to allow swapping with vector embeddings later.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: dict[str, CourseKnowledgeChunk] = {}
        # Inverted index: token -> dict(chunk_id -> term_frequency)
        self._inverted_index: dict[str, dict[str, int]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._chapters: set[int] = set()

    def add_chunks(self, chunks: list[CourseKnowledgeChunk]) -> None:
        """Add knowledge chunks to the deterministic in-memory index."""
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
            if chunk.chapter is not None:
                self._chapters.add(chunk.chapter)

            tokens = self._tokenize(chunk.content)
            doc_len = len(tokens)
            self._doc_lengths[chunk.id] = doc_len

            # Record term frequencies
            tf_map: dict[str, int] = {}
            for t in tokens:
                tf_map[t] = tf_map.get(t, 0) + 1

            for token, freq in tf_map.items():
                if token not in self._inverted_index:
                    self._inverted_index[token] = {}
                self._inverted_index[token][chunk.id] = freq

        # Recalculate average document length
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def search(self, query: KnowledgeQuery) -> KnowledgeSearchResult:
        """Execute deterministic BM25 search with section title and tag boosting."""
        if not self._chunks:
            return KnowledgeSearchResult(
                course_id=query.course_id,
                query=query.query,
                matches=[],
                match_count=0,
                source="Deterministic Course Knowledge Store (Empty)",
            )

        course_chunks = {
            chunk_id: chunk
            for chunk_id, chunk in self._chunks.items()
            if chunk.course_code.strip().upper() == query.course_id.strip().upper()
        }
        if not course_chunks:
            return KnowledgeSearchResult(
                course_id=query.course_id,
                query=query.query,
                matches=[],
                match_count=0,
                source=f"Course '{query.course_id}' is not indexed in this knowledge base.",
            )

        query_tokens = self._tokenize(query.query)
        if not query_tokens:
            return KnowledgeSearchResult(
                course_id=query.course_id,
                query=query.query,
                matches=[],
                match_count=0,
                source="Deterministic Course Knowledge Store",
            )

        total_docs = len(course_chunks)
        course_avg_doc_length = sum(
            self._doc_lengths.get(chunk_id, 0) for chunk_id in course_chunks
        ) / total_docs
        scores: dict[str, float] = {}
        norm_query_str = query.query.lower().strip()

        for token in query_tokens:
            postings = self._inverted_index.get(token, {})
            course_postings = {
                chunk_id: tf
                for chunk_id, tf in postings.items()
                if chunk_id in course_chunks
            }
            df = len(course_postings)
            if df == 0:
                continue

            # Standard BM25 IDF
            idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))

            for chunk_id, tf in course_postings.items():
                chunk = course_chunks[chunk_id]

                # Chapter filter
                if query.chapter is not None and chunk.chapter != query.chapter:
                    continue

                # Tag filter
                if query.tags:
                    if not any(t.lower() in [ct.lower() for ct in chunk.tags] for t in query.tags):
                        continue

                doc_len = self._doc_lengths.get(chunk_id, 1)
                tf_denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (course_avg_doc_length or 1.0)))
                bm25_tf = (tf * (self.k1 + 1.0)) / tf_denom

                scores[chunk_id] = scores.get(chunk_id, 0.0) + (idf * bm25_tf)

        # Apply structural multipliers: Title match, Tag match, Exact phrase match
        for chunk_id in list(scores.keys()):
            chunk = course_chunks[chunk_id]
            multiplier = 1.0

            title_lower = chunk.section_topic.lower()
            content_lower = chunk.content.lower()

            # Exact phrase match in content
            if norm_query_str in content_lower:
                multiplier += 0.5

            # Match in section title
            for token in query_tokens:
                if token in title_lower:
                    multiplier += 0.4

            # Match in tags
            for tag in chunk.tags:
                if any(qt in tag.lower() for qt in query_tokens):
                    multiplier += 0.3

            scores[chunk_id] = scores[chunk_id] * multiplier

        # Filter and rank by score descending
        # Require meaningful term coverage for multi-word queries to avoid false positives
        filtered_ranked = []
        for cid, sc in sorted(scores.items(), key=lambda item: item[1], reverse=True):
            matched_terms = [
                t for t in query_tokens
                if cid in self._inverted_index.get(t, {}) and cid in course_chunks
            ]
            # If 2-word query, require both terms to avoid single-word metaphorical false positives
            if len(query_tokens) == 2 and len(matched_terms) < 2:
                continue
            # If multi-word query (>= 3 words), require at least 50% term coverage
            if len(query_tokens) >= 3 and len(matched_terms) / len(query_tokens) < 0.5:
                continue
            # Minimum substantive score threshold
            if sc < 1.5:
                continue
            if sc >= query.min_score:
                filtered_ranked.append((cid, sc))

        top_matches: list[CourseKnowledgeMatch] = []
        for chunk_id, score in filtered_ranked[: query.top_k]:
            chunk = course_chunks[chunk_id]
            source_citation = (
                f"{chunk.source_document} ({chunk.source_location})"
                if chunk.source_location
                else chunk.source_document
            )
            top_matches.append(
                CourseKnowledgeMatch(
                    chunk_id=chunk.id,
                    chapter=chunk.chapter,
                    topic=chunk.section_topic,
                    matched_text=chunk.content,
                    source=source_citation,
                    source_document=chunk.source_document,
                    source_location=chunk.source_location,
                    source_chapter=chunk.chapter,
                    category=chunk.category,
                    lab=chunk.lab,
                    folder_path=chunk.folder_path,
                    material_id=chunk.material_id,
                    tags=chunk.tags,
                    score=round(score, 4),
                    version=chunk.version,
                )
            )

        return KnowledgeSearchResult(
            course_id=query.course_id,
            query=query.query,
            matches=top_matches,
            match_count=len(top_matches),
            source=f"Course Knowledge Store ({len(course_chunks)} chunks across {len(self._chapters)} known chapters)",
        )

    def get_stats(self) -> KnowledgeIndexStats:
        """Compute aggregated index statistics."""
        total_words = sum(c.word_count for c in self._chunks.values())
        return KnowledgeIndexStats(
            total_documents=len({c.source_document for c in self._chunks.values()}),
            total_chunks=len(self._chunks),
            chapters_indexed=sorted(list(self._chapters)),
            total_words=total_words,
        )

    def clear(self) -> None:
        """Clear in-memory indexed structures."""
        self._chunks.clear()
        self._inverted_index.clear()
        self._doc_lengths.clear()
        self._avg_doc_length = 0.0
        self._chapters.clear()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Normalize and tokenize text into lowercase word tokens, filtering common stopwords."""
        stop_words = {
            "a", "an", "the", "is", "in", "on", "of", "to", "for", "with", "and", "or",
            "by", "at", "from", "as", "it", "this", "that", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "non", "what",
            "how", "why", "which", "where", "who", "when", "can", "could", "should",
            "explain", "describe", "tell", "show", "give", "about", "me", "any", "some",
            "please", "concepts",
        }
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower().replace("-", " ").replace("—", " ").replace("–", " "))
        tokens = [
            t for t in cleaned.split()
            if len(t) >= 2 and t not in stop_words
        ]
        return tokens
