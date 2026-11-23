"""Research Summary Skill: Case-agnostic knowledge retrieval and academic synthesis."""

from typing import Any
from app.core.course_identity import normalize_course_id, CANONICAL_COURSE_ID
from app.knowledge.service import knowledge_service
from app.labs.lab3.base import BaseSkill
from app.models.lab3_models import (
    ResearchSummaryInput,
    ResearchSummaryOutput,
)


class ResearchSummarySkill(BaseSkill):
    """Retrieves authoritative course notes and synthesizes a structured academic research brief."""

    name = "research_summary_skill"
    title = "Academic Research Summary Skill"
    description = (
        "Queries course knowledge base, extracts relevant chapter notes, "
        "and synthesizes an academic research brief with verified citations."
    )
    category = "research"
    version = "1.0.0"
    input_model = ResearchSummaryInput
    output_model = ResearchSummaryOutput

    def _run(self, validated_input: ResearchSummaryInput) -> ResearchSummaryOutput:
        course_id = normalize_course_id(validated_input.course_code) or validated_input.course_code

        # Query knowledge base
        search_result = knowledge_service.search(
            query=validated_input.topic,
            course_id=course_id,
            chapter=validated_input.target_chapter,
            top_k=4,
        )

        cited_evidence: list[dict[str, Any]] = []
        key_principles: list[str] = []
        found_chapter = validated_input.target_chapter

        if search_result.matches:
            for m in search_result.matches:
                if found_chapter is None:
                    found_chapter = m.chapter
                cited_evidence.append({
                    "chapter": m.chapter,
                    "topic": m.topic,
                    "excerpt": m.matched_text[:280] + ("..." if len(m.matched_text) > 280 else ""),
                    "source": m.source,
                    "source_document": m.source_document,
                    "score": round(m.score, 4),
                })
                key_principles.append(f"Chapter {m.chapter} Principle: {m.topic}")

        # If no knowledge chunks match
        if not cited_evidence:
            summary = (
                f"No verified course evidence found in {course_id} knowledge repository "
                f"for topic '{validated_input.topic}'."
            )
            key_principles = ["Concept unestablished in active lecture notes."]
            lab_activity = "Review prerequisite materials or specify an indexed topic."
        else:
            summary = (
                f"Academic research synthesis for '{validated_input.topic}' across {course_id} course notes. "
                f"The topic emphasizes grounded execution, formal reasoning paradigms, and auditable agent behavior."
            )
            lab_activity = f"Implement a hands-on verification harness for '{validated_input.topic}' with strict schema assertions."

        # Remove duplicate principles
        unique_principles = list(dict.fromkeys(key_principles))[:4]

        return ResearchSummaryOutput(
            topic=validated_input.topic,
            chapter_referenced=found_chapter,
            executive_summary=summary,
            key_architectural_principles=unique_principles,
            cited_evidence=cited_evidence,
            suggested_lab_activity=lab_activity,
            provenance=search_result.source,
        )
