"""NotesDataSource: Governed access to indexed Chapter 1-4 course notes."""

from typing import Any
from app.knowledge.service import knowledge_service
from app.labs.lab5.sources.base_source import BaseDataSource
from app.models.lab5_models import ConnectorOperation, ConnectorRole


class NotesDataSource(BaseDataSource):
    """Governed connector data source for course lecture notes and materials."""

    source_id = "notes_source"
    name = "Authoritative Lecture Notes & Documents"
    source_type = "NOTES"
    description = "Governed access to indexed Chapter 1-4 lecture notes, slides, and syllabus documents."
    supported_operations = [
        ConnectorOperation.READ,
        ConnectorOperation.SEARCH,
        ConnectorOperation.LIST,
    ]
    is_read_only = True
    requires_auth = False

    def execute(
        self,
        operation: ConnectorOperation,
        resource_path: str,
        parameters: dict[str, Any],
        role: ConnectorRole,
    ) -> tuple[Any, str]:
        course_id = parameters.get("course_id", "26ECAC401")

        if operation == ConnectorOperation.SEARCH:
            query = parameters.get("query", "")
            chapter = parameters.get("chapter")
            top_k = parameters.get("top_k", 4)
            res = knowledge_service.search(query=query, course_id=course_id, chapter=chapter, top_k=top_k)
            matches = [
                {
                    "chapter": m.chapter,
                    "topic": m.topic,
                    "matched_text": m.matched_text,
                    "source": m.source,
                    "source_document": m.source_document,
                    "score": round(m.score, 4),
                }
                for m in res.matches
            ]
            return {
                "query": query,
                "matches": matches,
                "count": len(matches),
            }, res.source

        elif operation == ConnectorOperation.READ:
            # Resource path is chapter number, e.g. "chapter/1"
            target_ch = int(parameters.get("chapter", 1))
            res = knowledge_service.search(query="", course_id=course_id, chapter=target_ch, top_k=6)
            return {
                "chapter": target_ch,
                "sections_count": len(res.matches),
                "sections": [{"topic": m.topic, "text": m.matched_text[:300]} for m in res.matches],
            }, f"26ECAC401 Chapter {target_ch} Syllabus Notes"

        elif operation == ConnectorOperation.LIST:
            stats = knowledge_service.initialize()
            return {
                "chapters_indexed": list(stats.chapters_indexed),
                "total_documents": stats.total_documents,
                "total_chunks": stats.total_chunks,
            }, "Knowledge Service Directory Index"

        raise ValueError(f"Operation '{operation}' not supported by NotesDataSource.")
