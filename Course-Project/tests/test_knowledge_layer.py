"""Unit and integration tests for the Course Knowledge Ingestion and Retrieval Layer.

Verifies:
- Document discovery across Chapters 1-4
- Document extraction and coherent chunking
- Correct Course Code (26ECAC401) and Course Name (Agentic AI)
- Grounded Chapter 1, Chapter 2, Chapter 3, and Chapter 4 retrieval
- Source metadata preservation (filename, location, chapter)
- Anti-fabrication guarantees on unsupported terms
- Integration with Lab 2 SearchCourseNotesTool
"""

import pytest
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from app.knowledge.discovery import DocumentDiscovery
from app.knowledge.catalog import KnowledgeFileCatalog
from app.knowledge.models import CourseKnowledgeChunk, DiscoveredDocument, KnowledgeSearchResult
from app.knowledge.service import KnowledgeService, knowledge_service
from app.labs.lab2.tools.notes import SearchCourseNotesTool
from app.models.lab2_models import ToolExecutionStatus
from config import settings


# =========================================================================
# 1. Document Discovery Tests
# =========================================================================
def test_discovery_all_four_chapters():
    """Verify that document discovery scans knowledge/agentic_ai/ and finds all 4 chapters."""
    discovery = DocumentDiscovery()
    documents = discovery.discover()

    assert len(documents) >= 8, f"Expected at least 8 documents, discovered {len(documents)}"

    discovered_chapters = {doc.chapter for doc in documents}
    assert {1, 2, 3, 4}.issubset(discovered_chapters), f"Missing chapters: {discovered_chapters}"

    for doc in documents:
        assert isinstance(doc, DiscoveredDocument)
        assert doc.course_code == "26ECAC401"
        assert doc.course_name == "Agentic AI"
        assert doc.chapter in [1, 2, 3, 4]
        assert doc.document_type in ["docx", "pptx", "txt", "md", "markdown", "pdf", "csv"]
        assert doc.file_size_bytes > 0
        assert len(doc.content_hash) == 64  # Valid SHA256 hex string
        assert doc.source_filename != ""


# =========================================================================
# 2. Document Extraction & Knowledge Index Stats
# =========================================================================
def test_actual_documents_loaded_and_stats():
    """Verify that all four chapters are parsed, chunked, and indexed with substantial content."""
    stats = knowledge_service.get_stats()

    assert stats.total_documents >= 8
    assert stats.total_chunks >= 100
    assert stats.chapters_indexed == [1, 2, 3, 4]
    assert stats.total_words > 10000


def test_agentic_ai_course_metadata():
    """Verify that all generated chunks strictly adhere to course code 26ECAC401."""
    chunks = knowledge_service.get_chunks()
    assert len(chunks) > 0

    for chunk in chunks[:50]:  # Sample first 50 chunks
        assert isinstance(chunk, CourseKnowledgeChunk)
        assert chunk.course_code == "26ECAC401"
        assert chunk.course_name == "Agentic AI"
        assert chunk.chapter in [1, 2, 3, 4]
        assert len(chunk.content) > 10
        assert chunk.source_document != ""
        assert len(chunk.tags) >= 1
        assert f"chapter-{chunk.chapter}" in chunk.tags


# =========================================================================
# 3. Chapter 1 Retrieval Tests
# =========================================================================
def test_chapter_1_retrieval_plan_act_observe_revise():
    """Verify that a query for Plan-Act-Observe-Revise retrieves evidence from actual Chapter 1 documents."""
    result = knowledge_service.search("What is Plan-Act-Observe-Revise?", chapter=1, top_k=3)

    assert isinstance(result, KnowledgeSearchResult)
    assert result.match_count >= 1
    assert all(m.chapter == 1 for m in result.matches)

    top_match = result.matches[0]
    assert top_match.chapter == 1
    assert "Chapter1" in top_match.source_document or "Three Sentence Notes" in top_match.source_document
    assert top_match.score > 0.0


def test_chapter_1_retrieval_react_foundations():
    """Verify that ReAct keyword queries pull verified evidence from Chapter 1."""
    result = knowledge_service.search("ReAct reasoning and acting loop", chapter=1, top_k=3)

    assert result.match_count >= 1
    top_match = result.matches[0]
    assert top_match.chapter == 1
    assert "react" in top_match.matched_text.lower() or "react" in top_match.topic.lower()


# =========================================================================
# 4. Chapter 2 Retrieval Tests
# =========================================================================
def test_chapter_2_retrieval_function_calling():
    """Verify that queries for function calling retrieve evidence from actual Chapter 2 documents."""
    result = knowledge_service.search("What is function calling?", chapter=2, top_k=3)

    assert result.match_count >= 1
    assert all(m.chapter == 2 for m in result.matches)

    top_match = result.matches[0]
    assert top_match.chapter == 2
    assert "Chapter2" in top_match.source_document or "Chapter_2" in top_match.source_document
    assert "function" in top_match.matched_text.lower() or "tool" in top_match.matched_text.lower()


def test_chapter_2_retrieval_langgraph_memory():
    """Verify that memory and framework queries retrieve Chapter 2 materials."""
    result = knowledge_service.search("memory and state management", chapter=2, top_k=3)

    assert result.match_count >= 1
    top_match = result.matches[0]
    assert top_match.chapter == 2
    assert "memory" in top_match.matched_text.lower() or "state" in top_match.matched_text.lower()


# =========================================================================
# 5. Chapter 3 and Chapter 4 Discovery and Retrieval Tests
# =========================================================================
def test_chapter_3_indexed_and_retrievable():
    """Verify that Chapter 3 (Multi-Agent Orchestration) is indexed and retrievable."""
    result = knowledge_service.search("multi-agent coordination strategies", chapter=3, top_k=3)

    assert result.match_count >= 1
    top_match = result.matches[0]
    assert top_match.chapter == 3
    assert top_match.source_document.lower().startswith(("chapter_3", "chapter3"))
    assert "coordination" in top_match.matched_text.lower() or "multi-agent" in top_match.matched_text.lower()


def test_chapter_4_indexed_and_retrievable():
    """Verify that Chapter 4 (Learning, Deployment, Safety & Governance) is indexed and retrievable."""
    result = knowledge_service.search("RLHF alignment and safety", chapter=4, top_k=3)

    assert result.match_count >= 1
    top_match = result.matches[0]
    assert top_match.chapter == 4
    assert top_match.source_document.lower().startswith(("chapter_4", "chapter4"))
    assert "rlhf" in top_match.matched_text.lower() or "alignment" in top_match.matched_text.lower() or "safety" in top_match.matched_text.lower()


# =========================================================================
# 6. Source Metadata Preservation
# =========================================================================
def test_source_metadata_preserved():
    """Verify that retrieved matches contain complete provenance citations and locations."""
    result = knowledge_service.search("autonomous agents", top_k=5)

    assert result.match_count >= 1
    for match in result.matches:
        assert match.source_document.endswith((".docx", ".pptx", ".txt", ".md", ".markdown", ".pdf", ".csv"))
        assert match.source_chapter in [1, 2, 3, 4]
        assert match.source != ""
        assert len(match.tags) >= 1
        assert match.score > 0.0


def _write_text_pdf(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    fonts = DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
    stream = DecodedStreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 10 40 Td ({escaped}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as target:
        writer.write(target)


def test_nested_supported_formats_index_with_stable_source_metadata(tmp_path, monkeypatch):
    """Nested supported course documents are indexed with course-relative citations."""
    from docx import Document
    from pptx import Presentation

    knowledge_root = tmp_path / "knowledge"
    course_root = knowledge_root / "agentic_ai"
    nested = course_root / "chapter_2" / "nested"
    nested.mkdir(parents=True)
    body = "Chapter 2 nested evidence describes tools, function calling, memory and retrieval."
    (nested / "Chapter2_nested_notes.txt").write_text(body, encoding="utf-8")
    (nested / "Chapter2_nested_notes.md").write_text(body, encoding="utf-8")
    (nested / "Chapter2_nested_notes.markdown").write_text(body, encoding="utf-8")
    (nested / "Chapter2_nested_notes.csv").write_text("topic,details\nmemory," + body + "\n", encoding="utf-8")
    _write_text_pdf(nested / "Chapter2_nested_notes.pdf", body)

    word = Document()
    word.add_paragraph(body)
    word.save(nested / "Chapter2_nested_notes.docx")
    slides = Presentation()
    slide = slides.slides.add_slide(slides.slide_layouts[5])
    slide.shapes.title.text = "Nested function calling"
    slide.shapes.add_textbox(0, 1000000, 6000000, 2000000).text_frame.text = body
    slides.save(nested / "Chapter2_nested_notes.pptx")

    (nested / "Chapter2_unsupported.exe").write_bytes(b"not a course document")
    (nested / "Chapter2_corrupt.docx").write_bytes(b"not a DOCX archive")
    (nested / "Chapter2_corrupt.pdf").write_bytes(b"not a PDF")
    unrelated = knowledge_root / "another_course" / "chapter_2"
    unrelated.mkdir(parents=True)
    (unrelated / "Chapter2_outside.txt").write_text(body, encoding="utf-8")

    discovery = DocumentDiscovery(course_root)
    discovered = discovery.discover()
    assert {doc.document_type for doc in discovered} == {
        "docx", "pptx", "txt", "md", "markdown", "pdf", "csv",
    }
    assert all(Path(doc.source_path).is_relative_to(course_root.resolve()) for doc in discovered)
    assert not any(doc.source_filename.endswith(".exe") for doc in discovered)
    assert not any("outside" in doc.source_filename for doc in discovered)

    service = KnowledgeService(base_dir=course_root)
    service.initialize()
    indexed = service.get_discovered_documents()
    assert {doc.document_type for doc in indexed} == {
        "docx", "pptx", "txt", "md", "markdown", "pdf", "csv",
    }
    assert all(doc.source_filename != "Chapter2_corrupt.docx" for doc in indexed)
    assert all(doc.source_filename != "Chapter2_corrupt.pdf" for doc in indexed)

    result = service.search(body, chapter=2, top_k=20)
    citations = {match.source_document for match in result.matches}
    assert any("Chapter2_nested_notes.txt" in path for path in citations), citations
    assert all("chapter_2" in path.lower() and "nested" in path.lower() for path in citations)
    assert all(match.source_chapter == 2 and match.source for match in result.matches)

    monkeypatch.setattr(settings, "knowledge_root", str(knowledge_root))
    import app.knowledge.service as knowledge_service_module
    monkeypatch.setattr(knowledge_service_module, "knowledge_service", service)
    records = {record.relative_path: record for record in KnowledgeFileCatalog(knowledge_root).list_files()}
    assert records["agentic_ai/chapter_2/nested/Chapter2_nested_notes.txt"].indexed is True
    assert records["agentic_ai/chapter_2/nested/Chapter2_corrupt.docx"].indexed is False
    assert records["another_course/chapter_2/Chapter2_outside.txt"].indexed is False
    (nested / "Chapter2_nested_notes.txt").write_text("replaced content", encoding="utf-8")
    refreshed_records = {
        record.relative_path: record
        for record in KnowledgeFileCatalog(knowledge_root).list_files()
    }
    assert refreshed_records["agentic_ai/chapter_2/nested/Chapter2_nested_notes.txt"].indexed is False


# =========================================================================
# 7. Anti-Fabrication Guarantees
# =========================================================================
def test_unsupported_facts_return_no_fabricated_evidence():
    """Verify that queries for unsupported topics return 0 matches without hallucination."""
    result = knowledge_service.search("quantum gravity non-existent", course_id="26ECAC401")
    assert result.match_count == 0
    assert result.matches == []


def test_unknown_course_returns_zero_matches():
    """Verify that queries for unknown course codes return no matches."""
    result = knowledge_service.search("autonomous agents", course_id="UNKNOWN999")
    # KnowledgeService returns empty matches for unknown course codes
    assert result.match_count == 0
    assert result.matches == []


# =========================================================================
# 8. Chapter Filtering Accuracy
# =========================================================================
def test_chapter_filtering():
    """Verify that chapter filtering strictly isolates matches to the requested chapter."""
    res_ch1 = knowledge_service.search("agents", chapter=1, top_k=5)
    assert all(m.chapter == 1 for m in res_ch1.matches)

    res_ch3 = knowledge_service.search("agents", chapter=3, top_k=5)
    assert all(m.chapter == 3 for m in res_ch3.matches)


# =========================================================================
# 9. Lab 2 Tool Integration
# =========================================================================
def test_lab2_tool_retrieves_from_actual_documents():
    """Verify that Lab 2 SearchCourseNotesTool queries the knowledge layer and returns verified evidence."""
    tool = SearchCourseNotesTool()

    # Search for ReAct
    record = tool.execute({"course_id": "26ECAC401", "query": "react"})
    assert record.status == ToolExecutionStatus.SUCCESS
    assert record.output_data is not None
    assert record.output_data["match_count"] >= 1

    matches = record.output_data["matches"]
    assert any("Chapter1" in m["source_document"] or "Three Sentence Notes" in m["source_document"] for m in matches)

    # Search for function calling
    record_fc = tool.execute({"course_id": "26ECAC401", "query": "function calling"})
    assert record_fc.status == ToolExecutionStatus.SUCCESS
    matches_fc = record_fc.output_data["matches"]
    assert any("Chapter2" in m["source_document"] or "Chapter_2" in m["source_document"] for m in matches_fc)

    # Search for non-existent topic
    record_none = tool.execute({"course_id": "26ECAC401", "query": "quantum gravity non-existent"})
    assert record_none.status == ToolExecutionStatus.SUCCESS
    assert record_none.output_data["match_count"] == 0
