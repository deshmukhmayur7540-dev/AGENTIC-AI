"""Pydantic schemas and metadata models for Lab 3 Reusable Skills."""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    """Metadata describing a reusable skill registered in the Skill Registry."""
    name: str = Field(description="Unique identifier of the skill")
    title: str = Field(description="Human-readable title")
    description: str = Field(description="What this skill accomplishes")
    category: str = Field(description="Skill category (planning, research, formatting)")
    version: str = Field(default="1.0.0", description="SemVer skill version")
    input_schema: dict[str, Any] = Field(description="JSON schema of input parameters")
    output_schema: dict[str, Any] = Field(description="JSON schema of output data")


class SkillExecutionRequest(BaseModel):
    """API request model for executing a skill."""
    skill_name: str = Field(description="Name of skill to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input parameters")


class SkillExecutionRecord(BaseModel):
    """Auditable record produced whenever a skill executes."""
    execution_id: str
    skill_name: str
    status: str = Field(description="SUCCESS, VALIDATION_ERROR, or EXECUTION_ERROR")
    input_parameters: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    duration_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None


# -----------------------------------------------------------------------------
# Skill 1: Course Planning Skill Schemas
# -----------------------------------------------------------------------------
class CoursePlanningInput(BaseModel):
    """Input parameters for CoursePlanningSkill."""
    course_code: str = Field(default="26ECAC401", description="Academic course code")
    course_name: str = Field(default="Agentic AI", description="Course title")
    target_weeks: int = Field(default=12, ge=4, le=24, description="Course length in weeks")
    focus_chapters: list[int] = Field(default=[1, 2, 3, 4], description="Chapters to cover")
    pedagogical_goals: list[str] = Field(default_factory=list, description="Target competencies")


class WeeklyScheduleItem(BaseModel):
    """Weekly breakdown item in course plan."""
    week_number: int
    chapter_mapped: int
    module_title: str
    core_topics: list[str]
    lab_assignment: Optional[str] = None


class CoursePlanningOutput(BaseModel):
    """Output structure synthesized by CoursePlanningSkill."""
    course_code: str
    course_name: str
    total_weeks: int
    schedule: list[WeeklyScheduleItem]
    milestones: list[str]
    provenance_source: str


# -----------------------------------------------------------------------------
# Skill 2: Research Summary Skill Schemas
# -----------------------------------------------------------------------------
class ResearchSummaryInput(BaseModel):
    """Input parameters for ResearchSummarySkill."""
    topic: str = Field(description="Research subject or concept to synthesize")
    course_code: str = Field(default="26ECAC401", description="Associated course code")
    target_chapter: Optional[int] = Field(default=None, ge=1, le=4, description="Target chapter filter")
    depth: str = Field(default="standard", description="standard, deep_dive, or comparative")


class ResearchSummaryOutput(BaseModel):
    """Output structure synthesized by ResearchSummarySkill."""
    topic: str
    chapter_referenced: Optional[int] = None
    executive_summary: str
    key_architectural_principles: list[str]
    cited_evidence: list[dict[str, Any]]
    suggested_lab_activity: str
    provenance: str


# -----------------------------------------------------------------------------
# Skill 3: Course Content Formatting Skill Schemas
# -----------------------------------------------------------------------------
class CourseContentFormattingInput(BaseModel):
    """Input parameters for CourseContentFormattingSkill."""
    title: str = Field(description="Document or assignment title")
    course_code: str = Field(default="26ECAC401", description="Associated course code")
    raw_content: str = Field(description="Raw text or syllabus material to format")
    target_format: str = Field(
        default="markdown_handout",
        description="markdown_handout, syllabus_section, assignment_brief, or faculty_digest",
    )


class CourseContentFormattingOutput(BaseModel):
    """Output structure synthesized by CourseContentFormattingSkill."""
    title: str
    format_type: str
    formatted_content: str
    word_count: int
    character_count: int
    table_of_contents: list[str]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
