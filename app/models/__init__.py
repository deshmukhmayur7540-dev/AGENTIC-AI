"""Pydantic data models and contracts for CourseAgentAI."""

from app.models.common import APIEnvelope, ErrorDetail, AuditRecord, ScenarioDefinition
from app.models.lab1_models import (
    FacultyCourseRequest,
    MissingInfoCategory,
    ClarificationQuestion,
    ClarificationSubmission,
    WeeklyMaterial,
    AssignmentSpec,
    GradeBreakdownItem,
    CourseWorkspacePlan,
    RevisionRequest,
    StructuredDiffItem,
    PlanRevisionResponse,
    PlanHistoryRecord,
)

__all__ = [
    "APIEnvelope",
    "ErrorDetail",
    "AuditRecord",
    "ScenarioDefinition",
    "FacultyCourseRequest",
    "MissingInfoCategory",
    "ClarificationQuestion",
    "ClarificationSubmission",
    "WeeklyMaterial",
    "AssignmentSpec",
    "GradeBreakdownItem",
    "CourseWorkspacePlan",
    "RevisionRequest",
    "StructuredDiffItem",
    "PlanRevisionResponse",
    "PlanHistoryRecord",
]
