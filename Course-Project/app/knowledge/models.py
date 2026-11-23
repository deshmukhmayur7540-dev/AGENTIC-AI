"""Pydantic data models for the course knowledge ingestion, indexing, and retrieval layer."""

from typing import Optional
from pydantic import BaseModel, Field


class DiscoveredDocument(BaseModel):
    """Metadata representing a discovered course document in the knowledge folder."""

    document_id: str = Field(description="Unique deterministic ID of the discovered document")
    course_code: str = Field(default="26ECAC401", description="Official university course code")
    course_name: str = Field(default="Agentic AI", description="Official university course title")
    chapter: Optional[int] = Field(default=None, ge=1, le=14, description="Academic chapter, when associated")
    source_filename: str = Field(description="Base filename of the document")
    source_relative_path: str = Field(default="", description="Stable path relative to the course knowledge root")
    source_path: str = Field(description="Absolute or relative file path to the source document")
    document_type: str = Field(description="Normalized file extension/type (e.g. docx, pptx)")
    file_size_bytes: int = Field(ge=0, description="Size of the file on disk in bytes")
    content_hash: str = Field(description="SHA256 hash of the document binary content")
    last_modified: float = Field(description="File modification timestamp")
    category: Optional[str] = Field(default=None, description="Course material category")
    lab: Optional[int] = Field(default=None, ge=1, le=14, description="Associated lab, when applicable")
    folder_path: Optional[str] = Field(default=None, description="Course-library folder path")
    material_id: Optional[str] = Field(default=None, description="Database-backed course material ID")
    title: Optional[str] = Field(default=None, description="Course material display title")
    description: Optional[str] = Field(default=None, description="Course material description")


class ExtractedSection(BaseModel):
    """An intermediate raw section or slide extracted from a source document."""

    title: str = Field(description="Section heading or slide title")
    content: str = Field(description="Raw text content of the section or slide")
    source_location: Optional[str] = Field(
        default=None,
        description="Reference location in the document (e.g. 'Section 1.2', 'Slide 14')",
    )
    sequence_index: int = Field(ge=0, description="Zero-based ordering index in the document")


class CourseKnowledgeChunk(BaseModel):
    """A coherent, typed chunk of course knowledge indexed for fast, deterministic retrieval."""

    id: str = Field(description="Unique deterministic identifier for the knowledge chunk")
    course_code: str = Field(default="26ECAC401", description="Course code (e.g. 26ECAC401)")
    course_name: str = Field(default="Agentic AI", description="Course title")
    chapter: Optional[int] = Field(default=None, ge=1, le=14, description="Academic chapter number, when known")
    section_topic: str = Field(description="Section or topic heading representing this chunk")
    content: str = Field(description="Coherent text content of the chunk")
    source_document: str = Field(description="Source document filename")
    category: Optional[str] = Field(default=None, description="Course material category")
    lab: Optional[int] = Field(default=None, ge=1, le=14, description="Associated lab, when applicable")
    folder_path: Optional[str] = Field(default=None, description="Course-library folder path")
    material_id: Optional[str] = Field(default=None, description="Database-backed course material ID")
    description: Optional[str] = Field(default=None, description="Course material description")
    source_location: Optional[str] = Field(
        default=None,
        description="Specific location in source (e.g. 'Section 1.4', 'Slide 5')",
    )
    tags: list[str] = Field(default_factory=list, description="Extracted domain keywords and topic tags")
    version: str = Field(default="1.0", description="Knowledge version")
    content_hash: str = Field(description="SHA256 hex digest of the chunk content")
    word_count: int = Field(ge=0, description="Total word count in chunk content")


class KnowledgeQuery(BaseModel):
    """Query parameters for retrieving relevant course knowledge chunks."""

    course_id: str = Field(default="26ECAC401", description="Target course ID")
    query: str = Field(min_length=1, description="Search query or question")
    chapter: Optional[int] = Field(default=None, ge=1, le=14, description="Optional chapter filter (1-14)")
    tags: Optional[list[str]] = Field(default=None, description="Optional list of tags to filter by")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of matches to return")
    min_score: float = Field(default=0.0, ge=0.0, description="Minimum relevance score threshold")


class CourseKnowledgeMatch(BaseModel):
    """A scored search match produced by the knowledge retrieval engine."""

    chunk_id: str = Field(description="Unique ID of the matched knowledge chunk")
    chapter: Optional[int] = Field(default=None, description="Chapter number of the match, when known")
    topic: str = Field(description="Topic/Section title of the match")
    matched_text: str = Field(description="Coherent content snippet answering or matching the query")
    source: str = Field(description="Human-readable provenance citation")
    source_document: str = Field(description="Name of the source document file")
    source_location: Optional[str] = Field(default=None, description="Document location identifier")
    source_chapter: Optional[int] = Field(default=None, description="Chapter number of the source document, when known")
    category: Optional[str] = Field(default=None, description="Course material category")
    lab: Optional[int] = Field(default=None, ge=1, le=14, description="Associated lab, when applicable")
    folder_path: Optional[str] = Field(default=None, description="Course-library folder path")
    material_id: Optional[str] = Field(default=None, description="Database-backed course material ID")
    tags: list[str] = Field(default_factory=list, description="Topic tags")
    score: float = Field(ge=0.0, description="Deterministic relevance score")
    version: str = Field(default="1.0", description="Document version")


class KnowledgeSearchResult(BaseModel):
    """Aggregated search result payload returned to callers and tools."""

    course_id: str = Field(description="Course ID searched")
    query: str = Field(description="Original query string")
    matches: list[CourseKnowledgeMatch] = Field(default_factory=list, description="Ranked matches")
    match_count: int = Field(ge=0, description="Total count of retrieved matches")
    source: str = Field(description="Repository or index provenance metadata")


class KnowledgeIndexStats(BaseModel):
    """Summary metrics of the indexed knowledge base."""

    total_documents: int = Field(ge=0, description="Total source documents discovered and parsed")
    total_chunks: int = Field(ge=0, description="Total discrete knowledge chunks indexed")
    chapters_indexed: list[int] = Field(default_factory=list, description="Distinct known chapters present in index")
    total_words: int = Field(ge=0, description="Total cumulative word count indexed")
