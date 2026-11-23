"""Tool implementations for retrieving course configurations and computing TA policies."""

from typing import Optional

from app.data.repository import CourseRepository, course_repo
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import (
    CourseConfigOutput,
    CourseQueryInput,
    TAPolicyOutput,
    TAPolicyQueryInput,
    ToolCategory,
)


class GetCourseConfigTool(BaseTool):
    """Tool that retrieves course configuration parameters and lab policies."""

    name = "get_course_config"
    description = (
        "Retrieve course configuration parameters including duration, enrollment limits, "
        "TA ratio policy, prerequisites, grading policy, and lab environment."
    )
    category = ToolCategory.POLICY.value
    input_model = CourseQueryInput
    output_model = CourseConfigOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: CourseQueryInput) -> CourseConfigOutput:
        """Fetch course configuration from repository and validate output schema."""
        raw_config = self._repo.get_canonical_config(typed_input.course_id)
        if raw_config is None:
            raise ValueError(
                f"Course configuration for '{typed_input.course_id}' was not found in the repository."
            )
        return CourseConfigOutput.model_validate(raw_config)


class GetTAPolicyTool(BaseTool):
    """Tool that calculates required teaching assistant staffing based on policy ratios."""

    name = "get_ta_policy"
    description = (
        "Calculate deterministic teaching assistant staffing requirements, weekly hours, "
        "and ratio policy for a course given an enrollment count."
    )
    category = ToolCategory.POLICY.value
    input_model = TAPolicyQueryInput
    output_model = TAPolicyOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: TAPolicyQueryInput) -> TAPolicyOutput:
        """Calculate TA staffing policy from repository configuration and validate output schema."""
        raw_policy = self._repo.get_canonical_ta_policy(
            typed_input.course_id,
            typed_input.enrollment_count,
        )
        if raw_policy is None:
            raise ValueError(
                f"TA policy configuration for course '{typed_input.course_id}' was not found in the repository."
            )
        return TAPolicyOutput.model_validate(raw_policy)
