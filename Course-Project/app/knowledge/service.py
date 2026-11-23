"""High-level KnowledgeService coordinating document discovery, extraction, chunking, and retrieval."""

import logging
from pathlib import Path
from typing import Optional

from app.knowledge.chunker import CourseDocumentChunker
from app.knowledge.discovery import DocumentDiscovery
from app.knowledge.extractors import DocumentExtractorRegistry
from app.knowledge.models import (
    CourseKnowledgeChunk,
    DiscoveredDocument,
    ExtractedSection,
    KnowledgeIndexStats,
    KnowledgeQuery,
    KnowledgeSearchResult,
)
from app.knowledge.store import BaseKnowledgeStore, DeterministicBM25Index

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service orchestrating the complete lifecycle of course documents to indexed knowledge."""

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        store: Optional[BaseKnowledgeStore] = None,
        include_course_materials: bool | None = None,
    ) -> None:
        self.discovery = DocumentDiscovery(base_dir=base_dir)
        self.include_course_materials = base_dir is None if include_course_materials is None else include_course_materials
        self.extractor_registry = DocumentExtractorRegistry()
        self.chunker = CourseDocumentChunker()
        self.store = store or DeterministicBM25Index()
        self._is_initialized = False
        self._discovered_docs: list[DiscoveredDocument] = []
        self._indexed_source_hashes: dict[str, str] = {}
        self._all_chunks: list[CourseKnowledgeChunk] = []

    def initialize(self, force_reload: bool = False) -> KnowledgeIndexStats:
        """Scan knowledge directory, extract and chunk all documents, and populate the index."""
        if self._is_initialized and not force_reload:
            return self.store.get_stats()

        logger.info("Initializing course knowledge layer from documents...")
        self._is_initialized = False
        self.store.clear()
        self._indexed_source_hashes.clear()
        self._all_chunks.clear()

        # Step 1: Discover documents in knowledge/agentic_ai/
        discovered_docs = self.discovery.discover()
        if self.include_course_materials:
            discovered_docs.extend(DocumentDiscovery.discover_course_materials())
        logger.info("Discovered %d course documents.", len(discovered_docs))

        # Step 2: Extract & Chunk each discovered document
        indexed_docs: list[DiscoveredDocument] = []
        for doc in discovered_docs:
            try:
                sections = self.extractor_registry.extract(doc)
                if doc.material_id and (doc.title or doc.description):
                    metadata = "\n".join(
                        value for value in (doc.title, doc.description) if value
                    )
                    sections.insert(
                        0,
                        ExtractedSection(
                            title=doc.title or doc.source_filename,
                            content=metadata,
                            source_location="Material description",
                            sequence_index=0,
                        ),
                    )
                chunks = self.chunker.chunk_document(doc, sections)
                if not chunks:
                    continue
                self._all_chunks.extend(chunks)
                self.store.add_chunks(chunks)
                indexed_docs.append(doc)
                self._indexed_source_hashes[str(Path(doc.source_path).resolve())] = doc.content_hash
                logger.debug(
                    "Indexed %s (Chapter %s): %d sections -> %d chunks",
                    doc.source_filename,
                    doc.chapter,
                    len(sections),
                    len(chunks),
                )
            except Exception as err:
                logger.error("Failed to process document %s: %s", doc.source_filename, err)

        self._discovered_docs = indexed_docs
        self._is_initialized = True
        stats = self.store.get_stats()
        logger.info(
            "Knowledge initialization complete: %d documents, %d chunks, %d words across chapters %s",
            stats.total_documents,
            stats.total_chunks,
            stats.total_words,
            stats.chapters_indexed,
        )
        return stats

    def search(
        self,
        query: str,
        course_id: str = "26ECAC401",
        chapter: Optional[int] = None,
        tags: Optional[list[str]] = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> KnowledgeSearchResult:
        """Query the knowledge base with optional chapter/tag filtering."""
        if not self._is_initialized:
            self.initialize()

        k_query = KnowledgeQuery(
            course_id=course_id,
            query=query,
            chapter=chapter,
            tags=tags,
            top_k=top_k,
            min_score=min_score,
        )
        return self.store.search(k_query)

    def get_discovered_documents(self) -> list[DiscoveredDocument]:
        """Return metadata for documents that produced indexed chunks."""
        if not self._is_initialized:
            self.initialize()
        return list(self._discovered_docs)

    def get_indexed_source_paths(self) -> set[str]:
        """Return resolved source paths represented by at least one live index chunk."""
        if not self._is_initialized:
            self.initialize()
        return set(self._indexed_source_hashes)

    def get_indexed_source_hashes(self) -> dict[str, str]:
        """Return content hashes for source files represented by the live index."""
        if not self._is_initialized:
            self.initialize()
        return dict(self._indexed_source_hashes)

    def get_chunks(self) -> list[CourseKnowledgeChunk]:
        """Return all indexed knowledge chunks."""
        if not self._is_initialized:
            self.initialize()
        return list(self._all_chunks)

    def get_stats(self) -> KnowledgeIndexStats:
        """Return statistical metrics of the knowledge base."""
        if not self._is_initialized:
            self.initialize()
        return self.store.get_stats()


# Shared singleton instance
knowledge_service = KnowledgeService()
