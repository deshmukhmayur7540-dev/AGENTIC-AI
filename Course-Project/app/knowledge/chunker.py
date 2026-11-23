"""Coherent semantic and section-aware chunker for course knowledge documents."""

import hashlib
import re
from typing import Optional

from app.knowledge.models import CourseKnowledgeChunk, DiscoveredDocument, ExtractedSection

# Canonical domain keywords for tag extraction
AGENTIC_AI_TAG_MAPPINGS = {
    "react": ["react", "reasoning and acting"],
    "chain-of-thought": ["chain of thought", "cot"],
    "tree-of-thoughts": ["tree of thoughts", "tot"],
    "plan-act-observe-revise": ["plan-act-observe-revise", "plan act observe revise", "autonomous loop"],
    "plan-and-execute": ["plan-and-execute", "plan and execute"],
    "autonomy": ["autonomy", "autonomous agent"],
    "perception": ["perception", "perceive", "sensory"],
    "reasoning": ["reasoning", "cognitive", "deliberation"],
    "action": ["action execution", "action space", "actuate"],
    "langchain": ["langchain"],
    "langgraph": ["langgraph", "state graph", "cyclic"],
    "tools": ["tool", "function calling", "tool integration"],
    "sandboxing": ["sandbox", "code execution", "docker", "isolated"],
    "skills": ["skills", "modular skills", "skill library"],
    "memory": ["memory", "short-term memory", "long-term memory", "session state"],
    "rag": ["rag", "retrieval-augmented", "vector database", "embeddings"],
    "mcp": ["mcp", "model context protocol"],
    "multi-agent": ["multi-agent", "multi agent", "agents collaboration"],
    "orchestration": ["orchestration", "coordination", "hierarchical", "consensus"],
    "safety": ["safety", "governance", "guardrails", "jailbreak"],
    "alignment": ["alignment", "rlhf", "rlaif", "dpo"],
}


class CourseDocumentChunker:
    """Transforms raw extracted sections into coherent, typed knowledge chunks."""

    def __init__(self, target_chunk_words: int = 350, max_chunk_words: int = 500, overlap_words: int = 40) -> None:
        self.target_chunk_words = target_chunk_words
        self.max_chunk_words = max_chunk_words
        self.overlap_words = overlap_words

    def chunk_document(
        self,
        doc: DiscoveredDocument,
        sections: list[ExtractedSection],
    ) -> list[CourseKnowledgeChunk]:
        """Split extracted sections of a document into coherent knowledge chunks."""
        chunks: list[CourseKnowledgeChunk] = []
        chunk_counter = 0

        for section in sections:
            paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
            if not paragraphs:
                continue

            section_word_count = sum(len(p.split()) for p in paragraphs)

            # If section is within comfortable bounds, produce a single coherent chunk
            if section_word_count <= self.max_chunk_words:
                content = "\n\n".join(paragraphs).strip()
                if len(content) <= 10:
                    continue
                chunk_id = self._generate_chunk_id(doc.chapter or 0, doc.material_id or doc.source_relative_path or doc.source_filename, chunk_counter)
                tags = self._extract_tags(content, doc.chapter, section.title, doc)
                chunks.append(
                    CourseKnowledgeChunk(
                        id=chunk_id,
                        course_code=doc.course_code,
                        course_name=doc.course_name,
                        chapter=doc.chapter,
                        section_topic=section.title,
                        content=content,
                        source_document=doc.source_relative_path or doc.source_filename,
                        category=doc.category,
                        lab=doc.lab,
                        folder_path=doc.folder_path,
                        material_id=doc.material_id,
                        description=doc.description,
                        source_location=section.source_location,
                        tags=tags,
                        version="1.0",
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        word_count=section_word_count,
                    )
                )
                chunk_counter += 1
            else:
                # Sub-chunk longer sections with paragraph continuity
                sub_chunks = self._split_paragraphs_coherently(paragraphs)
                for part_idx, sub_content in enumerate(sub_chunks):
                    sub_content = sub_content.strip()
                    if len(sub_content) <= 10:
                        continue
                    sub_words = len(sub_content.split())
                    part_title = f"{section.title} (Part {part_idx + 1})" if len(sub_chunks) > 1 else section.title
                    chunk_id = self._generate_chunk_id(doc.chapter or 0, doc.material_id or doc.source_relative_path or doc.source_filename, chunk_counter)
                    tags = self._extract_tags(sub_content, doc.chapter, section.title, doc)
                    chunks.append(
                        CourseKnowledgeChunk(
                            id=chunk_id,
                            course_code=doc.course_code,
                            course_name=doc.course_name,
                            chapter=doc.chapter,
                            section_topic=part_title,
                            content=sub_content,
                            source_document=doc.source_relative_path or doc.source_filename,
                            category=doc.category,
                            lab=doc.lab,
                            folder_path=doc.folder_path,
                            material_id=doc.material_id,
                            description=doc.description,
                            source_location=section.source_location,
                            tags=tags,
                            version="1.0",
                            content_hash=hashlib.sha256(sub_content.encode("utf-8")).hexdigest(),
                            word_count=sub_words,
                        )
                    )
                    chunk_counter += 1

        return chunks

    def _split_paragraphs_coherently(self, paragraphs: list[str]) -> list[str]:
        """Group paragraphs into chunks of ~target_chunk_words preserving sentence structure."""
        grouped: list[str] = []
        current_group: list[str] = []
        current_words = 0

        for p in paragraphs:
            p_words = len(p.split())
            if current_words + p_words > self.target_chunk_words and current_group:
                grouped.append("\n\n".join(current_group))
                # Retain last paragraph if reasonably short to provide overlap context
                if len(current_group[-1].split()) <= self.overlap_words * 2:
                    current_group = [current_group[-1], p]
                    current_words = len(current_group[0].split()) + p_words
                else:
                    current_group = [p]
                    current_words = p_words
            else:
                current_group.append(p)
                current_words += p_words

        if current_group:
            grouped.append("\n\n".join(current_group))

        return grouped

    def _extract_tags(
        self,
        content: str,
        chapter: Optional[int],
        section_title: str,
        doc: DiscoveredDocument,
    ) -> list[str]:
        """Extract domain tags from content, section heading, and chapter metadata."""
        tags = [f"chapter-{chapter}"] if chapter is not None else []
        if doc.category:
            category_tag = re.sub(r"[^a-z0-9]+", "-", doc.category.lower()).strip("-")
            tags.append(f"category-{category_tag}")
        if doc.lab is not None:
            tags.append(f"lab-{doc.lab}")
        search_text = f"{section_title}\n{content}".lower()

        for tag, keywords in AGENTIC_AI_TAG_MAPPINGS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", search_text) for kw in keywords):
                if tag not in tags:
                    tags.append(tag)

        return tags

    @staticmethod
    def _generate_chunk_id(chapter: int, filename: str, index: int) -> str:
        """Deterministic unique chunk ID format: chk_ch{chapter}_{file_stem}_{hash}_{index:03d}."""
        f_hash = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:6]
        stem = re.sub(r"[^a-zA-Z0-9_]", "_", filename.replace(".", "_"))[:30].strip("_").lower()
        return f"chk_ch{chapter}_{stem}_{f_hash}_{index:03d}"
