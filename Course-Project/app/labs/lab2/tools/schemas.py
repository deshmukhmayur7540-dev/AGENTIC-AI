"""Typed Pydantic schemas and data contracts for Lab 2 tools."""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categorization of agent tools."""
    READER = "reader"
    CALCULATOR = "calculator"
    POLICY = "policy"
    CHECKER = "checker"


class ToolDefinition(BaseModel):
    """Declarative metadata describing a registered tool and its JSON schemas."""
    name: str = Field(description="Unique tool identifier name")
    description: str = Field(description="Human-readable explanation of what the tool accomplishes")
    category: str = Field(description="Tool category (e.g. reader, calculator, policy, checker)")
    input_schema: dict[str, Any] = Field(description="JSON schema representing valid inputs")
    output_schema: dict[str, Any] = Field(description="JSON schema representing valid outputs")


# =========================================================================
# Common Course Queries
# =========================================================================
class CourseQueryInput(BaseModel):
    """Input payload for course lookup tools."""
    course_id: str = Field(min_length=1, description="Course ID code (e.g. 26ECAC401)")


# =========================================================================
# Tool 1: read_course_syllabus
# =========================================================================
class SyllabusModule(BaseModel):
    """A structured syllabus module or chapter."""
    chapter: Optional[int] = Field(default=None, description="Chapter or unit number")
    week: Optional[int] = Field(default=None, description="Week number if established")
    title: str = Field(min_length=1, description="Module title")
    topics: list[str] = Field(min_length=1, description="Subtopics covered")
    readings: list[str] = Field(default_factory=list, description="Required reading materials")


class SyllabusGradeWeight(BaseModel):
    """Assessment component with grading percentage."""
    category: str = Field(min_length=1, description="Category name")
    weight_percentage: float = Field(ge=0.0, le=100.0, description="Percentage of final grade")
    description: str = Field(default="", description="Assessment criteria")


class SyllabusOutput(BaseModel):
    """Structured syllabus output retrieved from course repository."""
    course_id: str = Field(description="Course identifier code")
    course_name: str = Field(description="Full course name")
    description: str = Field(description="Course overview and pedagogical goals")
    duration_weeks: Optional[int] = Field(default=None, description="Course duration in weeks if established in notes")
    target_audience: Optional[str] = Field(default=None, description="Target student audience")
    prerequisites: list[str] = Field(default_factory=list, description="Required prerequisites")
    modules: list[SyllabusModule] = Field(min_length=1, description="Module/chapter breakdowns")
    grading_weights: list[SyllabusGradeWeight] = Field(default_factory=list, description="Grading breakdown components")
    grading_policy_status: Optional[str] = Field(default="Unavailable in supplied course notes", description="Grading policy status")


# =========================================================================
# Tool 2: search_course_notes
# =========================================================================
class CourseNotesQueryInput(BaseModel):
    """Input parameters for searching course notes and materials."""
    course_id: str = Field(min_length=1, description="Course ID code (e.g. 26ECAC401)")
    query: str = Field(min_length=1, description="Keyword or phrase to search within lecture materials")


class CourseNoteMatch(BaseModel):
    """A single matching lecture note or material section."""
    chapter: Optional[int] = Field(default=None, description="Chapter number")
    week: Optional[int] = Field(default=None, description="Week number if available")
    topic: str = Field(description="Topic/Lecture heading")
    matched_text: str = Field(description="Content snippet matching the search query")
    source: str = Field(description="Originating document or lecture source")
    source_document: Optional[str] = Field(default=None, description="Source document name")
    source_chapter: Optional[int] = Field(default=None, description="Source chapter number")
    tags: list[str] = Field(default_factory=list, description="Associated topic tags")
    version: Optional[str] = Field(default="1.0", description="Version metadata")


class CourseNotesOutput(BaseModel):
    """Structured search results for course notes and lecture materials."""
    course_id: str = Field(description="Course ID queried")
    query: str = Field(description="Search term queried")
    matches: list[CourseNoteMatch] = Field(default_factory=list, description="List of matched note items")
    match_count: int = Field(ge=0, description="Total number of matches found")
    source: str = Field(description="Source repository metadata")


# =========================================================================
# Tool 3 & 4: get_assignment_spec & get_rubric_breakdown
# =========================================================================
class AssignmentQueryInput(BaseModel):
    """Input payload for retrieving assignment specifications and rubrics."""
    course_id: str = Field(min_length=1, description="Course ID code (e.g. 26ECAC401)")
    assignment_id: str = Field(min_length=1, description="Assignment identifier code (e.g. hw1, lab1, capstone)")


class AssignmentSpecOutput(BaseModel):
    """Structured assignment specification and requirements."""
    course_id: str = Field(description="Course identifier code")
    assignment_id: str = Field(description="Assignment identifier code")
    title: str = Field(description="Title of the assignment")
    due_week: Optional[int] = Field(default=None, description="Target due week if established")
    deliverables: list[str] = Field(default_factory=list, description="List of expected submission files or artifacts")
    max_points: Optional[float] = Field(default=None, description="Maximum achievable points if established")
    submission_requirements: str = Field(description="Submission method and guidelines")
    description: Optional[str] = Field(default=None, description="Detailed problem statement and instructions")
    source: str = Field(default="Course Assignment Repository", description="Data provenance source")


class RubricCriterion(BaseModel):
    """A single grading criterion in an assignment rubric."""
    criterion_name: str = Field(min_length=1, description="Name of the rubric category")
    points: float = Field(ge=0.0, description="Points allocated to this criterion")
    description: str = Field(default="", description="Evaluation guidelines")


class RubricBreakdownOutput(BaseModel):
    """Structured rubric breakdown retrieved for an assignment."""
    course_id: str = Field(description="Course identifier code")
    assignment_id: str = Field(description="Assignment identifier code")
    rubric_criteria: list[RubricCriterion] = Field(min_length=1, description="Grading criteria breakdown")
    total_points: float = Field(gt=0.0, description="Total points across all criteria")
    evidence: str = Field(default="Course Rubric Standards", description="Provenance evidence")


# =========================================================================
# Tool 5: get_course_config
# =========================================================================
class CourseConfigOutput(BaseModel):
    """Structured course parameters, policies, and lab configurations."""
    course_id: str = Field(description="Course identifier code")
    course_name: str = Field(description="Full official course title")
    duration_weeks: Optional[int] = Field(default=None, description="Total instructional weeks if established")
    enrollment_limit: Optional[int] = Field(default=None, description="Maximum student enrollment capacity if specified")
    ta_ratio_policy: Optional[str] = Field(default="Unavailable in lecture notes", description="Official TA allocation policy ratio description")
    students_per_ta: Optional[int] = Field(default=None, description="Target students per teaching assistant")
    prerequisites: list[str] = Field(default_factory=list, description="Required academic prerequisites")
    grading_policy: Optional[str] = Field(default="Unavailable in supplied lecture notes", description="Grade weighting and letter curve policy")
    lab_environment: Optional[str] = Field(default="Python 3.10+, LLM APIs, Agent Sandboxes", description="Development platform, tools, and runtime environment")
    hours_per_ta_per_week: Optional[float] = Field(default=None, description="Contracted hours per week per TA")
    source: str = Field(description="Official department policy registry source")


# =========================================================================
# Tool 6: get_ta_policy
# =========================================================================
class TAPolicyQueryInput(BaseModel):
    """Input payload for calculating teaching assistant staffing requirements."""
    course_id: str = Field(min_length=1, description="Course ID code (e.g. 26ECAC401)")
    enrollment_count: int = Field(gt=0, description="Projected or enrolled student count")


class TAPolicyOutput(BaseModel):
    """Deterministic teaching assistant calculation results and policy breakdown."""
    course_id: str = Field(description="Course identifier code")
    enrollment: int = Field(gt=0, description="Input student enrollment count")
    required_ta_count: int = Field(ge=1, description="Calculated number of required TAs")
    required_hours_per_week: float = Field(gt=0.0, description="Total weekly TA hours needed across staff")
    policy_ratio: str = Field(description="Department staffing policy ratio")
    formula_applied: str = Field(description="Transparent formula calculation trace")
    source: str = Field(description="Department policy reference source")


# =========================================================================
# Tool 7: calculate_grade_breakdown_total
# =========================================================================
class GradeWeightsInput(BaseModel):
    """Input payload of numeric grade percentage weights."""
    weights: list[float] = Field(min_length=1, description="List of grade component percentage weights")


class GradeWeightsTotalOutput(BaseModel):
    """Calculated total and validation status for grade weight distribution."""
    total_percentage: float = Field(description="Sum total of all weight components")
    is_valid: bool = Field(description="True if total percentage equals exactly 100%")
    delta_from_hundred: float = Field(description="Absolute deviation from 100%")


# =========================================================================
# Tool 8: validate_rubric_sum
# =========================================================================
class RubricSumInput(BaseModel):
    """Input payload for validating criteria point sums against expected total."""
    criteria_points: list[float] = Field(min_length=1, description="List of point values for rubric criteria")
    expected_max_points: float = Field(gt=0.0, description="Expected total maximum points for the assignment")


class RubricSumOutput(BaseModel):
    """Result of rubric points summation check."""
    sum_points: float = Field(description="Sum of all individual criterion points")
    expected_points: float = Field(description="Expected total points target")
    is_matching: bool = Field(description="True if calculated sum equals expected max points")
    difference: float = Field(description="Absolute difference between sum and expected points")


# =========================================================================
# Tool 9: compute_workload_hours
# =========================================================================
class WorkloadInput(BaseModel):
    """Input payload for grading workload time computation."""
    enrollment: int = Field(gt=0, description="Number of students in the course")
    assignments_count: int = Field(ge=0, description="Number of graded assignments")
    grading_minutes_per_submission: float = Field(gt=0.0, description="Estimated grading time per student submission in minutes")


class WorkloadOutput(BaseModel):
    """Computed grading workload time estimates."""
    enrollment: int = Field(description="Student count")
    assignments_count: int = Field(description="Assignment count")
    grading_minutes_per_submission: float = Field(description="Grading minutes per submission")
    total_grading_hours: float = Field(description="Total grading workload in hours across all assignments")
    hours_per_assignment: float = Field(description="Grading workload in hours per single assignment batch")
