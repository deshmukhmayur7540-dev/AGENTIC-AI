"""Pydantic schemas and contracts for student GitHub assignment submissions and faculty review."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, FiniteFloat, field_validator, model_validator


class SubmissionStatus(str, Enum):
    """Lifecycle statuses of a student assignment submission."""
    SUBMITTED = "SUBMITTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    LATE = "LATE"
    UNDER_REVIEW = "UNDER_REVIEW"
    DRAFT_GRADED = "DRAFT_GRADED"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    RETURNED_FOR_REVISION = "RETURNED_FOR_REVISION"
    # Legacy values are accepted at API boundaries and normalized before persistence.
    REVIEWED = "REVIEWED"
    RESUBMISSION_REQUESTED = "RESUBMISSION_REQUESTED"


class AssignmentOut(BaseModel):
    """Structured assignment view presented to students and faculty."""
    id: str
    course_id: str = "26ECAC401"
    title: str
    max_points: int = 100
    weight_percentage: float = 10.0
    due_week: int = 1
    description: Optional[str] = Field(default=None, description="Official assignment description")
    due_date: Optional[str] = Field(default=None, description="ISO timestamp of deadline (or None if unestablished)")
    submission_rules: Optional[str] = Field(default=None, description="Faculty-configured submission rules")
    late_policy: Optional[str] = Field(default=None, description="Faculty-configured late policy (or None if unestablished)")
    status: str = Field(default="OPEN", description="OPEN, CLOSED, or ARCHIVED")


class StudentOut(BaseModel):
    """Student profile representation."""
    id: str
    name: str
    email: str
    course_id: str = "26ECAC401"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GitHubSubmissionRequest(BaseModel):
    """Request payload to submit a GitHub repository for an assignment."""
    assignment_id: str = Field(description="Target assignment identifier (e.g. lab1, lab2)")
    student_id: str = Field(description="Student identifier submitting the assignment")
    repository_url: str = Field(description="HTTPS URL pointing to student's GitHub repository")
    notes: Optional[str] = Field(default=None, description="Optional notes or implementation remarks")


class SubmissionRecord(BaseModel):
    """Persistent submission entity representing a solution attempt."""
    id: str
    assignment_id: str
    student_id: str
    course_id: str = "26ECAC401"
    repository_url: str
    normalized_url: str
    repo_owner: str
    repo_name: str
    submission_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attempt_number: int = 1
    status: str = Field(default=SubmissionStatus.SUBMITTED.value)
    validation_status: str = Field(default="PASSED")
    validation_details: dict[str, Any] = Field(default_factory=dict)
    is_latest: bool = True
    review_status: str = Field(default="PENDING")
    review_feedback: Optional[str] = None
    review_score: Optional[float] = None
    rubric_scores: Optional[dict[str, float]] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    published_at: Optional[str] = None
    published_by: Optional[str] = None
    file_attachment_path: Optional[str] = None
    notes: Optional[str] = None
    audit_trace_id: Optional[str] = None

    @field_validator("validation_details", mode="before")
    @classmethod
    def decode_validation_details(cls, value: Any) -> Any:
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value

    @field_validator("rubric_scores", mode="before")
    @classmethod
    def decode_rubric_scores(cls, value: Any) -> Any:
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value


class SubmissionReviewRequest(BaseModel):
    """Payload submitted by faculty to review a submission."""
    review_status: Literal[
        "UNDER_REVIEW",
        "DRAFT_GRADED",
        "RETURNED_FOR_REVISION",
        "REVIEWED",
        "RESUBMISSION_REQUESTED",
    ] = Field(
        default="DRAFT_GRADED",
        description="UNDER_REVIEW, DRAFT_GRADED, or RETURNED_FOR_REVISION",
    )
    review_score: Optional[FiniteFloat] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Numerical score awarded (0-100)",
    )
    review_feedback: Optional[str] = Field(default=None, description="Faculty written qualitative feedback")
    rubric_scores: Optional[dict[str, float]] = Field(default=None, description="Per-criterion scoring breakdown")

    @model_validator(mode="after")
    def require_completed_review_details(self) -> "SubmissionReviewRequest":
        if self.review_status in ("REVIEWED", "DRAFT_GRADED"):
            if self.review_score is None:
                raise ValueError("A saved grade draft requires a numeric score from 0 to 100.")
            if not self.review_feedback or not self.review_feedback.strip():
                raise ValueError("A saved grade draft requires non-empty feedback.")
        if self.review_status in ("RETURNED_FOR_REVISION", "RESUBMISSION_REQUESTED"):
            if not self.review_feedback or not self.review_feedback.strip():
                raise ValueError("Returning work for revision requires constructive feedback.")
        return self


class SubmissionApprovalRequest(BaseModel):
    """Request to approve a saved grade draft before publication."""
    pass


class SubmissionPublicationRequest(BaseModel):
    """Request to publish an approved grade."""
    pass
