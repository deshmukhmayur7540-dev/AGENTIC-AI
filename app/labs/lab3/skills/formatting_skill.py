"""Course Content Formatting Skill: Case-agnostic academic document structuring."""

import re
from datetime import datetime, timezone
from app.labs.lab3.base import BaseSkill
from app.models.lab3_models import (
    CourseContentFormattingInput,
    CourseContentFormattingOutput,
)


class CourseContentFormattingSkill(BaseSkill):
    """Transforms raw notes, syllabus text, or lab specs into standardized academic publication formats."""

    name = "course_content_formatting_skill"
    title = "Course Content Formatting & Export Skill"
    description = (
        "Parses raw course text and generates structured Markdown handouts, "
        "syllabus modules, assignment briefs, or faculty digests with automated table of contents."
    )
    category = "formatting"
    version = "1.0.0"
    input_model = CourseContentFormattingInput
    output_model = CourseContentFormattingOutput

    def _run(self, validated_input: CourseContentFormattingInput) -> CourseContentFormattingOutput:
        raw = validated_input.raw_content.strip()
        fmt = validated_input.target_format.lower()
        title = validated_input.title
        code = validated_input.course_code

        # Split content into meaningful sections
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        toc: list[str] = []
        body_parts: list[str] = []

        if fmt == "syllabus_section":
            body_parts.append(f"# {code}: {title}\n")
            body_parts.append(f"**Course:** {code}  \n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d')}  \n**Status:** Official Syllabus Extract\n")
            body_parts.append("## Module Overview\n")
            toc.append("Module Overview")
            
            for idx, line in enumerate(lines, 1):
                if line.startswith("#"):
                    sec_title = line.lstrip("#").strip()
                    toc.append(sec_title)
                    body_parts.append(f"\n{line}\n")
                elif ":" in line and len(line.split(":")[0]) < 35:
                    key, val = line.split(":", 1)
                    body_parts.append(f"- **{key.strip()}**: {val.strip()}")
                else:
                    body_parts.append(line)

        elif fmt == "assignment_brief":
            body_parts.append(f"# Assignment Specification: {title}\n")
            body_parts.append(f"**Course:** {code} | **Submission Policy:** GitHub Repository + Auditable Trace Log\n")
            body_parts.append("## 1. Problem Statement & Objectives\n")
            toc.append("Problem Statement & Objectives")
            
            in_deliverables = False
            for line in lines:
                if any(k in line.lower() for k in ["deliverable", "submission", "rubric", "grading"]):
                    if not in_deliverables:
                        body_parts.append("\n## 2. Required Deliverables & Evaluation Criteria\n")
                        toc.append("Required Deliverables & Evaluation Criteria")
                        in_deliverables = True
                body_parts.append(f"- {line}" if in_deliverables else line)

        else:  # Default: markdown_handout
            body_parts.append(f"# {title}\n")
            body_parts.append(f"> Academic Study Handout & Reference Guide — {code}\n")
            body_parts.append("## Summary & Key Concepts\n")
            toc.append("Summary & Key Concepts")

            for line in lines:
                if line.startswith(("-", "*", "•")):
                    body_parts.append(line)
                elif re.match(r"^\d+\.", line):
                    body_parts.append(line)
                    toc.append(line[:40])
                else:
                    body_parts.append(f"\n{line}\n")

        formatted_text = "\n".join(body_parts).strip()
        words = len(formatted_text.split())
        chars = len(formatted_text)

        return CourseContentFormattingOutput(
            title=title,
            format_type=fmt,
            formatted_content=formatted_text,
            word_count=words,
            character_count=chars,
            table_of_contents=toc or ["General Overview"],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
