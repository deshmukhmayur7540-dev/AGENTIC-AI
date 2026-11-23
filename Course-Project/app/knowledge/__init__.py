"""Course knowledge ingestion, indexing, and retrieval package for Agentic AI (26ECAC401)."""

from app.knowledge.models import (
    CourseKnowledgeChunk,
    CourseKnowledgeMatch,
    DiscoveredDocument,
    KnowledgeQuery,
    KnowledgeSearchResult,
)
from app.knowledge.service import KnowledgeService, knowledge_service

__all__ = [
    "CourseKnowledgeChunk",
    "CourseKnowledgeMatch",
    "DiscoveredDocument",
    "KnowledgeQuery",
    "KnowledgeSearchResult",
    "KnowledgeService",
    "knowledge_service",
]
